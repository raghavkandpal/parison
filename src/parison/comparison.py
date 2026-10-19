"""Keyed, aggregate, and multiset comparison execution."""

from __future__ import annotations

import html
import json
import sqlite3
import tempfile
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .core import (
    _RAW_VALUE,
    DEFAULT_MAX_TEMP_BYTES,
    ParisonError,
    _checked_policy_sha256,
    _normalize,
    _parse,
    _parse_row,
    _raw_value,
    _runtime_info,
    _with_input_projection,
    load_recipe,
)
from .inputs import (
    _decoded_sizes,
    _digest,
    _iter_input_rows,
    _read,
    _source_bytes,
    _source_digest,
    _source_metadata,
)


def _json_value(value: Any) -> Any:
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    return value


_MULTISET_TAGS = {
    "null": b"\x00",
    "boolean": b"\x01",
    "integer": b"\x02",
    "decimal": b"\x03",
    "string": b"\x04",
    "date": b"\x05",
    "timestamp": b"\x06",
    "float": b"\x07",
}


def _multiset_encoding(row: tuple[Any, ...], names: list[str], recipe: dict[str, Any]) -> bytes:
    encoded = bytearray()
    for name, value in zip(names, row, strict=False):
        policy = recipe["columns"][name]
        kind = policy["type"]
        if value is None:
            payload = b""
            tag = _MULTISET_TAGS["null"]
        elif kind == "boolean":
            payload, tag = (b"1" if value else b"0"), _MULTISET_TAGS["boolean"]
        elif kind == "integer":
            payload, tag = str(value).encode("ascii"), _MULTISET_TAGS["integer"]
        elif kind == "decimal":
            text = format(value, f".{policy['scale']}f")
            if value == 0:
                text = format(Decimal(0), f".{policy['scale']}f")
            payload, tag = text.encode("ascii"), _MULTISET_TAGS["decimal"]
        elif kind == "float":
            payload, tag = value.hex().encode("ascii"), _MULTISET_TAGS["float"]
        elif kind == "date":
            payload, tag = value.isoformat().encode("ascii"), _MULTISET_TAGS["date"]
        elif kind == "timestamp":
            utc = value.astimezone(UTC)
            text = utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond:06d}Z"
            payload, tag = text.encode("ascii"), _MULTISET_TAGS["timestamp"]
        else:
            payload, tag = value.encode("utf-8"), _MULTISET_TAGS["string"]
        if len(payload) >= 2**64:
            raise ParisonError("multiset row field exceeds encoding-v1 length limit")
        encoded.extend(tag)
        encoded.extend(len(payload).to_bytes(8, "big"))
        encoded.extend(payload)
    return bytes(encoded)


def _key_text(key: tuple[Any, ...]) -> list[Any]:
    return [_json_value(value) for value in key]


def _index(
    rows: list[dict[str, Any]], keys: list[str], side: str
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], list[str]]:
    problems: list[str] = []
    values = [tuple(row[k] for k in keys) for row in rows]
    null_count = sum(any(v is None for v in key) for key in values)
    duplicates = sorted((_key_text(k) for k, n in Counter(values).items() if n > 1), key=str)
    if null_count:
        problems.append(f"{side} has {null_count} row(s) with null key components")
    if duplicates:
        problems.append(f"{side} has {len(duplicates)} duplicate key(s)")
    return dict(zip(values, rows, strict=False)), problems


def _read_stream_index(
    path: Path, recipe: dict[str, Any], max_rows: int, side: str, decoded_sizes: dict[Path, int] | None = None
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], int, list[str]]:
    rows: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicates: set[tuple[Any, ...]] = set()
    null_count = row_count = 0
    for raw in _iter_input_rows(path, recipe, max_rows, side, decoded_sizes):
        row_count += 1
        row = _parse_row(raw, recipe, side)
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
    decoded_sizes: dict[Path, int] | None = None,
) -> dict[str, Any]:
    keys = recipe["keys"]
    compared = [name for name in recipe["columns"] if name not in keys]
    field_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in compared}
    row_counts = {"exact": 0, "within_tolerance": 0, "different": 0}
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    null_count = candidate_only = discrepancy_count = row_count = 0
    for raw in _iter_input_rows(path, recipe, max_rows, "candidate", decoded_sizes):
        row_count += 1
        row = _parse_row(raw, recipe, "candidate")
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


def _key_order_encoding(key: tuple[Any, ...]) -> bytes:
    encoded = bytearray()
    for value in key:
        for character in str(value):
            encoded.extend((ord(character) + 1).to_bytes(4, "big"))
        encoded.extend(b"\0\0\0\0")
    return bytes(encoded)


