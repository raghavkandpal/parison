from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import platform
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from importlib import metadata
from pathlib import Path
from typing import Any


OUTCOME_CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "INCONCLUSIVE": 3, "INTERRUPTED": 130}
_RECIPE_KEYS = {"recipe_version", "comparison_mode", "keys", "scope", "identity", "nulls_equal", "columns", "column_mappings", "excluded_columns", "output"}
_COLUMN_KEYS = {"type", "comparison", "tolerance", "timezone", "scale"}
_TYPES = {"string", "integer", "decimal", "float", "boolean", "date", "timestamp"}
_FILE_FORMATS = {".csv": "csv", ".jsonl": "jsonl", ".ndjson": "jsonl", ".parquet": "parquet", ".pq": "parquet"}


class ParisonError(ValueError):
    pass


def _runtime_info(paths: tuple[Any, Any] | None = None) -> dict[str, Any]:
    try:
        version = metadata.version("parison")
    except metadata.PackageNotFoundError:
        version = "source-tree"
    runtime = {
        "contract": "keyed-v1",
        "parison_version": version,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "machine": platform.machine(),
    }
    if paths and any(_source_path(path).suffix.lower() in {".parquet", ".pq"} for path in paths):
        try:
            runtime["polars"] = metadata.version("polars")
        except metadata.PackageNotFoundError:
            runtime["polars"] = "unavailable"
    return runtime


def _unknown(mapping: dict[str, Any], allowed: set[str], where: str) -> None:
    extras = set(mapping) - allowed
    if extras:
        raise ParisonError(f"unknown {where} field(s): {', '.join(sorted(extras))}")


def load_recipe(path: str | Path) -> dict[str, Any]:
    try:
        recipe = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read recipe: {exc}") from exc
    if not isinstance(recipe, dict):
        raise ParisonError("recipe must be a JSON object")
    _unknown(recipe, _RECIPE_KEYS, "recipe")
    if recipe.get("recipe_version") != 1:
        raise ParisonError("recipe_version must be 1")
    if recipe.get("comparison_mode") != "keyed":
        raise ParisonError("comparison_mode must be 'keyed'")
    keys = recipe.get("keys")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k for k in keys) or len(keys) != len(set(keys)):
        raise ParisonError("keys must be a nonempty list of unique column names")
    scope = recipe.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"snapshot", "cutoff", "filters", "completeness", "expected_empty"}:
        raise ParisonError("scope must contain exactly snapshot, cutoff, filters, completeness and expected_empty")
    for field in ("snapshot", "cutoff"):
        if not isinstance(scope[field], str) or not scope[field]:
            raise ParisonError(f"scope.{field} must be a nonempty string")
    if not isinstance(scope["filters"], list) or not all(isinstance(item, str) and item for item in scope["filters"]):
        raise ParisonError("scope.filters must be a list of nonempty strings")
    if scope["completeness"] != "full":
        raise ParisonError("MVP comparisons require scope.completeness='full'")
    if not isinstance(scope["expected_empty"], bool):
        raise ParisonError("scope.expected_empty must be a boolean")
    identity = recipe.get("identity", {})
    if identity != {"null_keys": "reject", "duplicates": "reject"}:
        raise ParisonError("identity must reject null_keys and duplicates")
    if not isinstance(recipe.get("nulls_equal"), bool):
        raise ParisonError("nulls_equal must be an explicit boolean")
    columns = recipe.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ParisonError("columns must be a nonempty object")
    if not set(keys) <= set(columns):
        raise ParisonError("every key must have a column policy")
    for name, policy in columns.items():
        if not isinstance(policy, dict):
            raise ParisonError(f"columns.{name} must be an object")
        _unknown(policy, _COLUMN_KEYS, f"columns.{name}")
        if policy.get("type") not in _TYPES:
            raise ParisonError(f"columns.{name}.type is unsupported")
        comparison = policy.get("comparison", "exact")
        if comparison not in {"exact", "numeric"}:
            raise ParisonError(f"columns.{name}.comparison is unsupported")
        timezone = policy.get("timezone")
        if policy["type"] == "timestamp":
            if timezone != "require-aware":
                raise ParisonError(f"columns.{name}.timezone must be 'require-aware'")
        elif timezone is not None:
            raise ParisonError(f"columns.{name}.timezone is only valid for timestamps")
        scale = policy.get("scale")
        if policy["type"] == "decimal":
            if not isinstance(scale, int) or isinstance(scale, bool) or scale < 0:
                raise ParisonError(f"columns.{name}.scale must be a non-negative integer")
        elif scale is not None:
            raise ParisonError(f"columns.{name}.scale is only valid for decimals")
        if name in keys and comparison != "exact":
            raise ParisonError(f"key column {name} must use exact comparison")
        tolerance = policy.get("tolerance")
        if comparison == "numeric":
            if policy["type"] not in {"integer", "decimal", "float"}:
                raise ParisonError(f"numeric comparison requires a numeric type for {name}")
            if not isinstance(tolerance, dict) or set(tolerance) != {"formula", "absolute", "relative"}:
                raise ParisonError(f"columns.{name}.tolerance must define formula, absolute and relative")
            if tolerance["formula"] != "symmetric-v1":
                raise ParisonError(f"columns.{name} requires symmetric-v1 tolerance")
            try:
                values = [Decimal(str(tolerance[k])) for k in ("absolute", "relative")]
            except InvalidOperation as exc:
                raise ParisonError(f"columns.{name} tolerance is not numeric") from exc
            if any(not v.is_finite() or v < 0 for v in values):
                raise ParisonError(f"columns.{name} tolerances must be finite and non-negative")
        elif tolerance is not None:
            raise ParisonError(f"columns.{name}.tolerance requires numeric comparison")
    excluded = recipe.get("excluded_columns", {})
    if not isinstance(excluded, dict) or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in excluded.items()):
        raise ParisonError("excluded_columns must map column names to nonempty rationales")
    overlap = set(columns) & set(excluded)
    if overlap:
        raise ParisonError(f"columns cannot also be excluded: {', '.join(sorted(overlap))}")
    mappings = recipe.get("column_mappings", {})
    if not isinstance(mappings, dict):
        raise ParisonError("column_mappings must be an object")
    if not set(mappings) <= set(columns):
        raise ParisonError("every column mapping must name a canonical column")
    for name, mapping in mappings.items():
        if not isinstance(mapping, dict) or set(mapping) != {"baseline", "candidate"}:
            raise ParisonError(f"column_mappings.{name} must contain exactly baseline and candidate")
        if not all(isinstance(value, str) and value for value in mapping.values()):
            raise ParisonError(f"column_mappings.{name} source names must be nonempty strings")
    for side in ("baseline", "candidate"):
        source_names = [mappings.get(name, {}).get(side, name) for name in columns]
        if len(source_names) != len(set(source_names)):
            raise ParisonError(f"column_mappings must use unique {side} source columns")
        mapped_exclusions = set(source_names) & set(excluded)
        if mapped_exclusions:
            raise ParisonError(f"mapped source columns cannot also be excluded: {', '.join(sorted(mapped_exclusions))}")
    output = recipe.get("output", {"sensitivity": "summary"})
    if not isinstance(output, dict) or set(output) != {"sensitivity"} or output["sensitivity"] not in {"summary", "raw"}:
        raise ParisonError("output must contain sensitivity='summary' or sensitivity='raw'")
    return recipe


