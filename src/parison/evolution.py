from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from parison.core import ParisonError, explain_recipe


_CHANGES = ("unchanged", "renamed", "added", "removed", "split", "merged")
_FIELD_KEYS = {"id", "name", "presence", "nullability", "default"}


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ParisonError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _valid_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, bool, int)) or (
        isinstance(value, float) and math.isfinite(value)
    )


def _field(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not {"id", "name", "presence", "nullability"} <= set(value) or set(value) - _FIELD_KEYS:
        raise ParisonError(f"{where} must contain id, name, presence and nullability, with optional default")
    if not isinstance(value["id"], str) or not value["id"]:
        raise ParisonError(f"{where}.id must be a nonempty string")
    if not isinstance(value["name"], str) or not value["name"]:
        raise ParisonError(f"{where}.name must be a nonempty string")
    if not isinstance(value["presence"], str) or value["presence"] not in {"required", "optional"}:
        raise ParisonError(f"{where}.presence must be 'required' or 'optional'")
    if not isinstance(value["nullability"], str) or value["nullability"] not in {"non-null", "nullable"}:
        raise ParisonError(f"{where}.nullability must be 'non-null' or 'nullable'")
    if "default" in value and not _valid_scalar(value["default"]):
        raise ParisonError(f"{where}.default must be a finite JSON scalar")
    return dict(value)


def normalize_evolution(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"evolution_version", "direction", "changes"}:
        raise ParisonError("evolution must contain exactly evolution_version, direction and changes")
    if type(value["evolution_version"]) is not int or value["evolution_version"] != 1:
        raise ParisonError("evolution_version must be 1")
    if value["direction"] != "baseline-to-candidate":
        raise ParisonError("direction must be 'baseline-to-candidate'")
    if not isinstance(value["changes"], list) or not value["changes"]:
        raise ParisonError("changes must be a nonempty array")

    normalized = []
    side_ids = {"baseline": set(), "candidate": set()}
    side_names = {"baseline": set(), "candidate": set()}
    for index, item in enumerate(value["changes"]):
        where = f"changes[{index}]"
        if not isinstance(item, dict) or set(item) != {"change", "baseline", "candidate"}:
            raise ParisonError(f"{where} must contain exactly change, baseline and candidate")
        change = item["change"]
        if change not in _CHANGES:
            raise ParisonError(f"{where}.change is unsupported")
        sides: dict[str, list[dict[str, Any]]] = {}
        for side in ("baseline", "candidate"):
            raw = item[side]
            if not isinstance(raw, list):
                raise ParisonError(f"{where}.{side} must be an array")
            fields = [_field(field, f"{where}.{side}[{field_index}]") for field_index, field in enumerate(raw)]
            for field in fields:
                if field["id"] in side_ids[side]:
                    raise ParisonError(f"logical field id {field['id']!r} is repeated on {side}")
                if field["name"] in side_names[side]:
                    raise ParisonError(f"physical field name {field['name']!r} is repeated on {side}")
                side_ids[side].add(field["id"])
                side_names[side].add(field["name"])
            sides[side] = sorted(fields, key=lambda field: field["id"])

        counts = (len(sides["baseline"]), len(sides["candidate"]))
        expected = {
            "unchanged": (1, 1), "renamed": (1, 1), "added": (0, 1), "removed": (1, 0),
        }
        if change in expected and counts != expected[change]:
            raise ParisonError(f"{where} has invalid baseline/candidate cardinality for {change}")
        if change == "split" and not (counts[0] == 1 and counts[1] >= 2):
            raise ParisonError(f"{where} split requires one baseline and at least two candidate fields")
        if change == "merged" and not (counts[0] >= 2 and counts[1] == 1):
            raise ParisonError(f"{where} merged requires at least two baseline and one candidate field")

        baseline_ids = {field["id"] for field in sides["baseline"]}
        candidate_ids = {field["id"] for field in sides["candidate"]}
        if change in {"unchanged", "renamed"}:
            if baseline_ids != candidate_ids:
                raise ParisonError(f"{where} {change} must preserve one logical field id")
            same_name = sides["baseline"][0]["name"] == sides["candidate"][0]["name"]
            if (change == "unchanged") != same_name:
                raise ParisonError(f"{where} names contradict change kind {change}")
        elif baseline_ids & candidate_ids:
            raise ParisonError(f"{where} {change} must not reuse retired logical field ids")
        normalized.append({"change": change, **sides})

    preserved = side_ids["baseline"] & side_ids["candidate"]
    declared_preserved = {
        item["baseline"][0]["id"] for item in normalized if item["change"] in {"unchanged", "renamed"}
    }
    if preserved != declared_preserved:
        raise ParisonError("logical field ids may span both sides only through unchanged or renamed entries")

    normalized.sort(key=lambda item: (_CHANGES.index(item["change"]), _sort_id(item)))
    return {"evolution_version": 1, "direction": "baseline-to-candidate", "changes": normalized}


def _sort_id(item: dict[str, Any]) -> tuple[str, ...]:
    return tuple(field["id"] for side in ("baseline", "candidate") for field in item[side])


def canonical_evolution_bytes(value: Any) -> bytes:
    normalized = normalize_evolution(value)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_evolution(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_object)
    except ParisonError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read evolution declaration: {exc}") from exc
    return normalize_evolution(value)


def explain_evolution(path: str | Path) -> dict[str, Any]:
    normalized = load_evolution(path)
    digest = hashlib.sha256(canonical_evolution_bytes(normalized)).hexdigest()
    return {**normalized, "evolution_sha256": digest}


def compile_evolution_mappings(path: str | Path) -> dict[str, Any]:
    evolution = explain_evolution(path)
    transformations = [item["change"] for item in evolution["changes"] if item["change"] in {"split", "merged"}]
    if transformations:
        raise ParisonError("split and merged evolution requires upstream materialization and cannot compile to column mappings")
    mappings = {}
    for item in evolution["changes"]:
        if item["change"] not in {"unchanged", "renamed"}:
            continue
        baseline, candidate = item["baseline"][0], item["candidate"][0]
        mappings[baseline["id"]] = {"baseline": baseline["name"], "candidate": candidate["name"]}
    return {
        "evolution_sha256": evolution["evolution_sha256"],
        "column_mappings": dict(sorted(mappings.items())),
    }


def _column_index(policy: dict[str, Any], side: str) -> dict[str, dict[str, Any]]:
    index = {}
    source_key = f"{side}_column"
    for canonical, configured in policy["columns"].items():
        source = configured[source_key]
        if source in index:
            raise ParisonError(f"effective policy repeats {side} physical column {source!r}")
        semantic = {key: value for key, value in configured.items() if key not in {"baseline_column", "candidate_column"}}
        index[source] = {"canonical": canonical, "semantic": semantic, "role": _role(policy, canonical, semantic)}
    return index


def _role(policy: dict[str, Any], canonical: str, semantic: dict[str, Any]) -> str:
    mode = policy["comparison_mode"]
    if mode == "keyed":
        return "key" if semantic["key"] else "value"
    if mode == "aggregate":
        if semantic["group_by"]:
            return "group"
        if any(measure.get("column") == canonical for measure in policy["measures"].values()):
            return "measure-input"
        return "value"
    return "value"


def _leaf_changes(left: Any, right: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any, Any]]:
    if isinstance(left, dict) and isinstance(right, dict):
        changes = []
        for key in sorted(set(left) | set(right)):
            if key not in left or key not in right:
                changes.append((path + (key,), left.get(key), right.get(key)))
            else:
                changes.extend(_leaf_changes(left[key], right[key], path + (key,)))
        return changes
    return [] if left == right else [(path, left, right)]


