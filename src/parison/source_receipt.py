"""Offline verification of optional PostgreSQL acquisition evidence."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .analysis import _canonical, _strict_object
from .core import ParisonError

MAX_ROWS = 300_000
MAX_BYTES = 1 << 30
MAX_STATEMENT_MS = 300_000
MAX_WALL_MS = 600_000
NULL_MARKER = r"\N"
TYPES = {"int2", "int4", "int8", "numeric", "bool", "text", "varchar", "uuid", "date", "timestamp", "timestamptz"}
FILES = {"data.csv", "receipt.json", "summary.json", "manifest.json"}


def _object(value: Any, names: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(names.split()):
        raise ParisonError("PostgreSQL evidence has invalid fields")
    return value


def _integer(value: Any, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ParisonError("PostgreSQL evidence has invalid limit or count")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value or not value.isprintable() or "\x00" in value:
        raise ParisonError("PostgreSQL evidence has invalid text")
    return value


def _identifier(value: Any) -> str:
    value = _text(value)
    if len(value.encode("utf-8")) > 63:
        raise ParisonError("PostgreSQL identifier is too long")
    return value


def _names(value: Any) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise ParisonError("PostgreSQL evidence has invalid columns")
    names = [_identifier(item) for item in value]
    if len(names) != len(set(names)):
        raise ParisonError("PostgreSQL evidence has duplicate columns")
    return names


def _sha(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ParisonError("PostgreSQL evidence has invalid digest")
    return value


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def selection_sql(schema: str, table: str, columns: list[str], primary_key: list[str]) -> str:
    """Generate the only supported, unfiltered and key-ordered selection."""
    return (
        f"SELECT {', '.join(_quote(name) for name in columns)} "
        f"FROM {_quote(schema)}.{_quote(table)} "
        f"ORDER BY {', '.join(_quote(name) for name in primary_key)}"
    )


def validate_postgres_plan(value: Any) -> dict[str, Any]:
    plan = _object(value, "plan_version source_id schema table columns primary_key limits")
    if type(plan["plan_version"]) is not int or plan["plan_version"] != 1:
        raise ParisonError("unsupported PostgreSQL export plan")
    _text(plan["source_id"])
    _identifier(plan["schema"])
    _identifier(plan["table"])
    columns, key = _names(plan["columns"]), _names(plan["primary_key"])
    if not set(key) <= set(columns):
        raise ParisonError("PostgreSQL primary key is not selected")
    limits = _object(plan["limits"], "max_rows max_output_bytes statement_timeout_ms wall_timeout_ms")
    for name, maximum in (
        ("max_rows", MAX_ROWS),
        ("max_output_bytes", MAX_BYTES),
        ("statement_timeout_ms", MAX_STATEMENT_MS),
        ("wall_timeout_ms", MAX_WALL_MS),
    ):
        _integer(limits[name], 1, maximum)
    return plan


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        if path.stat().st_size > 256 * 1024:
            raise ParisonError("PostgreSQL evidence JSON is too large")
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_strict_object)
        if not isinstance(value, dict) or data != _canonical(value) + b"\n":
            raise ParisonError("PostgreSQL evidence is not canonical")
    except (OSError, UnicodeError, ValueError, ParisonError) as exc:
        raise ParisonError("cannot read canonical PostgreSQL evidence") from exc
    return value, data


def _receipt(value: Any) -> dict[str, Any]:
    receipt = _object(
        value,
        "postgres_source_receipt_version kind plan_sha256 source transaction selection limits observed",
    )
    if type(receipt["postgres_source_receipt_version"]) is not int or receipt["postgres_source_receipt_version"] != 1:
        raise ParisonError("unsupported PostgreSQL source receipt")
    if receipt["kind"] != "postgresql-table-export":
        raise ParisonError("unsupported PostgreSQL source receipt")
    source = _object(
        receipt["source"],
        "source_id database schema table columns primary_key types server_version_num role role_is_owner role_bypassrls role_superuser",
    )
    for name in ("source_id", "database", "role"):
        _text(source[name])
    for name in ("schema", "table"):
        _identifier(source[name])
    columns, key = _names(source["columns"]), _names(source["primary_key"])
    if not set(key) <= set(columns):
        raise ParisonError("PostgreSQL primary key is not selected")
    if not isinstance(source["types"], list) or len(source["types"]) != len(columns):
        raise ParisonError("PostgreSQL evidence has invalid types")
    if any(type(name) is not str or name not in TYPES for name in source["types"]):
        raise ParisonError("PostgreSQL evidence has unsupported type")
    _integer(source["server_version_num"], 160_000, 999_999)
    if any(source[name] is not False for name in ("role_is_owner", "role_bypassrls", "role_superuser")):
        raise ParisonError("PostgreSQL role cannot qualify coverage")
    transaction = _object(
        receipt["transaction"], "isolation read_only row_security snapshot client_encoding date_style time_zone"
    )
    if (
        transaction["isolation"] != "repeatable read"
        or transaction["read_only"] is not True
        or transaction["row_security"] != "off"
        or transaction["client_encoding"] != "UTF8"
        or transaction["date_style"] != "ISO, YMD"
        or transaction["time_zone"] != "UTC"
    ):
        raise ParisonError("PostgreSQL snapshot settings do not qualify coverage")
    _text(transaction["snapshot"])
    selection = _object(receipt["selection"], "sql format null_marker null_marker_collision")
    if selection != {
        "sql": selection_sql(source["schema"], source["table"], columns, key),
        "format": "csv-utf8-v1",
        "null_marker": NULL_MARKER,
        "null_marker_collision": False,
    }:
        raise ParisonError("PostgreSQL selection does not qualify coverage")
    plan = {
        "plan_version": 1,
        **{name: source[name] for name in ("source_id", "schema", "table", "columns", "primary_key")},
        "limits": receipt["limits"],
    }
    validate_postgres_plan(plan)
    if receipt["plan_sha256"] != hashlib.sha256(_canonical(plan)).hexdigest():
        raise ParisonError("PostgreSQL plan digest mismatch")
    observed = _object(receipt["observed"], "server_rows local_rows output_bytes output_sha256 elapsed_ms complete")
    for name in ("server_rows", "local_rows"):
        _integer(observed[name], 0, receipt["limits"]["max_rows"])
    _integer(observed["output_bytes"], 0, receipt["limits"]["max_output_bytes"])
    _integer(observed["elapsed_ms"], 0, receipt["limits"]["wall_timeout_ms"])
    _sha(observed["output_sha256"])
    if observed["server_rows"] != observed["local_rows"] or observed["complete"] is not True:
        raise ParisonError("PostgreSQL export is incomplete")
    return receipt


def source_summary(receipt: dict[str, Any], receipt_data: bytes) -> dict[str, Any]:
    observed = receipt["observed"]
    return {
        "postgres_source_summary_version": 1,
        "kind": "postgresql-table-export",
        "complete": True,
        "coverage_claim": "adapter-all-rows-selected-columns",
        "rows": observed["local_rows"],
        "bytes": observed["output_bytes"],
        "output_sha256": observed["output_sha256"],
        "receipt_sha256": hashlib.sha256(receipt_data).hexdigest(),
    }


def count_csv_rows(data: Path, columns: list[str], max_rows: int) -> int:
    """Count complete CSV records, including rows with embedded newlines."""
    try:
        with data.open("r", encoding="utf-8", newline="") as handle:
            rows = csv.reader(handle, strict=True)
            if next(rows, None) != columns:
                raise ParisonError("PostgreSQL CSV header mismatch")
            count = 0
            for row in rows:
                if len(row) != len(columns):
                    raise ParisonError("PostgreSQL CSV row shape mismatch")
                count += 1
                if count > max_rows:
                    raise ParisonError("PostgreSQL CSV exceeds row limit")
            return count
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ParisonError("cannot read PostgreSQL CSV") from exc


def verify_postgres_export(directory: str | Path) -> dict[str, Any]:
    """Verify local bundle integrity without importing a database driver."""
    root = Path(directory)
    try:
        if root.is_symlink() or not root.is_dir() or {part.name for part in root.iterdir()} != FILES:
            raise ParisonError("PostgreSQL export has invalid files")
        if any((root / name).is_symlink() or not (root / name).is_file() for name in FILES):
            raise ParisonError("PostgreSQL export has unsafe file")
        manifest, _ = _read_json(root / "manifest.json")
        _object(manifest, "postgres_source_manifest_version kind complete files")
        if (
            type(manifest["postgres_source_manifest_version"]) is not int
            or manifest["postgres_source_manifest_version"] != 1
            or manifest["kind"] != "postgresql-table-export"
            or manifest["complete"] is not True
        ):
            raise ParisonError("unsupported PostgreSQL export manifest")
        files = _object(manifest["files"], "data.csv receipt.json summary.json")
        for digest in files.values():
            _sha(digest)
        receipt, receipt_data = _read_json(root / "receipt.json")
        _receipt(receipt)
        summary, summary_data = _read_json(root / "summary.json")
        _object(
            summary,
            "postgres_source_summary_version kind complete coverage_claim rows bytes output_sha256 receipt_sha256",
        )
        if summary != source_summary(receipt, receipt_data):
            raise ParisonError("PostgreSQL summary does not reconcile")
        if (
            files["receipt.json"] != hashlib.sha256(receipt_data).hexdigest()
            or files["summary.json"] != hashlib.sha256(summary_data).hexdigest()
        ):
            raise ParisonError("PostgreSQL evidence digest mismatch")
        data = root / "data.csv"
        if data.stat().st_size != receipt["observed"]["output_bytes"]:
            raise ParisonError("PostgreSQL data size mismatch")
        digest = hashlib.sha256()
        with data.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != receipt["observed"]["output_sha256"] or digest.hexdigest() != files["data.csv"]:
            raise ParisonError("PostgreSQL data digest mismatch")
        count = count_csv_rows(data, receipt["source"]["columns"], receipt["limits"]["max_rows"])
        if count != receipt["observed"]["local_rows"]:
            raise ParisonError("PostgreSQL CSV count mismatch")
        return summary
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ParisonError("cannot verify PostgreSQL export") from exc
