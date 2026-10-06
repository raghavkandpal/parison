from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import platform
import shutil
import tempfile
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from importlib import metadata
from pathlib import Path
from typing import Any


OUTCOME_CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "INCONCLUSIVE": 3, "INTERRUPTED": 130}
_RECIPE_KEYS = {"recipe_version", "comparison_mode", "keys", "scope", "identity", "nulls_equal", "columns", "excluded_columns", "output"}
_COLUMN_KEYS = {"type", "comparison", "tolerance", "timezone", "scale"}
_TYPES = {"string", "integer", "decimal", "float", "boolean", "date", "timestamp"}


class ParityError(ValueError):
    pass


def _runtime_info(paths: tuple[Path, Path] | None = None) -> dict[str, Any]:
    try:
        version = metadata.version("parity-compare")
    except metadata.PackageNotFoundError:
        version = "source-tree"
    runtime = {
        "contract": "keyed-v1",
        "parity_version": version,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "machine": platform.machine(),
    }
    if paths and any(path.suffix.lower() in {".parquet", ".pq"} for path in paths):
        try:
            runtime["polars"] = metadata.version("polars")
        except metadata.PackageNotFoundError:
            runtime["polars"] = "unavailable"
    return runtime


def _unknown(mapping: dict[str, Any], allowed: set[str], where: str) -> None:
    extras = set(mapping) - allowed
    if extras:
        raise ParityError(f"unknown {where} field(s): {', '.join(sorted(extras))}")


def load_recipe(path: str | Path) -> dict[str, Any]:
    try:
        recipe = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParityError(f"cannot read recipe: {exc}") from exc
    if not isinstance(recipe, dict):
        raise ParityError("recipe must be a JSON object")
    _unknown(recipe, _RECIPE_KEYS, "recipe")
    if recipe.get("recipe_version") != 1:
        raise ParityError("recipe_version must be 1")
    if recipe.get("comparison_mode") != "keyed":
        raise ParityError("comparison_mode must be 'keyed'")
    keys = recipe.get("keys")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k for k in keys) or len(keys) != len(set(keys)):
        raise ParityError("keys must be a nonempty list of unique column names")
    scope = recipe.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"snapshot", "cutoff", "filters", "completeness", "expected_empty"}:
        raise ParityError("scope must contain exactly snapshot, cutoff, filters, completeness and expected_empty")
    for field in ("snapshot", "cutoff"):
        if not isinstance(scope[field], str) or not scope[field]:
            raise ParityError(f"scope.{field} must be a nonempty string")
    if not isinstance(scope["filters"], list) or not all(isinstance(item, str) and item for item in scope["filters"]):
        raise ParityError("scope.filters must be a list of nonempty strings")
    if scope["completeness"] != "full":
        raise ParityError("MVP comparisons require scope.completeness='full'")
    if not isinstance(scope["expected_empty"], bool):
        raise ParityError("scope.expected_empty must be a boolean")
    identity = recipe.get("identity", {})
    if identity != {"null_keys": "reject", "duplicates": "reject"}:
        raise ParityError("identity must reject null_keys and duplicates")
    if not isinstance(recipe.get("nulls_equal"), bool):
        raise ParityError("nulls_equal must be an explicit boolean")
    columns = recipe.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ParityError("columns must be a nonempty object")
    if not set(keys) <= set(columns):
        raise ParityError("every key must have a column policy")
    for name, policy in columns.items():
        if not isinstance(policy, dict):
            raise ParityError(f"columns.{name} must be an object")
        _unknown(policy, _COLUMN_KEYS, f"columns.{name}")
        if policy.get("type") not in _TYPES:
            raise ParityError(f"columns.{name}.type is unsupported")
        comparison = policy.get("comparison", "exact")
        if comparison not in {"exact", "numeric"}:
            raise ParityError(f"columns.{name}.comparison is unsupported")
        timezone = policy.get("timezone")
        if policy["type"] == "timestamp":
            if timezone != "require-aware":
                raise ParityError(f"columns.{name}.timezone must be 'require-aware'")
        elif timezone is not None:
            raise ParityError(f"columns.{name}.timezone is only valid for timestamps")
        scale = policy.get("scale")
        if policy["type"] == "decimal":
            if not isinstance(scale, int) or isinstance(scale, bool) or scale < 0:
                raise ParityError(f"columns.{name}.scale must be a non-negative integer")
        elif scale is not None:
            raise ParityError(f"columns.{name}.scale is only valid for decimals")
        if name in keys and comparison != "exact":
            raise ParityError(f"key column {name} must use exact comparison")
        tolerance = policy.get("tolerance")
        if comparison == "numeric":
            if policy["type"] not in {"integer", "decimal", "float"}:
                raise ParityError(f"numeric comparison requires a numeric type for {name}")
            if not isinstance(tolerance, dict) or set(tolerance) != {"formula", "absolute", "relative"}:
                raise ParityError(f"columns.{name}.tolerance must define formula, absolute and relative")
            if tolerance["formula"] != "symmetric-v1":
                raise ParityError(f"columns.{name} requires symmetric-v1 tolerance")
            try:
                values = [Decimal(str(tolerance[k])) for k in ("absolute", "relative")]
            except InvalidOperation as exc:
                raise ParityError(f"columns.{name} tolerance is not numeric") from exc
            if any(not v.is_finite() or v < 0 for v in values):
                raise ParityError(f"columns.{name} tolerances must be finite and non-negative")
        elif tolerance is not None:
            raise ParityError(f"columns.{name}.tolerance requires numeric comparison")
    excluded = recipe.get("excluded_columns", {})
    if not isinstance(excluded, dict) or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in excluded.items()):
        raise ParityError("excluded_columns must map column names to nonempty rationales")
    overlap = set(columns) & set(excluded)
    if overlap:
        raise ParityError(f"columns cannot also be excluded: {', '.join(sorted(overlap))}")
    output = recipe.get("output", {"sensitivity": "summary"})
    if not isinstance(output, dict) or set(output) != {"sensitivity"} or output["sensitivity"] not in {"summary", "raw"}:
        raise ParityError("output must contain sensitivity='summary' or sensitivity='raw'")
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
        raise ParityError(f"cannot parse column {column} as {kind}: {detail}") from exc
    raise AssertionError(kind)