def _parse(raw: Any, policy: dict[str, Any], column: str) -> Any:
    kind = policy["type"]
    if raw is None:
        return None
    if kind == "string":
        return str(raw)
    if raw == "":
        return None
    try:
        if kind == "integer":
            return int(raw) if not isinstance(raw, float) or raw.is_integer() else (_ for _ in ()).throw(ValueError())
        if kind == "decimal":
            value = Decimal(str(raw))
            if not value.is_finite():
                raise ValueError("non-finite decimal")
            if max(-value.as_tuple().exponent, 0) > policy["scale"]:
                raise ValueError(f"value exceeds configured scale {policy['scale']}")
            return value
        if kind == "float":
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError("non-finite float")
            return value
        if kind == "boolean":
            if isinstance(raw, bool):
                return raw
            if raw == "true":
                return True
            if raw == "false":
                return False
            raise ValueError("expected true or false")
        if kind == "date":
            return date.fromisoformat(str(raw))
        if kind == "timestamp":
            value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if value.tzinfo is None:
                raise ValueError("timestamp requires an explicit timezone")
            return value
    except (ValueError, TypeError, InvalidOperation) as exc:
        detail = str(exc) or "invalid value"
        raise ParisonError(f"cannot parse column {column} as {kind}: {detail}") from exc
    raise AssertionError(kind)


def _source_name(recipe: dict[str, Any], name: str, side: str) -> str:
    return recipe.get("column_mappings", {}).get(name, {}).get(side, name)


def _validate_headers(path: Path, headers: list[str], recipe: dict[str, Any], side: str) -> None:
    if len(headers) != len(set(headers)):
        raise ParisonError(f"duplicate column names in {path}")
    expected = {_source_name(recipe, name, side) for name in recipe["columns"]}
    missing = expected - set(headers)
    extra = set(headers) - expected - set(recipe.get("excluded_columns", {}))
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing=" + ",".join(sorted(missing)))
        if extra:
            parts.append("unexpected=" + ",".join(sorted(extra)))
        raise ParisonError(f"schema mismatch in {path}: {'; '.join(parts)}")


def _sqlite_source(source: str | Path) -> tuple[Path, str] | None:
    text = str(source)
    if not text.startswith("sqlite:"):
        return None
    locator = text.removeprefix("sqlite:")
    if "?" in locator or "#" not in locator:
        raise ParisonError("SQLite locator must be sqlite:path#table without parameters")
    path_text, table = locator.rsplit("#", 1)
    if not path_text or not table:
        raise ParisonError("SQLite locator requires a database path and table")
    return Path(path_text), table


def _source_path(source: str | Path) -> Path:
    sqlite_source = _sqlite_source(source)
    return sqlite_source[0] if sqlite_source else Path(source)


def _source_paths(source: str | Path) -> tuple[Path, ...]:
    path = _source_path(source)
    if _sqlite_source(source) or not path.is_dir():
        return (path,)
    if path.is_symlink():
        raise ParisonError(f"partitioned input must not be a symlink: {path}")
    try:
        paths = tuple(sorted((item for item in path.iterdir() if not item.name.startswith(".")), key=lambda item: item.name))
    except OSError as exc:
        raise ParisonError(f"cannot inspect partitioned input {path}: {exc}") from exc
    if not paths:
        raise ParisonError(f"partitioned input has no files: {path}")
    if any(item.is_symlink() or not item.is_file() for item in paths):
        raise ParisonError(f"partitioned input must contain only regular non-symlink files: {path}")
    formats = {_FILE_FORMATS.get(item.suffix.lower()) for item in paths}
    if None in formats or len(formats) != 1:
        raise ParisonError(f"partitioned input must contain one supported file format: {path}")
    return paths


def _source_digest(source: str | Path) -> str:
    paths = _source_paths(source)
    if len(paths) == 1 and not _source_path(source).is_dir():
        return _digest(paths[0])
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_digest(path)))
    return digest.hexdigest()


