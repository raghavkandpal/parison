"""Deterministic, summary-safe discrepancy analysis."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import shutil
import tempfile
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .core import ParisonError
from .evidence import _verified_bundle, _write_once

_DOMAIN = b"parison:discrepancy-group:v1\0"
_KINDS = {"record": 0, "field": 1, "group": 2, "measure": 3, "row": 4}
_CLASSIFICATIONS = {
    "baseline_only": 0,
    "candidate_only": 1,
    "within_tolerance": 2,
    "different": 3,
    "baseline_surplus": 4,
    "candidate_surplus": 5,
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _ref(path: str, value: Any) -> dict[str, Any]:
    return {"path": path, "value": value}


def _group(descriptor: dict[str, Any], count: int, source: str, references: list[dict[str, Any]]) -> dict[str, Any]:
    identifier = hashlib.sha256(_DOMAIN + _canonical(descriptor)).hexdigest()
    return {
        "group_id": identifier,
        "descriptor": descriptor,
        "count": count,
        "count_source": source,
        "reason_codes": [f"{descriptor['kind']}.{descriptor['classification']}"],
        "policy_references": references,
    }


def _group_sort_key(group: dict[str, Any]) -> tuple[Any, ...]:
    descriptor = group["descriptor"]
    return (
        _KINDS[descriptor["kind"]],
        _CLASSIFICATIONS[descriptor["classification"]],
        descriptor.get("logical_name", "").encode("utf-8"),
        group["group_id"],
    )


def _read_verified_run(directory: str | Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    path = Path(directory)
    manifest, before = _verified_bundle(path)
    if manifest.get("kind") is not None:
        raise ParisonError("discrepancy analysis requires an ordinary run bundle")
    try:
        captured = {name: (path / name).read_bytes() for name in ("result.json", "effective-recipe.json")}
        if any(hashlib.sha256(data).hexdigest() != manifest["files"][name] for name, data in captured.items()):
            raise ParisonError("analysis inputs changed after verification")
        result = json.loads(captured["result.json"], object_pairs_hook=_strict_object)
        recipe = json.loads(captured["effective-recipe.json"], object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read analysis inputs: {exc}") from exc
    _, after = _verified_bundle(path)
    if before != after:
        raise ParisonError("bundle changed while preparing analysis")
    policy = result.get("policy_sha256")
    if not isinstance(policy, str) or len(policy) != 64:
        raise ParisonError("run has no supported policy digest")
    return result, recipe, hashlib.sha256(before).hexdigest()


def _column_refs(result: dict[str, Any], name: str) -> list[dict[str, Any]]:
    token = _pointer_token(name)
    policy = result["column_policies"][name]
    refs = [_ref(f"/column_policies/{token}/type", policy["type"])]
    for key in ("scale", "timezone", "normalize", "comparison", "tolerance"):
        if key in policy:
            refs.append(_ref(f"/column_policies/{token}/{key}", policy[key]))
    mapping = result.get("column_mappings", {}).get(name)
    if mapping is not None:
        refs.append(_ref(f"/column_mappings/{token}", mapping))
    return refs


def _scope_refs(result: dict[str, Any]) -> list[dict[str, Any]]:
    scope = result.get("scope")
    if not isinstance(scope, dict) or set(scope) != {"snapshot", "cutoff", "filters", "completeness", "expected_empty"}:
        raise ParisonError("run has an unsupported scope policy")
    return [
        _ref(f"/scope/{name}", scope[name])
        for name in ("snapshot", "cutoff", "filters", "completeness", "expected_empty")
    ]


def _descriptor(mode: str, kind: str, classification: str, logical_name: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "analysis_version": 1,
        "comparison_mode": mode,
        "kind": kind,
        "classification": classification,
    }
    if logical_name is not None:
        value["logical_name"] = logical_name
    return value


def _groups(result: dict[str, Any], recipe: dict[str, Any]) -> list[dict[str, Any]]:
    mode = recipe.get("comparison_mode")
    groups: list[dict[str, Any]] = []
    if result.get("schema_version") == 1 and mode == "keyed":
        counts = result.get("counts", {})
        groups.extend(
            _group(
                _descriptor(mode, "record", side),
                counts.get(side, 0),
                f"/counts/{side}",
                [
                    _ref("/keys", result["keys"]),
                    _ref("/identity/null_keys", recipe["identity"]["null_keys"]),
                    _ref("/identity/duplicates", recipe["identity"]["duplicates"]),
                ],
            )
            for side in ("baseline_only", "candidate_only")
        )
        for name in sorted(recipe.get("columns", {}), key=lambda value: value.encode("utf-8")):
            if name in recipe.get("keys", []):
                continue
            token = _pointer_token(name)
            for classification in ("within_tolerance", "different"):
                groups.append(
                    _group(
                        _descriptor(mode, "field", classification, name),
                        result.get("field_counts", {}).get(name, {}).get(classification, 0),
                        f"/field_counts/{token}/{classification}",
                        [_ref("/policy/nulls_equal", result["policy"]["nulls_equal"]), *_column_refs(result, name)],
                    )
                )
    elif result.get("schema_version") == 2 and mode == "aggregate":
        for classification, source in (
            ("baseline_only", "baseline_only_groups"),
            ("candidate_only", "candidate_only_groups"),
        ):
            groups.append(
                _group(
                    _descriptor(mode, "group", classification),
                    result.get("counts", {}).get(source, 0),
                    f"/counts/{source}",
                    [
                        _ref("/group_by", result["group_by"]),
                        _ref("/policy/group_nulls", result["policy"]["group_nulls"]),
                        *[reference for name in result["group_by"] for reference in _column_refs(result, name)],
                    ],
                )
            )
        for name in sorted(recipe.get("measures", {}), key=lambda value: value.encode("utf-8")):
            token = _pointer_token(name)
            for classification in ("within_tolerance", "different"):
                groups.append(
                    _group(
                        _descriptor(mode, "measure", classification, name),
                        result.get("measure_counts", {}).get(name, {}).get(classification, 0),
                        f"/measure_counts/{token}/{classification}",
                        [
                            *[
                                _ref(f"/measures/{token}/{key}", value)
                                for key, value in result["measures"][name].items()
                            ],
                            *(
                                _column_refs(result, result["measures"][name]["column"])
                                if "column" in result["measures"][name]
                                else []
                            ),
                        ],
                    )
                )
    elif result.get("schema_version") == 3 and mode == "multiset":
        for classification, source in (
            ("baseline_surplus", "baseline_surplus_shapes"),
            ("candidate_surplus", "candidate_surplus_shapes"),
        ):
            groups.append(
                _group(
                    _descriptor(mode, "row", classification),
                    result.get("counts", {}).get(source, 0),
                    f"/counts/{source}",
                    [
                        _ref("/policy/canonical_encoding", result["policy"]["canonical_encoding"]),
                        _ref("/policy/column_order", result["policy"]["column_order"]),
                        _ref("/policy/nulls_equal", result["policy"]["nulls_equal"]),
                        *[
                            reference
                            for name in result["policy"]["column_order"]
                            for reference in _column_refs(result, name)
                        ],
                    ],
                )
            )
    else:
        raise ParisonError("run result and comparison mode are unsupported for analysis")
    if any(type(group["count"]) is not int or group["count"] < 0 for group in groups):
        raise ParisonError("run contains invalid discrepancy counts")
    if sum(group["count"] for group in groups) != result.get("discrepancy_count"):
        raise ParisonError("run discrepancy groups do not reconcile with discrepancy_count")
    return sorted(groups, key=_group_sort_key)


def analyze_bundle(directory: str | Path) -> dict[str, Any]:
    """Project one verified run into exhaustive summary-safe discrepancy groups."""
    result, recipe, bundle_sha256 = _read_verified_run(directory)
    return {
        "analysis_version": 1,
        "kind": "run",
        "bundle_sha256": bundle_sha256,
        "policy_sha256": result["policy_sha256"],
        "comparison_mode": recipe["comparison_mode"],
        "sensitivity": "summary",
        "scope_references": _scope_refs(result),
        "groups": _groups(result, recipe),
    }


def analyze_series(directories: Iterable[str | Path]) -> dict[str, Any]:
    """Compare discrepancy group counts in caller-supplied run order."""
    runs = [analyze_bundle(directory) for directory in directories]
    if len(runs) < 2:
        raise ParisonError("discrepancy series requires at least two runs")
    if len({run["bundle_sha256"] for run in runs}) != len(runs):
        raise ParisonError("discrepancy series requires distinct run bundles")
    if len({(run["policy_sha256"], run["comparison_mode"]) for run in runs}) != 1:
        raise ParisonError("discrepancy series requires one exact policy and comparison mode")
    by_run = [{group["group_id"]: group for group in run["groups"]} for run in runs]
    descriptors = {group["group_id"]: group for run in runs for group in run["groups"]}
    groups = []
    transitions = []
    for identifier in [group["group_id"] for group in sorted(descriptors.values(), key=_group_sort_key)]:
        counts = [groups_by_id.get(identifier, {"count": 0})["count"] for groups_by_id in by_run]
        groups.append(
            {key: value for key, value in descriptors[identifier].items() if key != "count"} | {"counts": counts}
        )
        transitions.extend(
            _transition(identifier, index, before, after)
            for index, (before, after) in enumerate(itertools.pairwise(counts))
        )
    return {
        "analysis_version": 1,
        "kind": "series",
        "policy_sha256": runs[0]["policy_sha256"],
        "comparison_mode": runs[0]["comparison_mode"],
        "sensitivity": "summary",
        "runs": [{"bundle_sha256": run["bundle_sha256"]} for run in runs],
        "groups": groups,
        "transitions": transitions,
    }


def analyze_catalog(database: str | Path, policy_sha256: str) -> dict[str, Any]:
    """Analyze one exact policy's current, unaliased catalog runs in insertion order."""
    from .catalog import analysis_runs

    return analyze_series(analysis_runs(database, policy_sha256))