def _validate_headers(path: Path, headers: list[str], recipe: dict[str, Any]) -> None:
    if len(headers) != len(set(headers)):
        raise ParityError(f"duplicate column names in {path}")
    missing = set(recipe["columns"]) - set(headers)
    extra = set(headers) - set(recipe["columns"]) - set(recipe.get("excluded_columns", {}))
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing=" + ",".join(sorted(missing)))
        if extra:
            parts.append("unexpected=" + ",".join(sorted(extra)))
        raise ParityError(f"schema mismatch in {path}: {'; '.join(parts)}")


def _read(path: Path, recipe: dict[str, Any], max_rows: int) -> tuple[list[dict[str, Any]], list[str]]:
    if path.is_symlink():
        raise ParityError(f"input must not be a symlink: {path}")
    if not path.is_file():
        raise ParityError(f"input is not a regular file: {path}")
    if path.suffix.lower() == ".csv":
        try:
            handle = path.open("r", encoding="utf-8", newline="")
        except OSError as exc:
            raise ParityError(f"cannot read {path}: {exc}") from exc
        with handle:
            try:
                reader = csv.DictReader(handle, strict=True)
                headers = reader.fieldnames or []
                if len(headers) != len(set(headers)):
                    raise ParityError(f"duplicate column names in {path}")
                raw_rows = []
                for row in reader:
                    if len(raw_rows) >= max_rows:
                        raise ParityError(f"row count in {path} exceeds limit {max_rows}")
                    if None in row or any(value is None for value in row.values()):
                        raise ParityError(f"ragged CSV row {reader.line_num} in {path}")
                    raw_rows.append(row)
            except (csv.Error, UnicodeDecodeError) as exc:
                raise ParityError(f"cannot parse {path}: {exc}") from exc
    elif path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import polars as pl
        except ImportError as exc:
            raise ParityError("Parquet support requires: pip install 'parity-compare[parquet]'") from exc
        try:
            row_count = pl.scan_parquet(path).select(pl.len()).collect().item()
            if row_count > max_rows:
                raise ParityError(f"row count in {path} exceeds limit {max_rows}")
            frame = pl.read_parquet(path)
        except ParityError:
            raise
        except Exception as exc:
            raise ParityError(f"cannot read {path}: {exc}") from exc
        headers = frame.columns
        raw_rows = frame.to_dicts()
    else:
        raise ParityError(f"unsupported input format for {path}; use .csv or .parquet")
    _validate_headers(path, headers, recipe)
    rows = [
        {name: _parse(row.get(name), policy, name) for name, policy in recipe["columns"].items()}
        for row in raw_rows
    ]
    return rows, headers


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ParityError(f"cannot read {path}: {exc}") from exc
    return digest.hexdigest()


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