def _source_bytes(source: str | Path) -> int:
    try:
        return sum(path.stat().st_size for path in _source_paths(source))
    except OSError as exc:
        raise ParisonError(f"cannot inspect inputs: {exc}") from exc


def _source_metadata(source: str | Path, digest: str) -> dict[str, Any]:
    path = _source_path(source)
    paths = _source_paths(source)
    format_name = "sqlite" if _sqlite_source(source) else _FILE_FORMATS.get(paths[0].suffix.lower(), path.suffix.lower().lstrip("."))
    metadata = {"sha256": digest, "bytes": _source_bytes(source), "format": format_name}
    sqlite_source = _sqlite_source(source)
    if sqlite_source:
        metadata.update(format="sqlite", table=sqlite_source[1])
    elif path.is_dir():
        metadata["partitions"] = len(paths)
    return metadata


def _sqlite_rows(source: str | Path, max_rows: int):
    path, table = _sqlite_source(source) or (None, None)
    assert path is not None and table is not None
    if path.is_symlink() or not path.is_file():
        raise ParisonError(f"SQLite database must be a regular non-symlink file: {path}")
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal")):
        raise ParisonError(f"SQLite database has an active journal sidecar: {path}")
    cursors = []
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        cursors.append(connection.execute("PRAGMA query_only=ON"))
        lookup = connection.execute("SELECT type FROM sqlite_schema WHERE name=?", (table,))
        cursors.append(lookup)
        found = lookup.fetchone()
        if found != ("table",):
            raise ParisonError(f"SQLite object is not an ordinary table: {table}")
        cursor = connection.execute(f'SELECT * FROM "{table.replace(chr(34), chr(34) * 2)}"')
        cursors.append(cursor)
        headers = [item[0] for item in cursor.description or []]
        if not headers or any(not name for name in headers) or len(headers) != len(set(headers)):
            raise ParisonError(f"SQLite table has empty or duplicate columns: {table}")
        yield headers, None
        for row_count, values in enumerate(cursor):
            if row_count >= max_rows:
                raise ParisonError(f"row count in {source} exceeds limit {max_rows}")
            if any(isinstance(value, bytes) for value in values):
                raise ParisonError(f"SQLite table contains an unsupported BLOB value: {table}")
            yield headers, dict(zip(headers, values))
    except ParisonError:
        raise
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot read SQLite table {table} from {path}: {exc}") from exc
    finally:
        for opened_cursor in reversed(cursors):
            opened_cursor.close()
        if "connection" in locals():
            connection.close()


