"""Optional, explicit two-table PostgreSQL reader outside core execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from math import ceil
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .core import ParisonError
from .postgres_ingress import (
    _acquire_table,
    _configure_transaction,
    _lock_tables,
    _wall_cancellation,
    _write_json,
    _write_table_evidence,
)
from .source_pair import KIND, SLOTS, pair_summary, validate_postgres_pair_plan, verify_postgres_pair


def _pair_plan(path: Path) -> dict[str, Any]:
    try:
        if path.is_symlink() or path.stat().st_size > 256 * 1024:
            raise ParisonError("unsafe PostgreSQL pair plan")
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
        return validate_postgres_pair_plan(value)
    except (OSError, UnicodeError, ValueError, ParisonError) as exc:
        raise ParisonError("cannot read PostgreSQL pair plan") from exc


def export_postgres_pair(plan_path: str | Path, output: str | Path) -> dict[str, Any]:
    """Acquire the two reviewed slots under one source snapshot."""
    try:
        import psycopg
    except ImportError as exc:
        raise ParisonError("install parison[postgres] to use parison-postgres-pair") from exc

    plan = _pair_plan(Path(plan_path))
    target = Path(output)
    check_output_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise ParisonError("PostgreSQL pair output already exists")
    stage: Path | None = None
    started = time.monotonic()
    limits = plan["limits"]
    table_plans = {
        slot: {"plan_version": 1, "source_id": plan["source_id"], **plan["tables"][slot], "limits": limits}
        for slot in SLOTS
    }
    try:
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        tables_root = stage / "tables"
        tables_root.mkdir(mode=0o700)
        for slot in SLOTS:
            (tables_root / slot).mkdir(mode=0o700)
        connect_seconds = max(1, min(10, ceil(limits["wall_timeout_ms"] / 1000)))
        with psycopg.connect("", autocommit=True, connect_timeout=connect_seconds) as conn:
            conn.execute("SET client_encoding TO 'UTF8'")
            conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            try:
                remaining = limits["wall_timeout_ms"] / 1000 - (time.monotonic() - started)
                with _wall_cancellation(conn, remaining), conn.cursor() as cursor:
                    _configure_transaction(cursor, limits)
                    _lock_tables(cursor, list(table_plans.values()))
                    acquired = {}
                    remaining_rows, remaining_bytes = limits["max_rows"], limits["max_output_bytes"]
                    for slot in SLOTS:
                        acquired[slot] = _acquire_table(
                            cursor, table_plans[slot], tables_root / slot, started, remaining_rows, remaining_bytes
                        )
                        remaining_rows -= acquired[slot]["local_rows"]
                        remaining_bytes -= acquired[slot]["size"]
                    rows = sum(acquired[slot]["local_rows"] for slot in SLOTS)
                    size = sum(acquired[slot]["size"] for slot in SLOTS)
                    if rows > limits["max_rows"] or size > limits["max_output_bytes"]:
                        raise ParisonError("PostgreSQL pair exceeds total limit")
                    first = acquired[SLOTS[0]]
                    if any(
                        acquired[slot]["snapshot"] != first["snapshot"]
                        or any(
                            acquired[slot]["source"][name] != first["source"][name]
                            for name in ("source_id", "database", "role", "server_version_num")
                        )
                        for slot in SLOTS[1:]
                    ):
                        raise ParisonError("PostgreSQL pair sources or snapshots differ")
                conn.execute("COMMIT")
            except BaseException:
                try:
                    conn.execute("ROLLBACK")
                except psycopg.Error:
                    pass
                raise
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if elapsed_ms > limits["wall_timeout_ms"]:
            raise ParisonError("PostgreSQL pair exceeded wall limit")
        for slot in SLOTS:
            _write_table_evidence(tables_root / slot, table_plans[slot], acquired[slot], elapsed_ms)
        source = first["source"]
        receipt = {
            "postgres_pair_receipt_version": 1,
            "kind": KIND,
            "pair_plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
            "source": {name: source[name] for name in ("source_id", "database", "role", "server_version_num")},
            "transaction": {
                "isolation": "repeatable read",
                "read_only": True,
                "row_security": "off",
                "snapshot": first["snapshot"],
            },
            "table_manifests": {
                slot: hashlib.sha256((tables_root / slot / "manifest.json").read_bytes()).hexdigest() for slot in SLOTS
            },
            "limits": limits,
            "observed": {"rows": rows, "bytes": size, "elapsed_ms": elapsed_ms, "complete": True},
        }
        receipt_data = _write_json(stage / "receipt.json", receipt)
        summary = pair_summary(receipt, receipt_data)
        summary_data = _write_json(stage / "summary.json", summary)
        manifest = {
            "postgres_pair_manifest_version": 1,
            "kind": KIND,
            "complete": True,
            "files": {
                "receipt.json": hashlib.sha256(receipt_data).hexdigest(),
                "summary.json": hashlib.sha256(summary_data).hexdigest(),
                **receipt["table_manifests"],
            },
        }
        _write_json(stage / "manifest.json", manifest)
        if verify_postgres_pair(stage) != summary:
            raise ParisonError("PostgreSQL pair verification failed")
        if (time.monotonic() - started) * 1000 > limits["wall_timeout_ms"]:
            raise ParisonError("PostgreSQL pair exceeded wall limit")
        check_output_parent(target.parent)
        rename_no_replace(stage, target)
        stage = None
        return summary
    except psycopg.Error:
        raise ParisonError("PostgreSQL pair acquisition failed") from None
    except OSError:
        raise ParisonError("PostgreSQL pair could not be published") from None
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def parser(prog: str = "parison-postgres-pair") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="Optional local two-table PostgreSQL evidence reader")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None, *, prog: str = "parison-postgres-pair") -> int:
    args = parser(prog).parse_args(argv)
    try:
        summary = export_postgres_pair(args.plan, args.output)
    except ParisonError as exc:
        print(f"parison-postgres-pair: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("parison-postgres-pair: interrupted", file=sys.stderr)
        return 130
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