def _iter_input_rows(path: Path, recipe: dict[str, Any], max_rows: int):
    if path.is_symlink():
        raise ParityError(f"input must not be a symlink: {path}")
    if not path.is_file():
        raise ParityError(f"input is not a regular file: {path}")
    if path.suffix.lower() == ".csv":
        try:
            handle = path.open("r", encoding="utf-8", newline="")
        except OSError as exc:
            raise ParityError(f"cannot read {path}: {exc}") from exc
        with handle:
            try:
                reader = csv.DictReader(handle, strict=True)
                _validate_headers(path, reader.fieldnames or [], recipe)
                for row_count, raw in enumerate(reader):
                    if row_count >= max_rows:
                        raise ParityError(f"row count in {path} exceeds limit {max_rows}")
                    if None in raw or any(value is None for value in raw.values()):
                        raise ParityError(f"ragged CSV row {reader.line_num} in {path}")
                    yield raw
            except (csv.Error, UnicodeDecodeError) as exc:
                raise ParityError(f"cannot parse {path}: {exc}") from exc
    elif path.suffix.lower() in {".parquet", ".pq"}:
        try:
            import polars as pl
        except ImportError as exc:
            raise ParityError("Parquet support requires: pip install 'parity-compare[parquet]'") from exc
        try:
            row_count = pl.scan_parquet(path).select(pl.len()).collect().item()
            if row_count > max_rows:
                raise ParityError(f"row count in {path} exceeds limit {max_rows}")
            frame = pl.read_parquet(path)
        except ParityError:
            raise
        except Exception as exc:
            raise ParityError(f"cannot read {path}: {exc}") from exc
        _validate_headers(path, frame.columns, recipe)
        yield from frame.iter_rows(named=True)
    else:
        raise ParityError(f"unsupported input format for {path}; use .csv or .parquet")


