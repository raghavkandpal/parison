"""Offline verification of one coordinated PostgreSQL two-table export."""

from __future__ import annotations

import hashlib
import os
import stat
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from .analysis import _canonical
from .core import ParisonError
from .source_receipt import (
    _bundle_handles,
    _integer,
    _object,
    _read_json,
    _sha,
    _text,
    _verify_handles,
    validate_postgres_plan,
)

SLOTS = ("orders", "order_lines")
KIND = "postgresql-two-table-export"
CLAIM = "adapter-two-tables-one-source-snapshot"


def _read_pair_json(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink():
        raise ParisonError("PostgreSQL pair has unsafe file")
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ParisonError("PostgreSQL pair has unsafe file")
            return _read_json(handle)
    with path.open("rb") as handle:
        return _read_json(handle)


def validate_postgres_pair_plan(value: Any) -> dict[str, Any]:
    plan = _object(value, "pair_plan_version source_id tables limits")
    if type(plan["pair_plan_version"]) is not int or plan["pair_plan_version"] != 1:
        raise ParisonError("unsupported PostgreSQL pair plan")
    _text(plan["source_id"])
    tables = _object(plan["tables"], "orders order_lines")
    relations = set()
    for slot in SLOTS:
        table = _object(tables[slot], "schema table columns primary_key")
        validate_postgres_plan({"plan_version": 1, "source_id": plan["source_id"], **table, "limits": plan["limits"]})
        relation = (table["schema"], table["table"])
        if relation in relations:
            raise ParisonError("PostgreSQL pair selects the same relation twice")
        relations.add(relation)
    return plan


def pair_summary(receipt: dict[str, Any], receipt_data: bytes) -> dict[str, Any]:
    return {
        "postgres_pair_summary_version": 1,
        "kind": KIND,
        "complete": True,
        "coverage_claim": CLAIM,
        "tables": 2,
        "rows": receipt["observed"]["rows"],
        "bytes": receipt["observed"]["bytes"],
        "receipt_sha256": hashlib.sha256(receipt_data).hexdigest(),
    }


def verify_postgres_pair(directory: str | Path) -> dict[str, Any]:
    """Verify local pair coordination and both unchanged child bundles."""
    root = Path(directory)
    try:
        if root.is_symlink() or {path.name for path in root.iterdir()} != {
            "receipt.json",
            "summary.json",
            "manifest.json",
            "tables",
        }:
            raise ParisonError("PostgreSQL pair has invalid files")
        tables_root = root / "tables"
        if (
            tables_root.is_symlink()
            or not tables_root.is_dir()
            or {path.name for path in tables_root.iterdir()} != set(SLOTS)
        ):
            raise ParisonError("PostgreSQL pair has invalid tables")
        with ExitStack() as stack:
            children = {}
            for slot in SLOTS:
                child = tables_root / slot
                handles = stack.enter_context(_bundle_handles(child))
                _verify_handles(handles)
                handles["receipt.json"].seek(0)
                handles["manifest.json"].seek(0)
                child_receipt, _ = _read_json(handles["receipt.json"])
                _, child_manifest_bytes = _read_json(handles["manifest.json"])
                children[slot] = (child_receipt, hashlib.sha256(child_manifest_bytes).hexdigest())
            receipt, receipt_data = _read_pair_json(root / "receipt.json")
            summary, summary_data = _read_pair_json(root / "summary.json")
            manifest, _ = _read_pair_json(root / "manifest.json")
            _verify_pair_receipt(receipt, children)
            _object(
                summary, "postgres_pair_summary_version kind complete coverage_claim tables rows bytes receipt_sha256"
            )
            if summary != pair_summary(receipt, receipt_data):
                raise ParisonError("PostgreSQL pair summary does not reconcile")
            _object(manifest, "postgres_pair_manifest_version kind complete files")
            if (
                type(manifest["postgres_pair_manifest_version"]) is not int
                or manifest["postgres_pair_manifest_version"] != 1
                or manifest["kind"] != KIND
                or manifest["complete"] is not True
            ):
                raise ParisonError("unsupported PostgreSQL pair manifest")
            files = _object(manifest["files"], "receipt.json summary.json orders order_lines")
            expected = {
                "receipt.json": hashlib.sha256(receipt_data).hexdigest(),
                "summary.json": hashlib.sha256(summary_data).hexdigest(),
                **{slot: children[slot][1] for slot in SLOTS},
            }
            if files != expected:
                raise ParisonError("PostgreSQL pair manifest digest mismatch")
            return summary
    except (OSError, UnicodeError, ValueError) as exc:
        raise ParisonError("cannot verify PostgreSQL pair") from exc


def _verify_pair_receipt(receipt: Any, children: dict[str, tuple[dict[str, Any], str]]) -> None:
    _object(
        receipt,
        "postgres_pair_receipt_version kind pair_plan_sha256 source transaction table_manifests limits observed",
    )
    if (
        type(receipt["postgres_pair_receipt_version"]) is not int
        or receipt["postgres_pair_receipt_version"] != 1
        or receipt["kind"] != KIND
    ):
        raise ParisonError("unsupported PostgreSQL pair receipt")
    _sha(receipt["pair_plan_sha256"])
    source = _object(receipt["source"], "source_id database role server_version_num")
    for name in ("source_id", "database", "role"):
        _text(source[name])
    _integer(source["server_version_num"], 160_000, 999_999)
    transaction = _object(receipt["transaction"], "isolation read_only row_security snapshot")
    if (
        transaction["isolation"] != "repeatable read"
        or transaction["read_only"] is not True
        or transaction["row_security"] != "off"
    ):
        raise ParisonError("PostgreSQL pair transaction is invalid")
    _text(transaction["snapshot"])
    manifests = _object(receipt["table_manifests"], "orders order_lines")
    if any(manifests[slot] != children[slot][1] for slot in SLOTS):
        raise ParisonError("PostgreSQL pair child manifest mismatch")
    pair_plan = {"pair_plan_version": 1, "source_id": source["source_id"], "tables": {}, "limits": receipt["limits"]}
    rows = size = 0
    for slot in SLOTS:
        child = children[slot][0]
        descriptor = child["source"]
        if (
            any(descriptor[name] != source[name] for name in ("source_id", "database", "role", "server_version_num"))
            or child["transaction"]["snapshot"] != transaction["snapshot"]
            or any(
                child["transaction"][name] != transaction[name] for name in ("isolation", "read_only", "row_security")
            )
            or child["limits"] != receipt["limits"]
        ):
            raise ParisonError("PostgreSQL pair sources or snapshots differ")
        pair_plan["tables"][slot] = {name: descriptor[name] for name in ("schema", "table", "columns", "primary_key")}
        rows += child["observed"]["local_rows"]
        size += child["observed"]["output_bytes"]
    validate_postgres_pair_plan(pair_plan)
    if receipt["pair_plan_sha256"] != hashlib.sha256(_canonical(pair_plan)).hexdigest():
        raise ParisonError("PostgreSQL pair plan digest mismatch")
    observed = _object(receipt["observed"], "rows bytes elapsed_ms complete")
    _integer(observed["rows"], 0, receipt["limits"]["max_rows"])
    _integer(observed["bytes"], 0, receipt["limits"]["max_output_bytes"])
    _integer(observed["elapsed_ms"], 0, receipt["limits"]["wall_timeout_ms"])
    if observed["complete"] is not True or observed["rows"] != rows or observed["bytes"] != size:
        raise ParisonError("PostgreSQL pair is incomplete")
