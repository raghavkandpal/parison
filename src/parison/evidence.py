"""Evidence publication, verification, inspection, and derived reports."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .core import (
    OUTCOME_CODES,
    ParisonError,
    _digest,
    _portable_identifier,
    _report,
    _runtime_info,
    select_suite_cases,
)


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
