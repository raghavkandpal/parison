from __future__ import annotations

import hashlib
import html
import json
import math
import os
import platform
import re
import shutil
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from importlib import metadata, resources
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


# Compatibility re-exports; implementation lives in parison.inputs.
from .inputs import (  # noqa: E402, I001
    _LimitedText as _LimitedText,
    _aggregate_record_diagnostics as _aggregate_record_diagnostics,
    _decoded_sizes as _decoded_sizes,
    _digest as _digest,
    _file_format as _file_format,
    _input_columns as _input_columns,
    _iter_input_rows as _iter_input_rows,
    _iter_jsonl as _iter_jsonl,
    _jsonl_record as _jsonl_record,
    _multiset_record_diagnostics as _multiset_record_diagnostics,
    _open_text as _open_text,
    _read as _read,
    _record_diagnostics as _record_diagnostics,
    _schema_details as _schema_details,
    _source_bytes as _source_bytes,
    _source_digest as _source_digest,
    _source_metadata as _source_metadata,
    _source_path as _source_path,
    _source_paths as _source_paths,
    _sqlite_rows as _sqlite_rows,
    _sqlite_source as _sqlite_source,
    _suggest_keys as _suggest_keys,
    _suggest_type as _suggest_type,
    _validate_headers as _validate_headers,
    _validate_parquet_projection as _validate_parquet_projection,
    draft_recipe as draft_recipe,
    validate_inputs as validate_inputs,
)


# Compatibility re-exports; implementation lives in parison.evidence.
from .evidence import (  # noqa: E402
    _check_output_parent as _check_output_parent,
    _verify_manifest_files as _verify_manifest_files,
    _write_once as _write_once,
    bundle_integrity_matches as bundle_integrity_matches,
    error_result as error_result,
    evidence_statement as evidence_statement,
    export_evidence as export_evidence,
    export_statement as export_statement,
    inspect_bundle as inspect_bundle,
    publish as publish,
    report_ci as report_ci,
    report_cutover as report_cutover,
    terminal_result as terminal_result,
    verify_bundle as verify_bundle,
    verify_statement as verify_statement,
)


# Compatibility re-exports; implementation lives in parison.suites.
from .suites import (  # noqa: E402
    _execute_suite_case as _execute_suite_case,
    assemble_suite as assemble_suite,
    run_suite as run_suite,
)
