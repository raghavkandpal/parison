from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sqlite3
import stat
import sys
import unicodedata
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .core import ParisonError, _write_once


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROLES = {"baseline", "candidate", "receipt", "supporting"}
_FORMATS = {"csv", "tsv", "json", "jsonl", "parquet", "sqlite"}
_RUNTIME_FIELDS = (
    "parison_version", "python_implementation", "python_version", "os_family",
    "architecture", "sqlite_version", "parquet_reader",
)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ParisonError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ParisonError(f"{label} must be a JSON object")
    return value


def _digest(value: Any, domain: bytes) -> str:
    return hashlib.sha256(domain + json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ParisonError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ParisonError(f"{label} must be a portable identifier")
    return value


def _resource_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value or ":" in value.split("/", 1)[0]:
        raise ParisonError("resource path must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or str(path) != value:
        raise ParisonError("resource path must be a normalized relative POSIX path")
    return value


def normalize_dataset_manifest(value: Any) -> dict[str, Any]:
    required = {"manifest_version", "collection_id", "policy", "resources"}
    if not isinstance(value, dict) or set(value) != required or value.get("manifest_version") != 1:
        raise ParisonError("dataset manifest must contain exactly manifest_version 1, collection_id, policy and resources")
    policy = value["policy"]
    if not isinstance(policy, dict) or set(policy) != {"kind", "sha256"} or policy.get("kind") not in {"suite", "reconciliation"}:
        raise ParisonError("manifest policy must contain kind suite/reconciliation and sha256")
    normalized = []
    pairs, paths, collisions = set(), set(), set()
    resources = value["resources"]
    if not isinstance(resources, list) or not resources or len(resources) > 10_000:
        raise ParisonError("manifest resources must contain 1 to 10000 entries")
    for item in resources:
        allowed = {"id", "role", "format", "path", "bytes", "sha256", "schema_sha256"}
        if not isinstance(item, dict) or set(item) - allowed or not {"id", "role", "format", "path", "bytes", "sha256"} <= set(item):
            raise ParisonError("manifest resource has invalid fields")
        identifier = _identifier(item["id"], "resource id")
        role, format_name, path = item["role"], item["format"], _resource_path(item["path"])
        if role not in _ROLES or format_name not in _FORMATS:
            raise ParisonError("manifest resource has unsupported role or format")
        if format_name == "json" and role not in {"receipt", "supporting"}:
            raise ParisonError("json resources must have receipt or supporting role")
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            raise ParisonError("resource bytes must be a nonnegative integer")
        pair, collision = (identifier, role), unicodedata.normalize("NFC", path).casefold()
        if pair in pairs or path in paths or collision in collisions:
            raise ParisonError("manifest resources contain duplicate or non-portable identities")
        pairs.add(pair); paths.add(path); collisions.add(collision)
        resource = {"id": identifier, "role": role, "format": format_name, "path": path, "bytes": item["bytes"], "sha256": _sha256(item["sha256"], "resource sha256")}
        if "schema_sha256" in item:
            resource["schema_sha256"] = _sha256(item["schema_sha256"], "schema_sha256")
        normalized.append(resource)
    return {
        "manifest_version": 1,
        "collection_id": _identifier(value["collection_id"], "collection_id"),
        "policy": {"kind": policy["kind"], "sha256": _sha256(policy["sha256"], "policy sha256")},
        "resources": sorted(normalized, key=lambda item: (item["id"], item["role"], item["path"])),
    }


def canonical_dataset_manifest_bytes(value: Any) -> bytes:
    return json.dumps(normalize_dataset_manifest(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def explain_dataset_manifest(path: str | Path) -> dict[str, Any]:
    value = normalize_dataset_manifest(_read_json(path, "dataset manifest"))
    return {**value, "manifest_sha256": _digest(value, b"parison:dataset-manifest-v1\0")}


def _policy_fingerprint(kind: str, path: str | Path) -> str:
    if kind == "reconciliation":
        from .reconciliation import explain_reconciliation
        return explain_reconciliation(path)["reconciliation_sha256"]
    from .core import load_suite
    suite = load_suite(path)
    if suite["suite_version"] != 2:
        raise ParisonError("dataset manifests require suite version 2 policy binding")
    return suite["suite_policy_sha256"]


def _open_resource(root: Path, relative: str):
    current = root
    if root.is_symlink() or not root.is_dir():
        raise ParisonError("manifest root must be an existing non-symlink directory")
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ParisonError("declared resource is missing") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ParisonError("resource path contains an unsafe component")
    path = current / PurePosixPath(relative).name
    try:
        path_mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ParisonError("cannot inspect declared resource") from exc
    if stat.S_ISLNK(path_mode) or not stat.S_ISREG(path_mode):
        raise ParisonError("declared resource must be a regular non-symlink file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ParisonError("cannot safely open declared resource") from exc
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        os.close(descriptor)
        raise ParisonError("declared resource must be a regular file")
    return path, descriptor, before


def _identity(root: Path, relative: str, format_name: str) -> tuple[int, str, tuple[int, int]] | None:
    opened = _open_resource(root, relative)
    if opened is None:
        return None
    path, descriptor, before = opened
    if format_name == "sqlite" and any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal", "-shm")):
        os.close(descriptor)
        raise ParisonError("SQLite resource has ambiguous journal state")
    digest, size = hashlib.sha256(), 0
    try:
        with os.fdopen(descriptor, "rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk); size += len(chunk)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise ParisonError("cannot hash declared resource") from exc
    stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if not stable or size != after.st_size:
        raise ParisonError("resource changed during read")
    return size, digest.hexdigest(), (after.st_dev, after.st_ino)


def create_dataset_manifest(root: str | Path, collection_id: str, policy_kind: str, policy_sha256: str, resources: list[tuple[str, str, str, str]], output: str | Path, policy_path: str | Path | None = None) -> dict[str, Any]:
    if policy_path is not None and _policy_fingerprint(policy_kind, policy_path) != policy_sha256:
        raise ParisonError("declared policy SHA-256 does not match the supplied policy")
    root_path, items, identities = Path(root), [], set()
    for identifier, role, format_name, relative in resources:
        relative = _resource_path(relative)
        identity = _identity(root_path, relative, format_name)
        if identity is None:
            raise ParisonError("declared resource is missing")
        size, digest, file_identity = identity
        if file_identity in identities:
            raise ParisonError("manifest resources contain hard-link aliases")
        identities.add(file_identity)
        items.append({"id": identifier, "role": role, "format": format_name, "path": relative, "bytes": size, "sha256": digest})
    value = normalize_dataset_manifest({"manifest_version": 1, "collection_id": collection_id, "policy": {"kind": policy_kind, "sha256": policy_sha256}, "resources": items})
    _write_once(Path(output), json.dumps(value, indent=2, sort_keys=True) + "\n", "cannot publish dataset manifest")
    return {**value, "manifest_sha256": _digest(value, b"parison:dataset-manifest-v1\0")}


def verify_dataset_manifest(manifest_path: str | Path, root: str | Path, summary: bool = False, policy_path: str | Path | None = None) -> dict[str, Any]:
    manifest = explain_dataset_manifest(manifest_path)
    if policy_path is not None and _policy_fingerprint(manifest["policy"]["kind"], policy_path) != manifest["policy"]["sha256"]:
        raise ParisonError("manifest policy SHA-256 does not match the supplied policy")
    counts = {"declared": len(manifest["resources"]), "matched": 0, "missing": 0, "size_mismatch": 0, "digest_mismatch": 0}
    reasons, details, identities = set(), [], set()
    for resource in manifest["resources"]:
        identity = _identity(Path(root), resource["path"], resource["format"])
        status = "matched"
        if identity is None:
            status = "missing"; counts["missing"] += 1; reasons.add("resource-missing")
        else:
            size, digest, file_identity = identity
            if file_identity in identities:
                raise ParisonError("manifest resources contain hard-link aliases")
            identities.add(file_identity)
            if size != resource["bytes"]:
                status = "size-mismatch"; counts["size_mismatch"] += 1; reasons.add("resource-size-mismatch")
            elif digest != resource["sha256"]:
                status = "digest-mismatch"; counts["digest_mismatch"] += 1; reasons.add("resource-digest-mismatch")
            else:
                counts["matched"] += 1
        if not summary:
            details.append({"id": resource["id"], "role": resource["role"], "format": resource["format"], "status": status})
    outcome = "PASS" if counts["matched"] == counts["declared"] else "FAIL"
    result = {"manifest_result_version": 1, "outcome": outcome, "complete": True, "manifest_sha256": manifest["manifest_sha256"], "policy": manifest["policy"], "counts": counts, "reason_codes": sorted(reasons)}
    if not summary:
        result["resources"] = details
    return result


def normalize_reproducibility_diagnostic(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"diagnostic_version", "manifest_sha256", "runtime", "observations"} or value.get("diagnostic_version") != 1:
        raise ParisonError("reproducibility diagnostic has invalid fields or version")
    runtime = value["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != set(_RUNTIME_FIELDS):
        raise ParisonError("reproducibility diagnostic runtime fields are invalid")
    for key in _RUNTIME_FIELDS[:-1]:
        if not isinstance(runtime[key], str) or not runtime[key]:
            raise ParisonError(f"diagnostic runtime {key} must be a non-empty string")
    reader = runtime["parquet_reader"]
    if reader is not None and (not isinstance(reader, dict) or set(reader) != {"distribution", "version"} or not all(isinstance(item, str) and item for item in reader.values())):
        raise ParisonError("parquet_reader must be null or contain distribution and version")
    observations = value["observations"]
    if not isinstance(observations, list) or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in observations) or observations != sorted(set(observations)):
        raise ParisonError("diagnostic observations must be sorted unique reason codes")
    return {"diagnostic_version": 1, "manifest_sha256": _sha256(value["manifest_sha256"], "manifest_sha256"), "runtime": {name: runtime[name] for name in _RUNTIME_FIELDS}, "observations": observations}


def canonical_reproducibility_diagnostic_bytes(value: Any) -> bytes:
    return json.dumps(normalize_reproducibility_diagnostic(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def capture_reproducibility_diagnostic(manifest_path: str | Path, output: str | Path) -> dict[str, Any]:
    manifest = explain_dataset_manifest(manifest_path)
    reader = None
    if any(item["format"] == "parquet" for item in manifest["resources"]):
        try:
            reader = {"distribution": "polars", "version": metadata.version("polars")}
        except metadata.PackageNotFoundError:
            reader = None
    runtime = {
        "parison_version": __version__,
        "python_implementation": sys.implementation.name,
        "python_version": platform.python_version(),
        "os_family": platform.system().lower(),
        "architecture": platform.machine().lower() or "unknown",
        "sqlite_version": sqlite3.sqlite_version,
        "parquet_reader": reader,
    }
    value = normalize_reproducibility_diagnostic({"diagnostic_version": 1, "manifest_sha256": manifest["manifest_sha256"], "runtime": runtime, "observations": []})
    _write_once(Path(output), json.dumps(value, indent=2, sort_keys=False) + "\n", "cannot publish reproducibility diagnostic")
    return {**value, "diagnostic_sha256": _digest(value, b"parison:reproducibility-diagnostic-v1\0")}


def diff_reproducibility_diagnostics(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    left = normalize_reproducibility_diagnostic(_read_json(left_path, "left reproducibility diagnostic"))
    right = normalize_reproducibility_diagnostic(_read_json(right_path, "right reproducibility diagnostic"))
    if left["manifest_sha256"] != right["manifest_sha256"]:
        raise ParisonError("reproducibility diagnostics bind different manifests")
    fields = []
    for name in _RUNTIME_FIELDS:
        left_value, right_value = left["runtime"][name], right["runtime"][name]
        status = "same" if left_value == right_value else "missing-left" if left_value is None else "missing-right" if right_value is None else "different"
        fields.append({"field": name, "status": status})
    return {"diagnostic_diff_version": 1, "outcome": "INFORMATIONAL", "manifest_sha256": left["manifest_sha256"], "fields": fields, "observation_status": "same" if left["observations"] == right["observations"] else "different"}
