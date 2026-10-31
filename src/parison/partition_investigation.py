"""Bounded raw inspection of source-verified partition differences."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical
from .comparison import compare
from .core import ParisonError, _checked_policy_sha256
from .partition_discovery import (
    _bounded_bytes,
    _digest,
    _digest_text,
    _parse_json,
    _recipe,
    _route,
    _source,
    _verified_evidence,
)

_LIMIT_CAPS = {
    "max_cases_total": 10_000,
    "max_cases_per_partition": 1_000,
    "max_staged_bytes": 1_000_000_000,
    "max_output_bytes": 16_000_000,
}
_FILES = ("plan.json", "receipt.json", "cases.json", "summary.json")
_ALL_FILES = set(_FILES) | {"manifest.json"}


def validate_plan(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"investigation_plan_version", "discovery_manifest_sha256", "partition_indices", "limits"}
        or type(value["investigation_plan_version"]) is not int
        or value["investigation_plan_version"] != 1
        or not _digest_text(value["discovery_manifest_sha256"])
    ):
        raise ParisonError("invalid investigation plan")
    indices = value["partition_indices"]
    if (
        not isinstance(indices, list)
        or not 1 <= len(indices) <= 128
        or any(type(index) is not int or index < 0 for index in indices)
        or indices != sorted(set(indices))
    ):
        raise ParisonError("investigation partition indices must be strictly increasing")
    limits = value["limits"]
    if not isinstance(limits, dict) or set(limits) != set(_LIMIT_CAPS):
        raise ParisonError("invalid investigation limits")
    for name, cap in _LIMIT_CAPS.items():
        if type(limits[name]) is not int or not 0 < limits[name] <= cap:
            raise ParisonError(f"invalid investigation limit: {name}")
    return value


def _suspects(receipt: dict[str, Any]) -> set[int]:
    return {index for index, record in enumerate(receipt["partitions"]) if _population(record)}


def _population(record: dict[str, Any]) -> int:
    return (
        record["counts"]["baseline_only"]
        + record["counts"]["candidate_only"]
        + sum(fields["different"] + fields["within_tolerance"] for fields in record["field_counts"].values())
    )


def _summary(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "investigation_summary_version": 1,
        "kind": "selective-exact-investigation",
        "complete": receipt["complete"],
        "scope_complete": receipt["scope_complete"],
        "enumeration_complete": receipt["enumeration_complete"],
        "suspect_count": receipt["suspect_count"],
        "selected_count": len(receipt["selected"]),
        "population_count": receipt["population_count"],
        "returned_count": receipt["returned_count"],
        "discovery_manifest_sha256": receipt["discovery_manifest_sha256"],
        "policy_sha256": receipt["policy_sha256"],
        "input_sha256": {side: receipt["inputs"][side]["sha256"] for side in ("baseline", "candidate")},
    }


def _valid_raw_item(item: Any) -> bool:
    if (
        not isinstance(item, dict)
        or not isinstance(item.get("key"), list)
        or len(item["key"]) != 1
        or type(item["key"][0]) is not int
    ):
        return False
    if item.get("kind") == "record":
        return (
            set(item) == {"kind", "key", "classification"}
            and type(item["classification"]) is str
            and item["classification"]
            in {
                "baseline_only",
                "candidate_only",
            }
        )
    if item.get("kind") == "field":
        return (
            set(item) == {"kind", "key", "field", "baseline", "candidate", "classification", "delta", "allowance"}
            and isinstance(item["field"], str)
            and bool(item["field"])
            and type(item["classification"]) is str
            and item["classification"] in {"within_tolerance", "different"}
            and type(item["baseline"]) in {type(None), bool, int, float, str}
            and type(item["candidate"]) in {type(None), bool, int, float, str}
            and (item["delta"] is None or isinstance(item["delta"], str))
            and (item["allowance"] is None or isinstance(item["allowance"], str))
        )
    return False


def _compute(
    plan: dict[str, Any],
    discovery: str | Path,
    recipe_path: str | Path,
    baseline: str | Path,
    candidate: str | Path,
    workspace: Path,
) -> dict[str, Any]:
    discovery_plan, discovery_receipt, _, discovery_sha = _verified_evidence(
        discovery, recipe_path, baseline, candidate
    )
    if discovery_plan["partition_plan_version"] != 1:
        raise ParisonError("investigation-v1 requires range-v1 discovery")
    if plan["discovery_manifest_sha256"] != discovery_sha or not discovery_receipt["complete"]:
        raise ParisonError("investigation requires complete source-backed discovery")
    selected = set(plan["partition_indices"])
    suspects = _suspects(discovery_receipt)
    if not selected <= suspects:
        raise ParisonError("investigation selection includes a non-suspect partition")
    recipe, policy_sha256 = _recipe(Path(recipe_path))
    if policy_sha256 != discovery_receipt["policy_sha256"]:
        raise ParisonError("investigation policy changed")
    sources = {}
    identities = {}
    for side, source_path in (("baseline", baseline), ("candidate", candidate)):
        sources[side], identities[side] = _source(source_path, discovery_plan["limits"]["max_input_bytes"])
    if identities != discovery_receipt["inputs"]:
        raise ParisonError("investigation source identities changed")
    records, rows, staged = _route(
        discovery_plan, recipe, sources, workspace, selected, plan["limits"]["max_staged_bytes"]
    )
    if rows != discovery_receipt["route_rows"]:
        raise ParisonError("investigation source row totals changed")
    for index in selected:
        for side in ("baseline", "candidate"):
            if records[index][side] != discovery_receipt["partitions"][index][side]:
                raise ParisonError("investigation selected partition changed")
    raw_recipe = {**recipe, "output": {"sensitivity": "raw"}, "scope": {**recipe["scope"], "expected_empty": True}}
    raw_policy_sha256 = _checked_policy_sha256(raw_recipe, None)
    raw_path = workspace / "raw-recipe.json"
    raw_path.write_bytes(_canonical(raw_recipe))
    remaining = plan["limits"]["max_cases_total"]
    items: list[dict[str, Any]] = []
    selected_records: list[dict[str, Any]] = []
    population = 0
    item_bytes = 0
    for index in plan["partition_indices"]:
        result = compare(
            raw_path,
            workspace / f"baseline-{index}.csv",
            workspace / f"candidate-{index}.csv",
            sample_limit=min(remaining, plan["limits"]["max_cases_per_partition"]),
            max_rows=discovery_plan["limits"]["max_rows_per_partition_side"],
            max_input_bytes=discovery_plan["limits"]["max_staged_bytes"],
        )
        expected = discovery_receipt["partitions"][index]
        if (
            not result["complete"]
            or result["counts"] != expected["counts"]
            or result["field_counts"] != expected["field_counts"]
            or result["discrepancy_count"] != _population(expected)
        ):
            raise ParisonError("investigation exact partition differs from discovery")
        samples = [{"partition_index": index, "item": item} for item in result["discrepancy_sample"]]
        for item in samples:
            item_bytes += len(_canonical(item))
            if item_bytes > plan["limits"]["max_output_bytes"]:
                raise ParisonError("investigation raw output exceeds byte limit")
        items.extend(samples)
        remaining -= len(samples)
        population += result["discrepancy_count"]
        selected_records.append(
            {
                "partition_index": index,
                "upper": expected["upper"],
                "counts": result["counts"],
                "field_counts": result["field_counts"],
                "population_count": result["discrepancy_count"],
                "returned_count": len(samples),
                "baseline": records[index]["baseline"],
                "candidate": records[index]["candidate"],
            }
        )
    if any(
        _digest(workspace / f"{side}-{index}.csv") != records[index][side]["sha256"]
        for index in selected
        for side in ("baseline", "candidate")
    ):
        raise ParisonError("investigation staging changed during comparison")
    if any(_digest(sources[side]) != identities[side]["sha256"] for side in sources):
        raise ParisonError("investigation source changed during comparison")
    _, after_receipt, _, after_sha = _verified_evidence(discovery)
    if after_sha != discovery_sha or after_receipt != discovery_receipt:
        raise ParisonError("investigation discovery changed during comparison")
    scope_complete = selected == suspects
    enumeration_complete = len(items) == population
    receipt = {
        "investigation_receipt_version": 1,
        "kind": "selective-exact-investigation",
        "derivation": "raw-disclosure-v1",
        "sensitivity": "raw",
        "investigation_plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
        "discovery_manifest_sha256": discovery_sha,
        "policy_sha256": policy_sha256,
        "raw_policy_sha256": raw_policy_sha256,
        "inputs": identities,
        "suspect_count": len(suspects),
        "selected": selected_records,
        "population_count": population,
        "returned_count": len(items),
        "staged_bytes": staged,
        "scope_complete": scope_complete,
        "enumeration_complete": enumeration_complete,
        "complete": scope_complete and enumeration_complete,
    }
    return {
        "plan.json": plan,
        "receipt.json": receipt,
        "cases.json": {"investigation_cases_version": 1, "sensitivity": "raw", "items": items},
        "summary.json": _summary(receipt),
    }


def _read_artifact(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    if root.is_symlink() or not root.is_dir() or {path.name for path in root.iterdir()} != _ALL_FILES:
        raise ParisonError("invalid investigation evidence directory")
    manifest_bytes = _bounded_bytes(root / "manifest.json", 256 * 1024)
    manifest = _parse_json(manifest_bytes)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"investigation_manifest_version", "files"}
        or type(manifest["investigation_manifest_version"]) is not int
        or manifest["investigation_manifest_version"] != 1
        or not isinstance(manifest["files"], dict)
        or set(manifest["files"]) != set(_FILES)
    ):
        raise ParisonError("invalid investigation manifest")
    if manifest_bytes != _canonical(manifest) + b"\n":
        raise ParisonError("investigation manifest is not canonical")
    values = {}
    total_bytes = len(manifest_bytes)
    for name in _FILES:
        digest = manifest["files"][name]
        if not _digest_text(digest):
            raise ParisonError("invalid investigation file digest")
        data = _bounded_bytes(root / name, 16_000_000 if name == "cases.json" else 8_000_000)
        total_bytes += len(data)
        if hashlib.sha256(data).hexdigest() != digest:
            raise ParisonError("investigation file digest mismatch")
        value = _parse_json(data)
        if data != _canonical(value) + b"\n":
            raise ParisonError("investigation evidence is not canonical")
        values[name] = value
    values["manifest.json"] = manifest
    values["_manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    values["_total_bytes"] = total_bytes
    if not isinstance(values["receipt.json"], dict) or not isinstance(values["cases.json"], dict):
        raise ParisonError("invalid investigation evidence payload")
    return values


def investigate(
    plan_path: str | Path,
    discovery: str | Path,
    recipe: str | Path,
    baseline: str | Path,
    candidate: str | Path,
    output: str | Path,
) -> dict[str, Any]:
    plan = validate_plan(_parse_json(_bounded_bytes(Path(plan_path), 256 * 1024)))
    target = Path(output)
    check_output_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise ParisonError("investigation output already exists")
    stage: Path | None = None
    try:
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        workspace = stage / "temporary"
        workspace.mkdir(mode=0o700)
        values = _compute(plan, discovery, recipe, baseline, candidate, workspace)
        shutil.rmtree(workspace)
        for name, value in values.items():
            (stage / name).write_bytes(_canonical(value) + b"\n")
        manifest = {"investigation_manifest_version": 1, "files": {name: _digest(stage / name) for name in _FILES}}
        (stage / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
        if sum((stage / name).stat().st_size for name in _ALL_FILES) > plan["limits"]["max_output_bytes"]:
            raise ParisonError("investigation output exceeds byte limit")
        rename_no_replace(stage, target)
        return values["summary.json"]
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_investigation(
    directory: str | Path,
    discovery: str | Path,
    recipe: str | Path | None = None,
    baseline: str | Path | None = None,
    candidate: str | Path | None = None,
) -> dict[str, Any]:
    values = _read_artifact(directory)
    plan = validate_plan(values["plan.json"])
    discovery_plan, discovery_receipt, _, discovery_sha = _verified_evidence(discovery)
    if discovery_plan["partition_plan_version"] != 1:
        raise ParisonError("investigation-v1 requires range-v1 discovery")
    receipt = values["receipt.json"]
    cases = values["cases.json"]
    summary = values["summary.json"]
    if (
        plan["discovery_manifest_sha256"] != discovery_sha
        or not isinstance(receipt, dict)
        or set(receipt)
        != {
            "investigation_receipt_version",
            "kind",
            "derivation",
            "sensitivity",
            "investigation_plan_sha256",
            "discovery_manifest_sha256",
            "policy_sha256",
            "raw_policy_sha256",
            "inputs",
            "suspect_count",
            "selected",
            "population_count",
            "returned_count",
            "staged_bytes",
            "scope_complete",
            "enumeration_complete",
            "complete",
        }
        or not isinstance(cases, dict)
        or set(cases) != {"investigation_cases_version", "sensitivity", "items"}
        or type(cases["investigation_cases_version"]) is not int
        or cases["investigation_cases_version"] != 1
        or cases["sensitivity"] != "raw"
        or not isinstance(cases["items"], list)
        or receipt.get("investigation_plan_sha256") != hashlib.sha256(_canonical(plan)).hexdigest()
        or receipt.get("discovery_manifest_sha256") != discovery_sha
        or not discovery_receipt["complete"]
    ):
        raise ParisonError("invalid investigation evidence binding")
    suspects = _suspects(discovery_receipt)
    indices = plan["partition_indices"]
    if (
        not set(indices) <= suspects
        or not isinstance(receipt.get("selected"), list)
        or len(receipt["selected"]) != len(indices)
    ):
        raise ParisonError("invalid investigation selection")
    for index, record in zip(indices, receipt["selected"], strict=True):
        expected = discovery_receipt["partitions"][index]
        if (
            not isinstance(record, dict)
            or set(record)
            != {
                "partition_index",
                "upper",
                "counts",
                "field_counts",
                "population_count",
                "returned_count",
                "baseline",
                "candidate",
            }
            or type(record["partition_index"]) is not int
            or record["partition_index"] != index
            or type(record["upper"]) is not type(expected["upper"])
            or record["upper"] != expected["upper"]
            or any(record[name] != expected[name] for name in ("counts", "field_counts", "baseline", "candidate"))
            or type(record["population_count"]) is not int
            or record["population_count"] != _population(expected)
            or type(record["returned_count"]) is not int
            or record["returned_count"] < 0
            or record["returned_count"] > record["population_count"]
            or record["returned_count"] > plan["limits"]["max_cases_per_partition"]
        ):
            raise ParisonError("invalid investigation selected record")
    if (
        not isinstance(receipt.get("inputs"), dict)
        or receipt["inputs"] != discovery_receipt["inputs"]
        or not _digest_text(receipt.get("policy_sha256"))
        or receipt["policy_sha256"] != discovery_receipt["policy_sha256"]
        or not _digest_text(receipt.get("raw_policy_sha256"))
        or receipt.get("derivation") != "raw-disclosure-v1"
        or receipt.get("kind") != "selective-exact-investigation"
        or receipt.get("sensitivity") != "raw"
        or type(receipt.get("investigation_receipt_version")) is not int
        or receipt["investigation_receipt_version"] != 1
    ):
        raise ParisonError("invalid investigation receipt")
    population = sum(record["population_count"] for record in receipt["selected"])
    returned = sum(record["returned_count"] for record in receipt["selected"])
    staged = sum(record[side]["bytes"] for record in receipt["selected"] for side in ("baseline", "candidate"))
    if (
        type(receipt.get("population_count")) is not int
        or receipt["population_count"] != population
        or type(receipt.get("returned_count")) is not int
        or receipt["returned_count"] != returned
        or returned != len(cases["items"])
        or returned > plan["limits"]["max_cases_total"]
        or values["_total_bytes"] > plan["limits"]["max_output_bytes"]
        or type(receipt.get("staged_bytes")) is not int
        or receipt["staged_bytes"] != staged
        or staged > plan["limits"]["max_staged_bytes"]
        or type(receipt.get("suspect_count")) is not int
        or receipt["suspect_count"] != len(suspects)
        or type(receipt.get("scope_complete")) is not bool
        or receipt["scope_complete"] != (set(indices) == suspects)
        or type(receipt.get("enumeration_complete")) is not bool
        or receipt["enumeration_complete"] != (returned == population)
        or type(receipt.get("complete")) is not bool
        or receipt["complete"] != (receipt["scope_complete"] and receipt["enumeration_complete"])
        or summary != _summary(receipt)
    ):
        raise ParisonError("investigation arithmetic mismatch")
    if any(
        not isinstance(item, dict)
        or set(item) != {"partition_index", "item"}
        or type(item["partition_index"]) is not int
        or item["partition_index"] not in indices
        or not _valid_raw_item(item["item"])
        for item in cases["items"]
    ):
        raise ParisonError("invalid investigation case item")
    item_indices = [item["partition_index"] for item in cases["items"]]
    if item_indices != sorted(item_indices) or any(
        item_indices.count(record["partition_index"]) != record["returned_count"] for record in receipt["selected"]
    ):
        raise ParisonError("investigation case ordering or count mismatch")
    if recipe is None and baseline is None and candidate is None:
        if (
            _read_artifact(directory)["_manifest_sha256"] != values["_manifest_sha256"]
            or _verified_evidence(discovery)[3] != discovery_sha
        ):
            raise ParisonError("investigation evidence changed during verification")
        return {**summary, "verification": "integrity-only"}
    if recipe is None or baseline is None or candidate is None:
        raise ParisonError("source-backed investigation verification requires recipe and both inputs")
    with tempfile.TemporaryDirectory(prefix="parison-investigation-verify-") as temp:
        fresh = _compute(plan, discovery, recipe, baseline, candidate, Path(temp))
    if any(fresh[name] != values[name] for name in _FILES):
        raise ParisonError("investigation source-backed verification mismatch")
    if _read_artifact(directory)["_manifest_sha256"] != values["_manifest_sha256"]:
        raise ParisonError("investigation evidence changed during verification")
    return {**summary, "verification": "exact-source-backed"}