def _restore_row(rendered: str, recipe: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(rendered)
    row = {
        name: _normalize(_parse(payload["values"][name], policy, name), policy)
        for name, policy in recipe["columns"].items()
    }
    for name, value in payload.get("raw", {}).items():
        row[(_RAW_VALUE, name)] = _parse(value, recipe["columns"][name], name)
    return row


def _sqlite_keyed_summary(
    sources: tuple[str | Path, str | Path],
    recipe: dict[str, Any],
    max_rows: int,
    sample_limit: int,
    max_temp_bytes: int,
    temp_directory: str | Path | None,
    decoded_sizes: dict[Path, int],
) -> dict[str, Any]:
    parent = Path(temp_directory) if temp_directory is not None else None
    if parent is not None and (parent.is_symlink() or not parent.is_dir()):
        raise ParisonError("temp directory must be an existing non-symlink directory")
    keys = recipe["keys"]
    compared = [name for name in recipe["columns"] if name not in keys]
    raw_output = recipe["output"]["sensitivity"] == "raw"
    try:
        with tempfile.TemporaryDirectory(prefix="parison-spill-", dir=parent) as workspace:
            database = Path(workspace) / "keyed.sqlite"
            connection = sqlite3.connect(database)
            try:
                page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
                page_limit = max_temp_bytes // page_size
                if page_limit < 4:
                    raise ParisonError(f"temporary storage limit {max_temp_bytes} bytes is too small")
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                connection.execute(f"PRAGMA max_page_count={page_limit}")
                connection.execute(
                    "CREATE TABLE records (side INTEGER NOT NULL, key BLOB NOT NULL, key_order BLOB NOT NULL, "
                    "row_json TEXT NOT NULL, occurrences INTEGER NOT NULL, PRIMARY KEY (side, key)) WITHOUT ROWID"
                )
                connection.execute("CREATE INDEX records_order ON records (side, key_order)")
                row_totals: list[int] = []
                null_totals: list[int] = []
                for side_id, (side, source) in enumerate(zip(("baseline", "candidate"), sources, strict=False)):
                    rows = nulls = 0
                    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
                        row = _parse_row(raw, recipe, side, preserve_raw=raw_output)
                        key = tuple(row[name] for name in keys)
                        nulls += any(value is None for value in key)
                        payload = {"values": {name: _json_value(row[name]) for name in recipe["columns"]}}
                        if raw_output:
                            payload["raw"] = {name: _raw_value(row, name) for name in recipe["columns"]}
                        rendered = json.dumps(
                            payload,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        )
                        connection.execute(
                            "INSERT INTO records VALUES (?, ?, ?, ?, 1) "
                            "ON CONFLICT (side, key) DO UPDATE SET row_json = excluded.row_json, occurrences = occurrences + 1",
                            (side_id, _multiset_encoding(key, keys, recipe), _key_order_encoding(key), rendered),
                        )
                        rows += 1
                    row_totals.append(rows)
                    null_totals.append(nulls)
                connection.commit()
                duplicates = [
                    int(
                        connection.execute(
                            "SELECT COUNT(*) FROM records WHERE side = ? AND occurrences > 1", (side_id,)
                        ).fetchone()[0]
                    )
                    for side_id in (0, 1)
                ]
                problems = []
                for side, nulls, repeated in zip(("baseline", "candidate"), null_totals, duplicates, strict=False):
                    if nulls:
                        problems.append(f"{side} has {nulls} row(s) with null key components")
                    if repeated:
                        problems.append(f"{side} has {repeated} duplicate key(s)")
                common = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM records AS baseline JOIN records AS candidate ON candidate.side = 1 AND candidate.key = baseline.key WHERE baseline.side = 0"
                    ).fetchone()[0]
                )
                baseline_only = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM records AS baseline WHERE baseline.side = 0 AND NOT EXISTS "
                        "(SELECT 1 FROM records AS candidate WHERE candidate.side = 1 AND candidate.key = baseline.key)"
                    ).fetchone()[0]
                )
                candidate_only = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM records AS candidate WHERE candidate.side = 1 AND NOT EXISTS "
                        "(SELECT 1 FROM records AS baseline WHERE baseline.side = 0 AND baseline.key = candidate.key)"
                    ).fetchone()[0]
                )
                discrepancies: list[dict[str, Any]] = []
                if raw_output:
                    for side_id, classification in ((0, "baseline_only"), (1, "candidate_only")):
                        remaining = sample_limit - len(discrepancies)
                        if remaining <= 0:
                            break
                        other = 1 - side_id
                        records = connection.execute(
                            "SELECT row_json FROM records AS current WHERE side = ? AND NOT EXISTS "
                            "(SELECT 1 FROM records AS other WHERE other.side = ? AND other.key = current.key) "
                            "ORDER BY key_order LIMIT ?",
                            (side_id, other, remaining),
                        )
                        for (row_json,) in records:
                            row = _restore_row(row_json, recipe)
                            discrepancies.append(
                                {
                                    "kind": "record",
                                    "key": [_raw_value(row, name) for name in keys],
                                    "classification": classification,
                                }
                            )
                field_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in compared}
                row_counts = {"exact": 0, "within_tolerance": 0, "different": 0}
                field_discrepancy_count = 0
                if not problems:
                    records = connection.execute(
                        "SELECT baseline.row_json, candidate.row_json FROM records AS baseline "
                        "JOIN records AS candidate ON candidate.side = 1 AND candidate.key = baseline.key "
                        "WHERE baseline.side = 0 ORDER BY baseline.key_order"
                    )
                    for left_json, right_json in records:
                        left, right = _restore_row(left_json, recipe), _restore_row(right_json, recipe)
                        key = tuple(left[name] for name in keys)
                        row_class = "exact"
                        for name in compared:
                            classification, delta, allowance = _classify(
                                left[name], right[name], recipe["columns"][name], recipe["nulls_equal"]
                            )
                            field_counts[name][classification] += 1
                            if classification == "different":
                                row_class = "different"
                            elif classification == "within_tolerance" and row_class == "exact":
                                row_class = "within_tolerance"
                            if classification != "exact":
                                field_discrepancy_count += 1
                                if raw_output and len(discrepancies) < sample_limit:
                                    discrepancies.append(
                                        {
                                            "kind": "field",
                                            "key": _key_text(key),
                                            "field": name,
                                            "baseline": _raw_value(left, name),
                                            "candidate": _raw_value(right, name),
                                            "classification": classification,
                                            "delta": delta,
                                            "allowance": allowance,
                                        }
                                    )
                        row_counts[row_class] += 1
                return {
                    "baseline": row_totals[0],
                    "candidate": row_totals[1],
                    "common_keys": common,
                    "baseline_only": baseline_only,
                    "candidate_only": candidate_only,
                    "field_counts": field_counts,
                    "row_counts": row_counts,
                    "field_discrepancy_count": field_discrepancy_count,
                    "problems": problems,
                    "discrepancies": discrepancies,
                    "temporary_bytes": database.stat().st_size,
                }
            finally:
                connection.close()
    except ParisonError:
        raise
    except sqlite3.Error as exc:
        if "full" in str(exc).lower():
            raise ParisonError(f"temporary storage exceeds limit {max_temp_bytes} bytes") from exc
        raise ParisonError(f"spill database failed: {exc}") from exc
    except OSError as exc:
        raise ParisonError(f"cannot use spill directory: {exc}") from exc


