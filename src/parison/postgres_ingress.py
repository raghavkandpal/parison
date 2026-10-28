"""Optional, explicit PostgreSQL reader; never imported by core execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from math import ceil
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .core import ParisonError
from .source_receipt import (
    NULL_MARKER,
    TYPES,
    _quote,
    count_csv_rows,
    selection_sql,
    source_summary,
    validate_postgres_plan,
    verify_postgres_export,
)


def _plan(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or path.stat().st_size > 256 * 1024:
            raise ParisonError("unsafe PostgreSQL export plan")
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
        return validate_postgres_plan(value)
    except (OSError, UnicodeError, ValueError, ParisonError) as exc:
        raise ParisonError("cannot read PostgreSQL export plan") from exc


def _metadata(cursor, plan: dict[str, Any]) -> tuple[dict[str, Any], str]:
    cursor.execute(
        """
        SELECT c.oid, c.relkind, c.relpersistence, current_database(),
               current_user, current_setting('server_version_num')::integer,
               pg_current_snapshot()::text,
               pg_has_role(c.relowner, 'MEMBER'), r.rolbypassrls, r.rolsuper,
               has_table_privilege(c.oid, 'SELECT'),
               has_table_privilege(c.oid, 'INSERT'),
               has_table_privilege(c.oid, 'UPDATE'),
               has_table_privilege(c.oid, 'DELETE'),
               has_table_privilege(c.oid, 'TRUNCATE'),
               has_table_privilege(c.oid, 'REFERENCES'),
               has_table_privilege(c.oid, 'TRIGGER'),
               has_any_column_privilege(c.oid, 'INSERT'),
               has_any_column_privilege(c.oid, 'UPDATE'),
               has_any_column_privilege(c.oid, 'REFERENCES')
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_roles r ON r.rolname = current_user
        WHERE n.nspname = %s AND c.relname = %s
        """,
        (plan["schema"], plan["table"]),
    )
    row = cursor.fetchone()
    if row is None:
        raise ParisonError("PostgreSQL source relation is unavailable")
    (
        oid,
        kind,
        persistence,
        database,
        role,
        server_version,
        snapshot,
        owner,
        bypassrls,
        superuser,
        can_select,
        *can_write,
    ) = row
    if kind != "r" or persistence != "p" or owner or bypassrls or superuser or not can_select or any(can_write):
        raise ParisonError("PostgreSQL relation or role cannot qualify coverage")
    cursor.execute(
        """
        SELECT a.attname, t.typname
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
        WHERE a.attrelid = %s AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
        """,
        (oid,),
    )
    types_by_name = dict(cursor.fetchall())
    if any(name not in types_by_name or types_by_name[name] not in TYPES for name in plan["columns"]):
        raise ParisonError("PostgreSQL selection contains unsupported columns")
    cursor.execute(
        """
        SELECT i.indisvalid, i.indisready, i.indimmediate, NOT co.condeferrable,
               array_agg(a.attname ORDER BY k.ordinality)
        FROM pg_catalog.pg_index i
        JOIN pg_catalog.pg_constraint co ON co.conindid = i.indexrelid AND co.contype = 'p'
        JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, ordinality) ON TRUE
        JOIN pg_catalog.pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
        WHERE i.indrelid = %s AND i.indisprimary AND k.ordinality <= i.indnkeyatts
        GROUP BY i.indexrelid, i.indisvalid, i.indisready, i.indimmediate, co.condeferrable
        """,
        (oid,),
    )
    primary = cursor.fetchone()
    if primary is None or primary[:4] != (True, True, True, True) or primary[4] != plan["primary_key"]:
        raise ParisonError("PostgreSQL primary key does not match the plan")
    return {
        "source_id": plan["source_id"],
        "database": database,
        "schema": plan["schema"],
        "table": plan["table"],
        "columns": plan["columns"],
        "primary_key": plan["primary_key"],
        "types": [types_by_name[name] for name in plan["columns"]],
        "server_version_num": server_version,
        "role": role,
        "role_is_owner": False,
        "role_bypassrls": False,
        "role_superuser": False,
    }, snapshot


def _write_json(path: Path, value: dict[str, Any]) -> bytes:
    data = _canonical(value) + b"\n"
    path.write_bytes(data)
    return data


@contextmanager
def _wall_cancellation(conn, seconds: float):
    if seconds <= 0:
        raise ParisonError("PostgreSQL export exceeded wall limit")
    timer = threading.Timer(seconds, conn.cancel)
    timer.daemon = True
    timer.start()
    try:
        yield
    finally:
        timer.cancel()


def export_postgres(plan_path: str | Path, output: str | Path) -> dict[str, Any]:
    """Acquire one bounded source table into a verified local bundle."""
    try:
        import psycopg
    except ImportError as exc:
        raise ParisonError("install parison[postgres] to use parison-postgres") from exc

    plan = _plan(Path(plan_path))
    target = Path(output)
    check_output_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise ParisonError("PostgreSQL export output already exists")
    stage: Path | None = None
    started = time.monotonic()
    try:
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        connect_seconds = max(1, min(10, ceil(plan["limits"]["wall_timeout_ms"] / 1000)))
        with psycopg.connect("", autocommit=True, connect_timeout=connect_seconds) as conn:
            conn.execute("SET client_encoding TO 'UTF8'")
            conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            try:
                remaining = plan["limits"]["wall_timeout_ms"] / 1000 - (time.monotonic() - started)
                with _wall_cancellation(conn, remaining), conn.cursor() as cursor:
                    for setting, value in (
                        ("DateStyle", "ISO, YMD"),
                        ("TimeZone", "UTC"),
                        ("row_security", "off"),
                        ("statement_timeout", str(plan["limits"]["statement_timeout_ms"])),
                        ("lock_timeout", str(min(10_000, plan["limits"]["statement_timeout_ms"]))),
                        ("idle_in_transaction_session_timeout", "60000"),
                    ):
                        cursor.execute("SELECT set_config(%s, %s, true)", (setting, value))
                    relation = f"{_quote(plan['schema'])}.{_quote(plan['table'])}"
                    cursor.execute(f"LOCK TABLE {relation} IN ACCESS SHARE MODE")
                    source, snapshot = _metadata(cursor, plan)
                    cursor.execute(f"SELECT COUNT(*) FROM {relation}")
                    server_rows = cursor.fetchone()[0]
                    if server_rows > plan["limits"]["max_rows"]:
                        raise ParisonError("PostgreSQL source exceeds row limit")
                    text_columns = [
                        name
                        for name, kind in zip(plan["columns"], source["types"], strict=True)
                        if kind in {"text", "varchar"}
                    ]
                    if text_columns:
                        predicate = " OR ".join(f"{_quote(name)} = %s" for name in text_columns)
                        cursor.execute(
                            f"SELECT EXISTS(SELECT 1 FROM {relation} WHERE {predicate})",
                            [NULL_MARKER] * len(text_columns),
                        )
                        if cursor.fetchone()[0]:
                            raise ParisonError("PostgreSQL source contains reserved NULL marker")
                    selection = selection_sql(plan["schema"], plan["table"], plan["columns"], plan["primary_key"])
                    copy_sql = (
                        f"COPY ({selection}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE, NULL E'\\\\N', ENCODING 'UTF8')"
                    )
                    digest = hashlib.sha256()
                    size = 0
                    with (stage / "data.csv").open("xb") as handle, cursor.copy(copy_sql) as copy:
                        for block in copy:
                            if time.monotonic() - started > plan["limits"]["wall_timeout_ms"] / 1000:
                                raise ParisonError("PostgreSQL export exceeded wall limit")
                            size += len(block)
                            if size > plan["limits"]["max_output_bytes"]:
                                raise ParisonError("PostgreSQL export exceeded byte limit")
                            digest.update(block)
                            handle.write(block)
                    local_rows = count_csv_rows(stage / "data.csv", plan["columns"], plan["limits"]["max_rows"])
                    if local_rows != server_rows:
                        raise ParisonError("PostgreSQL source and local counts differ")
                conn.execute("COMMIT")
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except psycopg.Error:
                    pass
                raise
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if elapsed_ms > plan["limits"]["wall_timeout_ms"]:
            raise ParisonError("PostgreSQL export exceeded wall limit")
        receipt = {
            "postgres_source_receipt_version": 1,
            "kind": "postgresql-table-export",
            "plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
            "source": source,
            "transaction": {
                "isolation": "repeatable read",
                "read_only": True,
                "row_security": "off",
                "snapshot": snapshot,
                "client_encoding": "UTF8",
                "date_style": "ISO, YMD",
                "time_zone": "UTC",
            },
            "selection": {
                "sql": selection,
                "format": "csv-utf8-v1",
                "null_marker": NULL_MARKER,
                "null_marker_collision": False,
            },
            "limits": plan["limits"],
            "observed": {
                "server_rows": server_rows,
                "local_rows": local_rows,
                "output_bytes": size,
                "output_sha256": digest.hexdigest(),
                "elapsed_ms": elapsed_ms,
                "complete": True,
            },
        }
        receipt_data = _write_json(stage / "receipt.json", receipt)
        summary = source_summary(receipt, receipt_data)
        summary_data = _write_json(stage / "summary.json", summary)
        manifest = {
            "postgres_source_manifest_version": 1,
            "kind": "postgresql-table-export",
            "complete": True,
            "files": {
                "data.csv": digest.hexdigest(),
                "receipt.json": hashlib.sha256(receipt_data).hexdigest(),
                "summary.json": hashlib.sha256(summary_data).hexdigest(),
            },
        }
        _write_json(stage / "manifest.json", manifest)
        if verify_postgres_export(stage) != summary:
            raise ParisonError("PostgreSQL export verification failed")
        if (time.monotonic() - started) * 1000 > plan["limits"]["wall_timeout_ms"]:
            raise ParisonError("PostgreSQL export exceeded wall limit")
        check_output_parent(target.parent)
        rename_no_replace(stage, target)
        stage = None
        return summary
    except psycopg.Error:
        raise ParisonError("PostgreSQL acquisition failed") from None
    except OSError:
        raise ParisonError("PostgreSQL export could not be published") from None
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="parison-postgres", description="Optional local PostgreSQL evidence reader")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        summary = export_postgres(args.plan, args.output)
    except ParisonError as exc:
        print(f"parison-postgres: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("parison-postgres: interrupted", file=sys.stderr)
        return 130
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