def drill_down(directories: Iterable[str | Path], group_id: str, limit: int, per_run_limit: int) -> dict[str, Any]:
    """Select bounded raw items for one exact group from already-published samples."""
    paths = list(directories)
    if (
        not paths
        or not _is_sha(group_id)
        or type(limit) is not int
        or limit <= 0
        or type(per_run_limit) is not int
        or per_run_limit <= 0
    ):
        raise ParisonError("drill-down requires runs, an exact group ID and positive limits")
    output: list[dict[str, Any]] = []
    runs: list[dict[str, Any]] = []
    remaining = limit
    for run_index, directory in enumerate(paths):
        result, recipe, bundle_sha256 = _read_verified_run(directory)
        if result.get("sensitivity") != "raw":
            raise ParisonError("drill-down requires raw-sensitivity run bundles")
        groups = {group["group_id"]: group for group in _groups(result, recipe)}
        if group_id not in groups:
            raise ParisonError("group ID is not valid for every supplied run")
        descriptor = groups[group_id]["descriptor"]
        sample = result["discrepancy_sample"]
        matches = [
            (sample_index, item) for sample_index, item in enumerate(sample) if _sample_matches(item, descriptor)
        ]
        selected = matches[: min(per_run_limit, remaining)]
        output.extend(
            {"run_index": run_index, "sample_index": sample_index, "item": item} for sample_index, item in selected
        )
        remaining -= len(selected)
        runs.append(
            {
                "bundle_sha256": bundle_sha256,
                "policy_sha256": result["policy_sha256"],
                "population_count": groups[group_id]["count"],
                "published_sample_size": len(sample),
                "matched_sample_size": len(matches),
                "returned_size": len(selected),
                "sample_complete": len(sample) == result["discrepancy_count"],
            }
        )
    return {
        "drilldown_version": 1,
        "kind": "discrepancy-drilldown",
        "sensitivity": "raw",
        "group_id": group_id,
        "limit": limit,
        "per_run_limit": per_run_limit,
        "runs": runs,
        "returned_size": len(output),
        "items": output,
    }