_GLOBAL_PATHS = {
    ("schema_version",), ("recipe_version",), ("comparison_mode",), ("aggregate_contract",),
    ("multiset_contract",), ("canonical_encoding",), ("input_projection",), ("nulls_equal",),
    ("group_nulls",), ("column_order",), ("group_by",),
    ("scope", "snapshot"), ("scope", "cutoff"), ("scope", "filters"),
    ("scope", "completeness"), ("scope", "expected_empty"),
    ("identity", "null_keys"), ("identity", "duplicates"),
    ("delimiters", "baseline"), ("delimiters", "candidate"),
    ("null_tokens", "baseline"), ("null_tokens", "candidate"), ("output", "sensitivity"),
}
_MEASURE_FIELDS = {"operator", "column", "nulls", "comparison"}
_TOLERANCE_FIELDS = {"formula", "absolute", "relative"}


def _closed_policy_path(path: tuple[str, ...]) -> tuple[str | None, list[str]]:
    if path in _GLOBAL_PATHS:
        return ".".join(path), []
    if len(path) == 3 and path[0] == "measures" and path[2] in _MEASURE_FIELDS:
        return f"measures[].{path[2]}", [path[1]]
    if len(path) == 4 and path[0] == "measures" and path[2] == "tolerance" and path[3] in _TOLERANCE_FIELDS:
        return f"measures[].tolerance.{path[3]}", [path[1]]
    if len(path) == 2 and path[0] == "measures":
        return "measures[]", [path[1]]
    return None, []