def compare(
    recipe_path: str | Path,
    baseline_path: str | Path,
    candidate_path: str | Path,
    sample_limit: int = 100,
    max_input_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
    expected_policy_sha256: str | None = None,
    max_decoded_bytes: int = 1_000_000_000,
    max_groups: int = 100_000,
    max_distinct_rows: int = 100_000,
    engine: str = "memory",
    max_temp_bytes: int = DEFAULT_MAX_TEMP_BYTES,
    temp_directory: str | Path | None = None,
) -> dict[str, Any]:
    if sample_limit < 0:
        raise ParisonError("sample_limit must be non-negative")
    if max_input_bytes <= 0:
        raise ParisonError("max_input_bytes must be positive")
    if max_rows <= 0:
        raise ParisonError("max_rows must be positive")
    if max_groups <= 0:
        raise ParisonError("max_groups must be positive")
    if max_distinct_rows <= 0:
        raise ParisonError("max_distinct_rows must be positive")
    if engine not in {"memory", "sqlite"}:
        raise ParisonError("engine must be memory or sqlite")
    if max_temp_bytes <= 0:
        raise ParisonError("max_temp_bytes must be positive")
    recipe_path = Path(recipe_path)
    recipe = load_recipe(recipe_path)
    if engine == "memory" and temp_directory is not None:
        raise ParisonError("temp_directory requires engine='sqlite'")
    policy_sha256 = _checked_policy_sha256(recipe, expected_policy_sha256)
    if recipe["comparison_mode"] == "aggregate":
        return _compare_aggregate(
            recipe_path,
            recipe,
            baseline_path,
            candidate_path,
            sample_limit,
            max_input_bytes,
            max_rows,
            max_decoded_bytes,
            max_groups,
            policy_sha256,
            engine,
            max_temp_bytes,
            temp_directory,
        )
    if recipe["comparison_mode"] == "multiset":
        return _compare_multiset(
            recipe_path,
            recipe,
            baseline_path,
            candidate_path,
            sample_limit,
            max_input_bytes,
            max_rows,
            max_decoded_bytes,
            max_distinct_rows,
            policy_sha256,
            engine,
            max_temp_bytes,
            temp_directory,
        )
    input_bytes = _source_bytes(baseline_path) + _source_bytes(candidate_path)
    if input_bytes > max_input_bytes:
        raise ParisonError(f"combined input size {input_bytes} exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes((baseline_path, candidate_path), max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in (baseline_path, candidate_path)}
    keys = recipe["keys"]
    raw_output = recipe["output"]["sensitivity"] == "raw"
    streaming = not raw_output
    if engine == "sqlite":
        summary = _sqlite_keyed_summary(
            (baseline_path, candidate_path),
            recipe,
            max_rows,
            sample_limit,
            max_temp_bytes,
            temp_directory,
            decoded_sizes,
        )
        baseline_count = summary["baseline"]
        candidate_count = summary["candidate"]
        common_count = summary["common_keys"]
        baseline_only_count = summary["baseline_only"]
        candidate_only_count = summary["candidate_only"]
        field_counts = summary["field_counts"]
        row_counts = summary["row_counts"]
        discrepancy_count = summary["field_discrepancy_count"]
        problems = summary["problems"]
        discrepancies = summary["discrepancies"]
        temporary_bytes = summary["temporary_bytes"]
    elif streaming:
        left, baseline_count, left_problems = _read_stream_index(
            baseline_path, recipe, max_rows, "baseline", decoded_sizes
        )
    else:
        baseline, _ = _read(baseline_path, recipe, max_rows, "baseline", decoded_sizes)
        baseline_count = len(baseline)
        left, left_problems = _index(baseline, keys, "baseline")
        del baseline
    if engine == "sqlite":
        pass
    elif streaming:
        discrepancies = []
        summary = _compare_stream_summary(candidate_path, recipe, max_rows, left, left_problems, decoded_sizes)
        candidate_count = summary["candidate"]
        common_count = summary["common"]
        baseline_only_count = summary["baseline_only"]
        candidate_only_count = summary["candidate_only"]
        field_counts = summary["field_counts"]
        row_counts = summary["row_counts"]
        discrepancy_count = summary["field_discrepancy_count"]
        problems = summary["problems"]
    else:
        discrepancies = []
        candidate, _ = _read(candidate_path, recipe, max_rows, "candidate", decoded_sizes)
        right, right_problems = _index(candidate, keys, "candidate")
        problems = left_problems + right_problems
        common = set(left) & set(right)
        baseline_only = set(left) - set(right)
        candidate_only = set(right) - set(left)
        candidate_count = len(candidate)
        common_count = len(common)
        baseline_only_count = len(baseline_only)
        candidate_only_count = len(candidate_only)
        field_counts = {
            name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in recipe["columns"] if name not in keys
        }
        row_counts = {"exact": 0, "within_tolerance": 0, "different": 0}
        discrepancy_count = 0
        if raw_output:
            for classification, missing_keys in (("baseline_only", baseline_only), ("candidate_only", candidate_only)):
                for key in sorted(missing_keys, key=lambda item: tuple(str(v) for v in item)):
                    if len(discrepancies) >= sample_limit:
                        break
                    source = left if classification == "baseline_only" else right
                    discrepancies.append(
                        {
                            "kind": "record",
                            "key": [_raw_value(source[key], name) for name in keys],
                            "classification": classification,
                        }
                    )
    if engine != "sqlite" and not streaming and not problems:
        for key in sorted(common, key=lambda item: tuple(str(v) for v in item)):
            row_class = "exact"
            for name, policy in recipe["columns"].items():
                if name in keys:
                    continue
                classification, delta, allowance = _classify(
                    left[key][name], right[key][name], policy, recipe["nulls_equal"]
                )
                field_counts[name][classification] += 1
                if classification == "different":
                    row_class = "different"
                elif classification == "within_tolerance" and row_class == "exact":
                    row_class = "within_tolerance"
                if classification != "exact":
                    discrepancy_count += 1
                    if raw_output and len(discrepancies) < sample_limit:
                        discrepancies.append(
                            {
                                "kind": "field",
                                "key": _key_text(key),
                                "field": name,
                                "baseline": _raw_value(left[key], name),
                                "candidate": _raw_value(right[key], name),
                                "classification": classification,
                                "delta": delta,
                                "allowance": allowance,
                            }
                        )
            row_counts[row_class] += 1
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being read")
    empty = not baseline_count or not candidate_count
    if empty and not recipe["scope"]["expected_empty"]:
        problems.append("nonempty comparable inputs are required")
    outcome = (
        "INCONCLUSIVE"
        if problems
        else ("FAIL" if baseline_only_count or candidate_only_count or row_counts["different"] else "PASS")
    )
    runtime = _runtime_info((baseline_path, candidate_path))
    resource_limits = {
        "max_input_bytes": max_input_bytes,
        "max_decoded_bytes": max_decoded_bytes,
        "max_rows_per_input": max_rows,
    }
    if engine == "sqlite":
        runtime["execution_engine"] = engine
        runtime["temporary_bytes"] = temporary_bytes
        resource_limits["max_temp_bytes"] = max_temp_bytes
    return {
        "schema_version": 1,
        "outcome": outcome,
        "complete": not problems,
        "sensitivity": recipe["output"]["sensitivity"],
        "runtime": runtime,
        "resource_limits": resource_limits,
        "scope": recipe["scope"],
        "keys": keys,
        "policy": _with_input_projection(
            recipe,
            {
                "keys": keys,
                "nulls_equal": recipe["nulls_equal"],
                "delimiters": recipe["delimiters"],
                "null_tokens": recipe["null_tokens"],
                "sensitivity": recipe["output"]["sensitivity"],
            },
            False,
        ),
        "column_policies": recipe["columns"],
        "column_mappings": recipe.get("column_mappings", {}),
        "problems": problems,
        "counts": {
            "baseline": baseline_count,
            "candidate": candidate_count,
            "common_keys": common_count,
            "baseline_only": baseline_only_count,
            "candidate_only": candidate_only_count,
            "matched_exact": row_counts["exact"],
            "matched_within_tolerance": row_counts["within_tolerance"],
            "matched_with_required_difference": row_counts["different"],
        },
        "field_counts": field_counts,
        "field_discrepancy_count": discrepancy_count,
        "discrepancy_count": discrepancy_count + baseline_only_count + candidate_only_count,
        "discrepancy_sample": discrepancies,
        "discrepancy_sample_limit": sample_limit if raw_output else 0,
        "excluded_columns": recipe.get("excluded_columns", {}),
        "inputs": {
            "baseline": _source_metadata(
                baseline_path,
                before[str(baseline_path)],
                decoded_sizes,
                recipe["delimiters"]["baseline"],
                recipe["null_tokens"]["baseline"],
                recipe["output"]["sensitivity"] == "raw",
            ),
            "candidate": _source_metadata(
                candidate_path,
                before[str(candidate_path)],
                decoded_sizes,
                recipe["delimiters"]["candidate"],
                recipe["null_tokens"]["candidate"],
                recipe["output"]["sensitivity"] == "raw",
            ),
        },
        "recipe_sha256": _digest(recipe_path),
        "policy_sha256": policy_sha256,
    }


def _aggregate_value(value: Any, column: dict[str, Any]) -> Any:
    if column["type"] == "decimal":
        return int(value.scaleb(column["scale"]))
    return value


def _aggregate_json_value(value: Any, operator: str, column: dict[str, Any] | None) -> Any:
    if value is None:
        return None
    if operator == "sum" and column and column["type"] == "decimal":
        return str(Decimal(value).scaleb(-column["scale"]))
    return _json_value(value)


def _new_aggregate_group(recipe: dict[str, Any]) -> dict[str, Any]:
    return {
        "rows": 0,
        "measures": {
            name: {"value": 0 if policy["operator"] == "count" else None, "contributing": 0, "ignored_nulls": 0}
            for name, policy in recipe["measures"].items()
        },
    }


def _update_aggregate_group(group: dict[str, Any], row: dict[str, Any], recipe: dict[str, Any]) -> int:
    rejected_nulls = 0
    group["rows"] += 1
    for name, policy in recipe["measures"].items():
        state = group["measures"][name]
        operator = policy["operator"]
        if operator == "count":
            state["value"] += 1
            state["contributing"] += 1
            continue
        value = row[policy["column"]]
        if value is None:
            if policy["nulls"] == "ignore":
                state["ignored_nulls"] += 1
            else:
                rejected_nulls += 1
            continue
        value = _aggregate_value(value, recipe["columns"][policy["column"]])
        state["contributing"] += 1
        if operator == "sum":
            state["value"] = (state["value"] or 0) + value
        elif (
            state["value"] is None
            or (operator == "min" and value < state["value"])
            or (operator == "max" and value > state["value"])
        ):
            state["value"] = value
    return rejected_nulls


def _aggregate_input(
    source: str | Path,
    recipe: dict[str, Any],
    side: str,
    max_rows: int,
    max_groups: int,
    decoded_sizes: dict[Path, int],
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], int, list[str]]:
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    problems: list[str] = []
    null_groups = rejected_nulls = rows = 0
    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
        rows += 1
        row = _parse_row(raw, recipe, side)
        key = tuple(row[name] for name in recipe["group_by"])
        if any(value is None for value in key):
            null_groups += 1
            continue
        if key not in groups:
            if len(groups) >= max_groups:
                raise ParisonError(f"{side} group count exceeds limit {max_groups}")
            groups[key] = _new_aggregate_group(recipe)
        rejected_nulls += _update_aggregate_group(groups[key], row, recipe)
    if not recipe["group_by"] and not groups:
        groups[()] = _new_aggregate_group(recipe)
    if null_groups:
        problems.append(f"{side} has {null_groups} row(s) with null group components")
    if rejected_nulls:
        problems.append(f"{side} has {rejected_nulls} rejected null measure value(s)")
    return groups, rows, problems