def _read_stream_index(
    path: Path, recipe: dict[str, Any], max_rows: int, side: str
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], int, list[str]]:
    rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicates: set[tuple[Any, ...]] = set()
    null_count = row_count = 0
    for raw in _iter_input_rows(path, recipe, max_rows):
        row_count += 1
        row = {name: _parse(raw.get(name), policy, name) for name, policy in recipe["columns"].items()}
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
    for raw in _iter_input_rows(path, recipe, max_rows):
        row_count += 1
        row = {name: _parse(raw.get(name), policy, name) for name, policy in recipe["columns"].items()}
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
        raise ParityError("sample_limit must be non-negative")
    if max_input_bytes <= 0:
        raise ParityError("max_input_bytes must be positive")
    if max_rows <= 0:
        raise ParityError("max_rows must be positive")
    recipe_path, baseline_path, candidate_path = map(Path, (recipe_path, baseline_path, candidate_path))
    recipe = load_recipe(recipe_path)
    try:
        input_bytes = baseline_path.stat().st_size + candidate_path.stat().st_size
    except OSError as exc:
        raise ParityError(f"cannot inspect inputs: {exc}") from exc
    if input_bytes > max_input_bytes:
        raise ParityError(f"combined input size {input_bytes} exceeds limit {max_input_bytes} bytes")
    before = {_path: _digest(_path) for _path in (baseline_path, candidate_path)}
    keys = recipe["keys"]
    raw_output = recipe["output"]["sensitivity"] == "raw"
    streaming = not raw_output
    if streaming:
        left, baseline_count, left_problems = _read_stream_index(baseline_path, recipe, max_rows, "baseline")
    else:
        baseline, _ = _read(baseline_path, recipe, max_rows)
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
        candidate, _ = _read(candidate_path, recipe, max_rows)
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
    if any(_digest(path) != digest for path, digest in before.items()):
        raise ParityError("an input changed while it was being read")
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
            "baseline": {"sha256": before[baseline_path], "bytes": baseline_path.stat().st_size},
            "candidate": {"sha256": before[candidate_path], "bytes": candidate_path.stat().st_size},
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
        f"<tr><th>{esc(name)}</th><td>{esc(policy['type'])}</td><td>{esc(policy.get('comparison', 'exact'))}</td><td>{esc(json.dumps({key: value for key, value in policy.items() if key not in {'type', 'comparison'}}, sort_keys=True))}</td></tr>"
        for name, policy in result.get("column_policies", {}).items()
    ) or '<tr><td colspan="4">Unavailable</td></tr>'
    field_rows = "".join(
        f"<tr><th>{esc(name)}</th><td>{values['exact']}</td><td>{values['within_tolerance']}</td><td>{values['different']}</td></tr>"
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
            "<tr>" + "".join(f"<td>{esc(row.get(k, ''))}</td>" for k in ("kind", "key", "field", "baseline", "candidate", "classification", "delta", "allowance")) + "</tr>"
            for row in result["discrepancy_sample"]
        ) or '<tr><td colspan="8">No sampled discrepancies</td></tr>'
        evidence = f"""<h2>Raw discrepancy evidence</h2><p><strong>Sensitive:</strong> this report contains source keys and values. Showing {len(result['discrepancy_sample'])} of {result['discrepancy_count']} discrepancy items.</p>
<table><thead><tr><th>Kind</th><th>Key</th><th>Field</th><th>Baseline</th><th>Candidate</th><th>Class</th><th>Delta</th><th>Allowance</th></tr></thead><tbody>{rows}</tbody></table>"""
    else:
        evidence = "<h2>Privacy</h2><p>Summary mode stores no keys or raw field values. Field and record counts are complete.</p>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Parity report: {esc(result['outcome'])}</title><style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18202a}}h1{{color:{'#14733b' if result['outcome']=='PASS' else '#a22'}}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #ccd3da;padding:.5rem;text-align:left;vertical-align:top}}th{{background:#f3f5f7}}code{{overflow-wrap:anywhere}}</style>
<main><h1>{esc(result['outcome'])}</h1><p>Complete evaluation: <strong>{str(result['complete']).lower()}</strong></p>
<h2>Scope</h2><table>{scope_rows}</table><h2>Comparison policy</h2><table>{policy_rows}</table>
<h2>Column policies</h2><table><thead><tr><th>Field</th><th>Type</th><th>Comparison</th><th>Additional rules</th></tr></thead><tbody>{column_policy_rows}</tbody></table>
<h2>Record counts</h2><table>{counts}</table>
<h2>Field summary</h2><table><thead><tr><th>Field</th><th>Exact</th><th>Within tolerance</th><th>Different</th></tr></thead><tbody>{field_rows}</tbody></table>
<h2>Excluded columns</h2><table><thead><tr><th>Column</th><th>Rationale</th></tr></thead><tbody>{exclusion_rows}</tbody></table>
<h2>Preflight issues</h2><ul>{problems}</ul>{evidence}
<h2>Inputs</h2><table><thead><tr><th>Side</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{input_rows}</tbody></table>
<h2>Resource limits</h2><table>{limit_rows}</table><h2>Runtime</h2><table>{runtime_rows}</table>
<h2>Provenance</h2><p>Recipe SHA-256: <code>{esc(result.get('recipe_sha256') or 'unavailable')}</code></p></main></html>"""


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
        raise ParityError(f"output already exists: {output}")
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
        raise ParityError(f"run is not a regular directory: {directory}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParityError(f"cannot read manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("complete") is not True:
        raise ParityError("manifest is incomplete or unsupported")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ParityError("manifest has no files")
    for name, expected in files.items():
        if not isinstance(name, str) or Path(name).name != name or not isinstance(expected, str):
            raise ParityError("manifest contains an invalid file entry")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ParityError(f"bundle file is missing or unsafe: {name}")
        if _digest(path) != expected:
            raise ParityError(f"bundle file failed integrity check: {name}")
    return manifest