def _jsonl_record(line: str, path: Path, line_number: int) -> dict[str, Any]:
    if not line.strip():
        raise ParisonError(f"blank JSON Lines record at line {line_number} in {path}")

    def object_pairs(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ParisonError(f"duplicate JSON key at line {line_number} in {path}")
        return value

    try:
        value = json.loads(
            line, object_pairs_hook=object_pairs, parse_int=str, parse_float=str,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ParisonError(f"cannot parse JSON at line {line_number} in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ParisonError(f"JSON Lines record {line_number} in {path} must be an object")
    if any(not isinstance(name, str) or not name for name in value):
        raise ParisonError(f"JSON Lines record {line_number} in {path} has an empty or invalid field name")
    if any(isinstance(item, (dict, list)) for item in value.values()):
        raise ParisonError(f"JSON Lines record {line_number} in {path} contains a nested value")
    return {name: ("true" if item is True else "false" if item is False else item) for name, item in value.items()}


def _iter_jsonl(path: Path, max_rows: int):
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError as exc:
        raise ParisonError(f"cannot read {path}: {exc}") from exc
    with handle:
        headers = None
        try:
            for line_number, line in enumerate(handle, 1):
                if line_number > max_rows:
                    raise ParisonError(f"row count in {path} exceeds limit {max_rows}")
                row = _jsonl_record(line, path, line_number)
                if headers is None:
                    headers = list(row)
                elif set(row) != set(headers):
                    raise ParisonError(f"inconsistent JSON Lines fields at line {line_number} in {path}")
                yield row
        except UnicodeDecodeError as exc:
            raise ParisonError(f"cannot parse {path}: {exc}") from exc
        if headers is None:
            raise ParisonError(f"input has no schema: {path}")


def _read(path: str | Path, recipe: dict[str, Any], max_rows: int, side: str) -> tuple[list[dict[str, Any]], list[str]]:
    raw_rows = list(_iter_input_rows(path, recipe, max_rows, side))
    rows = [
        {name: _parse(row.get(_source_name(recipe, name, side)), policy, name) for name, policy in recipe["columns"].items()}
        for row in raw_rows
    ]
    return rows, []


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ParisonError(f"cannot read {path}: {exc}") from exc
    return digest.hexdigest()


def _input_columns(path: str | Path) -> list[str]:
    source_path = _source_path(path)
    if source_path.is_dir():
        schemas = [_input_columns(partition) for partition in _source_paths(path)]
        if any(set(schema) != set(schemas[0]) for schema in schemas[1:]):
            raise ParisonError(f"partitioned input has inconsistent schemas: {source_path}")
        return schemas[0]
    if _sqlite_source(path):
        rows = _sqlite_rows(path, 1)
        try:
            columns, _ = next(rows)
            return columns
        finally:
            rows.close()
    path = Path(path)
    if path.is_symlink():
        raise ParisonError(f"input must not be a symlink: {path}")
    if not path.is_file():
        raise ParisonError(f"input is not a regular file: {path}")
    if path.suffix.lower() == ".csv":
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                columns = next(csv.reader(handle, strict=True), [])
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            raise ParisonError(f"cannot read schema from {path}: {exc}") from exc
    elif path.suffix.lower() in {".jsonl", ".ndjson"}:
        try:
            with path.open("r", encoding="utf-8") as handle:
                line = next(handle, "")
            columns = list(_jsonl_record(line, path, 1)) if line else []
        except (OSError, UnicodeDecodeError) as exc:
            raise ParisonError(f"cannot read schema from {path}: {exc}") from exc
    elif path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import polars as pl
        except ImportError as exc:
            raise ParisonError("Parquet support requires: pip install 'parison[parquet]'") from exc
        try:
            columns = pl.scan_parquet(path).collect_schema().names()
        except Exception as exc:
            raise ParisonError(f"cannot read schema from {path}: {exc}") from exc
    else:
        raise ParisonError(f"unsupported input format for {path}; use .csv, .jsonl or .parquet")
    if not columns:
        raise ParisonError(f"input has no schema: {path}")
    if any(not isinstance(name, str) or not name for name in columns) or len(columns) != len(set(columns)):
        raise ParisonError(f"input has empty or duplicate column names: {path}")
    return columns


def _suggest_type(values: list[Any]) -> dict[str, Any]:
    present = [str(value) for value in values if value not in (None, "")]
    if not present:
        return {"type": "string", "comparison": "exact"}
    lowered = {value.lower() for value in present}
    if lowered <= {"true", "false"}:
        return {"type": "boolean", "comparison": "exact"}
    if all(value.lstrip("-").isdigit() and not (value.lstrip("-").startswith("0") and len(value.lstrip("-")) > 1) for value in present):
        return {"type": "integer", "comparison": "exact"}
    try:
        decimals = [Decimal(value) for value in present]
        if all(value.is_finite() for value in decimals):
            scale = max(max(-value.as_tuple().exponent, 0) for value in decimals)
            return {"type": "decimal", "comparison": "exact", "scale": scale}
    except InvalidOperation:
        pass
    try:
        parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in present]
        if all(value.tzinfo is not None for value in parsed):
            return {"type": "timestamp", "comparison": "exact", "timezone": "require-aware"}
    except ValueError:
        pass
    try:
        if all(date.fromisoformat(value) for value in present):
            return {"type": "date", "comparison": "exact"}
    except ValueError:
        pass
    return {"type": "string", "comparison": "exact"}


def _suggest_keys(columns: list[str], baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> list[str]:
    if not baseline or not candidate:
        return [columns[0]]

    def distinct_counts(names: list[str]) -> list[int]:
        counts = []
        for rows in (baseline, candidate):
            values = [tuple(row[name] for name in names) for row in rows]
            if any(value in (None, "") for key in values for value in key):
                return [-1, -1]
            counts.append(len(set(values)))
        return counts

    identifiers = [name for name in columns if any(token in name.lower().replace("_", " ").split() for token in ("id", "key", "code"))]
    chosen: list[str] = []
    for pool in (identifiers, [name for name in columns if name not in identifiers]):
        remaining = list(pool)
        while remaining:
            best = max(remaining, key=lambda name: min(distinct_counts([*chosen, name])))
            chosen.append(best)
            remaining.remove(best)
            if distinct_counts(chosen) == [len(baseline), len(candidate)]:
                return chosen
    return [columns[0]]


def draft_recipe(baseline: str | Path, candidate: str | Path, max_input_bytes: int = 1_000_000_000) -> dict[str, Any]:
    if max_input_bytes <= 0:
        raise ParisonError("max_input_bytes must be positive")
    for source in (baseline, candidate):
        path = _source_path(source)
        if path.is_symlink():
            raise ParisonError(f"input must not be a symlink: {path}")
        if not path.is_file() and not path.is_dir():
            raise ParisonError(f"input is not a regular file or partition directory: {path}")
        _source_paths(source)
    input_bytes = _source_bytes(baseline) + _source_bytes(candidate)
    if input_bytes > max_input_bytes:
        raise ParisonError(f"combined input size {input_bytes} exceeds limit {max_input_bytes} bytes")
    before = {str(source): _source_digest(source) for source in (baseline, candidate)}
    baseline_columns, candidate_columns = _input_columns(baseline), _input_columns(candidate)
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being inspected")
    candidate_names = set(candidate_columns)
    shared = [name for name in baseline_columns if name in candidate_names]
    if not shared:
        raise ParisonError("inputs have no shared columns")
    shared_names = set(shared)
    excluded = [name for name in baseline_columns + candidate_columns if name not in shared_names]
    inspection_recipe = {
        "columns": {name: {"type": "string", "comparison": "exact"} for name in shared},
        "excluded_columns": {name: "inspection" for name in excluded},
    }
    baseline_rows, _ = _read(baseline, inspection_recipe, 5_000_000, "baseline")
    candidate_rows, _ = _read(candidate, inspection_recipe, 5_000_000, "candidate")
    cutoff = datetime.fromtimestamp(
        max(path.stat().st_mtime for source in (baseline, candidate) for path in _source_paths(source)), timezone.utc
    ).isoformat().replace("+00:00", "Z")
    return {
        "recipe_version": 1,
        "comparison_mode": "keyed",
        "keys": _suggest_keys(shared, baseline_rows, candidate_rows),
        "scope": {
            "snapshot": f"{_source_path(baseline).stem} vs {_source_path(candidate).stem}",
            "cutoff": cutoff,
            "filters": [],
            "completeness": "full",
            "expected_empty": not baseline_rows and not candidate_rows,
        },
        "identity": {"null_keys": "reject", "duplicates": "reject"},
        "nulls_equal": True,
        "columns": {name: _suggest_type([row[name] for row in baseline_rows + candidate_rows]) for name in shared},
        "column_mappings": {},
        "excluded_columns": {
            name: "present only in baseline" if name in baseline_columns else "present only in candidate"
            for name in excluded
        },
        "output": {"sensitivity": "summary"},
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    return value


def _key_text(key: tuple[Any, ...]) -> list[Any]:
    return [_json_value(value) for value in key]


def _index(rows: list[dict[str, Any]], keys: list[str], side: str) -> tuple[dict[tuple[Any, ...], dict[str, Any]], list[str]]:
    problems: list[str] = []
    values = [tuple(row[k] for k in keys) for row in rows]
    null_count = sum(any(v is None for v in key) for key in values)
    duplicates = sorted((_key_text(k) for k, n in Counter(values).items() if n > 1), key=str)
    if null_count:
        problems.append(f"{side} has {null_count} row(s) with null key components")
    if duplicates:
        problems.append(f"{side} has {len(duplicates)} duplicate key(s)")
    return dict(zip(values, rows)), problems


def _iter_input_rows(path: str | Path, recipe: dict[str, Any], max_rows: int, side: str):
    source_path = _source_path(path)
    if source_path.is_dir():
        row_count = 0
        for partition in _source_paths(path):
            for row in _iter_input_rows(partition, recipe, max_rows, side):
                if row_count >= max_rows:
                    raise ParisonError(f"row count in {source_path} exceeds limit {max_rows}")
                row_count += 1
                yield row
        return
    if _sqlite_source(path):
        stream = _sqlite_rows(path, max_rows)
        headers, _ = next(stream)
        _validate_headers(Path(str(path)), headers, recipe, side)
        for _, row in stream:
            yield row
        return
    path = Path(path)
    if path.is_symlink():
        raise ParisonError(f"input must not be a symlink: {path}")
    if not path.is_file():
        raise ParisonError(f"input is not a regular file: {path}")
    if path.suffix.lower() == ".csv":
        try:
            handle = path.open("r", encoding="utf-8", newline="")
        except OSError as exc:
            raise ParisonError(f"cannot read {path}: {exc}") from exc
        with handle:
            try:
                reader = csv.DictReader(handle, strict=True)
                _validate_headers(path, reader.fieldnames or [], recipe, side)
                for row_count, raw in enumerate(reader):
                    if row_count >= max_rows:
                        raise ParisonError(f"row count in {path} exceeds limit {max_rows}")
                    if None in raw or any(value is None for value in raw.values()):
                        raise ParisonError(f"ragged CSV row {reader.line_num} in {path}")
                    yield raw
            except (csv.Error, UnicodeDecodeError) as exc:
                raise ParisonError(f"cannot parse {path}: {exc}") from exc
    elif path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import polars as pl
        except ImportError as exc:
            raise ParisonError("Parquet support requires: pip install 'parison[parquet]'") from exc
        try:
            row_count = pl.scan_parquet(path).select(pl.len()).collect().item()
            if row_count > max_rows:
                raise ParisonError(f"row count in {path} exceeds limit {max_rows}")
            frame = pl.read_parquet(path)
        except ParisonError:
            raise
        except Exception as exc:
            raise ParisonError(f"cannot read {path}: {exc}") from exc
        _validate_headers(path, frame.columns, recipe, side)
        yield from frame.iter_rows(named=True)
    elif path.suffix.lower() in {".jsonl", ".ndjson"}:
        rows = _iter_jsonl(path, max_rows)
        try:
            first = next(rows)
        except StopIteration:
            return
        _validate_headers(path, list(first), recipe, side)
        yield first
        yield from rows
    else:
        raise ParisonError(f"unsupported input format for {path}; use .csv, .jsonl or .parquet")


def _read_stream_index(
    path: Path, recipe: dict[str, Any], max_rows: int, side: str
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], int, list[str]]:
    rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicates: set[tuple[Any, ...]] = set()
    null_count = row_count = 0
    for raw in _iter_input_rows(path, recipe, max_rows, side):
        row_count += 1
        row = {name: _parse(raw.get(_source_name(recipe, name, side)), policy, name) for name, policy in recipe["columns"].items()}
        key = tuple(row[name] for name in recipe["keys"])
        null_count += any(value is None for value in key)
        if key in rows:
            duplicates.add(key)
        rows[key] = row
    problems = []
    if null_count:
        problems.append(f"{side} has {null_count} row(s) with null key components")
    if duplicates:
        problems.append(f"{side} has {len(duplicates)} duplicate key(s)")
    return rows, row_count, problems


def _classify(left: Any, right: Any, policy: dict[str, Any], nulls_equal: bool) -> tuple[str, str | None, str | None]:
    if left is None and right is None:
        return ("exact" if nulls_equal else "different"), None, None
    if left == right:
        return "exact", None, None
    if left is None or right is None or policy.get("comparison", "exact") == "exact":
        return "different", None, None
    lval, rval = Decimal(str(left)), Decimal(str(right))
    tolerance = policy["tolerance"]
    delta = abs(rval - lval)
    allowance = Decimal(str(tolerance["absolute"])) + Decimal(str(tolerance["relative"])) * max(abs(lval), abs(rval))
    return ("within_tolerance" if delta <= allowance else "different"), str(delta), str(allowance)


def _compare_stream_summary(
    path: Path,
    recipe: dict[str, Any],
    max_rows: int,
    left: dict[tuple[Any, ...], dict[str, Any]],
    prior_problems: list[str],
) -> dict[str, Any]:
    keys = recipe["keys"]
    compared = [name for name in recipe["columns"] if name not in keys]
    field_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in compared}
    row_counts = {"exact": 0, "within_tolerance": 0, "different": 0}
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    null_count = candidate_only = discrepancy_count = row_count = 0
    for raw in _iter_input_rows(path, recipe, max_rows, "candidate"):
        row_count += 1
        row = {name: _parse(raw.get(_source_name(recipe, name, "candidate")), policy, name) for name, policy in recipe["columns"].items()}
        key = tuple(row[name] for name in keys)
        if any(value is None for value in key):
            null_count += 1
        if key in seen:
            duplicates.add(key)
            continue
        seen.add(key)
        if key not in left:
            candidate_only += 1
            continue
        row_class = "exact"
        for name in compared:
            classification, _, _ = _classify(left[key][name], row[name], recipe["columns"][name], recipe["nulls_equal"])
            field_counts[name][classification] += 1
            if classification == "different":
                row_class = "different"
            elif classification == "within_tolerance" and row_class == "exact":
                row_class = "within_tolerance"
            discrepancy_count += classification != "exact"
        row_counts[row_class] += 1
    problems = list(prior_problems)
    if null_count:
        problems.append(f"candidate has {null_count} row(s) with null key components")
    if duplicates:
        problems.append(f"candidate has {len(duplicates)} duplicate key(s)")
    if problems:
        field_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in compared}
        row_counts = {"exact": 0, "within_tolerance": 0, "different": 0}
        discrepancy_count = 0
    baseline_only = sum(key not in seen for key in left)
    return {
        "candidate": row_count,
        "common": len(left) - baseline_only,
        "baseline_only": baseline_only,
        "candidate_only": candidate_only,
        "field_counts": field_counts,
        "row_counts": row_counts,
        "field_discrepancy_count": discrepancy_count,
        "problems": problems,
    }


def compare(
    recipe_path: str | Path,
    baseline_path: str | Path,
    candidate_path: str | Path,
    sample_limit: int = 100,
    max_input_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
) -> dict[str, Any]:
    if sample_limit < 0:
        raise ParisonError("sample_limit must be non-negative")
    if max_input_bytes <= 0:
        raise ParisonError("max_input_bytes must be positive")
    if max_rows <= 0:
        raise ParisonError("max_rows must be positive")
    recipe_path = Path(recipe_path)
    recipe = load_recipe(recipe_path)
    input_bytes = _source_bytes(baseline_path) + _source_bytes(candidate_path)
    if input_bytes > max_input_bytes:
        raise ParisonError(f"combined input size {input_bytes} exceeds limit {max_input_bytes} bytes")
    before = {str(source): _source_digest(source) for source in (baseline_path, candidate_path)}
    keys = recipe["keys"]
    raw_output = recipe["output"]["sensitivity"] == "raw"
    streaming = not raw_output
    if streaming:
        left, baseline_count, left_problems = _read_stream_index(baseline_path, recipe, max_rows, "baseline")
    else:
        baseline, _ = _read(baseline_path, recipe, max_rows, "baseline")
        baseline_count = len(baseline)
        left, left_problems = _index(baseline, keys, "baseline")
        del baseline
    discrepancies: list[dict[str, Any]] = []
    if streaming:
        summary = _compare_stream_summary(candidate_path, recipe, max_rows, left, left_problems)
        candidate_count = summary["candidate"]
        common_count = summary["common"]
        baseline_only_count = summary["baseline_only"]
        candidate_only_count = summary["candidate_only"]
        field_counts = summary["field_counts"]
        row_counts = summary["row_counts"]
        discrepancy_count = summary["field_discrepancy_count"]
        problems = summary["problems"]
    else:
        candidate, _ = _read(candidate_path, recipe, max_rows, "candidate")
        right, right_problems = _index(candidate, keys, "candidate")
        problems = left_problems + right_problems
        common = set(left) & set(right)
        baseline_only = set(left) - set(right)
        candidate_only = set(right) - set(left)
        candidate_count = len(candidate)
        common_count = len(common)
        baseline_only_count = len(baseline_only)
        candidate_only_count = len(candidate_only)
        field_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in recipe["columns"] if name not in keys}
        row_counts = {"exact": 0, "within_tolerance": 0, "different": 0}
        discrepancy_count = 0
        if raw_output:
            for classification, missing_keys in (("baseline_only", baseline_only), ("candidate_only", candidate_only)):
                for key in sorted(missing_keys, key=lambda item: tuple(str(v) for v in item)):
                    if len(discrepancies) >= sample_limit:
                        break
                    discrepancies.append({"kind": "record", "key": _key_text(key), "classification": classification})
    if not streaming and not problems:
        for key in sorted(common, key=lambda item: tuple(str(v) for v in item)):
            row_class = "exact"
            for name, policy in recipe["columns"].items():
                if name in keys:
                    continue
                classification, delta, allowance = _classify(left[key][name], right[key][name], policy, recipe["nulls_equal"])
                field_counts[name][classification] += 1
                if classification == "different":
                    row_class = "different"
                elif classification == "within_tolerance" and row_class == "exact":
                    row_class = "within_tolerance"
                if classification != "exact":
                    discrepancy_count += 1
                    if raw_output and len(discrepancies) < sample_limit:
                        discrepancies.append({
                            "kind": "field",
                            "key": _key_text(key),
                            "field": name,
                            "baseline": _json_value(left[key][name]),
                            "candidate": _json_value(right[key][name]),
                            "classification": classification,
                            "delta": delta,
                            "allowance": allowance,
                        })
            row_counts[row_class] += 1
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being read")
    empty = not baseline_count or not candidate_count
    if empty and not recipe["scope"]["expected_empty"]:
        problems.append("nonempty comparable inputs are required")
    outcome = "INCONCLUSIVE" if problems else ("FAIL" if baseline_only_count or candidate_only_count or row_counts["different"] else "PASS")
    return {
        "schema_version": 1,
        "outcome": outcome,
        "complete": not problems,
        "sensitivity": recipe["output"]["sensitivity"],
        "runtime": _runtime_info((baseline_path, candidate_path)),
        "resource_limits": {"max_input_bytes": max_input_bytes, "max_rows_per_input": max_rows},
        "scope": recipe["scope"],
        "keys": keys,
        "policy": {"keys": keys, "nulls_equal": recipe["nulls_equal"], "sensitivity": recipe["output"]["sensitivity"]},
        "column_policies": recipe["columns"],
        "column_mappings": recipe.get("column_mappings", {}),
        "problems": problems,
        "counts": {
            "baseline": baseline_count, "candidate": candidate_count, "common_keys": common_count,
            "baseline_only": baseline_only_count, "candidate_only": candidate_only_count,
            "matched_exact": row_counts["exact"], "matched_within_tolerance": row_counts["within_tolerance"],
            "matched_with_required_difference": row_counts["different"],
        },
        "field_counts": field_counts,
        "field_discrepancy_count": discrepancy_count,
        "discrepancy_count": discrepancy_count + baseline_only_count + candidate_only_count,
        "discrepancy_sample": discrepancies,
        "discrepancy_sample_limit": sample_limit if raw_output else 0,
        "excluded_columns": recipe.get("excluded_columns", {}),
        "inputs": {
            "baseline": _source_metadata(baseline_path, before[str(baseline_path)]),
            "candidate": _source_metadata(candidate_path, before[str(candidate_path)]),
        },
        "recipe_sha256": _digest(recipe_path),
    }


def _report(result: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))
    counts = "".join(f"<tr><th>{esc(k.replace('_', ' '))}</th><td>{v}</td></tr>" for k, v in result["counts"].items())
    problems = "".join(f"<li>{esc(item)}</li>" for item in result["problems"]) or "<li>None</li>"
    scope = result.get("scope") or {}
    scope_rows = "".join(
        f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(', '.join(value) if isinstance(value, list) else value)}</td></tr>"
        for key, value in scope.items()
    ) or '<tr><td colspan="2">Unavailable</td></tr>'
    policy_rows = "".join(
        f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(', '.join(value) if isinstance(value, list) else value)}</td></tr>"
        for key, value in result.get("policy", {}).items()
    ) or '<tr><td colspan="2">Unavailable</td></tr>'
    column_policy_rows = "".join(
        f"<tr><th>{esc(name)}</th><td>{esc(result.get('column_mappings', {}).get(name, {}).get('baseline', name))}</td><td>{esc(result.get('column_mappings', {}).get(name, {}).get('candidate', name))}</td><td>{esc(policy['type'])}</td><td>{esc(policy.get('comparison', 'exact'))}</td><td>{esc(json.dumps({key: value for key, value in policy.items() if key not in {'type', 'comparison'}}, sort_keys=True))}</td></tr>"
        for name, policy in result.get("column_policies", {}).items()
    ) or '<tr><td colspan="6">Unavailable</td></tr>'
    field_rows = "".join(
        f"<tr data-exact=\"{values['exact']}\" data-within_tolerance=\"{values['within_tolerance']}\" data-different=\"{values['different']}\"><th>{esc(name)}</th><td>{values['exact']}</td><td>{values['within_tolerance']}</td><td>{values['different']}</td></tr>"
        for name, values in result["field_counts"].items()
    ) or '<tr><td colspan="4">No comparable fields</td></tr>'
    exclusion_rows = "".join(
        f"<tr><th>{esc(name)}</th><td>{esc(reason)}</td></tr>"
        for name, reason in result["excluded_columns"].items()
    ) or '<tr><td colspan="2">None</td></tr>'
    runtime_rows = "".join(f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(value)}</td></tr>" for key, value in result["runtime"].items())
    limit_rows = "".join(f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(value)}</td></tr>" for key, value in result["resource_limits"].items()) or '<tr><td colspan="2">Unavailable</td></tr>'
    input_rows = "".join(
        f"<tr><th>{esc(side)}</th><td>{esc(values['bytes'])}</td><td><code>{esc(values['sha256'])}</code></td></tr>"
        for side, values in result["inputs"].items()
    ) or '<tr><td colspan="3">Unavailable</td></tr>'
    if result["sensitivity"] == "raw":
        rows = "".join(
            f'<tr data-key="{esc(row.get("key", ""))}" data-field="{esc(row.get("field", ""))}" data-class="{esc(row.get("classification", ""))}">' + "".join(f"<td>{esc(row.get(k, ''))}</td>" for k in ("kind", "key", "field", "baseline", "candidate", "classification", "delta", "allowance")) + "</tr>"
            for row in result["discrepancy_sample"]
        ) or '<tr><td colspan="8">No sampled discrepancies</td></tr>'
        evidence = f"""<h2>Raw discrepancy evidence</h2><p><strong>Sensitive:</strong> this report contains source keys and values. Showing {len(result['discrepancy_sample'])} of {result['discrepancy_count']} discrepancy items.</p>
<div class="filters"><label>Key contains <input id="raw-key" type="search"></label><label>Field <input id="raw-field" type="search"></label><label>Class <select id="raw-class"><option value="">All</option><option>baseline_only</option><option>candidate_only</option><option>within_tolerance</option><option>different</option></select></label></div><p id="raw-count" role="status" aria-live="polite">Showing {len(result['discrepancy_sample'])} of {len(result['discrepancy_sample'])} sampled items</p>
<table id="raw-evidence"><thead><tr><th>Kind</th><th>Key</th><th>Field</th><th>Baseline</th><th>Candidate</th><th>Class</th><th>Delta</th><th>Allowance</th></tr></thead><tbody>{rows}</tbody></table>"""
    else:
        evidence = "<h2>Privacy</h2><p>Summary mode stores no keys or raw field values. Field and record counts are complete.</p>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Parison report: {esc(result['outcome'])}</title><style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18202a}}h1{{color:{'#14733b' if result['outcome']=='PASS' else '#a22'}}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #ccd3da;padding:.5rem;text-align:left;vertical-align:top}}th{{background:#f3f5f7}}code{{overflow-wrap:anywhere}}.filters{{display:flex;gap:1rem;flex-wrap:wrap}}label{{display:grid;gap:.25rem}}input,select{{font:inherit;padding:.35rem}}</style>