def _aggregate_state_json(group: dict[str, Any]) -> str:
    return json.dumps(
        {
            "rows": group["rows"],
            "measures": {
                name: state | {"value": _json_value(state["value"])} for name, state in group["measures"].items()
            },
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _restore_aggregate_state(value: str, recipe: dict[str, Any]) -> dict[str, Any]:
    group = json.loads(value)
    for name, state in group["measures"].items():
        raw = state["value"]
        if raw is None:
            continue
        policy = recipe["measures"][name]
        if policy["operator"] in {"count", "sum"}:
            state["value"] = int(raw)
            continue
        kind = recipe["columns"][policy["column"]]["type"]
        if kind == "date":
            state["value"] = date.fromisoformat(raw)
        elif kind == "timestamp":
            state["value"] = datetime.fromisoformat(raw)
        elif kind == "decimal":
            state["value"] = int(raw)
    return group


def _sqlite_aggregate_summary(
    sources: tuple[str | Path, str | Path],
    recipe: dict[str, Any],
    max_rows: int,
    max_groups: int,
    sample_limit: int,
    max_temp_bytes: int,
    temp_directory: str | Path | None,
    decoded_sizes: dict[Path, int],
) -> dict[str, Any]:
    parent = Path(temp_directory) if temp_directory is not None else None
    if parent is not None and (parent.is_symlink() or not parent.is_dir()):
        raise ParisonError("temp directory must be an existing non-symlink directory")
    try:
        with tempfile.TemporaryDirectory(prefix="parison-spill-", dir=parent) as workspace:
            database = Path(workspace) / "aggregate.sqlite"
            connection = sqlite3.connect(database)
            try:
                page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
                page_limit = max_temp_bytes // page_size
                if page_limit < 4:
                    raise ParisonError(f"temporary storage limit {max_temp_bytes} bytes is too small")
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                connection.execute(f"PRAGMA max_page_count={page_limit}")
                connection.create_collation(
                    "parison_key",
                    lambda left, right: (
                        (tuple(map(str, json.loads(left))) > tuple(map(str, json.loads(right))))
                        - (tuple(map(str, json.loads(left))) < tuple(map(str, json.loads(right))))
                    ),
                )
                connection.execute(
                    "CREATE TABLE groups (side INTEGER NOT NULL, encoded BLOB NOT NULL, key_json TEXT NOT NULL, state_json TEXT NOT NULL, PRIMARY KEY (side, encoded)) WITHOUT ROWID"
                )
                row_totals, group_totals, problems = [], [], []
                for side_id, (side, source) in enumerate(zip(("baseline", "candidate"), sources, strict=True)):
                    rows = groups = null_groups = rejected_nulls = 0
                    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
                        rows += 1
                        row = _parse_row(raw, recipe, side)
                        key = tuple(row[name] for name in recipe["group_by"])
                        if any(value is None for value in key):
                            null_groups += 1
                            continue
                        encoded = _multiset_encoding(key, recipe["group_by"], recipe)
                        found = connection.execute(
                            "SELECT state_json FROM groups WHERE side = ? AND encoded = ?", (side_id, encoded)
                        ).fetchone()
                        if found is None:
                            groups += 1
                            if groups > max_groups:
                                raise ParisonError(f"{side} group count exceeds limit {max_groups}")
                            group = _new_aggregate_group(recipe)
                        else:
                            group = _restore_aggregate_state(found[0], recipe)
                        rejected_nulls += _update_aggregate_group(group, row, recipe)
                        connection.execute(
                            "INSERT OR REPLACE INTO groups VALUES (?, ?, ?, ?)",
                            (
                                side_id,
                                encoded,
                                json.dumps(_key_text(key), separators=(",", ":"), ensure_ascii=False),
                                _aggregate_state_json(group),
                            ),
                        )
                    if not recipe["group_by"] and not groups:
                        empty = _new_aggregate_group(recipe)
                        connection.execute(
                            "INSERT INTO groups VALUES (?, ?, '[]', ?)", (side_id, b"", _aggregate_state_json(empty))
                        )
                        groups = 1
                    if null_groups:
                        problems.append(f"{side} has {null_groups} row(s) with null group components")
                    if rejected_nulls:
                        problems.append(f"{side} has {rejected_nulls} rejected null measure value(s)")
                    row_totals.append(rows)
                    group_totals.append(groups)
                connection.commit()
                measure_counts = {
                    name: {kind: 0 for kind in ("exact", "within_tolerance", "different")}
                    for name in recipe["measures"]
                }
                conservation = {
                    name: {side: {"contributing": 0, "ignored_nulls": 0} for side in ("baseline", "candidate")}
                    for name in recipe["measures"]
                }
                samples, common = [], 0
                if recipe["output"]["sensitivity"] == "raw":
                    for classification, query in (
                        (
                            "baseline_only",
                            "SELECT baseline.key_json FROM groups AS baseline WHERE baseline.side = 0 AND NOT EXISTS (SELECT 1 FROM groups AS candidate WHERE candidate.side = 1 AND candidate.encoded = baseline.encoded) ORDER BY baseline.key_json COLLATE parison_key",
                        ),
                        (
                            "candidate_only",
                            "SELECT candidate.key_json FROM groups AS candidate WHERE candidate.side = 1 AND NOT EXISTS (SELECT 1 FROM groups AS baseline WHERE baseline.side = 0 AND baseline.encoded = candidate.encoded) ORDER BY candidate.key_json COLLATE parison_key",
                        ),
                    ):
                        for (key_json,) in connection.execute(query):
                            if len(samples) >= sample_limit:
                                break
                            samples.append(
                                {"kind": "group", "group": json.loads(key_json), "classification": classification}
                            )
                baseline_only = candidate_only = measure_discrepancies = 0
                records = connection.execute(
                    "SELECT baseline.encoded, baseline.key_json, baseline.state_json, candidate.state_json FROM groups AS baseline LEFT JOIN groups AS candidate ON candidate.side = 1 AND candidate.encoded = baseline.encoded WHERE baseline.side = 0 "
                    "UNION ALL SELECT candidate.encoded, candidate.key_json, NULL, candidate.state_json FROM groups AS candidate WHERE candidate.side = 1 AND NOT EXISTS (SELECT 1 FROM groups AS baseline WHERE baseline.side = 0 AND baseline.encoded = candidate.encoded) ORDER BY 2 COLLATE parison_key"
                )
                for _, key_json, left_json, right_json in records:
                    key = json.loads(key_json)
                    left = _restore_aggregate_state(left_json, recipe) if left_json else None
                    right = _restore_aggregate_state(right_json, recipe) if right_json else None
                    for side, group in (("baseline", left), ("candidate", right)):
                        if group:
                            for name, state in group["measures"].items():
                                conservation[name][side]["contributing"] += state["contributing"]
                                conservation[name][side]["ignored_nulls"] += state["ignored_nulls"]
                    if left is None or right is None:
                        classification = "candidate_only" if left is None else "baseline_only"
                        baseline_only += classification == "baseline_only"
                        candidate_only += classification == "candidate_only"
                        continue
                    common += 1
                    if problems:
                        continue
                    for name, policy in recipe["measures"].items():
                        lstate, rstate = left["measures"][name], right["measures"][name]
                        column = recipe["columns"].get(policy.get("column"))
                        lvalue = _aggregate_json_value(lstate["value"], policy["operator"], column)
                        rvalue = _aggregate_json_value(rstate["value"], policy["operator"], column)
                        classification, delta, allowance = _classify(lvalue, rvalue, policy, True)
                        measure_counts[name][classification] += 1
                        if classification != "exact":
                            measure_discrepancies += 1
                            if recipe["output"]["sensitivity"] == "raw" and len(samples) < sample_limit:
                                samples.append(
                                    {
                                        "kind": "measure",
                                        "group": key,
                                        "measure": name,
                                        "baseline": lvalue,
                                        "candidate": rvalue,
                                        "classification": classification,
                                        "delta": delta,
                                        "allowance": allowance,
                                        "baseline_count": lstate["contributing"],
                                        "candidate_count": rstate["contributing"],
                                        "baseline_ignored_nulls": lstate["ignored_nulls"],
                                        "candidate_ignored_nulls": rstate["ignored_nulls"],
                                    }
                                )
                return {
                    "rows": row_totals,
                    "groups": group_totals,
                    "problems": problems,
                    "common": common,
                    "baseline_only": baseline_only,
                    "candidate_only": candidate_only,
                    "measure_counts": measure_counts,
                    "measure_conservation": conservation,
                    "measure_discrepancies": measure_discrepancies,
                    "samples": samples,
                    "temporary_bytes": database.stat().st_size,
                }
            finally:
                connection.close()
    except ParisonError:
        raise
    except sqlite3.Error as exc:
        if "full" in str(exc).lower():
            raise ParisonError(f"temporary storage exceeds limit {max_temp_bytes} bytes") from exc
        raise ParisonError(f"spill database failed: {exc}") from exc
    except OSError as exc:
        raise ParisonError(f"cannot use spill directory: {exc}") from exc


def _compare_aggregate(
    recipe_path: Path,
    recipe: dict[str, Any],
    baseline_path: str | Path,
    candidate_path: str | Path,
    sample_limit: int,
    max_input_bytes: int,
    max_rows: int,
    max_decoded_bytes: int,
    max_groups: int,
    policy_sha256: str,
    engine: str = "memory",
    max_temp_bytes: int = DEFAULT_MAX_TEMP_BYTES,
    temp_directory: str | Path | None = None,
) -> dict[str, Any]:
    input_bytes = _source_bytes(baseline_path) + _source_bytes(candidate_path)
    if input_bytes > max_input_bytes:
        raise ParisonError(f"combined input size {input_bytes} exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes((baseline_path, candidate_path), max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in (baseline_path, candidate_path)}
    sqlite_summary = None
    if engine == "sqlite":
        sqlite_summary = _sqlite_aggregate_summary(
            (baseline_path, candidate_path),
            recipe,
            max_rows,
            max_groups,
            sample_limit,
            max_temp_bytes,
            temp_directory,
            decoded_sizes,
        )
        baseline_rows, candidate_rows = sqlite_summary["rows"]
        problems = sqlite_summary["problems"]
    else:
        left, baseline_rows, problems = _aggregate_input(
            baseline_path, recipe, "baseline", max_rows, max_groups, decoded_sizes
        )
        right, candidate_rows, right_problems = _aggregate_input(
            candidate_path, recipe, "candidate", max_rows, max_groups, decoded_sizes
        )
        problems += right_problems
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being read")
    if (not baseline_rows or not candidate_rows) and not recipe["scope"]["expected_empty"]:
        problems.append("nonempty aggregate inputs are required")
    raw_output = recipe["output"]["sensitivity"] == "raw"
    if sqlite_summary:
        baseline_groups, candidate_groups = sqlite_summary["groups"]
        common_count = sqlite_summary["common"]
        baseline_only_count = sqlite_summary["baseline_only"]
        candidate_only_count = sqlite_summary["candidate_only"]
        measure_counts = sqlite_summary["measure_counts"]
        measure_conservation = sqlite_summary["measure_conservation"]
        measure_discrepancies = sqlite_summary["measure_discrepancies"]
        discrepancies = sqlite_summary["samples"]
    else:
        common = set(left) & set(right)
        baseline_only, candidate_only = set(left) - set(right), set(right) - set(left)
        baseline_groups, candidate_groups = len(left), len(right)
        common_count, baseline_only_count, candidate_only_count = len(common), len(baseline_only), len(candidate_only)
        measure_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in recipe["measures"]}
        discrepancies = []
        for classification, keys in (("baseline_only", baseline_only), ("candidate_only", candidate_only)):
            for key in sorted(keys, key=lambda item: tuple(str(value) for value in item)):
                if raw_output and len(discrepancies) < sample_limit:
                    discrepancies.append({"kind": "group", "group": _key_text(key), "classification": classification})
        measure_discrepancies = 0
        if not problems:
            for key in sorted(common, key=lambda item: tuple(str(value) for value in item)):
                for name, policy in recipe["measures"].items():
                    lstate, rstate = left[key]["measures"][name], right[key]["measures"][name]
                    column = recipe["columns"].get(policy.get("column"))
                    lvalue = _aggregate_json_value(lstate["value"], policy["operator"], column)
                    rvalue = _aggregate_json_value(rstate["value"], policy["operator"], column)
                    classification, delta, allowance = _classify(lvalue, rvalue, policy, True)
                    measure_counts[name][classification] += 1
                    if classification != "exact":
                        measure_discrepancies += 1
                        if raw_output and len(discrepancies) < sample_limit:
                            discrepancies.append(
                                {
                                    "kind": "measure",
                                    "group": _key_text(key),
                                    "measure": name,
                                    "baseline": lvalue,
                                    "candidate": rvalue,
                                    "classification": classification,
                                    "delta": delta,
                                    "allowance": allowance,
                                    "baseline_count": lstate["contributing"],
                                    "candidate_count": rstate["contributing"],
                                    "baseline_ignored_nulls": lstate["ignored_nulls"],
                                    "candidate_ignored_nulls": rstate["ignored_nulls"],
                                }
                            )
        measure_conservation = {
            name: {
                side: {
                    "contributing": sum(group["measures"][name]["contributing"] for group in groups.values()),
                    "ignored_nulls": sum(group["measures"][name]["ignored_nulls"] for group in groups.values()),
                }
                for side, groups in (("baseline", left), ("candidate", right))
            }
            for name in recipe["measures"]
        }
    totals = {
        kind: sum(values[kind] for values in measure_counts.values())
        for kind in ("exact", "within_tolerance", "different")
    }
    outcome = (
        "INCONCLUSIVE"
        if problems
        else ("FAIL" if baseline_only_count or candidate_only_count or totals["different"] else "PASS")
    )
    runtime = _runtime_info((baseline_path, candidate_path), "aggregate-v1")
    resource_limits = {
        "max_input_bytes": max_input_bytes,
        "max_decoded_bytes": max_decoded_bytes,
        "max_rows_per_input": max_rows,
        "max_groups_per_input": max_groups,
    }
    if sqlite_summary:
        runtime.update(execution_engine="sqlite", temporary_bytes=sqlite_summary["temporary_bytes"])
        resource_limits["max_temp_bytes"] = max_temp_bytes
    return {
        "schema_version": 2,
        "outcome": outcome,
        "complete": not problems,
        "sensitivity": recipe["output"]["sensitivity"],
        "runtime": runtime,
        "resource_limits": resource_limits,
        "scope": recipe["scope"],
        "group_by": recipe["group_by"],
        "measures": recipe["measures"],
        "policy": _with_input_projection(
            recipe,
            {
                "group_nulls": "reject",
                "delimiters": recipe["delimiters"],
                "null_tokens": recipe["null_tokens"],
                "sensitivity": recipe["output"]["sensitivity"],
            },
            False,
        ),
        "column_policies": recipe["columns"],
        "column_mappings": recipe.get("column_mappings", {}),
        "problems": problems,
        "counts": {
            "baseline_rows": baseline_rows,
            "candidate_rows": candidate_rows,
            "baseline_groups": baseline_groups,
            "candidate_groups": candidate_groups,
            "common_groups": common_count,
            "baseline_only_groups": baseline_only_count,
            "candidate_only_groups": candidate_only_count,
            "exact_measures": totals["exact"],
            "within_tolerance_measures": totals["within_tolerance"],
            "different_measures": totals["different"],
        },
        "measure_counts": measure_counts,
        "measure_conservation": measure_conservation,
        "discrepancy_count": baseline_only_count + candidate_only_count + measure_discrepancies,
        "discrepancy_sample": discrepancies,
        "discrepancy_sample_limit": sample_limit if raw_output else 0,
        "excluded_columns": recipe.get("excluded_columns", {}),
        "inputs": {
            "baseline": _source_metadata(
                baseline_path,
                before[str(baseline_path)],
                decoded_sizes,
                recipe["delimiters"]["baseline"],
                recipe["null_tokens"]["baseline"],
                recipe["output"]["sensitivity"] == "raw",
            ),
            "candidate": _source_metadata(
                candidate_path,
                before[str(candidate_path)],
                decoded_sizes,
                recipe["delimiters"]["candidate"],
                recipe["null_tokens"]["candidate"],
                recipe["output"]["sensitivity"] == "raw",
            ),
        },
        "recipe_sha256": _digest(recipe_path),
        "policy_sha256": policy_sha256,
    }


def _sqlite_multiset_counts(
    sources: tuple[str | Path, str | Path],
    recipe: dict[str, Any],
    names: list[str],
    max_rows: int,
    max_distinct_rows: int,
    sample_limit: int,
    max_temp_bytes: int,
    temp_directory: str | Path | None,
    decoded_sizes: dict[Path, int],
) -> tuple[dict[str, int], list[dict[str, Any]], int, int]:
    parent = Path(temp_directory) if temp_directory is not None else None
    if parent is not None and (parent.is_symlink() or not parent.is_dir()):
        raise ParisonError("temp directory must be an existing non-symlink directory")
    try:
        with tempfile.TemporaryDirectory(prefix="parison-spill-", dir=parent) as workspace:
            database = Path(workspace) / "multiset.sqlite"
            connection = sqlite3.connect(database)
            try:
                page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
                page_limit = max_temp_bytes // page_size
                if page_limit < 4:
                    raise ParisonError(f"temporary storage limit {max_temp_bytes} bytes is too small")
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                connection.execute(f"PRAGMA max_page_count={page_limit}")
                connection.execute(
                    "CREATE TABLE counts (side INTEGER NOT NULL, encoded BLOB NOT NULL, row_json TEXT NOT NULL, occurrences INTEGER NOT NULL, PRIMARY KEY (side, encoded)) WITHOUT ROWID"
                )
                row_totals: list[int] = []
                for side_id, (side, source) in enumerate(zip(("baseline", "candidate"), sources, strict=False)):
                    rows = distinct = 0
                    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
                        row = _parse_row(raw, recipe, side)
                        values = tuple(row[name] for name in names)
                        encoded = _multiset_encoding(values, names, recipe)
                        rendered = json.dumps(
                            {name: _json_value(value) for name, value in zip(names, values, strict=False)},
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        )
                        cursor = connection.execute(
                            "INSERT OR IGNORE INTO counts VALUES (?, ?, ?, 0)",
                            (side_id, encoded, rendered),
                        )
                        if cursor.rowcount:
                            distinct += 1
                            if distinct > max_distinct_rows:
                                raise ParisonError(f"distinct row count in {side} exceeds limit {max_distinct_rows}")
                        connection.execute(
                            "UPDATE counts SET occurrences = occurrences + 1 WHERE side = ? AND encoded = ?",
                            (side_id, encoded),
                        )
                        rows += 1
                    row_totals.append(rows)
                connection.commit()
                records = connection.execute(
                    "SELECT baseline.encoded, baseline.row_json, baseline.occurrences, COALESCE(candidate.occurrences, 0) "
                    "FROM counts AS baseline LEFT JOIN counts AS candidate ON candidate.side = 1 AND candidate.encoded = baseline.encoded "
                    "WHERE baseline.side = 0 "
                    "UNION ALL "
                    "SELECT candidate.encoded, candidate.row_json, 0, candidate.occurrences FROM counts AS candidate "
                    "WHERE candidate.side = 1 AND NOT EXISTS (SELECT 1 FROM counts AS baseline WHERE baseline.side = 0 AND baseline.encoded = candidate.encoded) "
                    "ORDER BY 1"
                )
                summary, differing, differing_count = _summarize_multiset(
                    ((json.loads(row_json), left, right) for _, row_json, left, right in records),
                    row_totals[0],
                    row_totals[1],
                    recipe["output"]["sensitivity"] == "raw",
                    sample_limit,
                )
                return summary, differing, differing_count, database.stat().st_size
            finally:
                connection.close()
    except ParisonError:
        raise
    except sqlite3.Error as exc:
        if "full" in str(exc).lower():
            raise ParisonError(f"temporary storage exceeds limit {max_temp_bytes} bytes") from exc
        raise ParisonError(f"spill database failed: {exc}") from exc
    except OSError as exc:
        raise ParisonError(f"cannot use spill directory: {exc}") from exc


def _summarize_multiset(
    records, baseline_rows: int, candidate_rows: int, raw: bool, sample_limit: int
) -> tuple[dict[str, int], list[dict[str, Any]], int]:
    summary = {
        "baseline_rows": baseline_rows,
        "candidate_rows": candidate_rows,
        "common_occurrences": 0,
        "baseline_only_occurrences": 0,
        "candidate_only_occurrences": 0,
        "baseline_distinct_rows": 0,
        "candidate_distinct_rows": 0,
        "baseline_surplus_shapes": 0,
        "candidate_surplus_shapes": 0,
    }
    sample: list[dict[str, Any]] = []
    differing = 0
    for row, left, right in records:
        summary["baseline_distinct_rows"] += left > 0
        summary["candidate_distinct_rows"] += right > 0
        summary["common_occurrences"] += min(left, right)
        summary["baseline_only_occurrences"] += max(left - right, 0)
        summary["candidate_only_occurrences"] += max(right - left, 0)
        summary["baseline_surplus_shapes"] += left > right
        summary["candidate_surplus_shapes"] += right > left
        if left != right:
            differing += 1
            if raw and len(sample) < sample_limit:
                sample.append(
                    {
                        "row": row,
                        "baseline_count": left,
                        "candidate_count": right,
                        "classification": "baseline_surplus" if left > right else "candidate_surplus",
                    }
                )
    return summary, sample, differing


def _compare_multiset(
    recipe_path: Path,
    recipe: dict[str, Any],
    baseline_path: str | Path,
    candidate_path: str | Path,
    sample_limit: int,
    max_input_bytes: int,
    max_rows: int,
    max_decoded_bytes: int,
    max_distinct_rows: int,
    policy_sha256: str,
    engine: str = "memory",
    max_temp_bytes: int = DEFAULT_MAX_TEMP_BYTES,
    temp_directory: str | Path | None = None,
) -> dict[str, Any]:
    if _source_bytes(baseline_path) + _source_bytes(candidate_path) > max_input_bytes:
        raise ParisonError(f"combined input size exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes((baseline_path, candidate_path), max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in (baseline_path, candidate_path)}
    names = sorted(recipe["columns"])
    if engine == "sqlite":
        counts, differing_rows, differing_count, temporary_bytes = _sqlite_multiset_counts(
            (baseline_path, candidate_path),
            recipe,
            names,
            max_rows,
            max_distinct_rows,
            sample_limit,
            max_temp_bytes,
            temp_directory,
            decoded_sizes,
        )
        baseline_rows, candidate_rows = counts["baseline_rows"], counts["candidate_rows"]
    else:

        def counted(source, side):
            rows, _ = _read(source, recipe, max_rows, side, decoded_sizes)
            values = Counter(tuple(row[name] for name in names) for row in rows)
            if len(values) > max_distinct_rows:
                raise ParisonError(f"distinct row count in {side} exceeds limit {max_distinct_rows}")
            return values, len(rows)

        left, baseline_rows = counted(baseline_path, "baseline")
        right, candidate_rows = counted(candidate_path, "candidate")

        def sort_key(row):
            return _multiset_encoding(row, names, recipe)

        all_rows = sorted(set(left) | set(right), key=sort_key)
        counts, differing_rows, differing_count = _summarize_multiset(
            (
                ({name: _json_value(value) for name, value in zip(names, row, strict=False)}, left[row], right[row])
                for row in all_rows
            ),
            baseline_rows,
            candidate_rows,
            recipe["output"]["sensitivity"] == "raw",
            sample_limit,
        )
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being read")
    problems = (
        ["nonempty multiset inputs are required"]
        if not baseline_rows and not candidate_rows and not recipe["scope"]["expected_empty"]
        else []
    )
    raw = recipe["output"]["sensitivity"] == "raw"
    sample = differing_rows if raw else []
    runtime = _runtime_info((baseline_path, candidate_path), "multiset-v1")
    runtime["execution_engine"] = engine
    if engine == "sqlite":
        runtime["temporary_bytes"] = temporary_bytes
    limits = {
        "max_input_bytes": max_input_bytes,
        "max_decoded_bytes": max_decoded_bytes,
        "max_rows_per_input": max_rows,
        "max_distinct_rows_per_input": max_distinct_rows,
    }
    if engine == "sqlite":
        limits["max_temp_bytes"] = max_temp_bytes
    return {
        "schema_version": 3,
        "outcome": "INCONCLUSIVE" if problems else "FAIL" if differing_count else "PASS",
        "complete": not problems,
        "sensitivity": recipe["output"]["sensitivity"],
        "runtime": runtime,
        "resource_limits": limits,
        "scope": recipe["scope"],
        "policy": _with_input_projection(
            recipe,
            {"canonical_encoding": "typed-length-prefixed-v1", "column_order": names, "nulls_equal": True},
            False,
        ),
        "column_policies": recipe["columns"],
        "column_mappings": recipe.get("column_mappings", {}),
        "problems": problems,
        "counts": counts,
        "discrepancy_count": differing_count,
        "discrepancy_sample": sample,
        "discrepancy_sample_limit": sample_limit if raw else 0,
        "excluded_columns": recipe.get("excluded_columns", {}),
        "inputs": {
            side: _source_metadata(
                path,
                before[str(path)],
                decoded_sizes,
                recipe["delimiters"][side],
                recipe["null_tokens"][side],
                recipe["output"]["sensitivity"] == "raw",
            )
            for side, path in (("baseline", baseline_path), ("candidate", candidate_path))
        },
        "recipe_sha256": _digest(recipe_path),
        "policy_sha256": policy_sha256,
    }


def _report(result: dict[str, Any]) -> str:
    if result["schema_version"] == 2:
        return _aggregate_report(result)
    if result["schema_version"] == 3:
        return _multiset_report(result)

    def esc(value: Any) -> str:
        return html.escape(str(value))

    counts = "".join(f"<tr><th>{esc(k.replace('_', ' '))}</th><td>{v}</td></tr>" for k, v in result["counts"].items())
    problems = "".join(f"<li>{esc(item)}</li>" for item in result["problems"]) or "<li>None</li>"
    scope = result.get("scope") or {}
    scope_rows = (
        "".join(
            f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(', '.join(value) if isinstance(value, list) else value)}</td></tr>"
            for key, value in scope.items()
        )
        or '<tr><td colspan="2">Unavailable</td></tr>'
    )
    policy_rows = (
        "".join(
            f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(', '.join(value) if isinstance(value, list) else value)}</td></tr>"
            for key, value in result.get("policy", {}).items()
        )
        or '<tr><td colspan="2">Unavailable</td></tr>'
    )
    column_policy_rows = (
        "".join(
            f"<tr><th>{esc(name)}</th><td>{esc(result.get('column_mappings', {}).get(name, {}).get('baseline', name))}</td><td>{esc(result.get('column_mappings', {}).get(name, {}).get('candidate', name))}</td><td>{esc(policy['type'])}</td><td>{esc(policy.get('comparison', 'exact'))}</td><td>{esc(json.dumps({key: value for key, value in policy.items() if key not in {'type', 'comparison'}}, sort_keys=True))}</td></tr>"
            for name, policy in result.get("column_policies", {}).items()
        )
        or '<tr><td colspan="6">Unavailable</td></tr>'
    )
    field_rows = (
        "".join(
            f'<tr data-exact="{values["exact"]}" data-within_tolerance="{values["within_tolerance"]}" data-different="{values["different"]}"><th>{esc(name)}</th><td>{values["exact"]}</td><td>{values["within_tolerance"]}</td><td>{values["different"]}</td></tr>'
            for name, values in result["field_counts"].items()
        )
        or '<tr><td colspan="4">No comparable fields</td></tr>'
    )
    exclusion_rows = (
        "".join(
            f"<tr><th>{esc(name)}</th><td>{esc(reason)}</td></tr>"
            for name, reason in result["excluded_columns"].items()
        )
        or '<tr><td colspan="2">None</td></tr>'
    )
    runtime_rows = "".join(
        f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(value)}</td></tr>"
        for key, value in result["runtime"].items()
    )
    limit_rows = (
        "".join(
            f"<tr><th>{esc(key.replace('_', ' '))}</th><td>{esc(value)}</td></tr>"
            for key, value in result["resource_limits"].items()
        )
        or '<tr><td colspan="2">Unavailable</td></tr>'
    )
    input_rows = (
        "".join(
            f"<tr><th>{esc(side)}</th><td>{esc(values['bytes'])}</td><td><code>{esc(values['sha256'])}</code></td></tr>"
            for side, values in result["inputs"].items()
        )
        or '<tr><td colspan="3">Unavailable</td></tr>'
    )
    if result["sensitivity"] == "raw":
        rows = (
            "".join(
                f'<tr data-key="{esc(row.get("key", ""))}" data-field="{esc(row.get("field", ""))}" data-class="{esc(row.get("classification", ""))}">'
                + "".join(
                    f"<td>{esc(row.get(k, ''))}</td>"
                    for k in ("kind", "key", "field", "baseline", "candidate", "classification", "delta", "allowance")
                )
                + "</tr>"
                for row in result["discrepancy_sample"]
            )
            or '<tr><td colspan="8">No sampled discrepancies</td></tr>'
        )
        evidence = f"""<h2>Raw discrepancy evidence</h2><p><strong>Sensitive:</strong> this report contains source keys and values. Showing {len(result["discrepancy_sample"])} of {result["discrepancy_count"]} discrepancy items.</p>
<div class="filters"><label>Key contains <input id="raw-key" type="search"></label><label>Field <input id="raw-field" type="search"></label><label>Class <select id="raw-class"><option value="">All</option><option>baseline_only</option><option>candidate_only</option><option>within_tolerance</option><option>different</option></select></label></div><p id="raw-count" role="status" aria-live="polite">Showing {len(result["discrepancy_sample"])} of {len(result["discrepancy_sample"])} sampled items</p>
<table id="raw-evidence"><thead><tr><th>Kind</th><th>Key</th><th>Field</th><th>Baseline</th><th>Candidate</th><th>Class</th><th>Delta</th><th>Allowance</th></tr></thead><tbody>{rows}</tbody></table>"""
    else:
        evidence = "<h2>Privacy</h2><p>Summary mode stores no keys or raw field values. Field and record counts are complete.</p>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Parison report: {esc(result["outcome"])}</title><style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18202a}}h1{{color:{"#14733b" if result["outcome"] == "PASS" else "#a22"}}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #ccd3da;padding:.5rem;text-align:left;vertical-align:top}}th{{background:#f3f5f7}}code{{overflow-wrap:anywhere}}.filters{{display:flex;gap:1rem;flex-wrap:wrap}}label{{display:grid;gap:.25rem}}input,select{{font:inherit;padding:.35rem}}</style>
