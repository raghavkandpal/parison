from __future__ import annotations

import csv
import gzip
import hashlib
import html
import json
import math
import multiprocessing
import os
import platform
import re
import shutil
import sqlite3
import tempfile
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from importlib import metadata, resources
from multiprocessing.connection import wait
from pathlib import Path
from typing import Any

OUTCOME_CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "INCONCLUSIVE": 3, "INTERRUPTED": 130}
_RECIPE_KEYS = {
    "recipe_version",
    "comparison_mode",
    "keys",
    "scope",
    "identity",
    "nulls_equal",
    "null_tokens",
    "columns",
    "column_mappings",
    "excluded_columns",
    "delimiters",
    "input_projection",
    "output",
}
_AGGREGATE_RECIPE_KEYS = {
    "recipe_version",
    "comparison_mode",
    "group_by",
    "measures",
    "scope",
    "null_tokens",
    "columns",
    "column_mappings",
    "excluded_columns",
    "delimiters",
    "input_projection",
    "output",
}
_MULTISET_RECIPE_KEYS = {
    "recipe_version",
    "comparison_mode",
    "scope",
    "null_tokens",
    "columns",
    "column_mappings",
    "excluded_columns",
    "delimiters",
    "input_projection",
    "output",
}
_COLUMN_KEYS = {"type", "comparison", "tolerance", "timezone", "scale", "normalize"}
_MEASURE_KEYS = {"operator", "column", "nulls", "comparison", "tolerance"}
_TYPES = {"string", "integer", "decimal", "float", "boolean", "date", "timestamp"}
_NORMALIZATIONS = {"trim", "casefold", "unicode_nfc"}
_INPUT_PROJECTIONS = {"semantic-scalar-v1"}
_RAW_VALUE = object()
_FILE_FORMATS = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
    ".parquet": "parquet",
    ".pq": "parquet",
}
_SCHEMAS = {
    "recipe-authoring": "recipe-authoring.schema.json",
    "recipe": "recipe-v1.schema.json",
    "recipe-v2": "recipe-v2.schema.json",
    "recipe-v3": "recipe-v3.schema.json",
    "result": "result-v1.schema.json",
    "result-v2": "result-v2.schema.json",
    "result-v3": "result-v3.schema.json",
    "manifest": "manifest-v1.schema.json",
    "preflight": "preflight-v1.schema.json",
    "preflight-v2": "preflight-v2.schema.json",
    "preflight-v3": "preflight-v3.schema.json",
    "suite": "suite-v1.schema.json",
    "suite-authoring": "suite-authoring.schema.json",
    "suite-v2": "suite-v2.schema.json",
    "suite-result": "suite-result-v1.schema.json",
    "suite-result-v2": "suite-result-v2.schema.json",
    "suite-manifest": "suite-manifest-v1.schema.json",
    "suite-manifest-v2": "suite-manifest-v2.schema.json",
    "statement": "statement-v1.schema.json",
    "schema-evolution": "schema-evolution-v1.schema.json",
    "policy-diff": "policy-diff-v1.schema.json",
    "time-alignment": "time-alignment-v1.schema.json",
    "reconciliation": "reconciliation-v1.schema.json",
    "alignment-preflight": "alignment-preflight-v1.schema.json",
    "relationship-result": "relationship-result-v1.schema.json",
    "conservation-result": "conservation-result-v1.schema.json",
    "reconciliation-result": "reconciliation-result-v1.schema.json",
    "dataset-manifest": "dataset-manifest-v1.schema.json",
    "reproducibility-diagnostic": "reproducibility-diagnostic-v1.schema.json",
}

_SUITE_LIMIT_DEFAULTS = {
    "max_input_bytes": 1_000_000_000,
    "max_decoded_bytes": 1_000_000_000,
    "max_rows": 5_000_000,
    "max_groups": 100_000,
    "max_distinct_rows": 100_000,
}
_SUITE_LIMIT_KEYS = set(_SUITE_LIMIT_DEFAULTS)
_MAX_SUITE_JOBS = 16
DEFAULT_MAX_TEMP_BYTES = 5_000_000_000


class ParisonError(ValueError):
    pass


class _SafeParseError(ValueError):
    pass


