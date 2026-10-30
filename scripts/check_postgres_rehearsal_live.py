"""Explicit disposable PostgreSQL 16→18 gate; never connects to an existing cluster."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from parison.analysis import _canonical
from parison.core import explain_recipe
from parison.postgres_rehearsal import run, verify
from parison.reconciliation import normalize_reconciliation

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "postgres_rehearsal"


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def worker(root: Path, rows: int, label: str):
    import resource

    from parison.postgres_pair import export_postgres_pair

    started = time.monotonic()
    output = root / label
    output.mkdir()
    plan = json.loads((root / "plan.json").read_text())
    source_queries = []
    for side, port in (("baseline", "55416"), ("candidate", "55418")):
        os.environ.update(PGHOST=str(root / "socket"), PGPORT=port, PGUSER="rehearsal_reader", PGDATABASE="postgres")
        acquisition = root / f"{side}-acquire.json"
        export_postgres_pair(acquisition, output / side)
        receipt = json.loads((output / side / "receipt.json").read_text())
        children = {
            slot: json.loads((output / side / "tables" / slot / "receipt.json").read_text())
            for slot in ("orders", "order_lines")
        }
        plan["pairs"][side] = {
            "manifest_sha256": hashlib.sha256((output / side / "manifest.json").read_bytes()).hexdigest(),
            "pair_plan_sha256": hashlib.sha256(_canonical(json.loads(acquisition.read_text()))).hexdigest(),
            "snapshot": receipt["transaction"]["snapshot"],
            "expected_rows": {"orders": rows // 2, "order_lines": rows // 2},
            "types": {"orders": ["int4", "numeric", "text", "timestamptz"], "order_lines": ["int4", "int4", "numeric"]},
        }
        source_queries.append(
            {
                "side": side,
                "rows": receipt["observed"]["rows"],
                "bytes": receipt["observed"]["bytes"],
                "elapsed_ms": receipt["observed"]["elapsed_ms"],
                "server_version_num": receipt["source"]["server_version_num"],
                "table_count_scans": 2,
                "table_copy_scans": 2,
            }
        )
        assert all(child["source"]["role_is_owner"] is False for child in children.values())
    write(output / "plan.json", plan)
    kwargs = {
        "baseline": output / "baseline",
        "candidate": output / "candidate",
        "orders_recipe": root / "orders.json",
        "lines_recipe": root / "order_lines.json",
        "reconciliation": root / "relationships.json",
        "claim": root / "claim.txt",
    }
    summary = run(output / "plan.json", output=output / "result", **kwargs)
    assert verify(output / "result", **kwargs) == summary
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "label": label,
        "rows_per_side": rows,
        "elapsed_seconds": time.monotonic() - started,
        "worker_peak_rss_bytes": usage if sys.platform == "darwin" else usage * 1024,
        "retained_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "source_load": source_queries,
        "summary": summary,
    }


def prepare(root: Path, rows: int):
    for name in ("orders.json", "order_lines.json", "relationships.json", "plan.json"):
        shutil.copyfile(FIXTURES / name, root / name)
    orders = json.loads((root / "orders.json").read_text())
    orders["columns"].update(
        note={"type": "string", "comparison": "exact"},
        occurred_at={"type": "timestamp", "comparison": "exact", "timezone": "require-aware"},
    )
    # JSON fixture files preserve recipe insertion order.
    write(root / "orders.json", orders)
    relationship = json.loads((root / "relationships.json").read_text())
    policies = {}
    for dataset in relationship["datasets"]:
        slot = dataset["id"]
        recipe = json.loads((root / f"{slot}.json").read_text())
        policies[slot] = explain_recipe(root / f"{slot}.json")["policy_sha256"]
        dataset["policy_sha256"] = policies[slot]
        dataset["columns"] = [{"name": name, "type": spec["type"]} for name, spec in recipe["columns"].items()]
    normalized = normalize_reconciliation(
        {
            "reconciliation_version": 1,
            "alignment_sha256": "0" * 64,
            "datasets": relationship["datasets"],
            "checks": relationship["checks"],
        }
    )
    relationship.update(datasets=normalized["datasets"], checks=normalized["checks"])
    write(root / "relationships.json", relationship)
    (root / "claim.txt").write_text(
        "Controlled synthetic fixture: no application writers; PG18 pg_dump of PG16 restored to PG18 before independent read-only acquisitions. This is an unauthenticated operator claim.\n"
    )
    plan = json.loads((root / "plan.json").read_text())
    plan["policies"] = policies
    plan["reconciliation_sha256"] = hashlib.sha256(_canonical(relationship)).hexdigest()
    plan["coordination"]["claim_sha256"] = hashlib.sha256((root / "claim.txt").read_bytes()).hexdigest()
    plan["limits"] = {
        "max_input_bytes": 1000000000,
        "max_rows": 300000,
        "max_keys": 300000,
        "max_groups": 300000,
        "max_temp_bytes": 1000000000,
    }
    for partition in plan["partitions"].values():
        partition["ranges"] = [{"upper": rows // 4}, {"upper": None}]
        partition["limits"] = {
            "max_input_bytes": 1000000000,
            "max_rows_per_input": 300000,
            "max_rows_per_partition_side": 300000,
            "max_staged_bytes": 1000000000,
            "max_partition_bytes": 1000000000,
        }
    write(root / "plan.json", plan)
    for side in ("baseline", "candidate"):
        acquisition = {
            "pair_plan_version": 1,
            "source_id": side,
            "tables": {},
            "limits": {
                "max_rows": 300000,
                "max_output_bytes": 1 << 30,
                "statement_timeout_ms": 300000,
                "wall_timeout_ms": 600000,
            },
        }
        for slot in ("orders", "order_lines"):
            recipe = json.loads((root / f"{slot}.json").read_text())
            acquisition["tables"][slot] = {
                "schema": "public",
                "table": slot,
                "columns": list(recipe["columns"]),
                "primary_key": ["id"],
            }
        write(root / f"{side}-acquire.json", acquisition)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg16-bin", type=Path)
    parser.add_argument("--pg18-bin", type=Path)
    parser.add_argument("--rows", type=int, default=100000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--label", default="run")
    parser.add_argument("--adversarial", action="store_true")
    parser.add_argument("--dossier", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker, args.rows, args.label), sort_keys=True))
        return
    if not args.pg16_bin or not args.pg18_bin or not args.report or args.rows % 2 or not 4 <= args.rows <= 300000:
        parser.error("provide both binary directories, report and an even row count from 4 to 300000")
    import psycopg

    records, mutations, started_clusters = [], [], []
    with tempfile.TemporaryDirectory(prefix="parison-pg-rehearsal-") as temporary:
        root = Path(temporary)
        (root / "socket").mkdir(mode=0o700)
        env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
        env.update(PGHOST=str(root / "socket"), PGDATABASE="postgres", PGUSER=os.environ.get("USER", "raghav"))
        try:
            for major, binary in ((16, args.pg16_bin), (18, args.pg18_bin)):
                data = root / f"pg{major}"
                subprocess.run(
                    [str(binary / "initdb"), "-D", str(data), "-A", "trust", "--encoding=UTF8", "--locale=C"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    env=env,
                )
                subprocess.run(
                    [
                        str(binary / "pg_ctl"),
                        "-D",
                        str(data),
                        "-l",
                        str(root / f"pg{major}.log"),
                        "-o",
                        f"-k {root / 'socket'} -p 554{major} -c listen_addresses=''",
                        "-w",
                        "start",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    env=env,
                )
                started_clusters.append((binary, data))
                with psycopg.connect(
                    host=str(root / "socket"), port=55400 + major, dbname="postgres", autocommit=True
                ) as connection:
                    connection.execute("CREATE ROLE rehearsal_reader LOGIN")
            with psycopg.connect(
                host=str(root / "socket"), port=55416, dbname="postgres", autocommit=True
            ) as connection:
                connection.execute(
                    "CREATE TABLE orders (id integer PRIMARY KEY, amount numeric(12,2), note text, occurred_at timestamptz)"
                )
                connection.execute(
                    "CREATE TABLE order_lines (id integer PRIMARY KEY, order_id integer, amount numeric(12,2))"
                )
                connection.execute(
                    "INSERT INTO orders SELECT i, 10.00, CASE i %% 5 WHEN 0 THEN NULL WHEN 1 THEN '' WHEN 2 THEN 'é' WHEN 3 THEN E'e\\u0301' ELSE E'\\\\.' END, TIMESTAMPTZ '2026-10-01 00:00:00+00' FROM generate_series(1, %s) i",
                    (args.rows // 2,),
                )
                connection.execute(
                    "INSERT INTO order_lines SELECT i, i, 10.00 FROM generate_series(1, %s) i", (args.rows // 2,)
                )
                connection.execute("GRANT USAGE ON SCHEMA public TO rehearsal_reader")
                connection.execute("GRANT SELECT ON orders, order_lines TO rehearsal_reader")
            dump = root / "migration.dump"
            subprocess.run(
                [str(args.pg18_bin / "pg_dump"), "--format=custom", "--quote-all-identifiers", "--file", str(dump)],
                env={**env, "PGPORT": "55416"},
                check=True,
            )
            subprocess.run(
                [str(args.pg18_bin / "pg_restore"), "--exit-on-error", "--dbname=postgres", str(dump)],
                env={**env, "PGPORT": "55418"},
                check=True,
            )
            prepare(root, args.rows)

            def execute(label):
                with subprocess.Popen(
                    [sys.executable, __file__, "--worker", str(root), "--rows", str(args.rows), "--label", label],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                ) as process:
                    peak_bytes = 0
                    peak_temporary_bytes = 0
                    while process.poll() is None:
                        total = temporary_bytes = 0
                        for path in (root / label).rglob("*"):
                            try:
                                if path.is_file():
                                    size = path.stat().st_size
                                    total += size
                                    if any(
                                        part.startswith(".") or part == "temporary"
                                        for part in path.relative_to(root / label).parts
                                    ):
                                        temporary_bytes += size
                            except FileNotFoundError:
                                pass
                        peak_bytes = max(peak_bytes, total)
                        peak_temporary_bytes = max(peak_temporary_bytes, temporary_bytes)
                        time.sleep(0.01)
                    stdout, stderr = process.communicate()
                    if process.returncode:
                        raise RuntimeError(f"rehearsal worker failed: {stderr}")
                    result = json.loads(stdout)
                    result.update(
                        sampled_peak_output_bytes=peak_bytes,
                        sampled_peak_temporary_bytes=peak_temporary_bytes,
                        disk_sampling_interval_ms=10,
                    )
                    return result

            for index in range(args.repeats):
                record = execute(f"cold-{index}")
                assert record["summary"]["outcome"] == "PASS", record
                records.append(record)
            if args.adversarial:
                with psycopg.connect(
                    host=str(root / "socket"), port=55418, dbname="postgres", autocommit=True
                ) as connection:
                    for name, change, restore in (
                        (
                            "orphan",
                            "UPDATE order_lines SET order_id=999999 WHERE id=1",
                            "UPDATE order_lines SET order_id=id WHERE id=1",
                        ),
                        (
                            "offsetting",
                            "UPDATE order_lines SET amount=CASE id WHEN 1 THEN 11 ELSE 9 END WHERE id IN (1,2)",
                            "UPDATE order_lines SET amount=10 WHERE id IN (1,2)",
                        ),
                        (
                            "timestamp",
                            "UPDATE orders SET occurred_at=occurred_at + interval '1 second' WHERE id=1",
                            "UPDATE orders SET occurred_at=occurred_at - interval '1 second' WHERE id=1",
                        ),
                        ("unicode", "UPDATE orders SET note='e' WHERE id=2", "UPDATE orders SET note='é' WHERE id=2"),
                        ("partial", "DELETE FROM order_lines WHERE id=1", "INSERT INTO order_lines VALUES (1,1,10)"),
                    ):
                        connection.execute(change)
                        result = execute(name)
                        assert result["summary"]["outcome"] == "FAIL", result
                        mutations.append({"case": name, "summary": result["summary"]})
                        connection.execute(restore)
            for binary, data in reversed(started_clusters):
                subprocess.run(
                    [str(binary / "pg_ctl"), "-D", str(data), "-m", "fast", "-w", "stop"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    env=env,
                )
            started_clusters.clear()
            first = root / "cold-0"
            verify(
                first / "result",
                first / "baseline",
                first / "candidate",
                root / "orders.json",
                root / "order_lines.json",
                root / "relationships.json",
                root / "claim.txt",
            )
            dossier_offline = None
            if args.dossier:
                from parison.decision_dossier import create as create_dossier
                from parison.decision_dossier import verify as verify_dossier

                plan = {
                    "dossier_plan_version": 1,
                    "rehearsal_manifest_sha256": hashlib.sha256(
                        (first / "result" / "manifest.json").read_bytes()
                    ).hexdigest(),
                    "investigations": {"orders": None, "order_lines": None},
                    "exceptions": [],
                    "signoffs": [],
                }
                (root / "dossier-plan.json").write_bytes(_canonical(plan) + b"\n")
                dossier = root / "dossier"
                safe = create_dossier(
                    root / "dossier-plan.json",
                    first / "result",
                    first / "baseline",
                    first / "candidate",
                    root / "orders.json",
                    root / "order_lines.json",
                    root / "relationships.json",
                    dossier,
                    root / "claim.txt",
                )
                for path in (first / "result", first / "baseline", first / "candidate"):
                    shutil.rmtree(path)
                for name in ("orders.json", "order_lines.json", "relationships.json", "claim.txt"):
                    (root / name).unlink()
                assert verify_dossier(dossier) == safe
                dossier_offline = True
            report = {
                "machine": platform.platform(),
                "python": sys.version,
                "rows_per_side": args.rows,
                "runs": records,
                "adversarial": mutations,
                "offline_after_shutdown": True,
                "dossier_verified_after_source_removal": dossier_offline,
                "dump_client": subprocess.check_output(
                    [str(args.pg18_bin / "pg_dump"), "--version"], text=True
                ).strip(),
            }
            args.report.write_text(json.dumps(report, indent=2) + "\n")
        finally:
            for binary, data in reversed(started_clusters):
                subprocess.run(
                    [str(binary / "pg_ctl"), "-D", str(data), "-m", "immediate", "-w", "stop"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )


if __name__ == "__main__":
    main()
