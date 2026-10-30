"""Disposable single-server collection qualification; never uses an existing cluster."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql

from parison import postgres_collection as collection
from parison.core import ParisonError
from parison.source_collection import verify_postgres_collection

TABLES = ("customers", "orders", "order_lines", "payments", "refunds", "ledger")


def worker(plan, output):
    import resource

    started = time.monotonic()
    observed = {
        "source_execute_statements": 0,
        "source_count_scans": 0,
        "source_null_marker_checks": 0,
        "source_copy_scans": 0,
        "peak_staged_file_content_bytes": 0,
        "peak_staged_allocated_bytes": 0,
    }
    real_execute, real_copy = psycopg.Cursor.execute, psycopg.Cursor.copy

    def execute(cursor, query, *args, **kwargs):
        observed["source_execute_statements"] += 1
        text = str(query).strip().upper()
        observed["source_count_scans"] += text.startswith("SELECT COUNT(*)")
        observed["source_null_marker_checks"] += text.startswith("SELECT EXISTS(")
        return real_execute(cursor, query, *args, **kwargs)

    def copy_rows(cursor, query, *args, **kwargs):
        observed["source_copy_scans"] += 1
        return real_copy(cursor, query, *args, **kwargs)

    def staged_verify(path):
        members = [path, *path.rglob("*")]
        observed["peak_staged_file_content_bytes"] = sum(p.stat().st_size for p in members if p.is_file())
        observed["peak_staged_allocated_bytes"] = sum(p.stat().st_blocks * 512 for p in members)
        return verify_postgres_collection(path)

    with (
        patch.object(psycopg.Cursor, "execute", execute),
        patch.object(psycopg.Cursor, "copy", copy_rows),
        patch.object(collection, "verify_postgres_collection", staged_verify),
    ):
        summary = collection.export_postgres_collection(plan, output)
    verified = verify_postgres_collection(output)
    assert summary == verified
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        rss *= 1024
    result = {
        "elapsed_seconds": time.monotonic() - started,
        "peak_process_tree_rss_bytes": rss,
        "process_tree_scope": "worker has no child processes; database server excluded",
        "published_content_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "rows": summary["rows"],
        "csv_bytes": summary["bytes"],
        "table_count": summary["tables"],
        **observed,
    }
    print(json.dumps(result, sort_keys=True))


def qualify(binary, report, measure):
    results = {
        "server_binary": subprocess.check_output([str(binary / "postgres"), "--version"], text=True).strip(),
        "python": platform.python_version(),
        "psycopg": psycopg.__version__,
        "platform": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "gates": [],
        "measurements": [],
    }
    old_env = {name: os.environ.get(name) for name in ("PGHOST", "PGPORT", "PGUSER", "PGDATABASE")}
    with tempfile.TemporaryDirectory(prefix="parison-collection-live-") as temporary:
        root = Path(temporary)
        data = root / "data"
        sock = root / "socket"
        sock.mkdir()
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        subprocess.run(
            [
                str(binary / "initdb"),
                "-D",
                str(data),
                "-U",
                "parison_admin",
                "--auth=trust",
                "--encoding=UTF8",
                "--no-locale",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                str(binary / "pg_ctl"),
                "-D",
                str(data),
                "-l",
                str(root / "server.log"),
                "-o",
                f"-k {sock} -p {port} -h ''",
                "-w",
                "start",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        try:
            os.environ.update(PGHOST=str(sock), PGPORT=str(port), PGUSER="collection_reader", PGDATABASE="postgres")
            with psycopg.connect(
                host=str(sock), port=port, user="parison_admin", dbname="postgres", autocommit=True
            ) as admin:
                results["server_version_num"] = admin.execute("SHOW server_version_num").fetchone()[0]
                results["encoding"] = admin.execute("SHOW server_encoding").fetchone()[0]
                results["collation"] = admin.execute(
                    "SELECT datcollate FROM pg_catalog.pg_database WHERE datname=current_database()"
                ).fetchone()[0]
                admin.execute("CREATE ROLE collection_reader LOGIN")
                admin.execute("CREATE SCHEMA gate")
                admin.execute("GRANT USAGE ON SCHEMA gate TO collection_reader")
                for name in TABLES:
                    admin.execute(
                        sql.SQL("CREATE TABLE gate.{} (id integer PRIMARY KEY, note text)").format(sql.Identifier(name))
                    )
                    admin.execute(sql.SQL("INSERT INTO gate.{} VALUES (1,'initial')").format(sql.Identifier(name)))
                    admin.execute(sql.SQL("GRANT SELECT ON gate.{} TO collection_reader").format(sql.Identifier(name)))
                plan = {
                    "collection_plan_version": 1,
                    "source_id": "synthetic-collection",
                    "tables": {
                        name: {"schema": "gate", "table": name, "columns": ["id", "note"], "primary_key": ["id"]}
                        for name in TABLES
                    },
                    "limits": {
                        "max_rows": 300000,
                        "max_output_bytes": 1073741824,
                        "statement_timeout_ms": 300000,
                        "wall_timeout_ms": 600000,
                    },
                }
                plan_file = root / "plan.json"

                def save(value=plan):
                    plan_file.write_text(json.dumps(value))

                save()

                def export(label):
                    return collection.export_postgres_collection(plan_file, root / label)

                def fails(label, exception=ParisonError):
                    try:
                        export(label)
                    except exception:
                        pass
                    else:
                        raise AssertionError(f"gate accepted {label}")
                    assert not (root / label).exists()
                    assert not list(root.glob(f".{label}-*"))
                    results["gates"].append(label)

                original = collection._acquire_table
                calls = [0]

                def concurrent(cursor, declared, stage, *args):
                    item = original(cursor, declared, stage, *args)
                    calls[0] += 1
                    if calls[0] == 1:
                        admin.execute("SET lock_timeout TO '100ms'")
                        try:
                            admin.execute("ALTER TABLE gate.refunds RENAME TO changed")
                        except psycopg.errors.LockNotAvailable:
                            pass
                        else:
                            raise AssertionError("missing pre-snapshot lock")
                        for name in TABLES:
                            admin.execute(sql.SQL("INSERT INTO gate.{} VALUES (2,'late')").format(sql.Identifier(name)))
                    return item

                with patch.object(collection, "_acquire_table", side_effect=concurrent):
                    summary = export("snapshot")
                assert summary["rows"] == 6
                assert all(b"late" not in p.read_bytes() for p in (root / "snapshot/tables").glob("*/data.csv"))
                assert verify_postgres_collection(root / "snapshot") == summary
                results["gates"].append("shared-snapshot-ddl-lock")
                try:
                    export("snapshot")
                except ParisonError:
                    results["gates"].append("no-overwrite")
                else:
                    raise AssertionError("overwrite")
                admin.execute("ALTER TABLE gate.refunds ENABLE ROW LEVEL SECURITY")
                with patch.object(collection, "_acquire_table", wraps=original) as copied:
                    fails("late-rls")
                    assert copied.call_count == 0
                admin.execute("ALTER TABLE gate.refunds DISABLE ROW LEVEL SECURITY")
                admin.execute("GRANT INSERT ON gate.refunds TO collection_reader")
                fails("writer-role")
                admin.execute("REVOKE INSERT ON gate.refunds FROM collection_reader")
                admin.execute("GRANT parison_admin TO collection_reader")
                fails("inherited-owner")
                admin.execute("REVOKE parison_admin FROM collection_reader")
                for roleflag in ("SUPERUSER", "BYPASSRLS", "CREATEROLE", "CREATEDB", "REPLICATION"):
                    admin.execute("ALTER ROLE collection_reader " + roleflag)
                    fails("role-" + roleflag.lower())
                    admin.execute("ALTER ROLE collection_reader NO" + roleflag)
                if int(results["server_version_num"]) >= 170000:
                    admin.execute("GRANT MAINTAIN ON gate.refunds TO collection_reader")
                    fails("maintain-privilege")
                    admin.execute("REVOKE MAINTAIN ON gate.refunds FROM collection_reader")
                for changes, label in (({"max_rows": 11}, "late-row-cap"), ({"max_output_bytes": 70}, "late-byte-cap")):
                    save({**plan, "limits": {**plan["limits"], **changes}})
                    fails(label)
                save()

                def interrupted(cursor, declared, stage, *args):
                    if declared["table"] == "refunds":
                        (stage / "data.csv").write_bytes(b"private")
                        raise KeyboardInterrupt
                    return original(cursor, declared, stage, *args)

                with patch.object(collection, "_acquire_table", side_effect=interrupted):
                    fails("late-interrupt", KeyboardInterrupt)
                with patch.object(collection, "verify_postgres_collection", side_effect=ParisonError("injected")):
                    fails("verify-failure")
                with patch.object(collection, "rename_no_replace", side_effect=OSError("injected")):
                    fails("rename-failure")
                real_execute = psycopg.Cursor.execute

                def commit_failure(cursor, query, *args, **kwargs):
                    if query == "COMMIT":
                        raise psycopg.OperationalError("injected")
                    return real_execute(cursor, query, *args, **kwargs)

                with patch.object(psycopg.Cursor, "execute", commit_failure):
                    fails("commit-failure")
                admin.execute("BEGIN")
                admin.execute("LOCK TABLE gate.refunds IN ACCESS EXCLUSIVE MODE")
                save({**plan, "limits": {**plan["limits"], "statement_timeout_ms": 100, "wall_timeout_ms": 1000}})
                fails("lock-timeout")
                admin.execute("ROLLBACK")
                save()
                qualify_original = collection._qualify_table

                def delayed(cursor, declared):
                    cursor.execute("SELECT pg_sleep(0.2)")
                    return qualify_original(cursor, declared)

                for label, limits in (
                    ("statement-timeout", {"statement_timeout_ms": 10}),
                    ("wall-timeout", {"wall_timeout_ms": 50}),
                ):
                    save({**plan, "limits": {**plan["limits"], **limits}})
                    with patch.object(collection, "_qualify_table", side_effect=delayed):
                        fails(label)
                save()
                admin.execute("CREATE TABLE gate.descendant (extra text) INHERITS (gate.orders)")
                fails("inheritance-parent")
                admin.execute("DROP TABLE gate.descendant")
                for ddl, label in (
                    ("CREATE VIEW gate.unsupported AS SELECT * FROM gate.orders", "view"),
                    ("CREATE UNLOGGED TABLE gate.unsupported (id int PRIMARY KEY, note text)", "unlogged"),
                    (
                        "CREATE TABLE gate.unsupported (id int, note text, PRIMARY KEY(id)) PARTITION BY RANGE(id)",
                        "partitioned",
                    ),
                ):
                    admin.execute(ddl)
                    save(
                        {
                            **plan,
                            "tables": {
                                "unsupported": {
                                    "schema": "gate",
                                    "table": "unsupported",
                                    "columns": ["id", "note"],
                                    "primary_key": ["id"],
                                }
                            },
                        }
                    )
                    fails(label)
                    admin.execute("DROP VIEW gate.unsupported" if label == "view" else "DROP TABLE gate.unsupported")
                save()
                admin.execute("CREATE DOMAIN gate.text AS pg_catalog.text")
                admin.execute("ALTER TABLE gate.refunds ALTER note TYPE gate.text")
                fails("custom-type-name")
                admin.execute("ALTER TABLE gate.refunds ALTER note TYPE pg_catalog.text")
                admin.execute("DROP DOMAIN gate.text")
                admin.execute("TRUNCATE gate.refunds")
                assert export("empty-last")["rows"] == 10
                results["gates"].append("empty-last")
                # Cover every supported scalar representation, quoted UTF-8 names and composite keys.
                typed = 'Quoted " 名'
                admin.execute(
                    sql.SQL(
                        "CREATE TABLE gate.{} (a int2, b int4, c int8, d numeric, e bool, f text, g varchar, h uuid, i date, j timestamp, k timestamptz, PRIMARY KEY(a,b))"
                    ).format(sql.Identifier(typed))
                )
                admin.execute(
                    sql.SQL(
                        "INSERT INTO gate.{} VALUES(1,2,3,4.50,true,'héllo','quoted', '00000000-0000-0000-0000-000000000001','2026-01-01','2026-01-01 01:00:00','2026-01-01 01:00:00+00')"
                    ).format(sql.Identifier(typed))
                )
                admin.execute(sql.SQL("GRANT SELECT ON gate.{} TO collection_reader").format(sql.Identifier(typed)))
                typed_plan = {
                    **plan,
                    "tables": {
                        "typed": {
                            "schema": "gate",
                            "table": typed,
                            "columns": list("abcdefghijk"),
                            "primary_key": ["a", "b"],
                        }
                    },
                }
                save(typed_plan)
                assert export("all-types")["rows"] == 1
                results["gates"].append("all-types-quoted-composite-key")
                admin.execute(sql.SQL("UPDATE gate.{} SET f=%s").format(sql.Identifier(typed)), (r"\N",))
                fails("reserved-null-marker")
                save()
                sixteen = {}
                for index in range(16):
                    name = f"t{index}"
                    admin.execute(
                        sql.SQL("CREATE TABLE gate.{} (id int PRIMARY KEY, note text)").format(sql.Identifier(name))
                    )
                    admin.execute(sql.SQL("GRANT SELECT ON gate.{} TO collection_reader").format(sql.Identifier(name)))
                    sixteen[name] = {"schema": "gate", "table": name, "columns": ["id", "note"], "primary_key": ["id"]}
                save({**plan, "tables": sixteen})
                assert export("sixteen")["tables"] == 16
                results["gates"].append("sixteen-table-probe")
                save()
                if measure:
                    for total in (100000, 250000):
                        for index, name in enumerate(TABLES):
                            count = total // 6 + (index < total % 6)
                            admin.execute(sql.SQL("TRUNCATE gate.{}").format(sql.Identifier(name)))
                            admin.execute(
                                sql.SQL("INSERT INTO gate.{} SELECT g,'value-'||g FROM generate_series(1,%s) g").format(
                                    sql.Identifier(name)
                                ),
                                (count,),
                            )
                        for repeat in range(3):
                            output = root / f"measure-{total}-{repeat}"
                            command = [
                                sys.executable,
                                str(Path(__file__).resolve()),
                                "--worker-plan",
                                str(plan_file),
                                "--worker-output",
                                str(output),
                            ]
                            value = json.loads(subprocess.check_output(command, text=True))
                            assert value["rows"] == total
                            value.update(total_rows=total, repeat=repeat + 1)
                            results["measurements"].append(value)
                            shutil.rmtree(output)
            subprocess.run(
                [str(binary / "pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            assert verify_postgres_collection(root / "snapshot")["rows"] == 6
            results["gates"].append("offline-after-server-shutdown")
        finally:
            subprocess.run(
                [str(binary / "pg_ctl"), "-D", str(data), "-m", "immediate", "-w", "stop"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for name, value in old_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
    report.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "server_version_num": results["server_version_num"],
                "gates": len(results["gates"]),
                "measurements": len(results["measurements"]),
                "report": str(report),
            }
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--measure", action="store_true")
    parser.add_argument("--worker-plan", type=Path)
    parser.add_argument("--worker-output", type=Path)
    args = parser.parse_args()
    if args.worker_plan:
        worker(args.worker_plan, args.worker_output)
    else:
        qualify(args.bin, args.report, args.measure)


if __name__ == "__main__":
    main()