def _file_format(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".gz":
        suffix = Path(path.stem).suffix.lower()
        if suffix not in {".csv", ".tsv", ".jsonl", ".ndjson"}:
            return None
    return _FILE_FORMATS.get(suffix)


class _LimitedText:
    def __init__(self, handle, limit: int, path: Path):
        self.handle, self.remaining, self.path = handle, limit, path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.handle.close()

    def __iter__(self):
        return self

    def __next__(self):
        line = self.handle.readline(self.remaining + 1)
        if not line:
            raise StopIteration
        size = len(line.encode("utf-8"))
        if size > self.remaining:
            raise ParisonError(f"decoded input changed or exceeds checked size: {self.path}")
        self.remaining -= size
        return line


def _open_text(path: Path, decoded_sizes: dict[Path, int], newline: str | None = None):
    if path.suffix.lower() != ".gz":
        return path.open("r", encoding="utf-8", newline=newline)
    return _LimitedText(gzip.open(path, "rt", encoding="utf-8", newline=newline), decoded_sizes[path], path)


def load_schema(name: str) -> dict[str, Any]:
    if name not in _SCHEMAS:
        raise ParisonError(f"unknown schema {name!r}; choose {', '.join(_SCHEMAS)}")
    return json.loads(resources.files("parison").joinpath("schemas", _SCHEMAS[name]).read_text(encoding="utf-8"))


def export_editor_schemas(output: str | Path) -> dict[str, Any]:
    """Atomically export offline recipe and suite authoring schema sets."""
    target = Path(output)
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    exports = {
        "recipe.schema.json": "recipe-authoring",
        "recipe-v1.schema.json": "recipe",
        "recipe-v2.schema.json": "recipe-v2",
        "recipe-v3.schema.json": "recipe-v3",
        "suite.schema.json": "suite-authoring",
        "suite-v1.schema.json": "suite",
        "suite-v2.schema.json": "suite-v2",
    }
    stage = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        for filename, name in exports.items():
            schema = load_schema(name)
            schema.pop("$id")
            (stage / filename).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(stage, target)
        return {"output": str(target), "files": sorted(exports)}
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot export editor schemas: {exc}") from exc


def load_suite(path: str | Path) -> dict[str, Any]:
    suite_path = Path(path)
    try:
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read suite: {exc}") from exc
    if not isinstance(suite, dict) or suite.get("suite_version") not in {1, 2}:
        raise ParisonError("suite_version must be 1 or 2")
    version = suite["suite_version"]
    allowed_top = {"suite_version", "cases"} | ({"defaults"} if version == 2 else set())
    if set(suite) - allowed_top or not {"suite_version", "cases"} <= set(suite):
        raise ParisonError(f"suite v{version} has invalid fields")
    defaults = suite.get("defaults", {})
    if version == 2:
        if not isinstance(defaults, dict) or set(defaults) - {"limits"}:
            raise ParisonError("suite defaults may contain only limits")
        default_limits = defaults.get("limits", {})
        _validate_suite_limits(default_limits, "suite defaults")
    else:
        default_limits = {}
    cases = suite["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
        raise ParisonError("suite cases must be a nonempty array of at most 100 cases")
    base = suite_path.parent.absolute()
    loaded, identifiers = [], set()
    for index, case in enumerate(cases):
        required = {"id", "recipe", "baseline", "candidate"}
        optional = {"expected_policy_sha256"} | (
            {"tags", "description", "limits", "execution"} if version == 2 else set()
        )
        if not isinstance(case, dict) or not required <= set(case) or set(case) - required - optional:
            raise ParisonError(f"suite case {index} has invalid fields")
        identifier = case["id"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in identifier)
            or identifier.startswith("-")
            or identifier.endswith("-")
            or "--" in identifier
        ):
            raise ParisonError(f"suite case {index} has an invalid id")
        if identifier in identifiers:
            raise ParisonError(f"duplicate suite case id: {identifier}")
        identifiers.add(identifier)
        resolved = {"id": identifier}
        portable = {"id": identifier}
        for name in ("recipe", "baseline", "candidate"):
            value = case[name]
            if not isinstance(value, str) or not value or "\0" in value:
                raise ParisonError(f"suite case {identifier} has an invalid {name} reference")
            if version == 2:
                reference = value.split("#", 1)[0].removeprefix("sqlite:")
                if Path(reference).is_absolute():
                    raise ParisonError(f"suite case {identifier} {name} must be a portable plan-relative reference")
            sqlite_source = _sqlite_source(value) if name != "recipe" else None
            source_path = sqlite_source[0] if sqlite_source else Path(value)
            if not source_path.is_absolute():
                source_path = Path(os.path.abspath(base / source_path))
            if source_path.is_symlink():
                raise ParisonError(f"suite case {identifier} {name} must not be a symlink")
            resolved[name] = f"sqlite:{source_path}#{sqlite_source[1]}" if sqlite_source else str(source_path)
            portable[name] = value
        recipe = load_recipe(resolved["recipe"])
        expected = case.get("expected_policy_sha256")
        policy_sha256 = _checked_policy_sha256(recipe, expected)
        for name in ("baseline", "candidate"):
            source_path = _source_path(resolved[name])
            if not source_path.is_file() and not source_path.is_dir():
                raise ParisonError(f"suite case {identifier} {name} is not a regular input")
            _source_paths(resolved[name])
        if expected is not None:
            resolved["expected_policy_sha256"] = expected
            portable["expected_policy_sha256"] = expected
        if version == 2:
            tags = case.get("tags", [])
            if (
                not isinstance(tags, list)
                or len(tags) > 20
                or tags != sorted(set(tags))
                or not all(_portable_identifier(tag) and len(tag) <= 64 for tag in tags)
            ):
                raise ParisonError(f"suite case {identifier} tags must be sorted unique portable identifiers")
            description = case.get("description")
            if description is not None and (
                not isinstance(description, str) or not description or len(description) > 500
            ):
                raise ParisonError(f"suite case {identifier} has an invalid description")
            limits = case.get("limits", {})
            _validate_suite_limits(limits, f"suite case {identifier}")
            execution = case.get("execution", {})
            if (
                not isinstance(execution, dict)
                or set(execution) - {"engine", "max_temp_bytes"}
                or (execution and execution.get("engine") != "sqlite")
                or (
                    "max_temp_bytes" in execution
                    and (
                        not isinstance(execution["max_temp_bytes"], int)
                        or isinstance(execution["max_temp_bytes"], bool)
                        or execution["max_temp_bytes"] <= 0
                    )
                )
            ):
                raise ParisonError(f"suite case {identifier} has invalid execution settings")
            if execution and recipe["comparison_mode"] == "aggregate":
                raise ParisonError(f"suite case {identifier} sqlite execution does not support an aggregate recipe")
            effective_limits = {**_SUITE_LIMIT_DEFAULTS, **default_limits, **limits}
            resolved.update({"tags": tags, "limits": effective_limits, "policy_sha256": policy_sha256})
            portable.update({"tags": tags, "limits": effective_limits, "policy_sha256": policy_sha256})
            if description is not None:
                resolved["description"] = description
                portable["description"] = description
            if execution:
                resolved["execution"] = execution
                portable["execution"] = execution
        loaded.append(resolved)
        if version == 2:
            resolved["portable"] = portable
    result = {"suite_version": version, "cases": loaded}
    if version == 2:
        effective = {"suite_version": 2, "cases": [case["portable"] for case in loaded]}
        result["suite_policy_sha256"] = hashlib.sha256(
            json.dumps(effective, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
    return result


def _portable_identifier(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and all(character in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in value)
        and not value.startswith("-")
        and not value.endswith("-")
        and "--" not in value
    )


def _validate_suite_limits(limits: Any, where: str) -> None:
    if not isinstance(limits, dict) or set(limits) - _SUITE_LIMIT_KEYS:
        raise ParisonError(f"{where} limits contain invalid fields")
    if not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in limits.values()):
        raise ParisonError(f"{where} limits must be positive integers")


def select_suite_cases(
    suite: dict[str, Any],
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
) -> list[dict[str, Any]]:
    """Select suite cases once, in plan order, for listing and execution."""
    case_ids, tags = case_ids or [], tags or []
    if suite["suite_version"] != 2 and (case_ids or tags or shard_index is not None or shard_count is not None):
        raise ParisonError("selection and sharding require suite_version 2")
    if len(case_ids) != len(set(case_ids)) or len(tags) != len(set(tags)):
        raise ParisonError("case and tag filters must be unique")
    if any(not _portable_identifier(value) for value in case_ids + tags):
        raise ParisonError("case and tag filters must be portable identifiers")
    unknown_cases = set(case_ids) - {case["id"] for case in suite["cases"]}
    if unknown_cases:
        raise ParisonError(f"unknown suite case filter(s): {', '.join(sorted(unknown_cases))}")
    if (shard_index is None) != (shard_count is None):
        raise ParisonError("shard index and count must be provided together")
    if shard_count is not None and (not 1 <= shard_count <= 100 or not 0 <= shard_index < shard_count):
        raise ParisonError("shard count must be 1..100 and index must be within it")
    selected = [
        case
        for case in suite["cases"]
        if (not case_ids or case["id"] in case_ids) and (not tags or all(tag in case.get("tags", []) for tag in tags))
    ]
    if shard_count is not None:
        selected = [case for position, case in enumerate(selected) if position % shard_count == shard_index]
    if not selected:
        raise ParisonError("suite selection contains no cases")
    return selected


def list_suite(
    plan: str | Path,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
) -> dict[str, Any]:
    suite = load_suite(plan)
    selected = select_suite_cases(suite, case_ids, tags, shard_index, shard_count)
    return {
        "suite_version": suite["suite_version"],
        "suite_policy_sha256": suite.get("suite_policy_sha256"),
        "total_cases": len(suite["cases"]),
        "selected_cases": len(selected),
        "selection": {
            "case_ids": case_ids or [],
            "tags": tags or [],
            "shard_index": shard_index,
            "shard_count": shard_count,
        },
        "cases": [
            {name: case[name] for name in ("id", "tags", "description", "limits", "execution") if name in case}
            | {"comparison_mode": load_recipe(case["recipe"])["comparison_mode"]}
            for case in selected
        ],
    }


def _runtime_info(paths: tuple[Any, Any] | None = None, contract: str = "keyed-v1") -> dict[str, Any]:
    try:
        version = metadata.version("parison")
    except metadata.PackageNotFoundError:
        version = "source-tree"
    runtime = {
        "contract": contract,
        "parison_version": version,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.system(),
        "machine": platform.machine(),
    }
    if paths and any(_file_format(_source_path(path)) == "parquet" for path in paths):
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
    if recipe.get("recipe_version") == 2:
        return _load_aggregate_recipe(recipe)
    if recipe.get("recipe_version") == 3:
        return _load_multiset_recipe(recipe)
    _unknown(recipe, _RECIPE_KEYS, "recipe")
    if recipe.get("recipe_version") != 1:
        raise ParisonError("recipe_version must be 1")
    if recipe.get("comparison_mode") != "keyed":
        raise ParisonError("comparison_mode must be 'keyed'")
    keys = recipe.get("keys")
    if (
        not isinstance(keys, list)
        or not keys
        or not all(isinstance(k, str) and k for k in keys)
        or len(keys) != len(set(keys))
    ):
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
    delimiters = recipe.get("delimiters", {"baseline": ",", "candidate": ","})
    if not isinstance(delimiters, dict) or set(delimiters) != {"baseline", "candidate"}:
        raise ParisonError("delimiters must contain exactly baseline and candidate")
    for side, delimiter in delimiters.items():
        if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in {'"', "\r", "\n", "\0"}:
            raise ParisonError(f"delimiters.{side} must be one character other than quote, newline or NUL")
    recipe["delimiters"] = delimiters
    null_tokens = recipe.get("null_tokens", {"baseline": [], "candidate": []})
    if not isinstance(null_tokens, dict) or set(null_tokens) != {"baseline", "candidate"}:
        raise ParisonError("null_tokens must contain exactly baseline and candidate")
    for side, tokens in null_tokens.items():
        if (
            not isinstance(tokens, list)
            or not all(isinstance(token, str) and token for token in tokens)
            or len(tokens) != len(set(tokens))
        ):
            raise ParisonError(f"null_tokens.{side} must be a list of unique nonempty strings")
    recipe["null_tokens"] = null_tokens
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
        normalize = policy.get("normalize", [])
        if not isinstance(normalize, list) or not all(isinstance(rule, str) for rule in normalize):
            raise ParisonError(f"columns.{name}.normalize must be a list of unique supported rules")
        if len(normalize) != len(set(normalize)) or not all(rule in _NORMALIZATIONS for rule in normalize):
            raise ParisonError(f"columns.{name}.normalize must be a list of unique supported rules")
        if normalize and policy["type"] != "string":
            raise ParisonError(f"columns.{name}.normalize is only valid for strings")
    excluded = recipe.get("excluded_columns", {})
    if not isinstance(excluded, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v for k, v in excluded.items()
    ):
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
    if (
        not isinstance(output, dict)
        or set(output) != {"sensitivity"}
        or output["sensitivity"] not in {"summary", "raw"}
    ):
        raise ParisonError("output must contain sensitivity='summary' or sensitivity='raw'")
    recipe["output"] = output
    _validate_input_projection(recipe)
    return recipe


def _load_aggregate_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    _unknown(recipe, _AGGREGATE_RECIPE_KEYS, "recipe")
    if recipe.get("comparison_mode") != "aggregate":
        raise ParisonError("recipe_version 2 requires comparison_mode='aggregate'")
    group_by = recipe.get("group_by")
    if (
        not isinstance(group_by, list)
        or not all(isinstance(name, str) and name for name in group_by)
        or len(group_by) != len(set(group_by))
    ):
        raise ParisonError("group_by must be a list of unique column names")
    measures = recipe.get("measures")
    if not isinstance(measures, dict) or not measures:
        raise ParisonError("measures must be a nonempty object")
    if not all(isinstance(name, str) and name for name in measures):
        raise ParisonError("measure names must be nonempty strings")
    _validate_common_recipe(recipe)
    columns = recipe["columns"]
    if not set(group_by) <= set(columns):
        raise ParisonError("every group_by name must have a column policy")
    for name in group_by:
        if columns[name].get("comparison", "exact") != "exact":
            raise ParisonError(f"group_by column {name} must use exact comparison")
    for name, measure in measures.items():
        if not isinstance(measure, dict):
            raise ParisonError(f"measures.{name} must be an object")
        _unknown(measure, _MEASURE_KEYS, f"measures.{name}")
        operator = measure.get("operator")
        if operator not in {"count", "sum", "min", "max"}:
            raise ParisonError(f"measures.{name}.operator is unsupported")
        if operator == "count":
            if set(measure) != {"operator"}:
                raise ParisonError(f"count measure {name} accepts only operator")
            continue
        column = measure.get("column")
        if not isinstance(column, str) or column not in columns:
            raise ParisonError(f"measures.{name}.column must name a configured column")
        if measure.get("nulls") not in {"reject", "ignore"}:
            raise ParisonError(f"measures.{name}.nulls must be 'reject' or 'ignore'")
        if operator == "sum" and columns[column]["type"] not in {"integer", "decimal"}:
            raise ParisonError(f"sum measure {name} requires an integer or decimal column")
        comparison = measure.get("comparison", "exact")
        if comparison not in {"exact", "numeric"}:
            raise ParisonError(f"measures.{name}.comparison is unsupported")
        tolerance = measure.get("tolerance")
        if comparison == "numeric":
            if columns[column]["type"] not in {"integer", "decimal"}:
                raise ParisonError(f"numeric measure {name} requires an integer or decimal column")
            _validate_tolerance(tolerance, f"measures.{name}")
        elif tolerance is not None:
            raise ParisonError(f"measures.{name}.tolerance requires numeric comparison")
    return recipe


def _load_multiset_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    _unknown(recipe, _MULTISET_RECIPE_KEYS, "recipe")
    if recipe.get("comparison_mode") != "multiset":
        raise ParisonError("recipe_version 3 requires comparison_mode='multiset'")
    _validate_common_recipe(recipe, "multiset")
    return recipe


def _validate_tolerance(tolerance: Any, where: str) -> None:
    if not isinstance(tolerance, dict) or set(tolerance) != {"formula", "absolute", "relative"}:
        raise ParisonError(f"{where}.tolerance must define formula, absolute and relative")
    if tolerance["formula"] != "symmetric-v1":
        raise ParisonError(f"{where} requires symmetric-v1 tolerance")
    try:
        values = [Decimal(str(tolerance[key])) for key in ("absolute", "relative")]
    except InvalidOperation as exc:
        raise ParisonError(f"{where} tolerance is not numeric") from exc
    if any(not value.is_finite() or value < 0 for value in values):
        raise ParisonError(f"{where} tolerances must be finite and non-negative")


def _validate_common_recipe(recipe: dict[str, Any], mode: str = "aggregate") -> None:
    scope = recipe.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"snapshot", "cutoff", "filters", "completeness", "expected_empty"}:
        raise ParisonError("scope must contain exactly snapshot, cutoff, filters, completeness and expected_empty")
    if not all(isinstance(scope[field], str) and scope[field] for field in ("snapshot", "cutoff")):
        raise ParisonError("scope.snapshot and scope.cutoff must be nonempty strings")
    if not isinstance(scope["filters"], list) or not all(isinstance(item, str) and item for item in scope["filters"]):
        raise ParisonError("scope.filters must be a list of nonempty strings")
    if scope["completeness"] != "full" or not isinstance(scope["expected_empty"], bool):
        raise ParisonError("scope requires completeness='full' and boolean expected_empty")
    columns = recipe.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ParisonError("columns must be a nonempty object")
    for name, policy in columns.items():
        if not isinstance(name, str) or not name or not isinstance(policy, dict):
            raise ParisonError("columns must map nonempty names to policies")
        _unknown(policy, _COLUMN_KEYS, f"columns.{name}")
        if policy.get("type") not in _TYPES:
            raise ParisonError(f"columns.{name}.type is unsupported")
        comparison = policy.get("comparison", "exact")
        if comparison != "exact":
            suffix = "; measures own comparison policy" if mode == "aggregate" else ""
            raise ParisonError(f"{mode} column {name} must use exact comparison{suffix}")
        if policy["type"] == "decimal":
            if not isinstance(policy.get("scale"), int) or isinstance(policy.get("scale"), bool) or policy["scale"] < 0:
                raise ParisonError(f"columns.{name}.scale must be a non-negative integer")
        elif "scale" in policy:
            raise ParisonError(f"columns.{name}.scale is only valid for decimals")
        if policy["type"] == "timestamp":
            if policy.get("timezone") != "require-aware":
                raise ParisonError(f"columns.{name}.timezone must be 'require-aware'")
        elif "timezone" in policy:
            raise ParisonError(f"columns.{name}.timezone is only valid for timestamps")
        normalize = policy.get("normalize", [])
        if (
            not isinstance(normalize, list)
            or len(normalize) != len(set(normalize))
            or not all(rule in _NORMALIZATIONS for rule in normalize)
        ):
            raise ParisonError(f"columns.{name}.normalize must be a list of unique supported rules")
        if normalize and policy["type"] != "string":
            raise ParisonError(f"columns.{name}.normalize is only valid for strings")
    delimiters = recipe.get("delimiters", {"baseline": ",", "candidate": ","})
    if not isinstance(delimiters, dict) or set(delimiters) != {"baseline", "candidate"}:
        raise ParisonError("delimiters must contain exactly baseline and candidate")
    if any(
        not isinstance(value, str) or len(value) != 1 or value in {'"', "\r", "\n", "\0"}
        for value in delimiters.values()
    ):
        raise ParisonError("delimiters must be one character other than quote, newline or NUL")
    recipe["delimiters"] = delimiters
    null_tokens = recipe.get("null_tokens", {"baseline": [], "candidate": []})
    if not isinstance(null_tokens, dict) or set(null_tokens) != {"baseline", "candidate"}:
        raise ParisonError("null_tokens must contain exactly baseline and candidate")
    if any(
        not isinstance(tokens, list)
        or len(tokens) != len(set(tokens))
        or not all(isinstance(token, str) and token for token in tokens)
        for tokens in null_tokens.values()
    ):
        raise ParisonError("null_tokens must contain lists of unique nonempty strings")
    recipe["null_tokens"] = null_tokens
    mappings = recipe.get("column_mappings", {})
    if not isinstance(mappings, dict) or not set(mappings) <= set(columns):
        raise ParisonError("column_mappings must name configured columns")
    for name, mapping in mappings.items():
        if (
            not isinstance(mapping, dict)
            or set(mapping) != {"baseline", "candidate"}
            or not all(isinstance(value, str) and value for value in mapping.values())
        ):
            raise ParisonError(f"column_mappings.{name} must contain nonempty baseline and candidate names")
    for side in ("baseline", "candidate"):
        source_names = [mappings.get(name, {}).get(side, name) for name in columns]
        if len(source_names) != len(set(source_names)):
            raise ParisonError(f"column_mappings must use unique {side} source columns")
    excluded = recipe.get("excluded_columns", {})
    if not isinstance(excluded, dict) or not all(
        isinstance(name, str) and isinstance(reason, str) and reason for name, reason in excluded.items()
    ):
        raise ParisonError("excluded_columns must map column names to nonempty rationales")
    if set(columns) & set(excluded):
        raise ParisonError("columns cannot also be excluded")
    output = recipe.get("output", {"sensitivity": "summary"})
    if (
        not isinstance(output, dict)
        or set(output) != {"sensitivity"}
        or output["sensitivity"] not in {"summary", "raw"}
    ):
        raise ParisonError("output must contain sensitivity='summary' or sensitivity='raw'")
    recipe["output"] = output
    _validate_input_projection(recipe)


def _validate_input_projection(recipe: dict[str, Any]) -> None:
    projection = recipe.get("input_projection")
    if projection is not None and projection not in _INPUT_PROJECTIONS:
        raise ParisonError("input_projection must be 'semantic-scalar-v1'")


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
                raise _SafeParseError("non-finite decimal")
            if max(-value.as_tuple().exponent, 0) > policy["scale"]:
                raise _SafeParseError(f"value exceeds configured scale {policy['scale']}")
            return value
        if kind == "float":
            value = float(raw)
            if not math.isfinite(value):
                raise _SafeParseError("non-finite float")
            return value
        if kind == "boolean":
            if isinstance(raw, bool):
                return raw
            if raw == "true":
                return True
            if raw == "false":
                return False
            raise _SafeParseError("expected true or false")
        if kind == "date":
            return date.fromisoformat(str(raw))
        if kind == "timestamp":
            text = str(raw)
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if value.tzinfo is None:
                raise _SafeParseError("timestamp requires an explicit timezone")
            return value
    except _SafeParseError as exc:
        raise ParisonError(f"cannot parse column {column} as {kind}: {exc}") from exc
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ParisonError(f"cannot parse column {column} as {kind}") from exc
    raise AssertionError(kind)


def _parse_input(raw: Any, policy: dict[str, Any], column: str, recipe: dict[str, Any]) -> Any:
    if recipe.get("input_projection") != "semantic-scalar-v1" or raw is None:
        return _parse(raw, policy, column)
    kind = policy["type"]
    exact_type = type(raw)
    allowed = {
        "string": {str},
        "integer": {str, int},
        "decimal": {str, int, Decimal},
        "float": {str, int, float},
        "boolean": {str, bool},
        "date": {str, date},
        "timestamp": {str, datetime},
    }[kind]
    if exact_type not in allowed or (raw == "" and kind != "string"):
        raise ParisonError(f"cannot project column {column} to {kind} under semantic-scalar-v1")
    if kind == "timestamp" and exact_type is str:
        fraction = re.search(r"\d{2}:?\d{2}:?\d{2}[.,](\d+)", raw)
        if fraction and len(fraction.group(1)) > 6:
            raise ParisonError(f"cannot parse column {column} as timestamp: timestamp precision exceeds microseconds")
    if kind == "timestamp" and exact_type is datetime and raw.tzinfo is None:
        raise ParisonError(f"cannot project column {column} to timestamp under semantic-scalar-v1: timezone required")
    value = _parse(raw, policy, column)
    if kind == "integer" and not -(2**63) <= value < 2**63:
        raise ParisonError(
            f"cannot project column {column} to integer under semantic-scalar-v1: outside signed 64-bit range"
        )
    return value


def _source_name(recipe: dict[str, Any], name: str, side: str) -> str:
    return recipe.get("column_mappings", {}).get(name, {}).get(side, name)


def _with_input_projection(recipe: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    if "input_projection" in recipe:
        policy["input_projection"] = recipe["input_projection"]
    return policy


def _effective_policy(recipe: dict[str, Any]) -> dict[str, Any]:
    if recipe["comparison_mode"] == "aggregate":
        return _effective_aggregate_policy(recipe)
    if recipe["comparison_mode"] == "multiset":
        return _effective_multiset_policy(recipe)
    columns = {}
    for name, configured in recipe["columns"].items():
        policy = dict(configured)
        policy["comparison"] = policy.get("comparison", "exact")
        policy["normalize"] = policy.get("normalize", [])
        columns[name] = {
            "key": name in recipe["keys"],
            "baseline_column": _source_name(recipe, name, "baseline"),
            "candidate_column": _source_name(recipe, name, "candidate"),
            **policy,
        }
    policy = _with_input_projection(
        recipe,
        {
            "schema_version": 1,
            "recipe_version": recipe["recipe_version"],
            "comparison_mode": recipe["comparison_mode"],
            "scope": recipe["scope"],
            "identity": recipe["identity"],
            "nulls_equal": recipe["nulls_equal"],
            "delimiters": recipe["delimiters"],
            "null_tokens": recipe["null_tokens"],
            "columns": columns,
            "excluded_columns": recipe.get("excluded_columns", {}),
            "output": recipe.get("output", {"sensitivity": "summary"}),
        },
    )
    policy["policy_sha256"] = hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return policy


def _effective_aggregate_policy(recipe: dict[str, Any]) -> dict[str, Any]:
    columns = {}
    for name, configured in recipe["columns"].items():
        policy = dict(configured)
        policy["comparison"] = "exact"
        policy["normalize"] = policy.get("normalize", [])
        columns[name] = {
            "group_by": name in recipe["group_by"],
            "baseline_column": _source_name(recipe, name, "baseline"),
            "candidate_column": _source_name(recipe, name, "candidate"),
            **policy,
        }
    measures = {}
    for name, configured in recipe["measures"].items():
        measure = dict(configured)
        if measure["operator"] != "count":
            measure["comparison"] = measure.get("comparison", "exact")
        measures[name] = measure
    policy = _with_input_projection(
        recipe,
        {
            "schema_version": 2,
            "recipe_version": 2,
            "comparison_mode": "aggregate",
            "aggregate_contract": "aggregate-v1",
            "scope": recipe["scope"],
            "group_by": recipe["group_by"],
            "group_nulls": "reject",
            "measures": measures,
            "delimiters": recipe["delimiters"],
            "null_tokens": recipe["null_tokens"],
            "columns": columns,
            "excluded_columns": recipe.get("excluded_columns", {}),
            "output": recipe["output"],
        },
    )
    policy["policy_sha256"] = hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return policy


def _effective_multiset_policy(recipe: dict[str, Any]) -> dict[str, Any]:
    columns = {}
    for name in sorted(recipe["columns"]):
        configured = recipe["columns"][name]
        columns[name] = {
            "baseline_column": _source_name(recipe, name, "baseline"),
            "candidate_column": _source_name(recipe, name, "candidate"),
            **configured,
            "comparison": "exact",
            "normalize": configured.get("normalize", []),
        }
    policy = _with_input_projection(
        recipe,
        {
            "schema_version": 3,
            "recipe_version": 3,
            "comparison_mode": "multiset",
            "multiset_contract": "multiset-v1",
            "canonical_encoding": "typed-length-prefixed-v1",
            "column_order": sorted(columns),
            "nulls_equal": True,
            "scope": recipe["scope"],
            "delimiters": recipe["delimiters"],
            "null_tokens": recipe["null_tokens"],
            "columns": columns,
            "excluded_columns": recipe.get("excluded_columns", {}),
            "output": recipe["output"],
        },
    )
    policy["policy_sha256"] = hashlib.sha256(
        json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return policy


def explain_recipe(path: str | Path) -> dict[str, Any]:
    """Return a fully explicit policy view without reading input data."""
    return _effective_policy(load_recipe(path))


def _checked_policy_sha256(recipe: dict[str, Any], expected: str | None = None) -> str:
    actual = _effective_policy(recipe)["policy_sha256"]
    if expected is not None:
        if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise ParisonError("expected policy SHA-256 must be 64 lowercase hexadecimal characters")
        if expected != actual:
            raise ParisonError(f"effective policy SHA-256 {actual} does not match expected {expected}")
    return actual


def _normalize(value: Any, policy: dict[str, Any]) -> Any:
    if value is None:
        return None
    for rule in policy.get("normalize", []):
        if rule == "trim":
            value = value.strip()
        elif rule == "casefold":
            value = value.casefold()
        elif rule == "unicode_nfc":
            value = unicodedata.normalize("NFC", value)
    return value


def _parse_row(raw: dict[str, Any], recipe: dict[str, Any], side: str, preserve_raw: bool = False) -> dict[Any, Any]:
    row: dict[Any, Any] = {}
    for name, policy in recipe["columns"].items():
        parsed = _parse_input(raw.get(_source_name(recipe, name, side)), policy, name, recipe)
        row[name] = _normalize(parsed, policy)
        if preserve_raw:
            row[(_RAW_VALUE, name)] = parsed
    return row


def _raw_value(row: dict[Any, Any], name: str) -> Any:
    return _json_value(row.get((_RAW_VALUE, name), row[name]))


def _validate_headers(path: Path, headers: list[str], recipe: dict[str, Any], side: str) -> None:
    if len(headers) != len(set(headers)):
        raise ParisonError(f"duplicate column names in {path}")
    details = _schema_details(headers, recipe, side)
    missing, extra = details["missing"], details["unexpected"]
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing=" + ",".join(missing))
        if extra:
            parts.append("unexpected=" + ",".join(extra))
        raise ParisonError(f"schema mismatch in {path}: {'; '.join(parts)}")


def _schema_details(headers: list[str], recipe: dict[str, Any], side: str) -> dict[str, Any]:
    physical = {name: _source_name(recipe, name, side) for name in recipe["columns"]}
    header_names = set(headers)
    expected = set(physical.values())
    excluded = set(recipe.get("excluded_columns", {}))
    return {
        "missing": sorted(expected - header_names),
        "unexpected": sorted(header_names - expected - excluded),
        "mapped": {name: source for name, source in physical.items() if source != name},
        "excluded_present": sorted(header_names & excluded),
    }


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
        paths = tuple(
            sorted((item for item in path.iterdir() if not item.name.startswith(".")), key=lambda item: item.name)
        )
    except OSError as exc:
        raise ParisonError(f"cannot inspect partitioned input {path}: {exc}") from exc
    if not paths:
        raise ParisonError(f"partitioned input has no files: {path}")
    if any(item.is_symlink() or not item.is_file() for item in paths):
        raise ParisonError(f"partitioned input must contain only regular non-symlink files: {path}")
    formats = {_file_format(item) for item in paths}
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


def _decoded_sizes(sources: tuple[str | Path, ...], max_decoded_bytes: int) -> dict[Path, int]:
    if max_decoded_bytes <= 0:
        raise ParisonError("max_decoded_bytes must be positive")
    total = 0
    sizes = {}
    for source in sources:
        for path in _source_paths(source):
            if path.suffix.lower() != ".gz":
                continue
            size = 0
            try:
                with gzip.open(path, "rb") as handle:
                    while chunk := handle.read(min(1024 * 1024, max_decoded_bytes - total + 1)):
                        size += len(chunk)
                        total += len(chunk)
                        if total > max_decoded_bytes:
                            raise ParisonError(f"combined decoded input size exceeds limit {max_decoded_bytes} bytes")
            except ParisonError:
                raise
            except (OSError, EOFError, gzip.BadGzipFile) as exc:
                raise ParisonError(f"cannot decompress {path}: {exc}") from exc
            sizes[path] = size
    return sizes


def _source_metadata(
    source: str | Path,
    digest: str,
    decoded_sizes: dict[Path, int] | None = None,
    delimiter: str = ",",
    null_tokens: list[str] | None = None,
) -> dict[str, Any]:
    path = _source_path(source)
    paths = _source_paths(source)
    format_name = "sqlite" if _sqlite_source(source) else (_file_format(paths[0]) or path.suffix.lower().lstrip("."))
    metadata = {"sha256": digest, "bytes": _source_bytes(source), "format": format_name}
    if format_name in {"csv", "tsv"}:
        metadata["delimiter"] = delimiter
        metadata["null_tokens"] = null_tokens or []
    sqlite_source = _sqlite_source(source)
    if sqlite_source:
        metadata.update(format="sqlite", table=sqlite_source[1])
    elif path.is_dir():
        metadata["partitions"] = len(paths)
    if decoded_sizes and any(item in decoded_sizes for item in paths):
        metadata.update(compression="gzip", decoded_bytes=sum(decoded_sizes.get(item, 0) for item in paths))
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
            yield headers, dict(zip(headers, values, strict=False))
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
            line,
            object_pairs_hook=object_pairs,
            parse_int=str,
            parse_float=str,
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


def _iter_jsonl(path: Path, max_rows: int, decoded_sizes: dict[Path, int]):
    try:
        handle = _open_text(path, decoded_sizes)
    except (OSError, EOFError, gzip.BadGzipFile) as exc:
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


def _read(
    path: str | Path, recipe: dict[str, Any], max_rows: int, side: str, decoded_sizes: dict[Path, int] | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    raw_rows = list(_iter_input_rows(path, recipe, max_rows, side, decoded_sizes or {}))
    rows = [_parse_row(row, recipe, side, recipe.get("output", {}).get("sensitivity") == "raw") for row in raw_rows]
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


def _validate_parquet_projection(schema: Any, recipe: dict[str, Any], side: str) -> None:
    if recipe.get("input_projection") != "semantic-scalar-v1":
        return
    scalar = {
        "Null",
        "String",
        "Boolean",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "Float32",
        "Float64",
        "Decimal",
        "Date",
        "Datetime",
    }
    admitted = {
        "string": {"String"},
        "integer": {"Int8", "Int16", "Int32", "Int64", "UInt8", "UInt16", "UInt32", "UInt64", "String"},
        "decimal": {"Int8", "Int16", "Int32", "Int64", "UInt8", "UInt16", "UInt32", "UInt64", "Decimal", "String"},
        "float": {
            "Int8",
            "Int16",
            "Int32",
            "Int64",
            "UInt8",
            "UInt16",
            "UInt32",
            "UInt64",
            "Float32",
            "Float64",
            "String",
        },
        "boolean": {"Boolean", "String"},
        "date": {"Date", "String"},
        "timestamp": {"Datetime", "String"},
    }
    for dtype in schema.values():
        if str(dtype.base_type()) not in scalar:
            raise ParisonError(f"Parquet input has unsupported semantic-scalar-v1 type {dtype}")
    for name, policy in recipe["columns"].items():
        source = _source_name(recipe, name, side)
        if source not in schema:
            continue
        dtype = schema[source]
        base = str(dtype.base_type())
        if base != "Null" and base not in admitted[policy["type"]]:
            raise ParisonError(f"Parquet column {source} cannot project to {policy['type']} under semantic-scalar-v1")
        if base == "Datetime" and (
            getattr(dtype, "time_unit", None) == "ns" or getattr(dtype, "time_zone", None) is None
        ):
            raise ParisonError(
                f"Parquet column {source} has lossy or timezone-naive timestamp type under semantic-scalar-v1"
            )


def _input_columns(
    path: str | Path,
    decoded_sizes: dict[Path, int] | None = None,
    delimiter: str = ",",
    recipe: dict[str, Any] | None = None,
    side: str | None = None,
) -> list[str]:
    decoded_sizes = decoded_sizes or {}
    source_path = _source_path(path)
    if source_path.is_dir():
        schemas = [
            _input_columns(partition, decoded_sizes, delimiter, recipe, side) for partition in _source_paths(path)
        ]
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
    format_name = _file_format(path)
    if format_name in {"csv", "tsv"}:
        try:
            with _open_text(path, decoded_sizes, newline="") as handle:
                columns = next(csv.reader(handle, delimiter=delimiter, strict=True), [])
        except (OSError, EOFError, gzip.BadGzipFile, csv.Error, UnicodeDecodeError) as exc:
            raise ParisonError(f"cannot read schema from {path}: {exc}") from exc
    elif format_name == "jsonl":
        try:
            with _open_text(path, decoded_sizes) as handle:
                line = next(handle, "")
            columns = list(_jsonl_record(line, path, 1)) if line else []
        except (OSError, EOFError, gzip.BadGzipFile, UnicodeDecodeError) as exc:
            raise ParisonError(f"cannot read schema from {path}: {exc}") from exc
    elif format_name == "parquet":
        try:
            import polars as pl
        except ImportError as exc:
            raise ParisonError("Parquet support requires: pip install 'parison[parquet]'") from exc
        try:
            schema = pl.scan_parquet(path).collect_schema()
            if recipe is not None and side is not None:
                _validate_parquet_projection(schema, recipe, side)
            columns = schema.names()
        except Exception as exc:
            raise ParisonError(f"cannot read schema from {path}: {exc}") from exc
    else:
        raise ParisonError(
            f"unsupported input format for {path}; use .csv, .tsv, .jsonl, .parquet or gzip-compressed text"
        )
    if not columns:
        raise ParisonError(f"input has no schema: {path}")
    if any(not isinstance(name, str) or not name for name in columns) or len(columns) != len(set(columns)):
        raise ParisonError(f"input has empty or duplicate column names: {path}")
    return columns


def _record_diagnostics(
    source: str | Path,
    recipe: dict[str, Any],
    max_rows: int,
    side: str,
    decoded_sizes: dict[Path, int],
) -> dict[str, Any]:
    seen: set[tuple[Any, ...]] = set()
    duplicates: set[tuple[Any, ...]] = set()
    invalid_fields: Counter[str] = Counter()
    invalid_rows = null_key_rows = rows = 0
    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
        rows += 1
        row = {}
        row_is_invalid = False
        for name, policy in recipe["columns"].items():
            try:
                parsed = _parse_input(raw.get(_source_name(recipe, name, side)), policy, name, recipe)
                row[name] = _normalize(parsed, policy)
            except ParisonError:
                invalid_fields[name] += 1
                row_is_invalid = True
        invalid_rows += row_is_invalid
        if not set(recipe["keys"]) <= set(row):
            continue
        key = tuple(row[name] for name in recipe["keys"])
        null_key_rows += any(value is None for value in key)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return {
        "status": "invalid" if invalid_rows or null_key_rows or duplicates else "valid",
        "rows": rows,
        "invalid_rows": invalid_rows,
        "invalid_fields": dict(sorted(invalid_fields.items())),
        "null_key_rows": null_key_rows,
        "duplicate_keys": len(duplicates),
    }


def _aggregate_record_diagnostics(
    source: str | Path,
    recipe: dict[str, Any],
    max_rows: int,
    max_groups: int,
    side: str,
    decoded_sizes: dict[Path, int],
) -> dict[str, Any]:
    groups: set[tuple[Any, ...]] = set()
    invalid_fields: Counter[str] = Counter()
    invalid_rows = null_group_rows = rejected_null_values = rows = 0
    group_limit_exceeded = False
    rejected_columns = {
        policy["column"]
        for policy in recipe["measures"].values()
        if policy["operator"] != "count" and policy["nulls"] == "reject"
    }
    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
        rows += 1
        parsed = {}
        row_is_invalid = False
        for name, policy in recipe["columns"].items():
            try:
                parsed[name] = _normalize(
                    _parse_input(raw.get(_source_name(recipe, name, side)), policy, name, recipe), policy
                )
            except ParisonError:
                invalid_fields[name] += 1
                row_is_invalid = True
        invalid_rows += row_is_invalid
        if set(recipe["group_by"]) <= set(parsed):
            key = tuple(parsed[name] for name in recipe["group_by"])
            if any(value is None for value in key):
                null_group_rows += 1
            elif len(groups) < max_groups or key in groups:
                groups.add(key)
            else:
                group_limit_exceeded = True
        rejected_null_values += sum(parsed.get(name) is None for name in rejected_columns if name in parsed)
    invalid = invalid_rows or null_group_rows or rejected_null_values or group_limit_exceeded
    return {
        "status": "invalid" if invalid else "valid",
        "rows": rows,
        "invalid_rows": invalid_rows,
        "invalid_fields": dict(sorted(invalid_fields.items())),
        "null_group_rows": null_group_rows,
        "rejected_null_measure_values": rejected_null_values,
        "groups": len(groups),
        "group_limit_exceeded": group_limit_exceeded,
    }


def _multiset_record_diagnostics(source, recipe, max_rows, max_distinct_rows, side, decoded_sizes):
    seen: set[tuple[Any, ...]] = set()
    invalid_fields: Counter[str] = Counter()
    invalid_rows = rows = 0
    for raw in _iter_input_rows(source, recipe, max_rows, side, decoded_sizes):
        rows += 1
        parsed = {}
        row_invalid = False
        for name, policy in recipe["columns"].items():
            try:
                parsed[name] = _normalize(
                    _parse_input(raw.get(_source_name(recipe, name, side)), policy, name, recipe), policy
                )
            except ParisonError:
                invalid_fields[name] += 1
                row_invalid = True
        invalid_rows += row_invalid
        if not row_invalid:
            seen.add(tuple(parsed[name] for name in sorted(recipe["columns"])))
    limit_exceeded = len(seen) > max_distinct_rows
    return {
        "status": "invalid" if invalid_rows or limit_exceeded else "valid",
        "rows": rows,
        "invalid_rows": invalid_rows,
        "invalid_fields": dict(sorted(invalid_fields.items())),
        "distinct_rows": len(seen),
        "distinct_row_limit_exceeded": limit_exceeded,
    }


def validate_inputs(
    recipe_path: str | Path,
    baseline: str | Path,
    candidate: str | Path,
    max_input_bytes: int = 1_000_000_000,
    expected_policy_sha256: str | None = None,
    max_decoded_bytes: int = 1_000_000_000,
    validate_records: bool = False,
    max_rows: int = 5_000_000,
    max_groups: int = 100_000,
    max_distinct_rows: int = 100_000,
) -> dict[str, Any]:
    """Validate input schemas against a recipe without comparing records."""
    if max_input_bytes <= 0:
        raise ParisonError("max_input_bytes must be positive")
    if max_rows <= 0:
        raise ParisonError("max_rows must be positive")
    if max_groups <= 0:
        raise ParisonError("max_groups must be positive")
    if max_distinct_rows <= 0:
        raise ParisonError("max_distinct_rows must be positive")
    recipe = load_recipe(recipe_path)
    policy_sha256 = _checked_policy_sha256(recipe, expected_policy_sha256)
    sizes = {side: _source_bytes(source) for side, source in (("baseline", baseline), ("candidate", candidate))}
    if sum(sizes.values()) > max_input_bytes:
        raise ParisonError(f"combined input size {sum(sizes.values())} exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes((baseline, candidate), max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in (baseline, candidate)} if validate_records else {}
    inputs = {}
    status = "valid"
    for side, source in (("baseline", baseline), ("candidate", candidate)):
        delimiter = recipe["delimiters"][side]
        columns = _input_columns(source, decoded_sizes, delimiter, recipe, side)
        schema = _schema_details(columns, recipe, side)
        if schema["missing"] or schema["unexpected"]:
            status = "invalid"
        paths = _source_paths(source)
        sqlite_source = _sqlite_source(source)
        inputs[side] = {
            "format": "sqlite" if sqlite_source else _file_format(paths[0]),
            "bytes": sizes[side],
            "columns": len(columns),
            "partitions": len(paths),
            "schema": schema,
        }
        if sqlite_source:
            inputs[side]["table"] = sqlite_source[1]
        if inputs[side]["format"] in {"csv", "tsv"}:
            inputs[side]["delimiter"] = delimiter
            inputs[side]["null_tokens"] = recipe["null_tokens"][side]
        if any(path in decoded_sizes for path in paths):
            inputs[side].update(compression="gzip", decoded_bytes=sum(decoded_sizes.get(path, 0) for path in paths))
        if validate_records and not schema["missing"] and not schema["unexpected"]:
            inputs[side]["records"] = (
                _aggregate_record_diagnostics(source, recipe, max_rows, max_groups, side, decoded_sizes)
                if recipe["comparison_mode"] == "aggregate"
                else _multiset_record_diagnostics(source, recipe, max_rows, max_distinct_rows, side, decoded_sizes)
                if recipe["comparison_mode"] == "multiset"
                else _record_diagnostics(source, recipe, max_rows, side, decoded_sizes)
            )
            if inputs[side]["records"]["status"] == "invalid":
                status = "invalid"
    if validate_records and any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being validated")
    result = {
        "schema_version": 2
        if recipe["comparison_mode"] == "aggregate"
        else 3
        if recipe["comparison_mode"] == "multiset"
        else 1,
        "status": status,
        "comparison_mode": recipe["comparison_mode"],
        "canonical_columns": len(recipe["columns"]),
        "policy_sha256": policy_sha256,
        "inputs": inputs,
    }
    if recipe["comparison_mode"] == "aggregate":
        result.update(group_by=recipe["group_by"], measures=list(recipe["measures"]), max_groups=max_groups)
    elif recipe["comparison_mode"] == "multiset":
        result["max_distinct_rows"] = max_distinct_rows
    else:
        result["keys"] = recipe["keys"]
    return result


def _suggest_type(values: list[Any]) -> dict[str, Any]:
    present = [str(value) for value in values if value not in (None, "")]
    if not present:
        return {"type": "string", "comparison": "exact"}
    lowered = {value.lower() for value in present}
    if lowered <= {"true", "false"}:
        return {"type": "boolean", "comparison": "exact"}
    if all(
        value.lstrip("-").isdigit() and not (value.lstrip("-").startswith("0") and len(value.lstrip("-")) > 1)
        for value in present
    ):
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

    identifiers = [
        name
        for name in columns
        if any(token in name.lower().replace("_", " ").split() for token in ("id", "key", "code"))
    ]
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


def draft_recipe(
    baseline: str | Path,
    candidate: str | Path,
    max_input_bytes: int = 1_000_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    aggregate: bool = False,
    multiset: bool = False,
) -> dict[str, Any]:
    if aggregate and multiset:
        raise ParisonError("aggregate and multiset drafting are mutually exclusive")
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
    decoded_sizes = _decoded_sizes((baseline, candidate), max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in (baseline, candidate)}
    delimiters = {
        side: "\t" if _file_format(_source_paths(source)[0]) == "tsv" else ","
        for side, source in (("baseline", baseline), ("candidate", candidate))
    }
    baseline_columns = _input_columns(baseline, decoded_sizes, delimiters["baseline"])
    candidate_columns = _input_columns(candidate, decoded_sizes, delimiters["candidate"])
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
        "delimiters": delimiters,
        "null_tokens": {"baseline": [], "candidate": []},
    }
    baseline_rows, _ = _read(baseline, inspection_recipe, 5_000_000, "baseline", decoded_sizes)
    candidate_rows, _ = _read(candidate, inspection_recipe, 5_000_000, "candidate", decoded_sizes)
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while it was being inspected")
    cutoff = (
        datetime.fromtimestamp(
            max(path.stat().st_mtime for source in (baseline, candidate) for path in _source_paths(source)), UTC
        )
        .isoformat()
        .replace("+00:00", "Z")
    )
    columns = {name: _suggest_type([row[name] for row in baseline_rows + candidate_rows]) for name in shared}
    common = {
        "scope": {
            "snapshot": f"{_source_path(baseline).stem} vs {_source_path(candidate).stem}",
            "cutoff": cutoff,
            "filters": [],
            "completeness": "full",
            "expected_empty": not baseline_rows and not candidate_rows,
        },
        "delimiters": delimiters,
        "null_tokens": {"baseline": [], "candidate": []},
        "columns": columns,
        "column_mappings": {},
        "excluded_columns": {
            name: "present only in baseline" if name in baseline_columns else "present only in candidate"
            for name in excluded
        },
        "output": {"sensitivity": "summary"},
    }
    if aggregate:
        rows = baseline_rows + candidate_rows
        group_by = []
        for name in shared:
            values = [row[name] for row in rows]
            if values and all(value not in (None, "") for value in values) and 1 < len(set(values)) < len(values):
                group_by = [name]
                break
        measures = {"rows": {"operator": "count"}}
        for name, policy in columns.items():
            identifier = any(token in name.lower().replace("_", " ").split() for token in ("id", "key", "code"))
            if policy["type"] in {"integer", "decimal"} and name not in group_by and not identifier:
                measures[f"sum_{name}"] = {"operator": "sum", "column": name, "nulls": "reject"}
        return {
            "recipe_version": 2,
            "comparison_mode": "aggregate",
            "group_by": group_by,
            "measures": measures,
            **common,
        }
    if multiset:
        return {"recipe_version": 3, "comparison_mode": "multiset", **common}
    return {
        "recipe_version": 1,
        "comparison_mode": "keyed",
        "keys": _suggest_keys(shared, baseline_rows, candidate_rows),
        "identity": {"null_keys": "reject", "duplicates": "reject"},
        "nulls_equal": True,
        **common,
    }


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


def _iter_input_rows(
    path: str | Path, recipe: dict[str, Any], max_rows: int, side: str, decoded_sizes: dict[Path, int] | None = None
):
    decoded_sizes = decoded_sizes or {}
    source_path = _source_path(path)
    if source_path.is_dir():
        row_count = 0
        for partition in _source_paths(path):
            for row in _iter_input_rows(partition, recipe, max_rows, side, decoded_sizes):
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
    format_name = _file_format(path)
    if format_name in {"csv", "tsv"}:
        try:
            handle = _open_text(path, decoded_sizes, newline="")
        except (OSError, EOFError, gzip.BadGzipFile) as exc:
            raise ParisonError(f"cannot read {path}: {exc}") from exc
        with handle:
            try:
                reader = csv.DictReader(handle, delimiter=recipe.get("delimiters", {}).get(side, ","), strict=True)
                _validate_headers(path, reader.fieldnames or [], recipe, side)
                null_tokens = set(recipe.get("null_tokens", {}).get(side, []))
                for row_count, raw in enumerate(reader):
                    if row_count >= max_rows:
                        raise ParisonError(f"row count in {path} exceeds limit {max_rows}")
                    if None in raw or any(value is None for value in raw.values()):
                        raise ParisonError(f"ragged CSV row {reader.line_num} in {path}")
                    yield {name: None if value in null_tokens else value for name, value in raw.items()}
            except (csv.Error, UnicodeDecodeError) as exc:
                raise ParisonError(f"cannot parse {path}: {exc}") from exc
    elif format_name == "parquet":
        try:
            import polars as pl
        except ImportError as exc:
            raise ParisonError("Parquet support requires: pip install 'parison[parquet]'") from exc
        try:
            scan = pl.scan_parquet(path)
            _validate_parquet_projection(scan.collect_schema(), recipe, side)
            row_count = scan.select(pl.len()).collect().item()
            if row_count > max_rows:
                raise ParisonError(f"row count in {path} exceeds limit {max_rows}")
            frame = pl.read_parquet(path)
        except ParisonError:
            raise
        except Exception as exc:
            raise ParisonError(f"cannot read {path}: {exc}") from exc
        _validate_headers(path, frame.columns, recipe, side)
        yield from frame.iter_rows(named=True)
    elif format_name == "jsonl":
        rows = _iter_jsonl(path, max_rows, decoded_sizes)
        try:
            first = next(rows)
        except StopIteration:
            return
        _validate_headers(path, list(first), recipe, side)
        yield first
        yield from rows
    else:
        raise ParisonError(
            f"unsupported input format for {path}; use .csv, .tsv, .jsonl, .parquet or gzip-compressed text"
        )


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
    if engine == "sqlite" and recipe["comparison_mode"] == "aggregate":
        raise ParisonError("sqlite engine does not support aggregate recipes")
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
            ),
            "candidate": _source_metadata(
                candidate_path,
                before[str(candidate_path)],
                decoded_sizes,
                recipe["delimiters"]["candidate"],
                recipe["null_tokens"]["candidate"],
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
            groups[key] = {
                "rows": 0,
                "measures": {
                    name: {"value": 0 if policy["operator"] == "count" else None, "contributing": 0, "ignored_nulls": 0}
                    for name, policy in recipe["measures"].items()
                },
            }
        group = groups[key]
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
    if not recipe["group_by"] and not groups:
        groups[()] = {
            "rows": 0,
            "measures": {
                name: {"value": 0 if policy["operator"] == "count" else None, "contributing": 0, "ignored_nulls": 0}
                for name, policy in recipe["measures"].items()
            },
        }
    if null_groups:
        problems.append(f"{side} has {null_groups} row(s) with null group components")
    if rejected_nulls:
        problems.append(f"{side} has {rejected_nulls} rejected null measure value(s)")
    return groups, rows, problems


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
) -> dict[str, Any]:
    input_bytes = _source_bytes(baseline_path) + _source_bytes(candidate_path)
    if input_bytes > max_input_bytes:
        raise ParisonError(f"combined input size {input_bytes} exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes((baseline_path, candidate_path), max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in (baseline_path, candidate_path)}
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
    common, baseline_only, candidate_only = set(left) & set(right), set(left) - set(right), set(right) - set(left)
    measure_counts = {name: {"exact": 0, "within_tolerance": 0, "different": 0} for name in recipe["measures"]}
    raw_output = recipe["output"]["sensitivity"] == "raw"
    discrepancies: list[dict[str, Any]] = []
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
    totals = {
        kind: sum(values[kind] for values in measure_counts.values())
        for kind in ("exact", "within_tolerance", "different")
    }
    measure_conservation = {}
    for name in recipe["measures"]:
        measure_conservation[name] = {
            side: {
                "contributing": sum(group["measures"][name]["contributing"] for group in groups.values()),
                "ignored_nulls": sum(group["measures"][name]["ignored_nulls"] for group in groups.values()),
            }
            for side, groups in (("baseline", left), ("candidate", right))
        }
    outcome = (
        "INCONCLUSIVE" if problems else ("FAIL" if baseline_only or candidate_only or totals["different"] else "PASS")
    )
    return {
        "schema_version": 2,
        "outcome": outcome,
        "complete": not problems,
        "sensitivity": recipe["output"]["sensitivity"],
        "runtime": _runtime_info((baseline_path, candidate_path), "aggregate-v1"),
        "resource_limits": {
            "max_input_bytes": max_input_bytes,
            "max_decoded_bytes": max_decoded_bytes,
            "max_rows_per_input": max_rows,
            "max_groups_per_input": max_groups,
        },
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
        ),
        "column_policies": recipe["columns"],
        "column_mappings": recipe.get("column_mappings", {}),
        "problems": problems,
        "counts": {
            "baseline_rows": baseline_rows,
            "candidate_rows": candidate_rows,
            "baseline_groups": len(left),
            "candidate_groups": len(right),
            "common_groups": len(common),
            "baseline_only_groups": len(baseline_only),
            "candidate_only_groups": len(candidate_only),
            "exact_measures": totals["exact"],
            "within_tolerance_measures": totals["within_tolerance"],
            "different_measures": totals["different"],
        },
        "measure_counts": measure_counts,
        "measure_conservation": measure_conservation,
        "discrepancy_count": len(baseline_only) + len(candidate_only) + measure_discrepancies,
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
            ),
            "candidate": _source_metadata(
                candidate_path,
                before[str(candidate_path)],
                decoded_sizes,
                recipe["delimiters"]["candidate"],
                recipe["null_tokens"]["candidate"],
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
            recipe, {"canonical_encoding": "typed-length-prefixed-v1", "column_order": names, "nulls_equal": True}
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
                path, before[str(path)], decoded_sizes, recipe["delimiters"][side], recipe["null_tokens"][side]
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


def terminal_result(
    outcome: str,
    message: str,
    recipe: dict[str, Any] | None = None,
    execution_engine: str | None = None,
    max_temp_bytes: int | None = None,
) -> dict[str, Any]:
    if recipe and recipe.get("comparison_mode") == "multiset":
        runtime = _runtime_info(contract="multiset-v1")
        resource_limits = {}
        if execution_engine is not None:
            runtime["execution_engine"] = execution_engine
        if execution_engine == "sqlite" and max_temp_bytes is not None:
            resource_limits["max_temp_bytes"] = max_temp_bytes
        return {
            "schema_version": 3,
            "outcome": outcome,
            "complete": False,
            "sensitivity": "summary",
            "runtime": runtime,
            "resource_limits": resource_limits,
            "scope": recipe.get("scope"),
            "policy": {},
            "column_policies": recipe.get("columns", {}),
            "column_mappings": recipe.get("column_mappings", {}),
            "problems": [message],
            "counts": {},
            "discrepancy_count": 0,
            "discrepancy_sample": [],
            "discrepancy_sample_limit": 0,
            "excluded_columns": recipe.get("excluded_columns", {}),
            "inputs": {},
            "recipe_sha256": None,
            "policy_sha256": None,
        }
    if recipe and recipe.get("comparison_mode") == "aggregate":
        return {
            "schema_version": 2,
            "outcome": outcome,
            "complete": False,
            "sensitivity": "summary",
            "runtime": _runtime_info(contract="aggregate-v1"),
            "resource_limits": {},
            "scope": recipe.get("scope"),
            "group_by": recipe.get("group_by", []),
            "measures": recipe.get("measures", {}),
            "policy": {},
            "column_policies": recipe.get("columns", {}),
            "column_mappings": recipe.get("column_mappings", {}),
            "problems": [message],
            "counts": {},
            "measure_counts": {},
            "measure_conservation": {},
            "discrepancy_count": 0,
            "discrepancy_sample": [],
            "discrepancy_sample_limit": 0,
            "excluded_columns": recipe.get("excluded_columns", {}),
            "inputs": {},
            "recipe_sha256": None,
            "policy_sha256": None,
        }
    runtime = _runtime_info()
    resource_limits = {}
    if execution_engine == "sqlite":
        runtime["execution_engine"] = execution_engine
    if execution_engine == "sqlite" and max_temp_bytes is not None:
        resource_limits["max_temp_bytes"] = max_temp_bytes
    return {
        "schema_version": 1,
        "outcome": outcome,
        "complete": False,
        "sensitivity": "summary",
        "runtime": runtime,
        "resource_limits": resource_limits,
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
        "policy_sha256": None,
    }


def error_result(
    message: str,
    recipe: dict[str, Any] | None = None,
    execution_engine: str | None = None,
    max_temp_bytes: int | None = None,
) -> dict[str, Any]:
    return terminal_result("ERROR", message, recipe, execution_engine, max_temp_bytes)


def publish(output: str | Path, result: dict[str, Any], recipe: dict[str, Any] | None) -> None:
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot prepare bundle output: {exc}") from exc
    try:
        (stage / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "report.html").write_text(_report(result), encoding="utf-8")
        names = ["result.json", "report.html"]
        if recipe is not None:
            (stage / "effective-recipe.json").write_text(
                json.dumps(recipe, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
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
    except OSError as exc:
        shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot publish bundle: {exc}") from exc
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _read_bundle_result(directory: Path) -> dict[str, Any]:
    try:
        result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read result: {exc}") from exc
    if not isinstance(result, dict) or result.get("schema_version") not in {1, 2, 3}:
        raise ParisonError("result is incomplete or unsupported")
    sample = result.get("discrepancy_sample")
    if not isinstance(sample, list) or not all(isinstance(item, dict) for item in sample):
        raise ParisonError("result has an invalid discrepancy sample")
    if not isinstance(result.get("discrepancy_count"), int) or not isinstance(
        result.get("discrepancy_sample_limit"), int
    ):
        raise ParisonError("result has invalid discrepancy counts")
    return result


def _verify_manifest_files(directory: Path, files: Any, required: set[str]) -> None:
    if not isinstance(files, dict) or not files or not required <= set(files):
        raise ParisonError("manifest does not cover the required bundle files")
    for name, expected in files.items():
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or not isinstance(expected, str)
            or len(expected) != 64
            or any(character not in "0123456789abcdef" for character in expected)
        ):
            raise ParisonError("manifest contains an invalid file entry")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ParisonError(f"bundle file is missing or unsafe: {name}")
        if _digest(path) != expected:
            raise ParisonError(f"bundle file failed integrity check: {name}")


def bundle_integrity_matches(directory: str | Path, expected_manifest_digest: str) -> bool:
    """Check recursively manifest-covered bytes without decoding result evidence."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    try:
        if (
            directory.is_symlink()
            or not directory.is_dir()
            or manifest_path.is_symlink()
            or not manifest_path.is_file()
        ):
            return False
        if _digest(manifest_path) != expected_manifest_digest:
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return False
        _verify_manifest_files(directory, manifest.get("files"), set())
        cases = manifest.get("cases", {})
        if not isinstance(cases, dict):
            return False
        return all(
            isinstance(identifier, str)
            and Path(identifier).name == identifier
            and isinstance(digest, str)
            and bundle_integrity_matches(directory / "cases" / identifier, digest)
            for identifier, digest in cases.items()
        )
    except (OSError, json.JSONDecodeError, ParisonError, TypeError):
        return False


def _verify_suite_bundle(directory: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") == 2:
        return _verify_suite_bundle_v2(directory, manifest)
    if manifest.get("schema_version") != 1 or manifest.get("complete") is not True:
        raise ParisonError("suite manifest is incomplete or unsupported")
    if manifest.get("outcome") not in OUTCOME_CODES or not isinstance(manifest.get("runtime"), dict):
        raise ParisonError("suite manifest has invalid metadata")
    _verify_manifest_files(
        directory, manifest.get("files"), {"suite-result.json", "effective-suite.json", "report.html"}
    )
    try:
        result = json.loads((directory / "suite-result.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read suite result: {exc}") from exc
    if not isinstance(result, dict) or result.get("schema_version") != 1 or result.get("suite_version") != 1:
        raise ParisonError("suite result is incomplete or unsupported")
    for name in ("outcome", "runtime"):
        if result.get(name) != manifest.get(name):
            raise ParisonError(f"suite manifest {name} does not match result")
    cases = result.get("cases")
    case_digests = manifest.get("cases")
    if not isinstance(cases, list) or not isinstance(case_digests, dict):
        raise ParisonError("suite has invalid case metadata")
    if {case.get("id") for case in cases if isinstance(case, dict)} != set(case_digests) or len(cases) != len(
        case_digests
    ):
        raise ParisonError("suite manifest cases do not match result")
    for case in cases:
        expected_fields = {
            "id",
            "outcome",
            "complete",
            "schema_version",
            "contract",
            "policy_sha256",
            "manifest_sha256",
            "bundle",
        }
        if not isinstance(case, dict) or set(case) != expected_fields:
            raise ParisonError("suite result contains invalid case fields")
        identifier = case.get("id")
        if (
            not isinstance(identifier, str)
            or not identifier
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in identifier)
            or identifier.startswith("-")
            or identifier.endswith("-")
            or "--" in identifier
            or case.get("bundle") != f"cases/{identifier}"
        ):
            raise ParisonError("suite result contains an invalid child location")
        child = directory / "cases" / identifier
        child_manifest = verify_bundle(child)
        digest = _digest(child / "manifest.json")
        if digest != case_digests[identifier] or digest != case.get("manifest_sha256"):
            raise ParisonError(f"suite child manifest digest does not match: {identifier}")
        if child_manifest.get("outcome") != case.get("outcome") or child_manifest.get("runtime", {}).get(
            "contract"
        ) != case.get("contract"):
            raise ParisonError(f"suite child metadata does not match: {identifier}")
        child_result = _read_bundle_result(child)
        if (
            child_result.get("schema_version") != case.get("schema_version")
            or child_result.get("policy_sha256") != case.get("policy_sha256")
            or child_result.get("complete") != case.get("complete")
        ):
            raise ParisonError(f"suite child result metadata does not match: {identifier}")
    if (
        result.get("completed_cases") != len(cases)
        or not isinstance(result.get("total_cases"), int)
        or result["total_cases"] < len(cases)
    ):
        raise ParisonError("suite result has invalid case counts")
    expected_counts = {name: sum(case["outcome"] == name for case in cases) for name in OUTCOME_CODES}
    if result.get("outcome_counts") != expected_counts or result.get("suite_sha256") != _digest(
        directory / "effective-suite.json"
    ):
        raise ParisonError("suite result has invalid counts or plan digest")
    try:
        effective = json.loads((directory / "effective-suite.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read effective suite: {exc}") from exc
    planned = effective.get("cases") if isinstance(effective, dict) and effective.get("suite_version") == 1 else None
    if (
        not isinstance(planned, list)
        or result["total_cases"] != len(planned)
        or [case["id"] for case in cases]
        != [case.get("id") for case in planned[: len(cases)] if isinstance(case, dict)]
    ):
        raise ParisonError("suite result does not match effective plan")
    precedence = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3, "INTERRUPTED": 4}
    expected_outcome = max((case["outcome"] for case in cases), key=precedence.get)
    expected_complete = len(cases) == len(planned) and all(case["complete"] for case in cases)
    if result.get("outcome") != expected_outcome or result.get("complete") != expected_complete:
        raise ParisonError("suite result has invalid outcome or completeness")
    return manifest


def _verify_suite_bundle_v2(directory: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("kind") not in {"suite", "suite-shard"} or manifest.get("complete") is not True:
        raise ParisonError("suite v2 manifest is incomplete or unsupported")
    if manifest.get("outcome") not in OUTCOME_CODES or not isinstance(manifest.get("runtime"), dict):
        raise ParisonError("suite v2 manifest has invalid metadata")
    _verify_manifest_files(
        directory, manifest.get("files"), {"suite-result.json", "effective-suite.json", "report.html"}
    )
    try:
        result = json.loads((directory / "suite-result.json").read_text(encoding="utf-8"))
        effective = json.loads((directory / "effective-suite.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read suite v2 metadata: {exc}") from exc
    required = {
        "schema_version",
        "suite_version",
        "kind",
        "outcome",
        "complete",
        "scope_complete",
        "execution_complete",
        "runtime",
        "total_cases",
        "selected_cases",
        "completed_cases",
        "outcome_counts",
        "selection",
        "cases",
        "suite_policy_sha256",
        "effective_suite_sha256",
    }
    if (
        not isinstance(result, dict)
        or set(result) != required
        or result.get("schema_version") != 2
        or result.get("suite_version") != 2
    ):
        raise ParisonError("suite v2 result is incomplete or unsupported")
    for name in ("kind", "outcome", "runtime"):
        if result.get(name) != manifest.get(name):
            raise ParisonError(f"suite manifest {name} does not match result")
    if (
        not isinstance(effective, dict)
        or effective.get("suite_version") != 2
        or set(effective) != {"suite_version", "cases"}
    ):
        raise ParisonError("effective suite v2 is invalid")
    canonical_sha = hashlib.sha256(
        json.dumps(effective, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if result["suite_policy_sha256"] != canonical_sha or result["effective_suite_sha256"] != _digest(
        directory / "effective-suite.json"
    ):
        raise ParisonError("suite v2 result has invalid plan digests")
    selection = result.get("selection")
    if not isinstance(selection, dict) or set(selection) != {"case_ids", "tags", "shard_index", "shard_count"}:
        raise ParisonError("suite v2 result has invalid selection")
    selected = select_suite_cases(
        effective, selection["case_ids"], selection["tags"], selection["shard_index"], selection["shard_count"]
    )
    cases, case_digests = result.get("cases"), manifest.get("cases")
    if not isinstance(cases, list) or not isinstance(case_digests, dict) or len(cases) != len(case_digests):
        raise ParisonError("suite v2 has invalid case metadata")
    if [case.get("id") for case in cases if isinstance(case, dict)] != [case["id"] for case in selected[: len(cases)]]:
        raise ParisonError("suite v2 result does not match selected plan order")
    for case in cases:
        _verify_suite_child(directory, case, case_digests)
    expected_counts = {name: sum(case["outcome"] == name for case in cases) for name in OUTCOME_CODES}
    if result["outcome_counts"] != expected_counts:
        raise ParisonError("suite v2 result has invalid outcome counts")
    precedence = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3, "INTERRUPTED": 4}
    expected_outcome = max((case["outcome"] for case in cases), key=precedence.get)
    execution_complete = len(cases) == len(selected) and all(case["complete"] for case in cases)
    scope_complete = not selection["case_ids"] and not selection["tags"] and selection["shard_count"] is None
    if (
        result["outcome"] != expected_outcome
        or result["completed_cases"] != len(cases)
        or result["selected_cases"] != len(selected)
        or result["total_cases"] != len(effective["cases"])
        or result["execution_complete"] != execution_complete
        or result["scope_complete"] != scope_complete
        or result["complete"] != execution_complete
        or result["kind"] != ("suite-shard" if selection["shard_count"] is not None else "suite")
    ):
        raise ParisonError("suite v2 result has invalid outcome, scope or completeness")
    return manifest


def _verify_suite_child(directory: Path, case: Any, case_digests: dict[str, Any]) -> None:
    expected_fields = {
        "id",
        "outcome",
        "complete",
        "schema_version",
        "contract",
        "policy_sha256",
        "manifest_sha256",
        "bundle",
    }
    if not isinstance(case, dict) or set(case) != expected_fields or not _portable_identifier(case.get("id")):
        raise ParisonError("suite result contains invalid case fields")
    identifier = case["id"]
    if case["bundle"] != f"cases/{identifier}" or set(case_digests) != {
        entry for entry in case_digests if _portable_identifier(entry)
    }:
        raise ParisonError("suite result contains an invalid child location")
    child = directory / "cases" / identifier
    child_manifest = verify_bundle(child)
    digest = _digest(child / "manifest.json")
    if digest != case_digests.get(identifier) or digest != case["manifest_sha256"]:
        raise ParisonError(f"suite child manifest digest does not match: {identifier}")
    child_result = _read_bundle_result(child)
    if (
        child_manifest.get("outcome") != case["outcome"]
        or child_manifest.get("runtime", {}).get("contract") != case["contract"]
        or child_result.get("schema_version") != case["schema_version"]
        or child_result.get("policy_sha256") != case["policy_sha256"]
        or child_result.get("complete") != case["complete"]
    ):
        raise ParisonError(f"suite child metadata does not match: {identifier}")


def _verified_bundle(directory: str | Path) -> tuple[dict[str, Any], bytes]:
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    if directory.is_symlink() or not directory.is_dir():
        raise ParisonError(f"run is not a regular directory: {directory}")
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ParisonError("bundle manifest is missing or unsafe")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read manifest: {exc}") from exc
    if isinstance(manifest, dict) and manifest.get("kind") == "reconciliation":
        from parison.reconciliation import verify_reconciliation_bundle

        manifest = verify_reconciliation_bundle(directory)
    elif isinstance(manifest, dict) and manifest.get("kind") == "dataset-evidence":
        from parison.manifesting import verify_dataset_evidence_bundle

        manifest = verify_dataset_evidence_bundle(directory)
    elif isinstance(manifest, dict) and manifest.get("kind") in {"suite", "suite-shard"}:
        manifest = _verify_suite_bundle(directory, manifest)
    else:
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema_version") != 1
            or manifest.get("complete") is not True
        ):
            raise ParisonError("manifest is incomplete or unsupported")
        if manifest.get("outcome") not in OUTCOME_CODES or manifest.get("sensitivity") not in {"summary", "raw"}:
            raise ParisonError("manifest has invalid outcome or sensitivity metadata")
        if not isinstance(manifest.get("runtime"), dict):
            raise ParisonError("manifest has invalid runtime metadata")
        _verify_manifest_files(directory, manifest.get("files"), {"result.json", "report.html"})
        result = _read_bundle_result(directory)
        for name in ("outcome", "sensitivity", "runtime"):
            if result.get(name) != manifest[name]:
                raise ParisonError(f"manifest {name} does not match result")
    try:
        if manifest_path.read_bytes() != manifest_bytes:
            raise ParisonError("bundle changed during verification")
    except OSError as exc:
        raise ParisonError(f"cannot re-read manifest: {exc}") from exc
    return manifest, manifest_bytes


def verify_bundle(directory: str | Path) -> dict[str, Any]:
    return _verified_bundle(directory)[0]


def inspect_bundle(directory: str | Path) -> dict[str, Any]:
    """Return safe, schema-aware metadata from a verified bundle."""
    manifest = verify_bundle(directory)
    if manifest.get("kind") == "reconciliation":
        from parison.reconciliation import inspect_reconciliation_bundle

        return inspect_reconciliation_bundle(directory)
    if manifest.get("kind") == "dataset-evidence":
        from parison.manifesting import inspect_dataset_evidence_bundle

        return inspect_dataset_evidence_bundle(directory)
    if manifest.get("kind") in {"suite", "suite-shard"}:
        result = json.loads((Path(directory) / "suite-result.json").read_text(encoding="utf-8"))
        return {
            "kind": result.get("kind", "suite"),
            "schema_version": result["schema_version"],
            "suite_version": result["suite_version"],
            "outcome": result["outcome"],
            "complete": result["complete"],
            **(
                {
                    "scope_complete": result["scope_complete"],
                    "execution_complete": result["execution_complete"],
                    "selection": result["selection"],
                }
                if result["schema_version"] == 2
                else {}
            ),
            "runtime": result["runtime"],
            "total_cases": result["total_cases"],
            "completed_cases": result["completed_cases"],
            "outcome_counts": result["outcome_counts"],
            "cases": [
                {
                    name: case[name]
                    for name in (
                        "id",
                        "outcome",
                        "complete",
                        "schema_version",
                        "contract",
                        "policy_sha256",
                        "manifest_sha256",
                        "bundle",
                    )
                }
                for case in result["cases"]
            ],
            "bundle_sha256": _digest(Path(directory) / "manifest.json"),
            "manifest_files": sorted(manifest["files"]),
        }
    result = _read_bundle_result(Path(directory))
    return {
        "schema_version": result.get("schema_version"),
        "outcome": result.get("outcome"),
        "complete": result.get("complete"),
        "sensitivity": result.get("sensitivity"),
        "runtime": result.get("runtime", {}),
        "counts": result.get("counts", {}),
        "discrepancy_count": result.get("discrepancy_count", 0),
        "discrepancy_sample_size": len(result.get("discrepancy_sample", [])),
        "discrepancy_sample_limit": result.get("discrepancy_sample_limit", 0),
        "problems": result.get("problems", []),
        "resource_limits": result.get("resource_limits", {}),
        "input_sha256": {
            side: metadata.get("sha256")
            for side, metadata in result.get("inputs", {}).items()
            if metadata.get("sha256") is not None
        },
        "policy_sha256": result.get("policy_sha256"),
        "bundle_sha256": _digest(Path(directory) / "manifest.json"),
        "manifest_files": sorted(manifest.get("files", {})),
    }


_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
_EVIDENCE_PREDICATE_TYPE = "https://parison.dev/attestations/evidence/v1"


def _evidence_snapshot(directory: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    manifest, manifest_bytes = _verified_bundle(directory)
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    is_suite = manifest.get("kind") in {"suite", "suite-shard"}
    result_name = "suite-result.json" if is_suite else "result.json"
    try:
        result_bytes = (directory / result_name).read_bytes()
        result = json.loads(result_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read Statement source result: {exc}") from exc
    if (
        hashlib.sha256(result_bytes).hexdigest() != manifest["files"].get(result_name)
        or _digest(directory / result_name) != manifest["files"].get(result_name)
        or manifest_path.read_bytes() != manifest_bytes
    ):
        raise ParisonError("bundle changed while preparing Statement")
    kind = manifest.get("kind", "run")
    parison_version = result.get("runtime", {}).get("parison_version")
    if not isinstance(parison_version, str) or not parison_version:
        raise ParisonError("bundle lacks Statement-compatible Parison version provenance")
    predicate = {
        "bundleKind": kind,
        "complete": result["complete"],
        "outcome": result["outcome"],
        "parisonVersion": parison_version,
        "schemaVersion": result["schema_version"],
    }
    if is_suite:
        predicate.update(
            {
                "scopeComplete": result.get("scope_complete", result["complete"]),
                "suitePolicySha256": result.get("suite_policy_sha256"),
                "suiteVersion": result["suite_version"],
            }
        )
    else:
        contract = result["runtime"].get("contract")
        policy_sha256 = result.get("policy_sha256")
        if contract not in {"keyed-v1", "aggregate-v1", "multiset-v1"}:
            raise ParisonError("bundle lacks a Statement-compatible run contract")
        if policy_sha256 is not None and (
            not isinstance(policy_sha256, str)
            or len(policy_sha256) != 64
            or any(character not in "0123456789abcdef" for character in policy_sha256)
        ):
            raise ParisonError("bundle has an invalid effective-policy fingerprint")
        predicate.update(
            {
                "contract": contract,
                "policySha256": policy_sha256,
                "sensitivity": result["sensitivity"],
            }
        )
    statement = {
        "_type": _STATEMENT_TYPE,
        "subject": [{"name": "manifest.json", "digest": {"sha256": manifest_digest}}],
        "predicateType": _EVIDENCE_PREDICATE_TYPE,
        "predicate": predicate,
    }
    return statement, result


def evidence_statement(directory: str | Path) -> dict[str, Any]:
    """Build the deterministic unsigned Statement for a verified bundle."""
    return _evidence_snapshot(directory)[0]


def _check_output_parent(parent: Path) -> None:
    parent = parent.absolute()
    trusted = [
        root.absolute()
        for root in (Path.cwd(), Path(tempfile.gettempdir()))
        if parent == root.absolute() or parent.is_relative_to(root.absolute())
    ]
    boundary = max(trusted, key=lambda root: len(root.parts), default=Path(parent.anchor))
    current = parent
    while current != boundary:
        if current.is_symlink():
            raise ParisonError(f"output parent is unsafe: {current}")
        current = current.parent


def _write_once(target: Path, content: str, error: str) -> None:
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    _check_output_parent(target.parent)
    stage = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _check_output_parent(target.parent)
        descriptor, stage_name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
        stage = Path(stage_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.link(stage, target)
        stage.unlink()
    except ParisonError:
        raise
    except FileExistsError as exc:
        raise ParisonError(f"output already exists: {target}") from exc
    except OSError as exc:
        raise ParisonError(f"{error}: {exc}") from exc
    finally:
        if stage is not None:
            try:
                stage.unlink()
            except OSError:
                pass


def export_statement(directory: str | Path, output: str | Path) -> dict[str, Any]:
    """Atomically export the canonical unsigned Statement for a verified bundle."""
    statement = evidence_statement(directory)
    target = Path(output)
    _write_once(
        target,
        json.dumps(statement, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        "cannot export Statement",
    )
    return {"output": str(target), "bundle_sha256": statement["subject"][0]["digest"]["sha256"]}


def verify_statement(directory: str | Path, statement_path: str | Path) -> dict[str, Any]:
    """Match an already-authenticated Statement to a verified local bundle."""
    path = Path(statement_path)
    if path.is_symlink() or not path.is_file():
        raise ParisonError(f"Statement is not a regular file: {path}")

    def object_pairs(pairs):
        value = {}
        for name, item in pairs:
            if name in value:
                raise ParisonError(f"Statement contains duplicate JSON field: {name}")
            value[name] = item
        return value

    try:
        actual = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except ParisonError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read Statement: {exc}") from exc
    expected = evidence_statement(directory)

    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    if canonical(actual) != canonical(expected):
        raise ParisonError("authenticated Statement does not match verified bundle")
    return {"status": "valid", "bundle_sha256": expected["subject"][0]["digest"]["sha256"]}


def report_cutover(directory: str | Path, output: str | Path) -> dict[str, Any]:
    """Write a deterministic safe Markdown cover sheet for verified evidence."""
    statement, result = _evidence_snapshot(directory)
    predicate = statement["predicate"]
    rows = [
        ("Bundle kind", predicate["bundleKind"]),
        ("Manifest SHA-256", statement["subject"][0]["digest"]["sha256"]),
        ("Outcome", predicate["outcome"]),
        ("Complete", str(predicate["complete"]).lower()),
        ("Result schema", predicate["schemaVersion"]),
        ("Produced by Parison", predicate["parisonVersion"]),
    ]
    if predicate["bundleKind"] == "run":
        rows.extend(
            [
                ("Comparison contract", predicate["contract"]),
                ("Policy SHA-256", predicate["policySha256"] or "unavailable"),
                ("Sensitivity", predicate["sensitivity"]),
            ]
        )
        summary = [(name.replace("_", " "), value) for name, value in sorted(result["counts"].items())]
        summary.append(("discrepancy count", result["discrepancy_count"]))
    else:
        rows.extend(
            [
                ("Suite version", predicate["suiteVersion"]),
                ("Suite policy SHA-256", predicate["suitePolicySha256"] or "unavailable"),
                ("Scope complete", str(predicate["scopeComplete"]).lower()),
            ]
        )
        summary = [
            ("completed cases", result["completed_cases"]),
            ("total cases", result["total_cases"]),
            *[(f"{name} cases", value) for name, value in result["outcome_counts"].items()],
        ]
    lines = [
        "# Parison cutover evidence",
        "",
        "> Verified metadata cover sheet. This report is evidence, not cutover approval.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        *[f"| {name} | {value} |" for name, value in rows],
        "",
        "## Result summary",
        "",
        "| Measure | Value |",
        "| --- | ---: |",
        *[f"| {name} | {value} |" for name, value in summary],
    ]
    if predicate["bundleKind"] != "run":
        lines.extend(["", "## Cases", "", "| Case | Outcome | Complete |", "| --- | --- | --- |"])
        lines.extend(
            f"| {case['id']} | {case['outcome']} | {str(case['complete']).lower()} |" for case in result["cases"]
        )
    lines.extend(
        [
            "",
            "## Independent checks still required",
            "",
            "- Authenticate the canonical Statement and authorize its signer identity and issuer.",
            "- Require the reviewed policy fingerprint, outcome, completeness and suite scope.",
            "- Validate source-owned extraction snapshot, watermark and completeness guarantees.",
            "",
        ]
    )
    target = Path(output)
    _write_once(target, "\n".join(lines), "cannot write cutover report")
    return {"output": str(target), "bundle_sha256": statement["subject"][0]["digest"]["sha256"]}


def export_evidence(
    directory: str | Path,
    output: str | Path,
    classification: str | None = None,
    limit: int = 100,
    *,
    kind: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Export a bounded projection of raw discrepancy evidence from a verified bundle."""
    if limit <= 0:
        raise ParisonError("evidence export limit must be positive")
    manifest = verify_bundle(directory)
    if manifest.get("kind") == "suite":
        raise ParisonError("evidence export requires a child run bundle")
    manifest_path = Path(directory) / "manifest.json"
    result = _read_bundle_result(Path(directory))
    if result.get("sensitivity") != "raw":
        raise ParisonError("evidence export requires a raw-sensitivity bundle")
    allowed = {
        "baseline_only",
        "candidate_only",
        "within_tolerance",
        "different",
        "baseline_surplus",
        "candidate_surplus",
    }
    if classification is not None and classification not in allowed:
        raise ParisonError(f"unsupported evidence classification: {classification}")
    if kind is not None and kind not in {"record", "field", "group", "measure", "row"}:
        raise ParisonError(f"unsupported evidence kind: {kind}")
    if name is not None and not name:
        raise ParisonError("evidence name filter must be nonempty")

    def matches(item: dict[str, Any]) -> bool:
        item_kind = item.get("kind", "row" if result.get("schema_version") == 3 else None)
        item_name = item.get("field", item.get("measure"))
        return (
            (classification is None or item.get("classification") == classification)
            and (kind is None or item_kind == kind)
            and (name is None or item_name == name)
        )

    items = [item for item in result.get("discrepancy_sample", []) if matches(item)][:limit]
    target = Path(output)
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    stage = None
    try:
        descriptor, stage_name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent, text=True)
        stage = Path(stage_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "_parison_export": {
                            "bundle_sha256": _digest(manifest_path),
                            "schema_version": result.get("schema_version"),
                            "policy_sha256": result.get("policy_sha256"),
                            "classification": classification,
                            "kind": kind,
                            "name": name,
                            "limit": limit,
                        }
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            for item in items:
                handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
        os.link(stage, target)
        stage.unlink()
    except FileExistsError as exc:
        raise ParisonError(f"output already exists: {target}") from exc
    except OSError as exc:
        raise ParisonError(f"cannot export evidence: {exc}") from exc
    finally:
        if stage is not None:
            try:
                stage.unlink()
            except OSError:
                pass
    return {
        "output": str(target),
        "items": len(items),
        "limit": limit,
        "classification": classification,
        "kind": kind,
        "name": name,
        "bundle_files": sorted(manifest.get("files", {})),
    }


def report_ci(directory: str | Path, output: str | Path, format_name: str) -> dict[str, Any]:
    """Write a bounded summary-only CI projection from a verified suite bundle."""
    manifest = verify_bundle(directory)
    if manifest.get("kind") not in {"suite", "suite-shard"}:
        raise ParisonError("CI reports require a suite or suite-shard bundle")
    result = json.loads((Path(directory) / "suite-result.json").read_text(encoding="utf-8"))
    if format_name == "markdown":
        scope = _suite_scope_label(result)
        lines = [
            f"# Parison {scope}",
            "",
            f"**{result['outcome']}** — {result['completed_cases']} of {result.get('selected_cases', result['total_cases'])} selected cases completed.",
            "",
            "| Case | Outcome | Complete |",
            "|---|---:|:---:|",
        ]
        lines.extend(
            f"| `{case['id']}` | {case['outcome']} | {'yes' if case['complete'] else 'no'} |"
            for case in result["cases"]
        )
        content = "\n".join(lines) + "\n"
    elif format_name == "junit":
        cases = result["cases"]
        root = ET.Element(
            "testsuite",
            {
                "name": f"parison-{result['kind']}",
                "tests": str(len(cases)),
                "failures": str(sum(case["outcome"] == "FAIL" for case in cases)),
                "errors": str(sum(case["outcome"] in {"ERROR", "INTERRUPTED"} for case in cases)),
                "skipped": str(sum(case["outcome"] == "INCONCLUSIVE" for case in cases)),
            },
        )
        properties = ET.SubElement(root, "properties")
        ET.SubElement(properties, "property", {"name": "parison.outcome", "value": result["outcome"]})
        ET.SubElement(properties, "property", {"name": "parison.scope", "value": _suite_scope_label(result)})
        for case in cases:
            node = ET.SubElement(root, "testcase", {"classname": "parison", "name": case["id"]})
            case_properties = ET.SubElement(node, "properties")
            ET.SubElement(case_properties, "property", {"name": "parison.outcome", "value": case["outcome"]})
            if case["outcome"] == "FAIL":
                ET.SubElement(node, "failure", {"message": "Parison comparison found required differences"})
            elif case["outcome"] in {"ERROR", "INTERRUPTED"}:
                ET.SubElement(node, "error", {"message": f"Parison {case['outcome'].lower()}"})
            elif case["outcome"] == "INCONCLUSIVE":
                ET.SubElement(node, "skipped", {"message": "Parison comparison was inconclusive"})
        ET.indent(root)
        content = ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"
    else:
        raise ParisonError("CI report format must be markdown or junit")
    encoded = content.encode("utf-8")
    if len(encoded) > 1_000_000:
        raise ParisonError("CI report exceeds the 1,000,000-byte limit")
    target = Path(output)
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    stage = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, stage_name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
        stage = Path(stage_name)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
        os.link(stage, target)
    except FileExistsError as exc:
        raise ParisonError(f"output already exists: {target}") from exc
    except OSError as exc:
        raise ParisonError(f"cannot write CI report: {exc}") from exc
    finally:
        if stage is not None:
            try:
                stage.unlink()
            except OSError:
                pass
    return {
        "output": str(target),
        "format": format_name,
        "bytes": len(encoded),
        "cases": len(result["cases"]),
        "outcome": result["outcome"],
    }


def _suite_scope_label(result: dict[str, Any]) -> str:
    selection = result.get("selection", {})
    if result.get("kind") == "suite-shard":
        return f"shard {selection['shard_index'] + 1}/{selection['shard_count']}"
    if result.get("schema_version") == 2 and not result.get("scope_complete"):
        return "selected suite"
    return "suite"


def _suite_report(result: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(case[field]))}</td>" for field in ("id", "outcome", "complete", "contract", "bundle")
        )
        + "</tr>"
        for case in result["cases"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Parison suite report</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:.5rem;text-align:left}}</style></head>
<body><h1>Parison suite report</h1><p><strong>{html.escape(result["outcome"])}</strong> — {result["completed_cases"]} of {result["total_cases"]} cases published.</p>
<table><thead><tr><th>Case</th><th>Outcome</th><th>Complete</th><th>Contract</th><th>Bundle</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""


def assemble_suite(plan: str | Path, inputs: list[str | Path], output: str | Path) -> dict[str, Any]:
    """Assemble a complete suite from an exact set of verified v2 shards."""
    suite = load_suite(plan)
    if suite["suite_version"] != 2:
        raise ParisonError("suite assembly requires suite_version 2")
    if not inputs or len(inputs) > 100:
        raise ParisonError("suite assembly requires 1..100 shard inputs")
    shard_results, indexes, common = [], set(), None
    for source in map(Path, inputs):
        manifest = verify_bundle(source)
        if manifest.get("kind") != "suite-shard":
            raise ParisonError(f"assembly input is not a suite shard: {source}")
        result = json.loads((source / "suite-result.json").read_text(encoding="utf-8"))
        selection = result["selection"]
        identity = {
            "case_ids": selection["case_ids"],
            "tags": selection["tags"],
            "shard_count": selection["shard_count"],
        }
        if common is None:
            common = identity
        elif identity != common:
            raise ParisonError("suite shards use different selections or shard counts")
        index = selection["shard_index"]
        if index in indexes:
            raise ParisonError(f"duplicate suite shard index: {index}")
        indexes.add(index)
        if result["suite_policy_sha256"] != suite["suite_policy_sha256"]:
            raise ParisonError("suite shard plan fingerprint does not match current plan")
        if not result["execution_complete"]:
            raise ParisonError(f"suite shard is not execution-complete: {source}")
        shard_results.append((source, result))
    assert common is not None
    if indexes != set(range(common["shard_count"])):
        raise ParisonError("suite shard indexes do not provide exact coverage")
    selected = select_suite_cases(suite, common["case_ids"], common["tags"])
    by_id: dict[str, tuple[Path, dict[str, Any]]] = {}
    for source, result in shard_results:
        for case in result["cases"]:
            if case["id"] in by_id:
                raise ParisonError(f"duplicate assembled suite case: {case['id']}")
            by_id[case["id"]] = (source, case)
    expected_ids = [case["id"] for case in selected]
    if set(by_id) != set(expected_ids):
        raise ParisonError("suite shards do not provide exact selected-case coverage")
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
        (stage / "cases").mkdir()
        cases = []
        for identifier in expected_ids:
            source, case = by_id[identifier]
            child_source = source / case["bundle"]
            child_target = stage / "cases" / identifier
            _copy_verified_child(child_source, child_target)
            copied = dict(case)
            copied["manifest_sha256"] = _digest(child_target / "manifest.json")
            cases.append(copied)
        effective = {"suite_version": 2, "cases": [case["portable"] for case in suite["cases"]]}
        (stage / "effective-suite.json").write_text(
            json.dumps(effective, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        precedence = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3, "INTERRUPTED": 4}
        outcome = max((case["outcome"] for case in cases), key=precedence.get)
        selection = {"case_ids": common["case_ids"], "tags": common["tags"], "shard_index": None, "shard_count": None}
        result = {
            "schema_version": 2,
            "suite_version": 2,
            "kind": "suite",
            "outcome": outcome,
            "complete": all(case["complete"] for case in cases),
            "scope_complete": not common["case_ids"] and not common["tags"],
            "execution_complete": True,
            "runtime": _runtime_info(contract="suite-v2"),
            "total_cases": len(suite["cases"]),
            "selected_cases": len(cases),
            "completed_cases": len(cases),
            "outcome_counts": {name: sum(case["outcome"] == name for case in cases) for name in precedence},
            "selection": selection,
            "cases": cases,
            "suite_policy_sha256": suite["suite_policy_sha256"],
            "effective_suite_sha256": _digest(stage / "effective-suite.json"),
        }
        (stage / "suite-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "report.html").write_text(_suite_report(result), encoding="utf-8")
        manifest = {
            "schema_version": 2,
            "kind": "suite",
            "complete": True,
            "outcome": outcome,
            "runtime": result["runtime"],
            "files": {
                name: _digest(stage / name) for name in ("suite-result.json", "effective-suite.json", "report.html")
            },
            "cases": {case["id"]: case["manifest_sha256"] for case in cases},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(stage, output)
        return result
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot assemble suite: {exc}") from exc
    except Exception:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise


def _copy_verified_child(source: Path, target: Path) -> None:
    manifest = verify_bundle(source)
    target.mkdir()
    shutil.copy2(source / "manifest.json", target / "manifest.json")
    for name in manifest["files"]:
        shutil.copy2(source / name, target / name)
    verify_bundle(target)


def _checkpoint_data(
    case: dict[str, Any], child: Path, suite_sha256: str, limits: dict[str, int], sample_limit: int
) -> dict[str, Any]:
    result = _read_bundle_result(child)
    return {
        "case_id": case["id"],
        "suite_policy_sha256": suite_sha256,
        "policy_sha256": case["policy_sha256"],
        "limits": limits,
        "sample_limit": sample_limit,
        "parison_version": _runtime_info()["parison_version"],
        "inputs": {side: result.get("inputs", {}).get(side, {}).get("sha256") for side in ("baseline", "candidate")},
        "manifest_sha256": _digest(child / "manifest.json"),
    }


def _write_checkpoint(path: Path, data: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent, text=True)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        os.replace(temporary_path, path)
    finally:
        try:
            temporary_path.unlink()
        except OSError:
            pass


def _reusable_workspace_child(
    case: dict[str, Any],
    child: Path,
    checkpoint_path: Path,
    suite_sha256: str,
    limits: dict[str, int],
    sample_limit: int,
) -> bool:
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        expected = _checkpoint_data(case, child, suite_sha256, limits, sample_limit)
        verify_bundle(child)
        child_result = _read_bundle_result(child)
    except (OSError, json.JSONDecodeError, ParisonError):
        return False
    if checkpoint != expected:
        return False
    try:
        current_inputs = {"baseline": _source_digest(case["baseline"]), "candidate": _source_digest(case["candidate"])}
    except ParisonError:
        return False
    if checkpoint["inputs"] != current_inputs:
        return False
    resource_limits = child_result.get("resource_limits", {})
    expected_resources = {
        "max_input_bytes": limits["max_input_bytes"],
        "max_decoded_bytes": limits["max_decoded_bytes"],
        "max_rows_per_input": limits["max_rows"],
    }
    mode = load_recipe(case["recipe"])["comparison_mode"]
    if mode == "aggregate":
        expected_resources["max_groups_per_input"] = limits["max_groups"]
    elif mode == "multiset":
        expected_resources["max_distinct_rows_per_input"] = limits["max_distinct_rows"]
    if case.get("execution"):
        expected_resources["max_temp_bytes"] = case["execution"].get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES)
    return resource_limits == expected_resources


def _execute_suite_case(
    case: dict[str, Any], destination: Path, sample_limit: int, limits: dict[str, int]
) -> dict[str, Any]:
    """Execute and publish one isolated suite case."""
    recipe = load_recipe(case["recipe"])
    try:
        result = compare(
            case["recipe"],
            case["baseline"],
            case["candidate"],
            sample_limit,
            limits["max_input_bytes"],
            limits["max_rows"],
            case.get("expected_policy_sha256"),
            limits["max_decoded_bytes"],
            limits["max_groups"],
            limits["max_distinct_rows"],
            case.get("execution", {}).get("engine", "memory"),
            case.get("execution", {}).get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
            destination.parent if case.get("execution") else None,
        )
    except ParisonError as exc:
        execution = case.get("execution", {})
        result = error_result(
            str(exc),
            recipe,
            execution.get("engine", "memory"),
            execution.get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
        )
    publish(destination, result, recipe)
    return result


def _suite_worker(worker, sender, case, destination, sample_limit, limits) -> None:
    """Run one case without exposing worker failures or values to the parent."""
    try:
        sender.send(("ok", worker(case, destination, sample_limit, limits)))
    except Exception:
        sender.send(("error", None))
    finally:
        sender.close()


def _stop_suite_workers(active: dict, timeout: float = 2.0) -> None:
    """Bound shutdown of the small private process pool."""
    processes = [record[0] for record in active.values()]
    for process in processes:
        if process.is_alive():
            process.terminate()
    deadline = time.monotonic() + timeout
    for process in processes:
        process.join(max(0.0, deadline - time.monotonic()))
    survivors = [process for process in processes if process.is_alive()]
    for process in survivors:
        process.kill()
    deadline = time.monotonic() + timeout
    for process in survivors:
        process.join(max(0.0, deadline - time.monotonic()))
    if any(process.is_alive() for process in survivors):
        raise ParisonError("suite workers could not be stopped safely")


def _clean_interrupted_workspace_case(case: dict[str, Any], destination: Path) -> None:
    """Remove incomplete output and atomic-publish scratch left by termination."""
    try:
        verify_bundle(destination)
    except ParisonError:
        shutil.rmtree(destination, ignore_errors=True)
    for scratch in destination.parent.glob(f".{case['id']}-*"):
        if scratch.is_dir() and not scratch.is_symlink():
            shutil.rmtree(scratch, ignore_errors=True)
        else:
            try:
                scratch.unlink()
            except OSError:
                pass
    for spill in destination.parent.glob("parison-spill-*"):
        if spill.is_dir() and not spill.is_symlink():
            shutil.rmtree(spill, ignore_errors=True)


def run_suite(
    plan: str | Path,
    output: str | Path,
    sample_limit: int = 100,
    max_input_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    max_groups: int = 100_000,
    max_distinct_rows: int = 100_000,
    case_ids: list[str] | None = None,
    tags: list[str] | None = None,
    shard_index: int | None = None,
    shard_count: int | None = None,
    workspace: str | Path | None = None,
    resume: bool = False,
    jobs: int = 1,
) -> dict[str, Any]:
    """Run a validated ordered suite and atomically publish its child bundles."""
    suite = load_suite(plan)
    selected = select_suite_cases(suite, case_ids, tags, shard_index, shard_count)
    if not 1 <= jobs <= _MAX_SUITE_JOBS:
        raise ParisonError(f"jobs must be between 1 and {_MAX_SUITE_JOBS}")
    if (workspace is not None or resume) and suite["suite_version"] != 2:
        raise ParisonError("suite workspaces require suite_version 2")
    if resume and workspace is None:
        raise ParisonError("--resume requires --workspace")
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    workspace_path = Path(workspace) if workspace is not None else None
    if workspace_path is not None:
        if workspace_path.absolute() == output.absolute():
            raise ParisonError("workspace and output must be different directories")
        if resume:
            if workspace_path.is_symlink() or not workspace_path.is_dir():
                raise ParisonError("resume workspace is not a regular directory")
            if any(
                path.is_symlink() or not path.is_dir()
                for path in (workspace_path / "cases", workspace_path / "checkpoints")
            ):
                raise ParisonError("resume workspace is incomplete or unsafe")
        elif workspace_path.exists():
            raise ParisonError(f"workspace already exists: {workspace_path}")
        else:
            try:
                (workspace_path / "cases").mkdir(parents=True)
                (workspace_path / "checkpoints").mkdir()
                os.chmod(workspace_path, 0o700)
            except OSError as exc:
                raise ParisonError(f"cannot prepare suite workspace: {exc}") from exc
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
        (stage / "cases").mkdir()
        cases_by_id: dict[str, dict[str, Any]] = {}
        pending = []
        for case in selected:
            limits = case.get(
                "limits",
                {
                    "max_input_bytes": max_input_bytes,
                    "max_decoded_bytes": max_decoded_bytes,
                    "max_rows": max_rows,
                    "max_groups": max_groups,
                    "max_distinct_rows": max_distinct_rows,
                },
            )
            child = stage / "cases" / case["id"]
            workspace_child = workspace_path / "cases" / case["id"] if workspace_path is not None else None
            checkpoint = workspace_path / "checkpoints" / f"{case['id']}.json" if workspace_path is not None else None
            reused = bool(
                resume
                and workspace_child is not None
                and checkpoint is not None
                and _reusable_workspace_child(
                    case, workspace_child, checkpoint, suite["suite_policy_sha256"], limits, sample_limit
                )
            )
            if reused:
                _copy_verified_child(workspace_child, child)
                result = _read_bundle_result(child)
            else:
                if workspace_child is not None:
                    shutil.rmtree(workspace_child, ignore_errors=True)
                pending.append((case, child, workspace_child, checkpoint, limits))
                continue
            cases_by_id[case["id"]] = {
                "id": case["id"],
                "outcome": result["outcome"],
                "complete": result["complete"],
                "schema_version": result["schema_version"],
                "contract": result["runtime"]["contract"],
                "policy_sha256": result.get("policy_sha256"),
                "manifest_sha256": _digest(child / "manifest.json"),
                "bundle": f"cases/{case['id']}",
            }

        def finish(case, child, workspace_child, checkpoint, limits, result):
            if workspace_child is not None and checkpoint is not None:
                _write_checkpoint(
                    checkpoint,
                    _checkpoint_data(case, workspace_child, suite["suite_policy_sha256"], limits, sample_limit),
                )
                _copy_verified_child(workspace_child, child)
            cases_by_id[case["id"]] = {
                "id": case["id"],
                "outcome": result["outcome"],
                "complete": result["complete"],
                "schema_version": result["schema_version"],
                "contract": result["runtime"]["contract"],
                "policy_sha256": result.get("policy_sha256"),
                "manifest_sha256": _digest(child / "manifest.json"),
                "bundle": f"cases/{case['id']}",
            }

        interrupted = False
        if jobs == 1:
            for case, child, workspace_child, checkpoint, limits in pending:
                try:
                    result = _execute_suite_case(case, workspace_child or child, sample_limit, limits)
                except KeyboardInterrupt:
                    recipe = load_recipe(case["recipe"])
                    execution = case.get("execution", {})
                    result = terminal_result(
                        "INTERRUPTED",
                        "comparison interrupted by user",
                        recipe,
                        execution.get("engine", "memory"),
                        execution.get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
                    )
                    publish(workspace_child or child, result, recipe)
                    interrupted = True
                finish(case, child, workspace_child, checkpoint, limits, result)
                if interrupted:
                    break
        else:
            context = multiprocessing.get_context("spawn")
            waiting = iter(pending)
            active = {}

            def launch() -> bool:
                try:
                    item = next(waiting)
                except StopIteration:
                    return False
                case, child, workspace_child, _checkpoint, limits = item
                receiver, sender = context.Pipe(duplex=False)
                process = context.Process(
                    target=_suite_worker,
                    args=(_execute_suite_case, sender, case, workspace_child or child, sample_limit, limits),
                )
                process.start()
                sender.close()
                active[receiver] = (process, item)
                return True

            def recover(item, message):
                case, child, workspace_child, checkpoint, limits = item
                destination = workspace_child or child
                result = message[1] if message and message[0] == "ok" else None
                if result is None:
                    try:
                        verify_bundle(destination)
                        result = _read_bundle_result(destination)
                    except ParisonError:
                        shutil.rmtree(destination, ignore_errors=True)
                        recipe = load_recipe(case["recipe"])
                        execution = case.get("execution", {})
                        result = error_result(
                            "suite worker failed unexpectedly",
                            recipe,
                            execution.get("engine", "memory"),
                            execution.get("max_temp_bytes", DEFAULT_MAX_TEMP_BYTES),
                        )
                        publish(destination, result, recipe)
                finish(case, child, workspace_child, checkpoint, limits, result)

            try:
                for _ in range(min(jobs, len(pending))):
                    launch()
                while active:
                    ready = set(wait(active, timeout=0.05))
                    ready.update(receiver for receiver, (process, _item) in active.items() if not process.is_alive())
                    for receiver in ready:
                        process, item = active.pop(receiver)
                        try:
                            message = receiver.recv() if receiver.poll() else None
                        except (EOFError, OSError):
                            message = None
                        receiver.close()
                        process.join()
                        recover(item, message)
                        launch()
            except KeyboardInterrupt:
                _stop_suite_workers(active)
                for receiver in active:
                    receiver.close()
                for case, _child, workspace_child, checkpoint, limits in pending:
                    if workspace_child is None or checkpoint is None:
                        continue
                    _clean_interrupted_workspace_case(case, workspace_child)
                    try:
                        verify_bundle(workspace_child)
                    except ParisonError:
                        continue
                    _write_checkpoint(
                        checkpoint,
                        _checkpoint_data(case, workspace_child, suite["suite_policy_sha256"], limits, sample_limit),
                    )
                raise
            except BaseException:
                _stop_suite_workers(active)
                for receiver in active:
                    receiver.close()
                raise

        cases = [cases_by_id[case["id"]] for case in selected if case["id"] in cases_by_id]
        precedence = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3, "INTERRUPTED": 4}
        outcome = max((case["outcome"] for case in cases), key=precedence.get)
        outcome_counts = {name: sum(case["outcome"] == name for case in cases) for name in precedence}
        effective = (
            {"suite_version": 2, "cases": [case["portable"] for case in suite["cases"]]}
            if suite["suite_version"] == 2
            else json.loads(Path(plan).read_text(encoding="utf-8"))
        )
        (stage / "effective-suite.json").write_text(
            json.dumps(effective, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        result = {
            "schema_version": 1,
            "suite_version": 1,
            "outcome": outcome,
            "complete": len(cases) == len(suite["cases"]) and all(case["complete"] for case in cases),
            "runtime": _runtime_info(contract="suite-v1"),
            "total_cases": len(suite["cases"]),
            "completed_cases": len(cases),
            "outcome_counts": outcome_counts,
            "cases": cases,
            "suite_sha256": _digest(stage / "effective-suite.json"),
        }
        kind = "suite"
        if suite["suite_version"] == 2:
            selection = {
                "case_ids": case_ids or [],
                "tags": tags or [],
                "shard_index": shard_index,
                "shard_count": shard_count,
            }
            scope_complete = not selection["case_ids"] and not selection["tags"] and shard_count is None
            execution_complete = len(cases) == len(selected) and all(case["complete"] for case in cases)
            kind = "suite-shard" if shard_count is not None else "suite"
            result = {
                "schema_version": 2,
                "suite_version": 2,
                "kind": kind,
                "outcome": outcome,
                "complete": execution_complete,
                "scope_complete": scope_complete,
                "execution_complete": execution_complete,
                "runtime": _runtime_info(contract="suite-v2"),
                "total_cases": len(suite["cases"]),
                "selected_cases": len(selected),
                "completed_cases": len(cases),
                "outcome_counts": outcome_counts,
                "selection": selection,
                "cases": cases,
                "suite_policy_sha256": suite["suite_policy_sha256"],
                "effective_suite_sha256": _digest(stage / "effective-suite.json"),
            }
        (stage / "suite-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / "report.html").write_text(_suite_report(result), encoding="utf-8")
        files = {name: _digest(stage / name) for name in ("suite-result.json", "effective-suite.json", "report.html")}
        manifest = {
            "schema_version": result["schema_version"],
            "kind": kind,
            "complete": True,
            "outcome": outcome,
            "runtime": result["runtime"],
            "files": files,
            "cases": {case["id"]: case["manifest_sha256"] for case in cases},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(stage, output)
        return result
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot publish suite: {exc}") from exc
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise
