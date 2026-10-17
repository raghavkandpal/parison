"""Deterministic, summary-safe discrepancy analysis."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .core import ParisonError
from .evidence import _verified_bundle, _write_once

_DOMAIN = b"parison:discrepancy-group:v1\0"
_KINDS = {"missing": 0, "field": 1, "measure": 2, "shape": 3}
_CLASSIFICATIONS = {
    "baseline_only": 0,
    "candidate_only": 1,
    "within_tolerance": 2,
    "different": 3,
    "baseline_surplus": 4,
    "candidate_surplus": 5,
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _group(descriptor: dict[str, str], count: int, source: str, references: list[str]) -> dict[str, Any]:
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
        descriptor.get("name", "").encode("utf-8"),
        group["group_id"],
    )


def _read_verified_run(directory: str | Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    path = Path(directory)
    manifest, before = _verified_bundle(path)
    if manifest.get("kind") is not None:
        raise ParisonError("discrepancy analysis requires an ordinary run bundle")
    try:
        result = json.loads((path / "result.json").read_text(encoding="utf-8"))
        recipe = json.loads((path / "effective-recipe.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read analysis inputs: {exc}") from exc
    _, after = _verified_bundle(path)
    if before != after:
        raise ParisonError("bundle changed while preparing analysis")
    policy = result.get("policy_sha256")
    if not isinstance(policy, str) or len(policy) != 64:
        raise ParisonError("run has no supported policy digest")
    return result, recipe, hashlib.sha256(before).hexdigest()


def _groups(result: dict[str, Any], recipe: dict[str, Any]) -> list[dict[str, Any]]:
    mode = recipe.get("comparison_mode")
    groups: list[dict[str, Any]] = []
    if result.get("schema_version") == 1 and mode == "keyed":
        counts = result.get("counts", {})
        groups.extend(
            _group(
                {"comparison_mode": mode, "kind": "missing", "classification": side},
                counts.get(side, 0),
                f"/counts/{side}",
                ["/keys", "/identity"],
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
                        {"comparison_mode": mode, "kind": "field", "classification": classification, "name": name},
                        result.get("field_counts", {}).get(name, {}).get(classification, 0),
                        f"/field_counts/{token}/{classification}",
                        [f"/columns/{token}"],
                    )
                )
    elif result.get("schema_version") == 2 and mode == "aggregate":
        for classification, source in (
            ("baseline_only", "baseline_only_groups"),
            ("candidate_only", "candidate_only_groups"),
        ):
            groups.append(
                _group(
                    {"comparison_mode": mode, "kind": "missing", "classification": classification},
                    result.get("counts", {}).get(source, 0),
                    f"/counts/{source}",
                    ["/group_by"],
                )
            )
        for name in sorted(recipe.get("measures", {}), key=lambda value: value.encode("utf-8")):
            token = _pointer_token(name)
            for classification in ("within_tolerance", "different"):
                groups.append(
                    _group(
                        {"comparison_mode": mode, "kind": "measure", "classification": classification, "name": name},
                        result.get("measure_counts", {}).get(name, {}).get(classification, 0),
                        f"/measure_counts/{token}/{classification}",
                        [f"/measures/{token}"],
                    )
                )
    elif result.get("schema_version") == 3 and mode == "multiset":
        for classification, source in (
            ("baseline_surplus", "baseline_surplus_shapes"),
            ("candidate_surplus", "candidate_surplus_shapes"),
        ):
            groups.append(
                _group(
                    {"comparison_mode": mode, "kind": "shape", "classification": classification},
                    result.get("counts", {}).get(source, 0),
                    f"/counts/{source}",
                    ["/columns"],
                )
            )
    else:
        raise ParisonError("run result and comparison mode are unsupported for analysis")
    if any(type(group["count"]) is not int or group["count"] < 0 for group in groups):
        raise ParisonError("run contains invalid discrepancy counts")
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
        "scope_references": ["/scope"],
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
        for index, (before, after) in enumerate(itertools.pairwise(counts)):
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
            transitions.append(
                {
                    "group_id": identifier,
                    "from_run": index,
                    "to_run": index + 1,
                    "before": before,
                    "after": after,
                    "delta": delta,
                    "status": status,
                }
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
                "population_count": groups[group_id]["count"],
                "published_sample_size": len(sample),
                "matched_size": len(matches),
                "returned_size": len(selected),
                "published_sample_complete": len(sample) == result["discrepancy_count"],
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
    content = (_canonical(drilldown) + b"\n").decode("utf-8")
    _write_once(Path(output), content, "cannot export discrepancy drill-down")
    return {"output": str(output), "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}


def _sample_matches(item: Any, descriptor: dict[str, str]) -> bool:
    if not isinstance(item, dict) or item.get("classification") != descriptor["classification"]:
        return False
    expected_kind = {"missing": {"record", "group"}, "field": {"field"}, "measure": {"measure"}, "shape": {None}}[
        descriptor["kind"]
    ]
    if item.get("kind") not in expected_kind:
        return False
    if "name" not in descriptor:
        return True
    return item.get("field", item.get("measure")) == descriptor["name"]


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
            "schema_version": 1,
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
        manifest = json.loads(manifest_bytes)
        analysis = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read analysis bundle: {exc}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    expected = {
        "schema_version": 1,
        "kind": "discrepancy-analysis",
        "complete": True,
        "sensitivity": "summary",
        "analysis_kind": analysis.get("kind"),
        "analysis_sha256": digest,
        "files": {"analysis.json": digest},
    }
    if (
        manifest != expected
        or payload != _canonical(analysis) + b"\n"
        or manifest_bytes != _canonical(manifest) + b"\n"
    ):
        raise ParisonError("analysis bundle failed canonical integrity verification")
    _validate_analysis(analysis)
    if manifest_path.read_bytes() != manifest_bytes or analysis_path.read_bytes() != payload:
        raise ParisonError("analysis bundle changed during verification")
    return manifest


def _validate_analysis(analysis: Any) -> None:
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
                {"comparison_mode", "kind", "classification"},
                {"comparison_mode", "kind", "classification", "name"},
            )
            or descriptor.get("comparison_mode") != analysis["comparison_mode"]
            or descriptor.get("kind") not in _KINDS
            or descriptor.get("classification") not in _CLASSIFICATIONS
            or ("name" in descriptor and (not isinstance(descriptor["name"], str) or not descriptor["name"]))
        ):
            raise ParisonError("analysis contains an invalid group descriptor")
        expected_id = hashlib.sha256(_DOMAIN + _canonical(descriptor)).hexdigest()
        expected_source, expected_references = _expected_group_metadata(descriptor)
        values = [group[value_key]] if value_key == "count" else group[value_key]
        if (
            group["group_id"] != expected_id
            or not isinstance(values, list)
            or not values
            or any(type(value) is not int or value < 0 for value in values)
            or group["count_source"] != expected_source
            or not isinstance(group["reason_codes"], list)
            or group["reason_codes"] != [f"{descriptor['kind']}.{descriptor['classification']}"]
            or group["policy_references"] != expected_references
        ):
            raise ParisonError("analysis contains invalid group evidence")
        identifiers.append(expected_id)
    if groups != sorted(groups, key=_group_sort_key) or len(set(identifiers)) != len(identifiers):
        raise ParisonError("analysis groups are not canonical")
    if analysis["kind"] == "run":
        if not _is_sha(analysis["bundle_sha256"]) or analysis["scope_references"] != ["/scope"]:
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
        for index, (before, after) in enumerate(itertools.pairwise(group["counts"])):
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
            expected_transitions.append(
                {
                    "group_id": group["group_id"],
                    "from_run": index,
                    "to_run": index + 1,
                    "before": before,
                    "after": after,
                    "delta": delta,
                    "status": status,
                }
            )
    if transitions != expected_transitions:
        raise ParisonError("series analysis transitions are not canonical")


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _expected_group_metadata(descriptor: dict[str, str]) -> tuple[str, list[str]]:
    mode, kind, classification = (
        descriptor["comparison_mode"],
        descriptor["kind"],
        descriptor["classification"],
    )
    name = descriptor.get("name")
    if mode == "keyed" and kind == "missing" and name is None and classification in {"baseline_only", "candidate_only"}:
        return f"/counts/{classification}", ["/keys", "/identity"]
    if mode == "keyed" and kind == "field" and name and classification in {"within_tolerance", "different"}:
        token = _pointer_token(name)
        return f"/field_counts/{token}/{classification}", [f"/columns/{token}"]
    if (
        mode == "aggregate"
        and kind == "missing"
        and name is None
        and classification in {"baseline_only", "candidate_only"}
    ):
        return f"/counts/{classification}_groups", ["/group_by"]
    if mode == "aggregate" and kind == "measure" and name and classification in {"within_tolerance", "different"}:
        token = _pointer_token(name)
        return f"/measure_counts/{token}/{classification}", [f"/measures/{token}"]
    if (
        mode == "multiset"
        and kind == "shape"
        and name is None
        and classification in {"baseline_surplus", "candidate_surplus"}
    ):
        return f"/counts/{classification}_shapes", ["/columns"]
    raise ParisonError("analysis contains an unsupported group descriptor")
