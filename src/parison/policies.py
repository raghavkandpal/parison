"""Recipe and suite loading, policy normalization, and fingerprints."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from importlib import resources
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent as _check_output_parent
from ._safe_fs import rename_no_replace as _rename_no_replace
from .core import (
    _AGGREGATE_RECIPE_KEYS,
    _COLUMN_KEYS,
    _INPUT_PROJECTIONS,
    _MEASURE_KEYS,
    _MULTISET_RECIPE_KEYS,
    _NORMALIZATIONS,
    _RAW_VALUE,
    _RECIPE_KEYS,
    _SCHEMAS,
    _SUITE_LIMIT_DEFAULTS,
    _SUITE_LIMIT_KEYS,
    _TYPES,
    ParisonError,
    _SafeParseError,
)


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
        _check_output_parent(target.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        for filename, name in exports.items():
            schema = load_schema(name)
            schema.pop("$id")
            (stage / filename).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _rename_no_replace(stage, target)
        return {"output": str(target), "files": sorted(exports)}
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot export editor schemas: {exc}") from exc


def load_suite(path: str | Path) -> dict[str, Any]:
    from .inputs import _source_path, _source_paths, _sqlite_source

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