<main><h1>{esc(result["outcome"])}</h1><p>Complete evaluation: <strong>{str(result["complete"]).lower()}</strong></p>
<h2>Scope</h2><table>{scope_rows}</table><h2>Comparison policy</h2><table>{policy_rows}</table>
<h2>Column policies</h2><table><thead><tr><th>Field</th><th>Baseline column</th><th>Candidate column</th><th>Type</th><th>Comparison</th><th>Additional rules</th></tr></thead><tbody>{column_policy_rows}</tbody></table>
<h2>Record counts</h2><table>{counts}</table>
<h2>Field summary</h2><label>Show fields with <select id="field-class"><option value="">any result</option><option value="exact">exact matches</option><option value="within_tolerance">within-tolerance matches</option><option value="different">differences</option></select></label><p id="field-count" role="status" aria-live="polite">Showing {len(result["field_counts"])} of {len(result["field_counts"])} fields</p><table id="field-summary"><thead><tr><th>Field</th><th>Exact</th><th>Within tolerance</th><th>Different</th></tr></thead><tbody>{field_rows}</tbody></table>
<h2>Excluded columns</h2><table><thead><tr><th>Column</th><th>Rationale</th></tr></thead><tbody>{exclusion_rows}</tbody></table>
<h2>Preflight issues</h2><ul>{problems}</ul>{evidence}
<h2>Inputs</h2><table><thead><tr><th>Side</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{input_rows}</tbody></table>
<h2>Resource limits</h2><table>{limit_rows}</table><h2>Runtime</h2><table>{runtime_rows}</table>
<h2>Provenance</h2><p>Recipe SHA-256: <code>{esc(result.get("recipe_sha256") or "unavailable")}</code></p><p>Effective policy SHA-256: <code>{esc(result.get("policy_sha256") or "unavailable")}</code></p></main><script>
const fieldClass=document.querySelector('#field-class');
const setCount=(id,rows,label)=>document.querySelector(id).textContent='Showing '+[...rows].filter(row=>!row.hidden).length+' of '+rows.length+' '+label;
const fieldRows=document.querySelectorAll('#field-summary tbody tr[data-exact]');
const filterFields=()=>{{fieldRows.forEach(row=>row.hidden=fieldClass.value && Number(row.dataset[fieldClass.value])===0);setCount('#field-count',fieldRows,'fields');}};
fieldClass.addEventListener('change',filterFields);
filterFields();
const rawTable=document.querySelector('#raw-evidence');
if(rawTable){{const key=document.querySelector('#raw-key'),field=document.querySelector('#raw-field'),kind=document.querySelector('#raw-class'),rows=rawTable.querySelectorAll('tbody tr[data-class]');const filter=()=>{{rows.forEach(row=>row.hidden=!row.dataset.key.toLowerCase().includes(key.value.toLowerCase())||!row.dataset.field.toLowerCase().includes(field.value.toLowerCase())||(kind.value&&row.dataset.class!==kind.value));setCount('#raw-count',rows,'sampled items');}};key.addEventListener('input',filter);field.addEventListener('input',filter);kind.addEventListener('change',filter);filter();}}
</script></html>"""


def _aggregate_report(result: dict[str, Any]) -> str:
    def esc(value):
        return html.escape(str(value))

    counts = "".join(
        f"<tr><th>{esc(name.replace('_', ' '))}</th><td>{value}</td></tr>" for name, value in result["counts"].items()
    )
    measures = "".join(
        f"<tr><th>{esc(name)}</th><td>{values['exact']}</td><td>{values['within_tolerance']}</td><td>{values['different']}</td></tr>"
        for name, values in result["measure_counts"].items()
    )
    problems = "".join(f"<li>{esc(item)}</li>" for item in result["problems"]) or "<li>None</li>"
    evidence = "<p>Summary mode stores no group keys, per-group counts, aggregate values or source values.</p>"
    if result["sensitivity"] == "raw":
        rows = (
            "".join(
                "<tr>"
                + "".join(
                    f"<td>{esc(item.get(field, ''))}</td>"
                    for field in ("kind", "group", "measure", "baseline", "candidate", "classification")
                )
                + "</tr>"
                for item in result["discrepancy_sample"]
            )
            or '<tr><td colspan="6">No sampled discrepancies</td></tr>'
        )
        evidence = f"<p><strong>Sensitive:</strong> showing {len(result['discrepancy_sample'])} of {result['discrepancy_count']} discrepancy items.</p><table><thead><tr><th>Kind</th><th>Group</th><th>Measure</th><th>Baseline</th><th>Candidate</th><th>Class</th></tr></thead><tbody>{rows}</tbody></table>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Parison aggregate report: {esc(result["outcome"])}</title><style>body{{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#18202a}}h1{{color:{"#14733b" if result["outcome"] == "PASS" else "#a22"}}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #ccd3da;padding:.5rem;text-align:left}}th{{background:#f3f5f7}}code{{overflow-wrap:anywhere}}</style>
<main><h1>{esc(result["outcome"])}</h1><p>Complete aggregate evaluation: <strong>{str(result["complete"]).lower()}</strong>. Aggregate equality does not prove row equality.</p>
<h2>Group and row counts</h2><table>{counts}</table>
<h2>Measure summary</h2><table><thead><tr><th>Measure</th><th>Exact</th><th>Within tolerance</th><th>Different</th></tr></thead><tbody>{measures}</tbody></table>
<h2>Issues</h2><ul>{problems}</ul><h2>Evidence and privacy</h2>{evidence}
<h2>Provenance</h2><p>Recipe SHA-256: <code>{esc(result["recipe_sha256"])}</code></p><p>Effective policy SHA-256: <code>{esc(result["policy_sha256"])}</code></p></main></html>"""