<main><h1>{esc(result['outcome'])}</h1><p>Complete evaluation: <strong>{str(result['complete']).lower()}</strong></p>
<h2>Scope</h2><table>{scope_rows}</table><h2>Comparison policy</h2><table>{policy_rows}</table>
<h2>Column policies</h2><table><thead><tr><th>Field</th><th>Baseline column</th><th>Candidate column</th><th>Type</th><th>Comparison</th><th>Additional rules</th></tr></thead><tbody>{column_policy_rows}</tbody></table>
<h2>Record counts</h2><table>{counts}</table>
<h2>Field summary</h2><label>Show fields with <select id="field-class"><option value="">any result</option><option value="exact">exact matches</option><option value="within_tolerance">within-tolerance matches</option><option value="different">differences</option></select></label><p id="field-count" role="status" aria-live="polite">Showing {len(result['field_counts'])} of {len(result['field_counts'])} fields</p><table id="field-summary"><thead><tr><th>Field</th><th>Exact</th><th>Within tolerance</th><th>Different</th></tr></thead><tbody>{field_rows}</tbody></table>
<h2>Excluded columns</h2><table><thead><tr><th>Column</th><th>Rationale</th></tr></thead><tbody>{exclusion_rows}</tbody></table>
<h2>Preflight issues</h2><ul>{problems}</ul>{evidence}
<h2>Inputs</h2><table><thead><tr><th>Side</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{input_rows}</tbody></table>
<h2>Resource limits</h2><table>{limit_rows}</table><h2>Runtime</h2><table>{runtime_rows}</table>
<h2>Provenance</h2><p>Recipe SHA-256: <code>{esc(result.get('recipe_sha256') or 'unavailable')}</code></p></main><script>
const fieldClass=document.querySelector('#field-class');
const setCount=(id,rows,label)=>document.querySelector(id).textContent='Showing '+[...rows].filter(row=>!row.hidden).length+' of '+rows.length+' '+label;
const fieldRows=document.querySelectorAll('#field-summary tbody tr[data-exact]');
const filterFields=()=>{{fieldRows.forEach(row=>row.hidden=fieldClass.value && Number(row.dataset[fieldClass.value])===0);setCount('#field-count',fieldRows,'fields');}};
fieldClass.addEventListener('change',filterFields);
filterFields();
const rawTable=document.querySelector('#raw-evidence');
if(rawTable){{const key=document.querySelector('#raw-key'),field=document.querySelector('#raw-field'),kind=document.querySelector('#raw-class'),rows=rawTable.querySelectorAll('tbody tr[data-class]');const filter=()=>{{rows.forEach(row=>row.hidden=!row.dataset.key.toLowerCase().includes(key.value.toLowerCase())||!row.dataset.field.toLowerCase().includes(field.value.toLowerCase())||(kind.value&&row.dataset.class!==kind.value));setCount('#raw-count',rows,'sampled items');}};key.addEventListener('input',filter);field.addEventListener('input',filter);kind.addEventListener('change',filter);filter();}}
</script></html>"""


def terminal_result(outcome: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "outcome": outcome,
        "complete": False,
        "sensitivity": "summary",
        "runtime": _runtime_info(),
        "resource_limits": {},
        "scope": None,
        "keys": [],
        "policy": {},
        "column_policies": {},
        "column_mappings": {},
        "problems": [message],
        "counts": {},
        "field_counts": {},
        "field_discrepancy_count": 0,
        "discrepancy_count": 0,
        "discrepancy_sample": [],
        "discrepancy_sample_limit": 0,
        "excluded_columns": {},
        "inputs": {},
        "recipe_sha256": None,
    }


def error_result(message: str) -> dict[str, Any]:
    return terminal_result("ERROR", message)


def publish(output: str | Path, result: dict[str, Any], recipe: dict[str, Any] | None) -> None:
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    os.chmod(stage, 0o700)
    try:
        (stage / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "report.html").write_text(_report(result), encoding="utf-8")
        names = ["result.json", "report.html"]
        if recipe is not None:
            (stage / "effective-recipe.json").write_text(json.dumps(recipe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            names.append("effective-recipe.json")
        files = {}
        for name in names:
            files[name] = _digest(stage / name)
        manifest = {
            "schema_version": 1,
            "complete": True,
            "outcome": result["outcome"],
            "sensitivity": result["sensitivity"],
            "runtime": result["runtime"],
            "files": files,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(stage, output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_bundle(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if directory.is_symlink() or not directory.is_dir():
        raise ParisonError(f"run is not a regular directory: {directory}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("complete") is not True:
        raise ParisonError("manifest is incomplete or unsupported")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ParisonError("manifest has no files")
    for name, expected in files.items():
        if not isinstance(name, str) or Path(name).name != name or not isinstance(expected, str):
            raise ParisonError("manifest contains an invalid file entry")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ParisonError(f"bundle file is missing or unsafe: {name}")
        if _digest(path) != expected:
            raise ParisonError(f"bundle file failed integrity check: {name}")
    return manifest