def _record(kind: str, compatibility: str, impact: str, reason: str, **metadata: Any) -> dict[str, Any]:
    return {"kind": kind, "compatibility": compatibility, "impact": impact, "reason": reason, **metadata}


def diff_policies(baseline_recipe: str | Path, candidate_recipe: str | Path, evolution_path: str | Path) -> dict[str, Any]:
    baseline = explain_recipe(baseline_recipe)
    candidate = explain_recipe(candidate_recipe)
    evolution = explain_evolution(evolution_path)
    baseline_index = _column_index(baseline, "baseline")
    candidate_index = _column_index(candidate, "candidate")
    baseline_excluded = baseline["excluded_columns"]
    candidate_excluded = candidate["excluded_columns"]
    seen = {"baseline": set(), "candidate": set()}
    changes: list[dict[str, Any]] = []

    global_baseline = {key: value for key, value in baseline.items() if key not in {"policy_sha256", "columns", "excluded_columns"}}
    global_candidate = {key: value for key, value in candidate.items() if key not in {"policy_sha256", "columns", "excluded_columns"}}
    for path, old, new in _leaf_changes(global_baseline, global_candidate):
        closed_path, policy_names = _closed_policy_path(path)
        if closed_path is None:
            changes.append(_record("policy-modified", "INCONCLUSIVE", "unknown", "UNKNOWN_POLICY_PATH", path="unknown"))
        else:
            changes.append(_record(
                "policy-modified", "DENY", "meaning-changed", "GLOBAL_POLICY_CHANGED",
                path=closed_path, baseline=old, candidate=new, **({"policy_names": policy_names} if policy_names else {}),
            ))

    for operation in evolution["changes"]:
        kind = operation["change"]
        for side in ("baseline", "candidate"):
            seen[side].update(field["name"] for field in operation[side])
        if kind in {"unchanged", "renamed"}:
            old_field, new_field = operation["baseline"][0], operation["candidate"][0]
            old = baseline_index.get(old_field["name"])
            new = candidate_index.get(new_field["name"])
            old_is_excluded = old_field["name"] in baseline_excluded
            new_is_excluded = new_field["name"] in candidate_excluded
            old_contract = {key: old_field.get(key) for key in ("presence", "nullability", "default") if key in old_field}
            new_contract = {key: new_field.get(key) for key in ("presence", "nullability", "default") if key in new_field}
            if old_contract != new_contract:
                changes.append(_record(kind, "DENY", "meaning-changed", "FIELD_CONTRACT_CHANGED", logical_ids=[old_field["id"]], baseline_names=[old_field["name"]], candidate_names=[new_field["name"]]))
            elif old_is_excluded and new_is_excluded:
                changes.append(_record(kind, "ACCEPT", "input-only", "EXCLUDED_FIELD_IDENTITY_PRESERVED", logical_ids=[old_field["id"]], baseline_names=[old_field["name"]], candidate_names=[new_field["name"]]))
            elif old is None or new is None:
                changes.append(_record(kind, "DENY", "meaning-changed", "MAPPED_FIELD_NOT_COMPARED", logical_ids=[old_field["id"]], baseline_names=[old_field["name"]], candidate_names=[new_field["name"]]))
            elif old["semantic"] != new["semantic"] or old["role"] != new["role"]:
                changes.append(_record(kind, "DENY", "meaning-changed", "FIELD_POLICY_CHANGED", logical_ids=[old_field["id"]], baseline_names=[old_field["name"]], candidate_names=[new_field["name"]], baseline={"role": old["role"], "policy": old["semantic"]}, candidate={"role": new["role"], "policy": new["semantic"]}))
            else:
                changes.append(_record(kind, "ACCEPT", "none" if kind == "unchanged" else "input-only", "FIELD_IDENTITY_PRESERVED", logical_ids=[old_field["id"]], baseline_names=[old_field["name"]], candidate_names=[new_field["name"]]))
        elif kind in {"added", "removed"}:
            side = "candidate" if kind == "added" else "baseline"
            field = operation[side][0]
            active = candidate_index if side == "candidate" else baseline_index
            excluded = candidate_excluded if side == "candidate" else baseline_excluded
            if field["name"] in active:
                changes.append(_record(kind, "DENY", "meaning-changed", "STRUCTURAL_FIELD_IS_COMPARED", logical_ids=[field["id"]], **{f"{side}_names": [field["name"]]}))
            elif field["name"] not in excluded:
                changes.append(_record(kind, "INCONCLUSIVE", "unknown", "STRUCTURAL_FIELD_ROLE_UNKNOWN", logical_ids=[field["id"]], **{f"{side}_names": [field["name"]]}))
            elif field["presence"] != "required" or field["nullability"] != "non-null" or "default" in field:
                changes.append(_record(kind, "DENY", "meaning-changed", "STRUCTURAL_FIELD_CONTRACT_UNSAFE", logical_ids=[field["id"]], **{f"{side}_names": [field["name"]]}))
            else:
                changes.append(_record(kind, "ACCEPT", "input-only", "EXCLUDED_STRUCTURAL_FIELD", logical_ids=[field["id"]], **{f"{side}_names": [field["name"]]}))
        else:
            active_names = [
                field["name"] for side, index in (("baseline", baseline_index), ("candidate", candidate_index))
                for field in operation[side] if field["name"] in index
            ]
            compatibility = "DENY" if active_names else "INCONCLUSIVE"
            reason = "TRANSFORMATION_FIELD_IS_COMPARED" if active_names else "TRANSFORMATION_REQUIRES_UPSTREAM_MATERIALIZATION"
            changes.append(_record(kind, compatibility, "unsupported-transformation", reason, logical_ids=sorted(field["id"] for side in ("baseline", "candidate") for field in operation[side]), baseline_names=[field["name"] for field in operation["baseline"]], candidate_names=[field["name"] for field in operation["candidate"]]))

    for side, index, excluded in (
        ("baseline", baseline_index, baseline_excluded), ("candidate", candidate_index, candidate_excluded),
    ):
        for name in sorted((set(index) | set(excluded)) - seen[side]):
            changes.append(_record("policy-modified", "DENY", "meaning-changed", "UNDECLARED_POLICY_FIELD", path=f"{side}.field", **{f"{side}_names": [name]}))

    order = {name: index for index, name in enumerate((*_CHANGES, "policy-modified"))}
    changes.sort(key=lambda item: (order[item["kind"]], item.get("path", ""), tuple(item.get("logical_ids", [])), tuple(item.get("baseline_names", [])), tuple(item.get("candidate_names", [])), item["reason"]))
    labels = {item["compatibility"] for item in changes}
    compatibility = "DENY" if "DENY" in labels else "INCONCLUSIVE" if "INCONCLUSIVE" in labels else "ACCEPT"
    result = {
        "policy_diff_version": 1,
        "direction": "baseline-to-candidate",
        "compatibility": compatibility,
        "baseline_policy_sha256": baseline["policy_sha256"],
        "candidate_policy_sha256": candidate["policy_sha256"],
        "evolution_sha256": evolution["evolution_sha256"],
        "changes": changes,
    }
    result["policy_diff_sha256"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return result


def summarize_policy_diff(result: dict[str, Any]) -> dict[str, Any]:
    counts = {label: sum(item["compatibility"] == label for item in result["changes"]) for label in ("ACCEPT", "DENY", "INCONCLUSIVE")}
    reasons = sorted({item["reason"] for item in result["changes"]})
    return {
        "policy_diff_version": result["policy_diff_version"],
        "direction": result["direction"],
        "compatibility": result["compatibility"],
        "baseline_policy_sha256": result["baseline_policy_sha256"],
        "candidate_policy_sha256": result["candidate_policy_sha256"],
        "evolution_sha256": result["evolution_sha256"],
        "policy_diff_sha256": result["policy_diff_sha256"],
        "change_counts": counts,
        "reason_codes": reasons,
    }
