"""Optional bounded N-table reader outside offline verification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import time
from math import ceil
from pathlib import Path

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .core import ParisonError
from .postgres_ingress import (
    _acquire_table,
    _configure_transaction,
    _lock_tables,
    _metadata,
    _wall_cancellation,
    _write_json,
    _write_table_evidence,
)
from .source_collection import (
    KIND,
    META_LIMIT,
    PROFILE,
    _stat_stamp,
    collection_summary,
    validate_postgres_collection_plan,
    verify_postgres_collection,
)
from .source_receipt import _quote

# Promotion requires the exact live gates in docs/2.4/278 before integration.
LIVE_VERSIONS = frozenset({160015, 170011, 180006})
_ERROR = "invalid or incomplete collection evidence"


def _load_plan(path: Path) -> dict:
    check_output_parent(path.parent)
    flags = os.O_RDONLY | (os.O_NOFOLLOW | os.O_NONBLOCK if os.name == "posix" else 0)
    if path.is_symlink():
        raise ParisonError(_ERROR)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > META_LIMIT:
            raise ParisonError(_ERROR)
        data = handle.read(META_LIMIT + 1)
        after = os.fstat(handle.fileno())
        if len(data) > META_LIMIT or _stat_stamp(before) != _stat_stamp(after):
            raise ParisonError(_ERROR)
    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )
    return validate_postgres_collection_plan(value)


def _remaining(started: float, limits: dict) -> float:
    remaining = limits["wall_timeout_ms"] / 1000 - (time.monotonic() - started)
    if remaining <= 0:
        raise ParisonError(_ERROR)
    return remaining


def _qualify_table(cursor, plan: dict) -> tuple[dict, str]:
    source, snapshot = _metadata(cursor, plan)
    if source["server_version_num"] not in LIVE_VERSIONS:
        raise ParisonError(_ERROR)
    cursor.execute(
        "SELECT rolcreaterole, rolcreatedb, rolreplication FROM pg_catalog.pg_roles WHERE rolname=current_user"
    )
    if cursor.fetchone() != (False, False, False):
        raise ParisonError(_ERROR)
    if source["server_version_num"] >= 170000:
        # MAINTAIN was introduced in PostgreSQL17; it is not SELECT-only.
        relation = f"{_quote(plan['schema'])}.{_quote(plan['table'])}"
        cursor.execute("SELECT has_table_privilege(%s, 'MAINTAIN')", (relation,))
        if cursor.fetchone() != (False,):
            raise ParisonError(_ERROR)
    cursor.execute(
        """
        SELECT c.relispartition,
               EXISTS(SELECT 1 FROM pg_catalog.pg_inherits i
                      WHERE i.inhrelid = c.oid OR i.inhparent = c.oid)
        FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relname = %s
    """,
        (plan["schema"], plan["table"]),
    )
    if cursor.fetchone() != (False, False):
        raise ParisonError(_ERROR)
    cursor.execute(
        """
        SELECT a.attname, t.typname, tn.nspname
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
        JOIN pg_catalog.pg_namespace tn ON tn.oid = t.typnamespace
        WHERE n.nspname = %s AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
    """,
        (plan["schema"], plan["table"]),
    )
    types = {name: (kind, namespace) for name, kind, namespace in cursor.fetchall()}
    if any(
        types.get(name) != (kind, "pg_catalog") for name, kind in zip(plan["columns"], source["types"], strict=True)
    ):
        raise ParisonError(_ERROR)
    # Force row-security planning on every member before any COPY. This also
    # observes each declared table under the already anchored shared snapshot.
    cursor.execute(f"SELECT COUNT(*) FROM {_quote(plan['schema'])}.{_quote(plan['table'])}")
    cursor.fetchone()
    return source, snapshot


def parser() -> argparse.ArgumentParser:
    root = _SafeParser(
        prog="parison postgres collection", description="Acquire one bounded PostgreSQL snapshot collection"
    )
    root.add_argument("--plan", required=True)
    root.add_argument("--output", required=True)
    return root


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParisonError(_ERROR)


def export_postgres_collection(plan_path: str | Path, output: str | Path) -> dict:
    """Acquire every reviewed table or publish nothing."""
    stage = None
    try:
        plan = _load_plan(Path(plan_path))
        target = Path(output)
        check_output_parent(target.parent)
        if target.exists() or target.is_symlink():
            raise ParisonError(_ERROR)
        import psycopg

        limits = plan["limits"]
        started = time.monotonic()
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        tables = stage / "tables"
        tables.mkdir(mode=0o700)
        children = {
            table_id: {"plan_version": 1, "source_id": plan["source_id"], **selection, "limits": limits}
            for table_id, selection in sorted(plan["tables"].items())
        }
        for table_id in children:
            (tables / table_id).mkdir(mode=0o700)
        _remaining(started, limits)
        timeout = max(1, min(10, ceil(_remaining(started, limits))))
        acquired = {}
        with psycopg.connect("", autocommit=True, connect_timeout=timeout) as conn:
            try:
                with _wall_cancellation(conn, _remaining(started, limits)), conn.cursor() as cursor:
                    cursor.execute("SET client_encoding TO 'UTF8'")
                    cursor.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    _configure_transaction(cursor, limits)
                    _remaining(started, limits)
                    _lock_tables(cursor, list(children.values()))
                    qualified = {}
                    for table_id, child_plan in children.items():
                        _remaining(started, limits)
                        qualified[table_id] = _qualify_table(cursor, child_plan)
                    first_source, first_snapshot = next(iter(qualified.values()))
                    for source, snapshot in qualified.values():
                        if snapshot != first_snapshot or any(
                            source[name] != first_source[name]
                            for name in ("source_id", "database", "role", "server_version_num")
                        ):
                            raise ParisonError(_ERROR)
                    rows, size = 0, 0
                    for table_id, child_plan in children.items():
                        _remaining(started, limits)
                        item = _acquire_table(
                            cursor,
                            child_plan,
                            tables / table_id,
                            started,
                            limits["max_rows"] - rows,
                            limits["max_output_bytes"] - size,
                        )
                        if (item["source"], item["snapshot"]) != qualified[table_id]:
                            raise ParisonError(_ERROR)
                        acquired[table_id] = item
                        rows += item["local_rows"]
                        size += item["size"]
                        if rows > limits["max_rows"] or size > limits["max_output_bytes"]:
                            raise ParisonError(_ERROR)
                    _remaining(started, limits)
                    cursor.execute("COMMIT")
                    elapsed_ms = int((time.monotonic() - started) * 1000)
                    _remaining(started, limits)
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except psycopg.Error:
                    pass
                raise
        for table_id, child_plan in children.items():
            _remaining(started, limits)
            _write_table_evidence(tables / table_id, child_plan, acquired[table_id], elapsed_ms)
        receipt = {
            "postgres_collection_receipt_version": 1,
            "kind": KIND,
            "collection_plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
            "capability_profile": PROFILE,
            "source": {name: first_source[name] for name in ("source_id", "database", "role", "server_version_num")},
            "transaction": {
                "isolation": "repeatable read",
                "read_only": True,
                "row_security": "off",
                "snapshot": first_snapshot,
            },
            "table_manifests": {
                table_id: hashlib.sha256((tables / table_id / "manifest.json").read_bytes()).hexdigest()
                for table_id in children
            },
            "limits": limits,
            "observed": {"rows": rows, "bytes": size, "elapsed_ms": elapsed_ms, "complete": True},
        }
        receipt_data = _write_json(stage / "receipt.json", receipt)
        summary = collection_summary(receipt, receipt_data)
        summary_data = _write_json(stage / "summary.json", summary)
        _write_json(
            stage / "manifest.json",
            {
                "postgres_collection_manifest_version": 1,
                "kind": KIND,
                "complete": True,
                "files": {
                    "receipt.json": hashlib.sha256(receipt_data).hexdigest(),
                    "summary.json": hashlib.sha256(summary_data).hexdigest(),
                },
                "table_manifests": receipt["table_manifests"],
            },
        )
        _remaining(started, limits)
        if verify_postgres_collection(stage) != summary:
            raise ParisonError(_ERROR)
        _remaining(started, limits)
        check_output_parent(target.parent)
        _remaining(started, limits)
        rename_no_replace(stage, target)
        stage = None
        return summary
    except KeyboardInterrupt:
        raise
    except Exception:
        raise ParisonError(_ERROR) from None
    finally:
        if stage is not None:
            try:
                shutil.rmtree(stage)
            except OSError:
                raise ParisonError(_ERROR) from None


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        print(_canonical(export_postgres_collection(args.plan, args.output)).decode("utf-8"))
        return 0
    except (ParisonError, OSError, ValueError, TypeError):
        print(f"parison postgres collection: {_ERROR}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("parison postgres collection: interrupted", file=sys.stderr)
        return 130