def _multiset_report(result: dict[str, Any]) -> str:
    def esc(value):
        return html.escape(str(value))

    counts = "".join(
        f"<tr><th>{esc(name.replace('_', ' '))}</th><td>{value}</td></tr>" for name, value in result["counts"].items()
    )
    problems = "".join(f"<li>{esc(item)}</li>" for item in result["problems"]) or "<li>None</li>"
    evidence = "<p>Summary mode stores no row values.</p>"
    if result["sensitivity"] == "raw":
        rows = (
            "".join(
                f"<tr><td>{esc(item['classification'])}</td><td>{item['baseline_count']}</td><td>{item['candidate_count']}</td><td><code>{esc(json.dumps(item['row'], sort_keys=True))}</code></td></tr>"
                for item in result["discrepancy_sample"]
            )
            or '<tr><td colspan="4">No sampled discrepancies</td></tr>'
        )
        evidence = f"<p><strong>Sensitive:</strong> showing {len(result['discrepancy_sample'])} row shapes.</p><table><tr><th>Class</th><th>Baseline</th><th>Candidate</th><th>Row</th></tr>{rows}</table>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Parison multiset report: {esc(result["outcome"])}</title><style>body{{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3da;padding:.5rem;text-align:left}}</style><main><h1>{esc(result["outcome"])}</h1><p>Complete multiset evaluation: <strong>{str(result["complete"]).lower()}</strong>.</p><table>{counts}</table><h2>Issues</h2><ul>{problems}</ul><h2>Evidence and privacy</h2>{evidence}</main></html>"""