def export_drilldown(output: str | Path, drilldown: dict[str, Any]) -> dict[str, Any]:
    """Write a canonical raw drill-down artifact once."""
    _validate_drilldown(drilldown)
    content = (_canonical(drilldown) + b"\n").decode("utf-8")
    _write_once(Path(output), content, "cannot export discrepancy drill-down")
    return {"output": str(output), "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}


def verify_drilldown(path: str | Path) -> dict[str, Any]:
    """Verify one canonical, strict discrepancy drill-down artifact."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ParisonError(f"drill-down is not a regular file: {path}")
    try:
        before = path.read_bytes()
        value = json.loads(before, object_pairs_hook=_strict_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read discrepancy drill-down: {exc}") from exc
    _validate_drilldown(value)
    if before != _canonical(value) + b"\n":
        raise ParisonError("drill-down failed canonical integrity verification")
    try:
        if path.read_bytes() != before:
            raise ParisonError("drill-down changed during verification")
    except OSError as exc:
        raise ParisonError(f"cannot read discrepancy drill-down: {exc}") from exc
    return {
        "kind": value["kind"],
        "sensitivity": value["sensitivity"],
        "group_id": value["group_id"],
        "returned_size": value["returned_size"],
        "sha256": hashlib.sha256(before).hexdigest(),
    }


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ParisonError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _validate_drilldown(value: Any) -> None:
    keys = {
        "drilldown_version",
        "kind",
        "sensitivity",
        "group_id",
        "limit",
        "per_run_limit",
        "runs",
        "returned_size",
        "items",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value.get("drilldown_version") != 1
        or value.get("kind") != "discrepancy-drilldown"
        or value.get("sensitivity") != "raw"
        or not _is_sha(value.get("group_id"))
        or type(value.get("limit")) is not int
        or value["limit"] <= 0
        or type(value.get("per_run_limit")) is not int
        or value["per_run_limit"] <= 0
        or not isinstance(value.get("runs"), list)
        or not value["runs"]
        or not isinstance(value.get("items"), list)
        or type(value.get("returned_size")) is not int
        or value["returned_size"] != len(value["items"])
        or value["returned_size"] > value["limit"]
    ):
        raise ParisonError("drill-down content is incomplete or unsupported")
    run_keys = {
        "bundle_sha256",
        "policy_sha256",
        "population_count",
        "published_sample_size",
        "matched_sample_size",
        "returned_size",
        "sample_complete",
    }
    for run in value["runs"]:
        if (
            not isinstance(run, dict)
            or set(run) != run_keys
            or not _is_sha(run["bundle_sha256"])
            or not _is_sha(run["policy_sha256"])
            or any(
                type(run[name]) is not int or run[name] < 0
                for name in ("population_count", "published_sample_size", "matched_sample_size", "returned_size")
            )
            or type(run["sample_complete"]) is not bool
            or run["matched_sample_size"] > run["published_sample_size"]
            or run["returned_size"] > min(run["matched_sample_size"], value["per_run_limit"])
        ):
            raise ParisonError("drill-down contains invalid run provenance")
    item_counts = [0] * len(value["runs"])
    for index, item in enumerate(value["items"]):
        if (
            not isinstance(item, dict)
            or set(item) != {"run_index", "sample_index", "item"}
            or type(item["run_index"]) is not int
            or not 0 <= item["run_index"] < len(value["runs"])
            or type(item["sample_index"]) is not int
            or item["sample_index"] < 0
            or item["sample_index"] >= value["runs"][item["run_index"]]["published_sample_size"]
            or not isinstance(item["item"], dict)
            or (
                index
                and (item["run_index"], item["sample_index"])
                <= (value["items"][index - 1]["run_index"], value["items"][index - 1]["sample_index"])
            )
        ):
            raise ParisonError("drill-down contains invalid sample items")
        item_counts[item["run_index"]] += 1
    if item_counts != [run["returned_size"] for run in value["runs"]]:
        raise ParisonError("drill-down counts do not reconcile")


def _sample_matches(item: Any, descriptor: dict[str, Any]) -> bool:
    if not isinstance(item, dict) or item.get("classification") != descriptor["classification"]:
        return False
    expected_kind = {
        "record": {"record"},
        "field": {"field"},
        "group": {"group"},
        "measure": {"measure"},
        "row": {None},
    }[descriptor["kind"]]
    if item.get("kind") not in expected_kind:
        return False
    if "logical_name" not in descriptor:
        return True
    return item.get("field", item.get("measure")) == descriptor["logical_name"]


def publish_analysis(output: str | Path, analysis: dict[str, Any]) -> dict[str, Any]:
    """Atomically publish a canonical discrepancy analysis bundle."""
    _validate_analysis(analysis)
    output = Path(output)
    if output.exists():
        raise ParisonError(f"output already exists: {output}")
    stage = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        check_output_parent(output.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
        os.chmod(stage, 0o700)
        payload = _canonical(analysis) + b"\n"
        (stage / "analysis.json").write_bytes(payload)
        manifest = {
            "schema_version": 2 if analysis["kind"] == "suite-series" else 1,
            "kind": "discrepancy-analysis",
            "complete": True,
            "sensitivity": "summary",
            "analysis_kind": analysis["kind"],
            "analysis_sha256": hashlib.sha256(payload).hexdigest(),
            "files": {"analysis.json": hashlib.sha256(payload).hexdigest()},
        }
        manifest_bytes = _canonical(manifest) + b"\n"
        (stage / "manifest.json").write_bytes(manifest_bytes)
        rename_no_replace(stage, output)
        return {"output": str(output), "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest()}
    except OSError as exc:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise ParisonError(f"cannot publish analysis: {exc}") from exc
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_analysis_bundle(directory: str | Path) -> dict[str, Any]:
    """Verify canonical bytes and digests for a discrepancy analysis bundle."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ParisonError(f"analysis is not a regular directory: {directory}")
    try:
        if {entry.name for entry in directory.iterdir()} != {"manifest.json", "analysis.json"}:
            raise ParisonError("analysis bundle contains unexpected members")
        manifest_path = directory / "manifest.json"
        analysis_path = directory / "analysis.json"
        if manifest_path.is_symlink() or analysis_path.is_symlink():
            raise ParisonError("analysis bundle contains an unsafe file")
        manifest_bytes = manifest_path.read_bytes()
        payload = analysis_path.read_bytes()
        manifest = json.loads(manifest_bytes, object_pairs_hook=_strict_object)
        analysis = json.loads(payload, object_pairs_hook=_strict_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read analysis bundle: {exc}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    expected = {
        "schema_version": 2 if isinstance(analysis, dict) and analysis.get("kind") == "suite-series" else 1,
        "kind": "discrepancy-analysis",
        "complete": True,
        "sensitivity": "summary",
        "analysis_kind": analysis.get("kind") if isinstance(analysis, dict) else None,
        "analysis_sha256": digest,
        "files": {"analysis.json": digest},
    }
    _validate_analysis(analysis)
    if (
        manifest != expected
        or payload != _canonical(analysis) + b"\n"
        or manifest_bytes != _canonical(manifest) + b"\n"
    ):
        raise ParisonError("analysis bundle failed canonical integrity verification")
    if manifest_path.read_bytes() != manifest_bytes or analysis_path.read_bytes() != payload:
        raise ParisonError("analysis bundle changed during verification")
    return manifest


def _validate_analysis(analysis: Any) -> None:
    if isinstance(analysis, dict) and analysis.get("kind") == "suite-series":
        from .suite_series import validate_suite_series

        validate_suite_series(analysis)
        return
    common = {"analysis_version", "kind", "policy_sha256", "comparison_mode", "sensitivity", "groups"}
    if (
        not isinstance(analysis, dict)
        or analysis.get("analysis_version") != 1
        or analysis.get("kind") not in {"run", "series"}
        or analysis.get("comparison_mode") not in {"keyed", "aggregate", "multiset"}
        or analysis.get("sensitivity") != "summary"
        or not _is_sha(analysis.get("policy_sha256"))
        or not isinstance(analysis.get("groups"), list)
    ):
        raise ParisonError("analysis content is incomplete or unsupported")
    expected_keys = common | (
        {"bundle_sha256", "scope_references"} if analysis["kind"] == "run" else {"runs", "transitions"}
    )
    if set(analysis) != expected_keys:
        raise ParisonError("analysis content contains invalid fields")
    groups = analysis["groups"]
    identifiers = []
    for group in groups:
        required = {"group_id", "descriptor", "count_source", "reason_codes", "policy_references"}
        value_key = "count" if analysis["kind"] == "run" else "counts"
        if not isinstance(group, dict) or set(group) != required | {value_key}:
            raise ParisonError("analysis contains an invalid group")
        descriptor = group["descriptor"]
        if (
            not isinstance(descriptor, dict)
            or set(descriptor)
            not in (
                {"analysis_version", "comparison_mode", "kind", "classification"},
                {"analysis_version", "comparison_mode", "kind", "classification", "logical_name"},
            )
            or descriptor.get("analysis_version") != 1
            or descriptor.get("comparison_mode") != analysis["comparison_mode"]
            or descriptor.get("kind") not in _KINDS
            or descriptor.get("classification") not in _CLASSIFICATIONS
            or (
                "logical_name" in descriptor
                and (not isinstance(descriptor["logical_name"], str) or not descriptor["logical_name"])
            )
        ):
            raise ParisonError("analysis contains an invalid group descriptor")
        expected_id = hashlib.sha256(_DOMAIN + _canonical(descriptor)).hexdigest()
        expected_source = _expected_count_source(descriptor)
        values = [group[value_key]] if value_key == "count" else group[value_key]
        if (
            group["group_id"] != expected_id
            or not isinstance(values, list)
            or not values
            or any(type(value) is not int or value < 0 for value in values)
            or group["count_source"] != expected_source
            or not isinstance(group["reason_codes"], list)
            or group["reason_codes"] != [f"{descriptor['kind']}.{descriptor['classification']}"]
            or not _valid_policy_refs(group["policy_references"], descriptor)
        ):
            raise ParisonError("analysis contains invalid group evidence")
        identifiers.append(expected_id)
    if groups != sorted(groups, key=_group_sort_key) or len(set(identifiers)) != len(identifiers):
        raise ParisonError("analysis groups are not canonical")
    if analysis["kind"] == "run":
        if not _is_sha(analysis["bundle_sha256"]) or not _valid_scope_refs(analysis["scope_references"]):
            raise ParisonError("run analysis has invalid provenance")
        return
    runs, transitions = analysis["runs"], analysis["transitions"]
    if (
        not isinstance(runs, list)
        or len(runs) < 2
        or any(
            not isinstance(run, dict) or set(run) != {"bundle_sha256"} or not _is_sha(run["bundle_sha256"])
            for run in runs
        )
        or len({run["bundle_sha256"] for run in runs}) != len(runs)
        or any(len(group["counts"]) != len(runs) for group in groups)
        or not isinstance(transitions, list)
    ):
        raise ParisonError("series analysis has invalid provenance or counts")
    expected_transitions = []
    for group in groups:
        expected_transitions.extend(
            _transition(group["group_id"], index, before, after)
            for index, (before, after) in enumerate(itertools.pairwise(group["counts"]))
        )
    if transitions != expected_transitions:
        raise ParisonError("series analysis transitions are not canonical")


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _transition(group_id: str, index: int, before: int, after: int) -> dict[str, Any]:
    delta = after - before
    status = (
        "introduced"
        if before == 0 < after
        else "resolved"
        if before > 0 == after
        else "increased"
        if delta > 0
        else "decreased"
        if delta < 0
        else "unchanged"
    )
    return {
        "group_id": group_id,
        "from_run": index,
        "to_run": index + 1,
        "before": before,
        "after": after,
        "delta": delta,
        "status": status,
    }


def _expected_count_source(descriptor: dict[str, Any]) -> str:
    mode, kind, classification = (
        descriptor["comparison_mode"],
        descriptor["kind"],
        descriptor["classification"],
    )
    name = descriptor.get("logical_name")
    if mode == "keyed" and kind == "record" and name is None and classification in {"baseline_only", "candidate_only"}:
        return f"/counts/{classification}"
    if mode == "keyed" and kind == "field" and name and classification in {"within_tolerance", "different"}:
        return f"/field_counts/{_pointer_token(name)}/{classification}"
    if (
        mode == "aggregate"
        and kind == "group"
        and name is None
        and classification in {"baseline_only", "candidate_only"}
    ):
        return f"/counts/{classification}_groups"
    if mode == "aggregate" and kind == "measure" and name and classification in {"within_tolerance", "different"}:
        return f"/measure_counts/{_pointer_token(name)}/{classification}"
    if (
        mode == "multiset"
        and kind == "row"
        and name is None
        and classification in {"baseline_surplus", "candidate_surplus"}
    ):
        return f"/counts/{classification}_shapes"
    raise ParisonError("analysis contains an unsupported group descriptor")


def _valid_scope_refs(references: Any) -> bool:
    paths = [f"/scope/{name}" for name in ("snapshot", "cutoff", "filters", "completeness", "expected_empty")]
    return _reference_paths(references) == paths and all(
        _valid_reference_value(reference["path"], reference["value"]) for reference in references
    )


def _reference_paths(references: Any) -> list[str] | None:
    if not isinstance(references, list) or not references:
        return None
    if any(
        not isinstance(ref, dict) or set(ref) != {"path", "value"} or not isinstance(ref["path"], str)
        for ref in references
    ):
        return None
    return [ref["path"] for ref in references]


def _valid_policy_refs(references: Any, descriptor: dict[str, Any]) -> bool:
    paths = _reference_paths(references)
    if (
        paths is None
        or len(paths) != len(set(paths))
        or not all(_valid_reference_value(reference["path"], reference["value"]) for reference in references)
    ):
        return False
    mode, kind = descriptor["comparison_mode"], descriptor["kind"]
    if (mode, kind) == ("keyed", "record"):
        return paths == ["/keys", "/identity/null_keys", "/identity/duplicates"]
    if (mode, kind) == ("keyed", "field"):
        token = _pointer_token(descriptor["logical_name"])
        return (
            paths[0] == "/policy/nulls_equal"
            and all(_valid_column_path(path, token) for path in paths[1:])
            and f"/column_policies/{token}/type" in paths
            and f"/column_policies/{token}/comparison" in paths
        )
    if (mode, kind) == ("aggregate", "group"):
        return paths[:2] == ["/group_by", "/policy/group_nulls"] and all(_valid_column_path(path) for path in paths[2:])
    if (mode, kind) == ("aggregate", "measure"):
        token = _pointer_token(descriptor["logical_name"])
        measure_paths = [path for path in paths if path.startswith(f"/measures/{token}/")]
        return (
            f"/measures/{token}/operator" in measure_paths
            and all(_valid_measure_path(path, token) for path in measure_paths)
            and all(_valid_column_path(path) for path in paths[len(measure_paths) :])
            and paths[: len(measure_paths)] == measure_paths
        )
    if (mode, kind) == ("multiset", "row"):
        return paths[:3] == [
            "/policy/canonical_encoding",
            "/policy/column_order",
            "/policy/nulls_equal",
        ] and all(_valid_column_path(path) for path in paths[3:])
    return False


def _valid_column_path(path: str, token: str | None = None) -> bool:
    if path.startswith("/column_mappings/"):
        return token is None or path == f"/column_mappings/{token}"
    prefix = "/column_policies/"
    if not path.startswith(prefix):
        return False
    remainder = path[len(prefix) :]
    try:
        name, leaf = remainder.rsplit("/", 1)
    except ValueError:
        return False
    return (
        bool(name)
        and (token is None or name == token)
        and leaf
        in {
            "type",
            "scale",
            "timezone",
            "normalize",
            "comparison",
            "tolerance",
        }
    )


def _valid_measure_path(path: str, token: str) -> bool:
    prefix = f"/measures/{token}/"
    return path.startswith(prefix) and path[len(prefix) :] in {"column", "comparison", "nulls", "operator", "tolerance"}


def _valid_reference_value(path: str, value: Any) -> bool:
    if path in {"/keys", "/group_by", "/policy/column_order"}:
        return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)
    if path in {"/identity/null_keys", "/identity/duplicates", "/policy/group_nulls"}:
        return value == "reject"
    if path in {"/policy/nulls_equal", "/scope/expected_empty"}:
        return type(value) is bool
    if path == "/policy/canonical_encoding":
        return value == "typed-length-prefixed-v1"
    if path in {"/scope/snapshot", "/scope/cutoff"}:
        return isinstance(value, str) and bool(value)
    if path == "/scope/filters":
        return isinstance(value, list) and all(isinstance(item, str) and item for item in value)
    if path == "/scope/completeness":
        return value == "full"
    if path.startswith("/column_mappings/"):
        return (
            isinstance(value, dict)
            and set(value) == {"baseline", "candidate"}
            and all(isinstance(item, str) and item for item in value.values())
        )
    leaf = path.rsplit("/", 1)[-1]
    if path.startswith("/column_policies/"):
        if leaf == "type":
            return value in {"string", "integer", "decimal", "float", "boolean", "date", "timestamp"}
        if leaf == "scale":
            return type(value) is int and value >= 0
        if leaf == "timezone":
            return value == "require-aware"
        if leaf == "normalize":
            return (
                isinstance(value, list)
                and len(value) == len(set(value))
                and all(item in {"trim", "casefold", "unicode_nfc"} for item in value)
            )
        if leaf == "comparison":
            return value in {"exact", "numeric"}
        if leaf == "tolerance":
            return _valid_tolerance(value)
    if path.startswith("/measures/"):
        if leaf == "column":
            return isinstance(value, str) and bool(value)
        if leaf == "comparison":
            return value in {"exact", "numeric"}
        if leaf == "nulls":
            return value in {"reject", "ignore"}
        if leaf == "operator":
            return value in {"count", "sum", "min", "max"}
        if leaf == "tolerance":
            return _valid_tolerance(value)
    return False


def _valid_tolerance(value: Any) -> bool:
    def scalar(item: Any) -> bool:
        if type(item) not in {str, int, float} or (type(item) is float and not math.isfinite(item)):
            return False
        try:
            decimal = Decimal(str(item))
        except InvalidOperation:
            return False
        return decimal.is_finite() and decimal >= 0

    return (
        isinstance(value, dict)
        and set(value) == {"formula", "absolute", "relative"}
        and value["formula"] == "symmetric-v1"
        and scalar(value["absolute"])
        and scalar(value["relative"])
    )
