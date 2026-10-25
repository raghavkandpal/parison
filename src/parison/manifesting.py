from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
import unicodedata
from importlib import metadata
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlencode

from . import __version__
from ._safe_fs import check_output_parent as _check_output_parent
from ._safe_fs import rename_no_replace as _rename_no_replace
from .core import ParisonError, _write_once
from .core import _digest as _file_digest

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ROLES = {"baseline", "candidate", "receipt", "supporting"}
_FORMATS = {"csv", "tsv", "json", "jsonl", "parquet", "sqlite"}
_OBSERVATIONS = {"parquet-writer-differs", "runtime-version-differs", "semantic-pass-byte-identity-differs"}
_RUNTIME_FIELDS = (
    "parison_version",
    "python_implementation",
    "python_version",
    "os_family",
    "architecture",
    "sqlite_version",
    "parquet_reader",
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
    return hashlib.sha256(
        domain + json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


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


def _scope_path(value: Any) -> str:
    if value == ".":
        return value
    return _resource_path(value)


def normalize_dataset_manifest(value: Any) -> dict[str, Any]:
    required = {"manifest_version", "collection_id", "policy", "closed_scopes", "resources"}
    if not isinstance(value, dict) or set(value) != required or value.get("manifest_version") != 1:
        raise ParisonError(
            "dataset manifest must contain exactly manifest_version 1, collection_id, policy, closed_scopes and resources"
        )
    policy = value["policy"]
    if (
        not isinstance(policy, dict)
        or set(policy) != {"kind", "sha256"}
        or policy.get("kind") not in {"suite", "reconciliation"}
    ):
        raise ParisonError("manifest policy must contain kind suite/reconciliation and sha256")
    normalized = []
    pairs, paths, collisions = set(), set(), set()
    resources = value["resources"]
    if not isinstance(resources, list) or not resources or len(resources) > 10_000:
        raise ParisonError("manifest resources must contain 1 to 10000 entries")
    for item in resources:
        allowed = {"id", "role", "format", "path", "bytes", "sha256", "schema_sha256"}
        if (
            not isinstance(item, dict)
            or set(item) - allowed
            or not {"id", "role", "format", "path", "bytes", "sha256"} <= set(item)
        ):
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
        pairs.add(pair)
        paths.add(path)
        collisions.add(collision)
        resource = {
            "id": identifier,
            "role": role,
            "format": format_name,
            "path": path,
            "bytes": item["bytes"],
            "sha256": _sha256(item["sha256"], "resource sha256"),
        }
        if "schema_sha256" in item:
            resource["schema_sha256"] = _sha256(item["schema_sha256"], "schema_sha256")
        normalized.append(resource)
    scopes = value["closed_scopes"]
    if not isinstance(scopes, list) or len(scopes) > 100:
        raise ParisonError("closed_scopes must be an array of at most 100 reviewed directories")
    normalized_scopes = sorted(_scope_path(item) for item in scopes)
    scope_collisions = [unicodedata.normalize("NFC", item).casefold() for item in normalized_scopes]
    if len(scope_collisions) != len(set(scope_collisions)) or any(
        left != right and (left == "." or right.startswith(left + "/"))
        for left in scope_collisions
        for right in scope_collisions
    ):
        raise ParisonError("closed_scopes must be unique and non-overlapping")
    if normalized_scopes and any(
        not any(scope == "." or item["path"].startswith(scope + "/") for scope in normalized_scopes)
        for item in normalized
    ):
        raise ParisonError("every resource must be inside a declared closed scope")
    return {
        "manifest_version": 1,
        "collection_id": _identifier(value["collection_id"], "collection_id"),
        "policy": {"kind": policy["kind"], "sha256": _sha256(policy["sha256"], "policy sha256")},
        "closed_scopes": normalized_scopes,
        "resources": sorted(normalized, key=lambda item: (item["id"], item["role"], item["path"])),
    }


def canonical_dataset_manifest_bytes(value: Any) -> bytes:
    return json.dumps(
        normalize_dataset_manifest(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _closed_object(value: Any, fields: str, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ParisonError(f"{label} has invalid fields")
    return value


def _portable_binding_source(source: Any, source_kind: Any) -> tuple[str, str, dict[str, Any]]:
    from .inputs import _source_selection

    if not isinstance(source, str) or "\0" in source or not isinstance(source_kind, str):
        raise ParisonError("binding source must be an explicit portable locator")
    selection = _source_selection(source, source_kind)
    selection = _normalize_binding_selection(selection, source_kind)
    prefix = source.split(":", 1)[0]
    if prefix in {"sqlite", "xlsx", "json", "xml"}:
        locator = source[len(prefix) + 1 :]
        path = locator.split("#", 1)[0] if prefix == "json" else locator.rsplit("#", 1)[0]
    else:
        path = source
    _resource_path(path)
    try:
        source.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ParisonError("binding source must be valid UTF-8") from exc
    return source, path, selection


def normalize_dataset_manifest_v2(value: Any) -> dict[str, Any]:
    """Normalize declared identity without opening source files or executing policy."""
    value = _closed_object(value, "manifest_version collection_id policy closed_scopes files bindings", "manifest v2")
    if type(value["manifest_version"]) is not int or value["manifest_version"] != 2:
        raise ParisonError("dataset manifest version must be 2")
    policy = _closed_object(value["policy"], "kind sha256", "manifest policy")
    if policy["kind"] not in ("suite", "reconciliation"):
        raise ParisonError("manifest policy kind must be suite or reconciliation")
    policy = {"kind": policy["kind"], "sha256": _sha256(policy["sha256"], "policy sha256")}
    inventory = value["files"]
    if not isinstance(inventory, list) or not 1 <= len(inventory) <= 10_000:
        raise ParisonError("manifest files must contain 1 to 10000 entries")
    files, collisions = {}, set()
    for item in inventory:
        item = _closed_object(item, "path bytes sha256", "manifest file")
        path = _resource_path(item["path"])
        try:
            path.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ParisonError("inventory paths must be valid UTF-8") from exc
        collision = unicodedata.normalize("NFC", path).casefold()
        if collision in collisions:
            raise ParisonError("manifest files contain duplicate or non-portable paths")
        collisions.add(collision)
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            raise ParisonError("file bytes must be a nonnegative integer")
        files[path] = {"path": path, "bytes": item["bytes"], "sha256": _sha256(item["sha256"], "file sha256")}
    if any(str(parent) in files for path in files for parent in PurePosixPath(path).parents):
        raise ParisonError("inventoried files cannot also be parent directories")
    scopes = value["closed_scopes"]
    if not isinstance(scopes, list) or len(scopes) > 100:
        raise ParisonError("closed_scopes must contain at most 100 entries")
    scopes = sorted(_scope_path(item) for item in scopes)
    try:
        for scope in scopes:
            scope.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ParisonError("closed scopes must be valid UTF-8") from exc
    folded = [unicodedata.normalize("NFC", item).casefold() for item in scopes]
    if len(set(folded)) != len(folded) or any(
        left != right and (left == "." or right.startswith(left + "/")) for left in folded for right in folded
    ):
        raise ParisonError("closed_scopes must be unique and non-overlapping")
    if scopes and any(not any(scope == "." or path.startswith(scope + "/") for scope in scopes) for path in files):
        raise ParisonError("every file must be inside a declared closed scope")
    bindings = value["bindings"]
    if not isinstance(bindings, list) or not 1 <= len(bindings) <= 10_000:
        raise ParisonError("manifest bindings must contain 1 to 10000 entries")
    normalized, pairs = [], set()
    for item in bindings:
        item = _closed_object(item, "id role source_kind source members source_sha256 policy_sha256", "binding")
        identifier = _identifier(item["id"], "binding id")
        role = item["role"]
        if role not in ("baseline", "candidate"):
            raise ParisonError("binding role must be baseline or candidate")
        pair = identifier, role
        if pair in pairs:
            raise ParisonError("duplicate logical binding")
        pairs.add(pair)
        source, path, _ = _portable_binding_source(item["source"], item["source_kind"])
        members = item["members"]
        if not isinstance(members, list) or not 1 <= len(members) <= 10_000:
            raise ParisonError("binding members must contain 1 to 10000 entries")
        members = [_resource_path(member) for member in members]
        if len(set(members)) != len(members) or any(member not in files for member in members):
            raise ParisonError("binding members must reference unique inventoried files")
        if item["source_kind"] == "file":
            if members != [path]:
                raise ParisonError("file binding must reference its one physical file")
            digest = files[path]["sha256"]
        else:
            from .inputs import _file_format

            if any(
                PurePosixPath(member).parent.as_posix() != path or PurePosixPath(member).name.startswith(".")
                for member in members
            ):
                raise ParisonError("partition members must be visible immediate children")
            formats = {_file_format(Path(member)) for member in members}
            if None in formats or len(formats) != 1 or formats == {"xlsx"}:
                raise ParisonError("partition members must use one released supported format")
            ordered = sorted(members, key=lambda member: PurePosixPath(member).name.encode("utf-8"))
            if members != ordered:
                raise ParisonError("partition members must be in released basename order")
            digest = hashlib.sha256()
            for member in members:
                digest.update(
                    PurePosixPath(member).name.encode("utf-8") + b"\0" + bytes.fromhex(files[member]["sha256"])
                )
            digest = digest.hexdigest()
        if _sha256(item["source_sha256"], "source sha256") != digest:
            raise ParisonError("binding source identity does not match physical membership")
        normalized.append(
            {
                "id": identifier,
                "role": role,
                "source_kind": item["source_kind"],
                "source": source,
                "members": members,
                "source_sha256": digest,
                "policy_sha256": _sha256(item["policy_sha256"], "binding policy sha256"),
            }
        )
    try:
        ordered_files = sorted(files.values(), key=lambda item: item["path"].encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ParisonError("inventory paths must be valid UTF-8") from exc
    return {
        "manifest_version": 2,
        "collection_id": _identifier(value["collection_id"], "collection id"),
        "policy": policy,
        "closed_scopes": scopes,
        "files": ordered_files,
        "bindings": sorted(normalized, key=lambda item: (item["id"], item["role"])),
    }


def canonical_dataset_manifest_v2_bytes(value: Any) -> bytes:
    return json.dumps(
        normalize_dataset_manifest_v2(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _normalize_binding_selection(value: Any, source_kind: Any) -> dict[str, Any]:
    from .inputs import _source_selection

    if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
        raise ParisonError("binding selection must be a closed tagged object")
    kind = value["kind"]
    fields = {
        "file": "kind",
        "partition": "kind",
        "sqlite-table": "kind table",
        "json-pointer": "kind pointer",
        "xml-record": "kind record_path namespaces",
        "xlsx-range": "kind sheet range",
        "xlsx-table": "kind table",
        "xlsx-defined-name": "kind name",
    }
    if kind not in fields:
        raise ParisonError("unsupported binding selection kind")
    _closed_object(value, fields[kind], "binding selection")
    if not isinstance(source_kind, str) or source_kind not in ("file", "partition"):
        raise ParisonError("unsupported source kind")
    if (kind == "partition") != (source_kind == "partition"):
        raise ParisonError("selection and source kind disagree")
    for field, item in value.items():
        if field == "namespaces":
            if not isinstance(item, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in item.items()
            ):
                raise ParisonError("XML namespaces must map strings to strings")
        elif not isinstance(item, str) or "\0" in item or (not item and field != "pointer"):
            raise ParisonError("binding selectors must contain explicit strings")
    try:
        json.dumps(value, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ParisonError("binding selectors must be valid UTF-8") from exc
    if kind in {"file", "partition"}:
        source = "binding.csv"
    elif kind == "sqlite-table":
        source = "sqlite:binding.sqlite#" + value["table"]
    elif kind == "json-pointer":
        source = "json:binding.json#" + value["pointer"]
        if any("~" in token.replace("~0", "").replace("~1", "") for token in value["pointer"].split("/")):
            raise ParisonError("JSON pointer has an invalid escape")
    elif kind == "xml-record":
        source = "xml:binding.xml#" + value["record_path"]
        if value["namespaces"]:
            source += "?" + urlencode([("ns", f"{key},{uri}") for key, uri in sorted(value["namespaces"].items())])
    elif kind == "xlsx-range":
        from .inputs import _xlsx_range

        try:
            _xlsx_range(value["range"])
        except ImportError as exc:
            raise ParisonError("XLSX support requires the optional openpyxl dependency") from exc
        source = "xlsx:binding.xlsx#" + value["sheet"] + "!" + value["range"]
    elif kind == "xlsx-table":
        source = "xlsx:binding.xlsx#table=" + value["table"]
    else:
        source = "xlsx:binding.xlsx#defined-name=" + value["name"]
    observed = _source_selection(source, source_kind)
    if observed != value:
        raise ParisonError("binding selection does not match released locator syntax")
    try:
        json.dumps(observed, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ParisonError("binding selectors must be valid UTF-8") from exc
    return observed


def normalize_input_bindings(value: Any) -> dict[str, Any]:
    value = _closed_object(value, "binding_version policy bindings", "input bindings")
    if type(value["binding_version"]) is not int or value["binding_version"] != 1:
        raise ParisonError("input binding version must be 1")
    policy = _closed_object(value["policy"], "kind sha256", "binding policy")
    if policy["kind"] not in ("suite", "reconciliation"):
        raise ParisonError("binding policy must be suite or reconciliation")
    policy = {"kind": policy["kind"], "sha256": _sha256(policy["sha256"], "policy sha256")}
    items = value["bindings"]
    if not isinstance(items, list) or not 1 <= len(items) <= 10_000:
        raise ParisonError("input bindings must contain 1 to 10000 entries")
    normalized, pairs = [], set()
    for item in items:
        item = _closed_object(item, "id role source_kind selection source_sha256 policy_sha256", "input binding")
        identifier = _identifier(item["id"], "binding id")
        role = item["role"]
        if role not in ("baseline", "candidate"):
            raise ParisonError("binding role must be baseline or candidate")
        if (identifier, role) in pairs:
            raise ParisonError("duplicate input binding")
        pairs.add((identifier, role))
        normalized.append(
            {
                "id": identifier,
                "role": role,
                "source_kind": item["source_kind"],
                "selection": _normalize_binding_selection(item["selection"], item["source_kind"]),
                "source_sha256": _sha256(item["source_sha256"], "source sha256"),
                "policy_sha256": _sha256(item["policy_sha256"], "binding policy sha256"),
            }
        )
    return {
        "binding_version": 1,
        "policy": policy,
        "bindings": sorted(normalized, key=lambda item: (item["id"], item["role"])),
    }


def canonical_input_bindings_bytes(value: Any) -> bytes:
    return json.dumps(
        normalize_input_bindings(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def capture_suite_input_bindings(suite: dict[str, Any], selected: list[dict[str, Any]]) -> dict[str, Any]:
    """Capture selected source identity from a freshly loaded suite, before execution."""
    from .inputs import _source_digest, _source_path, _source_selection

    if suite.get("suite_version") != 2 or not selected:
        raise ParisonError("input binding capture requires selected suite v2 cases")
    bindings = []
    for case in selected:
        for role in ("baseline", "candidate"):
            source = case[role]
            kind = "partition" if _source_path(source).is_dir() else "file"
            bindings.append(
                {
                    "id": case["id"],
                    "role": role,
                    "source_kind": kind,
                    "selection": _source_selection(source, kind),
                    "source_sha256": _source_digest(source),
                    "policy_sha256": case["policy_sha256"],
                }
            )
    return normalize_input_bindings(
        {
            "binding_version": 1,
            "policy": {"kind": "suite", "sha256": suite["suite_policy_sha256"]},
            "bindings": bindings,
        }
    )


def capture_reconciliation_input_bindings(
    declaration: dict[str, Any], inputs: dict[str, dict[str, str | Path]]
) -> dict[str, Any]:
    """Capture the declared reconciliation's actual local source selections."""
    from .inputs import _source_digest, _source_path, _source_selection

    datasets = declaration.get("datasets")
    if not isinstance(datasets, list) or set(inputs) != {item["id"] for item in datasets}:
        raise ParisonError("reconciliation inputs do not match declared datasets")
    bindings = []
    for dataset in datasets:
        for role in ("baseline", "candidate"):
            source = inputs[dataset["id"]][role]
            kind = "partition" if _source_path(source).is_dir() else "file"
            bindings.append(
                {
                    "id": dataset["id"],
                    "role": role,
                    "source_kind": kind,
                    "selection": _source_selection(source, kind),
                    "source_sha256": _source_digest(source),
                    "policy_sha256": dataset["policy_sha256"],
                }
            )
    return normalize_input_bindings(
        {
            "binding_version": 1,
            "policy": {"kind": "reconciliation", "sha256": declaration["reconciliation_sha256"]},
            "bindings": bindings,
        }
    )


def verify_dataset_input_bindings(manifest: Any, record: Any) -> None:
    """Check preserved declarations against a separately verified semantic record."""
    manifest, record = normalize_dataset_manifest_v2(manifest), normalize_input_bindings(record)
    expected = []
    for item in manifest["bindings"]:
        _, _, selection = _portable_binding_source(item["source"], item["source_kind"])
        expected.append(
            {key: item[key] for key in ("id", "role", "source_kind", "source_sha256", "policy_sha256")}
            | {"selection": _normalize_binding_selection(selection, item["source_kind"])}
        )
    if record != {"binding_version": 1, "policy": manifest["policy"], "bindings": expected}:
        raise ParisonError("dataset input bindings do not match semantic evidence")


def explain_dataset_manifest(path: str | Path) -> dict[str, Any]:
    value = normalize_dataset_manifest(_read_json(path, "dataset manifest"))
    return {**value, "manifest_sha256": _digest(value, b"parison:dataset-manifest-v1\0")}


def explain_dataset_manifest_v2(path: str | Path) -> dict[str, Any]:
    value = normalize_dataset_manifest_v2(_read_json(path, "dataset manifest v2"))
    return {**value, "manifest_sha256": _digest(value, b"parison:dataset-manifest-v2\0")}


def dataset_manifest_version(path: str | Path) -> int:
    value = _read_json(path, "dataset manifest")
    version = value.get("manifest_version")
    if type(version) is not int or version not in (1, 2):
        raise ParisonError("dataset manifest version must be 1 or 2")
    return version


def explain_dataset_manifest_any(path: str | Path) -> dict[str, Any]:
    return explain_dataset_manifest_v2(path) if dataset_manifest_version(path) == 2 else explain_dataset_manifest(path)


def _policy_fingerprint(kind: str, path: str | Path) -> str:
    return _effective_policy_fingerprint(kind, _effective_policy(kind, path))


def _effective_policy(kind: str, path: str | Path) -> dict[str, Any]:
    if kind == "reconciliation":
        from .reconciliation import explain_reconciliation

        value = explain_reconciliation(path)
        return {key: item for key, item in value.items() if key != "reconciliation_sha256"}
    from .core import load_suite

    suite = load_suite(path)
    if suite["suite_version"] != 2:
        raise ParisonError("dataset manifests require suite version 2 policy binding")
    return {"suite_version": 2, "cases": [case["portable"] for case in suite["cases"]]}


def _effective_policy_fingerprint(kind: str, value: Any) -> str:
    if kind == "reconciliation":
        from .reconciliation import normalize_reconciliation

        normalized = normalize_reconciliation(value)
    else:
        if (
            not isinstance(value, dict)
            or set(value) != {"suite_version", "cases"}
            or value.get("suite_version") != 2
            or not isinstance(value["cases"], list)
        ):
            raise ParisonError("dataset evidence contains an invalid effective suite")
        normalized = value
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _read_regular_bytes(path: Path, label: str) -> bytes:
    try:
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise ParisonError(f"{label} is missing or unsafe")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    except ParisonError:
        raise
    except OSError as exc:
        raise ParisonError(f"cannot open {label}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        with os.fdopen(descriptor, "rb") as handle:
            value = handle.read()
            after = os.fstat(handle.fileno())
        observed = path.lstat()
    except OSError as exc:
        raise ParisonError(f"{label} is missing or unsafe") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or stat.S_ISLNK(observed.st_mode)
        or (after.st_dev, after.st_ino) != (observed.st_dev, observed.st_ino)
    ):
        raise ParisonError(f"{label} changed during verification")
    return value


def _read_bundle_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(_read_regular_bytes(path, label).decode("utf-8"), object_pairs_hook=_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot decode {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ParisonError(f"{label} must be a JSON object")
    return value


def _open_resource(root: Path, relative: str):
    parts = PurePosixPath(relative).parts
    directory_flags = (
        os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    if os.open in os.supports_dir_fd and getattr(os, "O_NOFOLLOW", 0):
        keep_directory = False
        try:
            current_fd = os.open(root, directory_flags)
        except OSError as exc:
            raise ParisonError("manifest root must be an existing non-symlink directory") from exc
        try:
            if not stat.S_ISDIR(os.fstat(current_fd).st_mode):
                raise ParisonError("manifest root must be an existing non-symlink directory")
            for part in parts[:-1]:
                try:
                    next_fd = os.open(part, directory_flags, dir_fd=current_fd)
                except OSError as exc:
                    raise ParisonError("resource path contains an unsafe or missing component") from exc
                os.close(current_fd)
                current_fd = next_fd
            try:
                descriptor = os.open(parts[-1], file_flags, dir_fd=current_fd)
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise ParisonError("cannot safely open declared resource") from exc
            keep_directory = True
        finally:
            if not keep_directory:
                os.close(current_fd)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            os.close(descriptor)
            raise ParisonError("declared resource must be a regular non-symlink file")

        def sidecar_exists(suffix: str) -> bool:
            try:
                os.stat(parts[-1] + suffix, dir_fd=current_fd, follow_symlinks=False)
            except FileNotFoundError:
                return False
            except OSError as exc:
                raise ParisonError("cannot safely inspect SQLite journal state") from exc
            return True

        return root.joinpath(*parts), descriptor, before, [(os.close, current_fd)], sidecar_exists

    if os.name == "nt":
        return _open_resource_windows(root, parts)

    current = root
    if root.is_symlink() or not root.is_dir():
        raise ParisonError("manifest root must be an existing non-symlink directory")
    for part in parts[:-1]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ParisonError("declared resource is missing") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ParisonError("resource path contains an unsafe component")
    path = current / parts[-1]
    try:
        path_mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ParisonError("cannot inspect declared resource") from exc
    if stat.S_ISLNK(path_mode) or not stat.S_ISREG(path_mode):
        raise ParisonError("declared resource must be a regular non-symlink file")
    try:
        descriptor = os.open(path, file_flags)
    except OSError as exc:
        raise ParisonError("cannot safely open declared resource") from exc
    before = os.fstat(descriptor)
    after_lstat = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or stat.S_ISLNK(after_lstat.st_mode)
        or (before.st_dev, before.st_ino) != (after_lstat.st_dev, after_lstat.st_ino)
    ):
        os.close(descriptor)
        raise ParisonError("declared resource changed during safe open")
    return path, descriptor, before, [], lambda suffix: Path(str(path) + suffix).exists()


def _open_resource_windows(root: Path, parts: tuple[str, ...]):
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class FileInformation(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    information = kernel.GetFileInformationByHandle
    information.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileInformation)]
    information.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    invalid = ctypes.c_void_p(-1).value
    read, share_read_write, existing = 0x80000000, 0x00000003, 3
    open_reparse, backup_semantics = 0x00200000, 0x02000000
    reparse_attribute, directory_attribute = 0x00000400, 0x00000010
    handles: list[int] = []

    def opened(path: Path, directory: bool) -> int:
        flags = open_reparse | (backup_semantics if directory else 0)
        handle = create(str(path.absolute()), read, share_read_write, None, existing, flags, None)
        if handle == invalid:
            error = ctypes.get_last_error()
            if error in {2, 3} and not directory:
                raise FileNotFoundError(error, os.strerror(error), path)
            raise ParisonError("resource path contains an unsafe or missing component")
        value = FileInformation()
        if not information(handle, ctypes.byref(value)):
            error = ctypes.get_last_error()
            close(handle)
            raise ParisonError(f"cannot inspect opened resource: Windows error {error}")
        is_directory = bool(value.dwFileAttributes & directory_attribute)
        if value.dwFileAttributes & reparse_attribute or is_directory != directory:
            close(handle)
            raise ParisonError("resource path contains an unsafe component")
        return handle

    current = root
    try:
        handles.append(opened(current, True))
        for part in parts[:-1]:
            current = current / part
            handles.append(opened(current, True))
        path = current / parts[-1]
        try:
            file_handle = opened(path, False)
        except FileNotFoundError:
            for handle in reversed(handles):
                close(handle)
            return None
        try:
            descriptor = msvcrt.open_osfhandle(file_handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        except OSError:
            close(file_handle)
            raise
        return (
            path,
            descriptor,
            os.fstat(descriptor),
            [(close, handle) for handle in handles],
            lambda suffix: Path(str(path) + suffix).exists(),
        )
    except Exception:
        for handle in reversed(handles):
            close(handle)
        raise


def _open_scope(root: Path, relative: str) -> int | Path:
    if os.open in os.supports_dir_fd and getattr(os, "O_NOFOLLOW", 0):
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
        descriptor = None
        try:
            descriptor = os.open(root, flags)
            for part in () if relative == "." else PurePosixPath(relative).parts:
                next_descriptor = os.open(part, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = next_descriptor
            return descriptor
        except OSError as exc:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise ParisonError("closed scope is missing or unsafe") from exc
    path = root if relative == "." else root.joinpath(*PurePosixPath(relative).parts)
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise ParisonError("closed scope is missing or unsafe") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise ParisonError("closed scope is missing or unsafe")
    return path


def _windows_directory_lock(path: Path):
    import ctypes
    from ctypes import wintypes

    class FileInformation(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create, information, close = kernel.CreateFileW, kernel.GetFileInformationByHandle, kernel.CloseHandle
    create.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    create.restype = wintypes.HANDLE
    information.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileInformation)]
    information.restype = wintypes.BOOL
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    handle = create(str(path.absolute()), 0x80000000, 0x00000003, None, 3, 0x00200000 | 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ParisonError("closed scope is missing or unsafe")
    value = FileInformation()
    if (
        not information(handle, ctypes.byref(value))
        or value.dwFileAttributes & 0x00000400
        or not value.dwFileAttributes & 0x00000010
    ):
        close(handle)
        raise ParisonError("closed scope is missing or unsafe")
    return close, handle


def _enumerate_scope(root: Path, relative: str, *, partition: bool = False) -> set[str]:
    opened = _open_scope(root, relative)
    prefix = "" if relative == "." else relative
    found: set[str] = set()
    if isinstance(opened, int):

        def walk(descriptor: int, parent: str) -> None:
            try:
                names = sorted(os.listdir(descriptor))
            except OSError as exc:
                raise ParisonError("cannot enumerate closed scope") from exc
            for name in names:
                if partition and name.startswith("."):
                    continue
                portable = f"{parent}/{name}" if parent else name
                try:
                    metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                except OSError as exc:
                    raise ParisonError("closed scope changed during enumeration") from exc
                if stat.S_ISLNK(metadata.st_mode):
                    raise ParisonError("closed scope contains a symlink")
                if stat.S_ISDIR(metadata.st_mode):
                    if partition:
                        raise ParisonError("partition must contain only regular files")
                    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
                    child = os.open(name, flags, dir_fd=descriptor)
                    try:
                        walk(child, portable)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(metadata.st_mode):
                    found.add(portable)
                else:
                    raise ParisonError("closed scope contains an unsupported object")

        try:
            walk(opened, prefix)
        finally:
            os.close(opened)
        return found

    def walk_path(directory: Path, parent: str) -> None:
        lock = _windows_directory_lock(directory) if os.name == "nt" else None
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise ParisonError("cannot enumerate closed scope") from exc
        try:
            for entry in entries:
                if partition and entry.name.startswith("."):
                    continue
                portable = f"{parent}/{entry.name}" if parent else entry.name
                mode = entry.lstat().st_mode
                if stat.S_ISLNK(mode):
                    raise ParisonError("closed scope contains a symlink")
                if stat.S_ISDIR(mode):
                    if partition:
                        raise ParisonError("partition must contain only regular files")
                    walk_path(entry, portable)
                elif stat.S_ISREG(mode):
                    found.add(portable)
                else:
                    raise ParisonError("closed scope contains an unsupported object")
        finally:
            if lock is not None:
                lock[0](lock[1])

    ancestor_locks = []
    if os.name == "nt":
        current = root
        ancestor_locks.append(_windows_directory_lock(current))
        for part in () if relative == "." else PurePosixPath(relative).parts:
            current = current / part
            ancestor_locks.append(_windows_directory_lock(current))
    try:
        walk_path(opened, prefix)
        return found
    finally:
        for close, handle in reversed(ancestor_locks):
            close(handle)


def _scope_members(root: Path, scopes: list[str]) -> set[str]:
    members: set[str] = set()
    for scope in scopes:
        discovered = _enumerate_scope(root, scope)
        if members & discovered:
            raise ParisonError("closed scopes overlap during enumeration")
        members.update(discovered)
    return members


def _identity(
    root: Path, relative: str, format_name: str, *, max_bytes: int | None = None
) -> tuple[int, str, tuple[int, int]] | None:
    opened = _open_resource(root, relative)
    if opened is None:
        return None
    _path, descriptor, before, locks, sidecar_exists = opened
    try:
        if max_bytes is not None and before.st_size > max_bytes:
            raise ParisonError("manifest input byte limit exceeded")
        if format_name == "sqlite" and any(sidecar_exists(suffix) for suffix in ("-wal", "-journal", "-shm")):
            raise ParisonError("SQLite resource has ambiguous journal state")
        digest, size = hashlib.sha256(), 0
        with os.fdopen(descriptor, "rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                if max_bytes is not None and size > max_bytes:
                    raise ParisonError("manifest input byte limit exceeded")
            after = os.fstat(handle.fileno())
        stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if not stable or size != after.st_size:
            raise ParisonError("resource-changed-during-read")
        if format_name == "sqlite" and any(sidecar_exists(suffix) for suffix in ("-wal", "-journal", "-shm")):
            raise ParisonError("SQLite resource has ambiguous journal state")
        return size, digest.hexdigest(), (after.st_dev, after.st_ino)
    except ParisonError:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    except OSError as exc:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise ParisonError("cannot hash declared resource") from exc
    finally:
        for close, handle in reversed(locks):
            close(handle)


def create_dataset_manifest(
    root: str | Path,
    collection_id: str,
    policy_kind: str,
    policy_sha256: str,
    resources: list[tuple[str, str, str, str]],
    output: str | Path,
    policy_path: str | Path,
    closed_scopes: list[str] | None = None,
) -> dict[str, Any]:
    if _policy_fingerprint(policy_kind, policy_path) != policy_sha256:
        raise ParisonError("declared policy SHA-256 does not match the supplied policy")
    root_path, items, identities = Path(root), [], set()
    closed_scopes = closed_scopes or []
    before_scope = _scope_members(root_path, closed_scopes)
    for identifier, role, format_name, relative in resources:
        relative = _resource_path(relative)
        identity = _identity(root_path, relative, format_name)
        if identity is None:
            raise ParisonError("declared resource is missing")
        size, digest, file_identity = identity
        if file_identity in identities:
            raise ParisonError("manifest resources contain hard-link aliases")
        identities.add(file_identity)
        items.append(
            {"id": identifier, "role": role, "format": format_name, "path": relative, "bytes": size, "sha256": digest}
        )
    value = normalize_dataset_manifest(
        {
            "manifest_version": 1,
            "collection_id": collection_id,
            "policy": {"kind": policy_kind, "sha256": policy_sha256},
            "closed_scopes": closed_scopes,
            "resources": items,
        }
    )
    after_scope = _scope_members(root_path, value["closed_scopes"])
    if before_scope != after_scope:
        raise ParisonError("closed scope changed during manifest creation")
    if value["closed_scopes"] and after_scope != {item["path"] for item in value["resources"]}:
        raise ParisonError("closed scope contains undeclared resources")
    _write_once(Path(output), json.dumps(value, indent=2, sort_keys=True) + "\n", "cannot publish dataset manifest")
    return {**value, "manifest_sha256": _digest(value, b"parison:dataset-manifest-v1\0")}


def create_dataset_manifest_v2(
    root: str | Path, declaration_path: str | Path, output: str | Path, policy_path: str | Path
) -> dict[str, Any]:
    """Publish an explicit v2 declaration only after local source verification."""
    value = normalize_dataset_manifest_v2(_read_json(declaration_path, "dataset manifest v2 declaration"))
    if _policy_fingerprint(value["policy"]["kind"], policy_path) != value["policy"]["sha256"]:
        raise ParisonError("declared policy SHA-256 does not match the supplied policy")
    if verify_dataset_manifest_v2(declaration_path, root, policy_path)["outcome"] != "PASS":
        raise ParisonError("dataset v2 declaration does not match local sources")
    _write_once(
        Path(output), canonical_dataset_manifest_v2_bytes(value).decode("utf-8"), "cannot publish dataset manifest"
    )
    return {**value, "manifest_sha256": _digest(value, b"parison:dataset-manifest-v2\0")}


def verify_dataset_manifest_v2(
    manifest_path: str | Path,
    root: str | Path,
    policy_path: str | Path,
    summary: bool = False,
    max_input_bytes: int = 1_000_000_000,
) -> dict[str, Any]:
    """Check local physical bytes and exact logical membership under explicit policy."""
    manifest = normalize_dataset_manifest_v2(_read_json(manifest_path, "dataset manifest v2"))
    if _policy_fingerprint(manifest["policy"]["kind"], policy_path) != manifest["policy"]["sha256"]:
        raise ParisonError("manifest policy SHA-256 does not match the supplied policy")
    if type(max_input_bytes) is not int or max_input_bytes <= 0:
        raise ParisonError("manifest input byte limit must be a positive integer")
    if sum(item["bytes"] for item in manifest["files"]) > max_input_bytes:
        raise ParisonError("manifest input byte limit exceeded")
    root = Path(root)
    opened = _open_scope(root, ".")
    if isinstance(opened, int):
        os.close(opened)
    partitions, sqlite_paths = {}, set()
    for binding in manifest["bindings"]:
        _, path, selection = _portable_binding_source(binding["source"], binding["source_kind"])
        if selection["kind"] == "sqlite-table":
            sqlite_paths.add(path)
        if binding["source_kind"] == "partition":
            partitions[path] = None

    def membership(path: str) -> set[str] | None:
        try:
            return _enumerate_scope(root, path, partition=True)
        except ParisonError as exc:
            if isinstance(exc.__cause__, FileNotFoundError):
                return None
            raise

    def closed_members() -> set[str]:
        found: set[str] = set()
        for scope in manifest["closed_scopes"]:
            try:
                found.update(_enumerate_scope(root, scope))
            except ParisonError as exc:
                if not isinstance(exc.__cause__, FileNotFoundError):
                    raise
        return found

    before_partitions = {path: membership(path) for path in partitions}
    before_scope = closed_members()
    files, identities, statuses = [], set(), {}
    remaining = max_input_bytes
    reasons = set()
    for item in manifest["files"]:
        path = item["path"]
        format_name = (
            "sqlite" if path in sqlite_paths or Path(path).suffix.lower() in {".db", ".sqlite", ".sqlite3"} else "file"
        )
        try:
            observed = _identity(root, path, format_name, max_bytes=remaining)
        except ParisonError as exc:
            if not isinstance(exc.__cause__, FileNotFoundError):
                raise
            observed = None
        size, digest = None, None
        if observed is None:
            status = "missing"
            reasons.add("missing-resource")
        else:
            size, digest, identity = observed
            if identity in identities:
                raise ParisonError("manifest files contain hard-link aliases")
            identities.add(identity)
            remaining -= size
            status = (
                "size-mismatch" if size != item["bytes"] else "digest-mismatch" if digest != item["sha256"] else "match"
            )
            if status != "match":
                reasons.add(status)
        statuses[path] = status
        files.append(
            {
                "path": path,
                "expected_bytes": item["bytes"],
                "expected_sha256": item["sha256"],
                "observed_bytes": size,
                "observed_sha256": digest,
                "status": status,
            }
        )
    after_partitions = {path: membership(path) for path in partitions}
    after_scope = closed_members()
    if before_scope != after_scope or before_partitions != after_partitions:
        raise ParisonError("source membership changed during manifest verification")
    undeclared = after_scope - set(statuses)
    if undeclared:
        reasons.add("undeclared-members")
    bindings = []
    for binding in manifest["bindings"]:
        matched = all(statuses[member] == "match" for member in binding["members"])
        if binding["source_kind"] == "partition":
            _, path, _ = _portable_binding_source(binding["source"], "partition")
            matched &= after_partitions[path] == set(binding["members"])
        if not matched:
            reasons.add("logical-member-mismatch")
        bindings.append(
            {
                "id": binding["id"],
                "role": binding["role"],
                "source_sha256": binding["source_sha256"],
                "status": "match" if matched else "member-mismatch",
            }
        )
    result = {
        "manifest_result_version": 2,
        "complete": True,
        "outcome": "FAIL" if reasons else "PASS",
        "manifest_sha256": _digest(manifest, b"parison:dataset-manifest-v2\0"),
        "policy": manifest["policy"],
        "files": files,
        "bindings": bindings,
        "closed_scope_status": "undeclared-members" if undeclared else "match",
        "reason_codes": sorted(reasons),
        "diagnostic_sha256": None,
        "semantic_result": None,
    }
    if not summary:
        return result
    return {
        key: result[key]
        for key in ("manifest_result_version", "complete", "outcome", "manifest_sha256", "policy", "reason_codes")
    } | {
        "file_count": len(files),
        "binding_count": len(bindings),
        "status_counts": {
            status: sum(item["status"] == status for item in files)
            for status in ("match", "missing", "size-mismatch", "digest-mismatch")
        },
    }


def verify_dataset_manifest(
    manifest_path: str | Path, root: str | Path, policy_path: str | Path, summary: bool = False
) -> dict[str, Any]:
    manifest = explain_dataset_manifest(manifest_path)
    if _policy_fingerprint(manifest["policy"]["kind"], policy_path) != manifest["policy"]["sha256"]:
        raise ParisonError("manifest policy SHA-256 does not match the supplied policy")
    before_scope = _scope_members(Path(root), manifest["closed_scopes"])
    counts = {
        "declared": len(manifest["resources"]),
        "matched": 0,
        "missing": 0,
        "undeclared": 0,
        "size_mismatch": 0,
        "digest_mismatch": 0,
    }
    reasons, details, identities = set(), [], set()
    for resource in manifest["resources"]:
        identity = _identity(Path(root), resource["path"], resource["format"])
        status = "matched"
        if identity is None:
            status = "missing"
            counts["missing"] += 1
            reasons.add("resource-missing")
        else:
            size, digest, file_identity = identity
            if file_identity in identities:
                raise ParisonError("manifest resources contain hard-link aliases")
            identities.add(file_identity)
            if size != resource["bytes"]:
                status = "size-mismatch"
                counts["size_mismatch"] += 1
                reasons.add("resource-size-mismatch")
            elif digest != resource["sha256"]:
                status = "digest-mismatch"
                counts["digest_mismatch"] += 1
                reasons.add("resource-digest-mismatch")
            else:
                counts["matched"] += 1
        if not summary:
            detail = {
                "id": resource["id"],
                "role": resource["role"],
                "format": resource["format"],
                "bytes": resource["bytes"],
                "sha256": resource["sha256"],
                "status": status,
            }
            if "schema_sha256" in resource:
                detail["schema_sha256"] = resource["schema_sha256"]
            details.append(detail)
    after_scope = _scope_members(Path(root), manifest["closed_scopes"])
    if before_scope != after_scope:
        raise ParisonError("closed scope changed during manifest verification")
    undeclared = after_scope - {item["path"] for item in manifest["resources"]}
    counts["undeclared"] = len(undeclared)
    if undeclared:
        reasons.add("resource-undeclared")
    outcome = "PASS" if counts["matched"] == counts["declared"] and not undeclared else "FAIL"
    result = {
        "manifest_result_version": 1,
        "outcome": outcome,
        "complete": True,
        "manifest_sha256": manifest["manifest_sha256"],
        "policy": manifest["policy"],
        "counts": counts,
        "reason_codes": sorted(reasons),
    }
    if not summary:
        result["resources"] = details
    return result


def verify_dataset_manifest_any(
    manifest_path: str | Path, root: str | Path, policy_path: str | Path, summary: bool = False
) -> dict[str, Any]:
    return (
        verify_dataset_manifest_v2(manifest_path, root, policy_path, summary)
        if dataset_manifest_version(manifest_path) == 2
        else verify_dataset_manifest(manifest_path, root, policy_path, summary)
    )


def normalize_reproducibility_diagnostic(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"diagnostic_version", "manifest_sha256", "runtime", "observations"}
        or value.get("diagnostic_version") != 1
    ):
        raise ParisonError("reproducibility diagnostic has invalid fields or version")
    runtime = value["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != set(_RUNTIME_FIELDS):
        raise ParisonError("reproducibility diagnostic runtime fields are invalid")
    for key in _RUNTIME_FIELDS[:-1]:
        if not isinstance(runtime[key], str) or not runtime[key]:
            raise ParisonError(f"diagnostic runtime {key} must be a non-empty string")
    reader = runtime["parquet_reader"]
    if reader is not None and (
        not isinstance(reader, dict)
        or set(reader) != {"distribution", "version"}
        or not all(isinstance(item, str) and item for item in reader.values())
    ):
        raise ParisonError("parquet_reader must be null or contain distribution and version")
    observations = value["observations"]
    if (
        not isinstance(observations, list)
        or any(item not in _OBSERVATIONS for item in observations)
        or observations != sorted(set(observations))
    ):
        raise ParisonError("diagnostic observations must be sorted unique reason codes")
    return {
        "diagnostic_version": 1,
        "manifest_sha256": _sha256(value["manifest_sha256"], "manifest_sha256"),
        "runtime": {name: runtime[name] for name in _RUNTIME_FIELDS},
        "observations": observations,
    }


def canonical_reproducibility_diagnostic_bytes(value: Any) -> bytes:
    return json.dumps(
        normalize_reproducibility_diagnostic(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


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
    value = normalize_reproducibility_diagnostic(
        {
            "diagnostic_version": 1,
            "manifest_sha256": manifest["manifest_sha256"],
            "runtime": runtime,
            "observations": [],
        }
    )
    _write_once(
        Path(output), json.dumps(value, indent=2, sort_keys=False) + "\n", "cannot publish reproducibility diagnostic"
    )
    return {**value, "diagnostic_sha256": _digest(value, b"parison:reproducibility-diagnostic-v1\0")}


def normalize_reproducibility_diagnostic_v2(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or type(value.get("diagnostic_version")) is not int
        or value["diagnostic_version"] != 2
    ):
        raise ParisonError("reproducibility diagnostic version must be 2")
    if not isinstance(value.get("observations"), list) or any(
        not isinstance(item, str) for item in value["observations"]
    ):
        raise ParisonError("diagnostic observations must be strings")
    try:
        json.dumps(value, ensure_ascii=False).encode("utf-8")
    except (UnicodeError, TypeError, ValueError) as exc:
        raise ParisonError("reproducibility diagnostic must be valid UTF-8 JSON") from exc
    normalized = normalize_reproducibility_diagnostic({**value, "diagnostic_version": 1})
    return {**normalized, "diagnostic_version": 2}


def capture_reproducibility_diagnostic_v2(manifest_path: str | Path, output: str | Path) -> dict[str, Any]:
    manifest = explain_dataset_manifest_v2(manifest_path)
    reader = None
    if any(Path(item["path"]).suffix.lower() == ".parquet" for item in manifest["files"]):
        try:
            reader = {"distribution": "polars", "version": metadata.version("polars")}
        except metadata.PackageNotFoundError:
            reader = None
    value = normalize_reproducibility_diagnostic_v2(
        {
            "diagnostic_version": 2,
            "manifest_sha256": manifest["manifest_sha256"],
            "runtime": {
                "parison_version": __version__,
                "python_implementation": sys.implementation.name,
                "python_version": platform.python_version(),
                "os_family": platform.system().lower(),
                "architecture": platform.machine().lower() or "unknown",
                "sqlite_version": sqlite3.sqlite_version,
                "parquet_reader": reader,
            },
            "observations": [],
        }
    )
    _write_once(
        Path(output),
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        "cannot publish reproducibility diagnostic",
    )
    return {**value, "diagnostic_sha256": _digest(value, b"parison:reproducibility-diagnostic-v2\0")}


def capture_reproducibility_diagnostic_any(manifest_path: str | Path, output: str | Path) -> dict[str, Any]:
    return (
        capture_reproducibility_diagnostic_v2(manifest_path, output)
        if dataset_manifest_version(manifest_path) == 2
        else capture_reproducibility_diagnostic(manifest_path, output)
    )


def diff_reproducibility_diagnostics(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    left = normalize_reproducibility_diagnostic(_read_json(left_path, "left reproducibility diagnostic"))
    right = normalize_reproducibility_diagnostic(_read_json(right_path, "right reproducibility diagnostic"))
    if left["manifest_sha256"] != right["manifest_sha256"]:
        raise ParisonError("reproducibility diagnostics bind different manifests")
    fields = []
    for name in _RUNTIME_FIELDS:
        left_value, right_value = left["runtime"][name], right["runtime"][name]
        status = (
            "same"
            if left_value == right_value
            else "missing-left"
            if left_value is None
            else "missing-right"
            if right_value is None
            else "different"
        )
        fields.append({"field": name, "status": status})
    return {
        "diagnostic_diff_version": 1,
        "outcome": "INFORMATIONAL",
        "manifest_sha256": left["manifest_sha256"],
        "fields": fields,
        "observation_status": "same" if left["observations"] == right["observations"] else "different",
    }


_EVIDENCE_FILES = {
    "dataset-manifest.json",
    "manifest-result.json",
    "reproducibility-diagnostic.json",
    "effective-policy.json",
}


def _read_regular_at(directory: int | Path, name: str, label: str) -> bytes:
    if isinstance(directory, Path):
        return _read_regular_bytes(directory / name, label)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory)
        before = os.fstat(descriptor)
        with os.fdopen(descriptor, "rb") as handle:
            value = handle.read()
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise ParisonError(f"{label} is missing or unsafe") from exc
    if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ParisonError(f"{label} changed during verification")
    return value


def _bundle_manifest_at(directory: int | Path) -> dict[str, Any]:
    try:
        value = json.loads(
            _read_regular_at(directory, "manifest.json", "semantic bundle manifest"), object_pairs_hook=_object
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot decode semantic bundle manifest: {exc}") from exc
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("files"), dict)
        or not isinstance(value.get("cases", {}), dict)
    ):
        raise ParisonError("semantic bundle manifest is invalid")
    return value


def _copy_bundle_snapshot(source: int | Path, target: Path) -> None:
    lock = _windows_directory_lock(source) if isinstance(source, Path) and os.name == "nt" else None
    try:
        manifest = _bundle_manifest_at(source)
        target.mkdir()
        (target / "manifest.json").write_bytes(_read_regular_at(source, "manifest.json", "semantic bundle manifest"))
        for name in manifest["files"]:
            if not isinstance(name, str) or Path(name).name != name:
                raise ParisonError("semantic bundle manifest contains an invalid file entry")
            (target / name).write_bytes(_read_regular_at(source, name, f"semantic bundle file {name}"))
        cases = manifest.get("cases", {})
        if cases:
            (target / "cases").mkdir()
            for identifier in sorted(cases):
                if not isinstance(identifier, str) or Path(identifier).name != identifier:
                    raise ParisonError("semantic bundle manifest contains an invalid case entry")
                if isinstance(source, int):
                    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
                    cases_fd = None
                    try:
                        cases_fd = os.open("cases", flags, dir_fd=source)
                        child_fd = os.open(identifier, flags, dir_fd=cases_fd)
                    except OSError as exc:
                        raise ParisonError("semantic bundle case is missing or unsafe") from exc
                    finally:
                        if cases_fd is not None:
                            os.close(cases_fd)
                    try:
                        _copy_bundle_snapshot(child_fd, target / "cases" / identifier)
                    finally:
                        os.close(child_fd)
                else:
                    _copy_bundle_snapshot(source / "cases" / identifier, target / "cases" / identifier)
    finally:
        if lock is not None:
            lock[0](lock[1])


def _copy_verified_bundle(source: Path, target: Path) -> dict[str, Any]:
    from .core import verify_bundle

    opened = _open_scope(source, ".")
    try:
        _copy_bundle_snapshot(opened, target)
    finally:
        if isinstance(opened, int):
            os.close(opened)
    return verify_bundle(target)


def _semantic_result_metadata(bundle: Path, declaration: dict[str, Any]) -> dict[str, Any]:
    from .core import verify_bundle

    bundle_manifest = verify_bundle(bundle)
    policy_kind = declaration["policy"]["kind"]
    expected_kind = "reconciliation" if policy_kind == "reconciliation" else "suite"
    if bundle_manifest.get("kind") != expected_kind:
        raise ParisonError(f"dataset manifest policy requires a complete {expected_kind} result bundle")
    declared = {
        (item["id"], item["role"]): item["sha256"]
        for item in declaration["resources"]
        if item["role"] in {"baseline", "candidate"}
    }
    observed: dict[tuple[str, str], str] = {}
    if expected_kind == "reconciliation":
        result = _read_bundle_json(bundle / "reconciliation-result.json", "semantic reconciliation result")
        if result.get("complete") is not True:
            raise ParisonError("semantic reconciliation result must be complete")
        effective = _read_bundle_json(bundle / "effective-reconciliation.json", "semantic reconciliation policy")
        if _effective_policy_fingerprint("reconciliation", effective) != declaration["policy"]["sha256"]:
            raise ParisonError("semantic reconciliation policy does not match dataset manifest")
        for item in result.get("datasets", []):
            observed[(item["id"], "baseline")] = item["baseline_sha256"]
            observed[(item["id"], "candidate")] = item["candidate_sha256"]
        receipts = [item["sha256"] for item in declaration["resources"] if item["role"] == "receipt"]
        if len(receipts) != 1 or receipts[0] != result.get("receipt_sha256"):
            raise ParisonError("dataset manifest receipt does not match semantic reconciliation result")
    else:
        result = _read_bundle_json(bundle / "suite-result.json", "semantic suite result")
        if (
            result.get("complete") is not True
            or result.get("scope_complete") is not True
            or result.get("execution_complete") is not True
        ):
            raise ParisonError("semantic suite result must have complete execution and scope")
        if result.get("suite_policy_sha256") != declaration["policy"]["sha256"]:
            raise ParisonError("semantic suite policy does not match dataset manifest")
        for case in result.get("cases", []):
            child = bundle / case["bundle"]
            child_result = _read_bundle_json(child / "result.json", f"semantic suite case {case['id']}")
            for role in ("baseline", "candidate"):
                observed[(case["id"], role)] = child_result["inputs"][role]["sha256"]
    if declared != observed:
        raise ParisonError("dataset manifest resources do not exactly match semantic result inputs")
    return {
        "kind": expected_kind,
        "outcome": bundle_manifest["outcome"],
        "manifest_sha256": _file_digest(bundle / "manifest.json"),
    }


def _semantic_result_metadata_v2(bundle: Path, declaration: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct v2 logical identity from a verified versioned semantic child."""
    from .core import verify_bundle

    child = verify_bundle(bundle)
    kind = declaration["policy"]["kind"]
    required_schema = 3 if kind == "suite" else 2
    if child.get("kind") != kind or child.get("schema_version") != required_schema:
        raise ParisonError("dataset v2 requires a versioned semantic child of the declared kind")
    if child.get("outcome") not in ("PASS", "FAIL", "INCONCLUSIVE"):
        raise ParisonError("dataset v2 requires a completed semantic child")
    if kind == "suite":
        result = _read_bundle_json(bundle / "suite-result.json", "semantic suite result")
        if any(result.get(name) is not True for name in ("complete", "scope_complete", "execution_complete")):
            raise ParisonError("dataset v2 requires complete suite execution and scope")
        if result.get("suite_policy_sha256") != declaration["policy"]["sha256"]:
            raise ParisonError("semantic suite policy does not match dataset manifest")
    else:
        result = _read_bundle_json(bundle / "reconciliation-result.json", "semantic reconciliation result")
        effective = _read_bundle_json(bundle / "effective-reconciliation.json", "semantic reconciliation policy")
        if (
            result.get("complete") is not True
            or _effective_policy_fingerprint("reconciliation", effective) != declaration["policy"]["sha256"]
        ):
            raise ParisonError("semantic reconciliation policy does not match dataset manifest")
        receipt_matches = [item["path"] for item in declaration["files"] if item["sha256"] == result["receipt_sha256"]]
        bound_members = {member for binding in declaration["bindings"] for member in binding["members"]}
        if len(receipt_matches) != 1 or receipt_matches[0] in bound_members:
            raise ParisonError("dataset v2 receipt must match one unbound physical file")
    record = normalize_input_bindings(_read_json(bundle / "input-bindings.json", "semantic input bindings"))
    verify_dataset_input_bindings(declaration, record)
    record_bytes = canonical_input_bindings_bytes(record)
    if (bundle / "input-bindings.json").read_bytes() != record_bytes:
        raise ParisonError("semantic input bindings are not canonical")
    return {
        "kind": kind,
        "outcome": child["outcome"],
        "manifest_sha256": _file_digest(bundle / "manifest.json"),
        "input_bindings_sha256": _digest(record, b"parison:input-bindings-v1\0"),
    }


def publish_dataset_evidence_bundle(
    output: str | Path, manifest_path: str | Path, root: str | Path, policy_path: str | Path, result_bundle: str | Path
) -> dict[str, Any]:
    manifest = explain_dataset_manifest(manifest_path)
    result = verify_dataset_manifest(manifest_path, root, policy_path)
    policy = _effective_policy(manifest["policy"]["kind"], policy_path)
    target, stage = Path(output), None
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _check_output_parent(target.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        declaration = {
            key: manifest[key] for key in ("manifest_version", "collection_id", "policy", "closed_scopes", "resources")
        }
        (stage / "dataset-manifest.json").write_bytes(canonical_dataset_manifest_bytes(declaration))
        (stage / "effective-policy.json").write_text(
            json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        diagnostic = capture_reproducibility_diagnostic(
            stage / "dataset-manifest.json", stage / "reproducibility-diagnostic.json"
        )
        _copy_verified_bundle(Path(result_bundle), stage / "semantic-result")
        semantic_result = _semantic_result_metadata(stage / "semantic-result", manifest)
        result.update({"diagnostic_sha256": diagnostic["diagnostic_sha256"], "semantic_result": semantic_result})
        (stage / "manifest-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        outer = {
            "schema_version": 1,
            "kind": "dataset-evidence",
            "complete": True,
            "outcome": result["outcome"],
            "manifest_sha256": manifest["manifest_sha256"],
            "diagnostic_sha256": diagnostic["diagnostic_sha256"],
            "semantic_result": semantic_result,
            "policy": manifest["policy"],
            "files": {name: _file_digest(stage / name) for name in sorted(_EVIDENCE_FILES)},
        }
        (stage / "manifest.json").write_text(json.dumps(outer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _rename_no_replace(stage, target)
        stage = None
        return outer
    except ParisonError:
        raise
    except OSError as exc:
        raise ParisonError(f"cannot publish dataset evidence bundle: {exc}") from exc
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def publish_dataset_evidence_bundle_v2(
    output: str | Path, manifest_path: str | Path, root: str | Path, policy_path: str | Path, result_bundle: str | Path
) -> dict[str, Any]:
    """Atomically publish verified physical/logical identity and a versioned child."""
    manifest = explain_dataset_manifest_v2(manifest_path)
    source_result = verify_dataset_manifest_v2(manifest_path, root, policy_path)
    if source_result["outcome"] != "PASS":
        raise ParisonError("dataset v2 publication requires matching local sources")
    policy = _effective_policy(manifest["policy"]["kind"], policy_path)
    target, stage = Path(output), None
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _check_output_parent(target.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        declaration = {
            key: manifest[key]
            for key in ("manifest_version", "collection_id", "policy", "closed_scopes", "files", "bindings")
        }
        (stage / "dataset-manifest.json").write_bytes(canonical_dataset_manifest_v2_bytes(declaration))
        (stage / "effective-policy.json").write_text(
            json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        diagnostic = capture_reproducibility_diagnostic_v2(
            stage / "dataset-manifest.json", stage / "reproducibility-diagnostic.json"
        )
        _copy_verified_bundle(Path(result_bundle), stage / "semantic-result")
        semantic = _semantic_result_metadata_v2(stage / "semantic-result", declaration)
        result = {**source_result, "diagnostic_sha256": diagnostic["diagnostic_sha256"], "semantic_result": semantic}
        (stage / "manifest-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        outer = {
            "schema_version": 2,
            "kind": "dataset-evidence",
            "complete": True,
            "outcome": result["outcome"],
            "manifest_sha256": manifest["manifest_sha256"],
            "diagnostic_sha256": diagnostic["diagnostic_sha256"],
            "semantic_result": semantic,
            "policy": manifest["policy"],
            "files": {name: _file_digest(stage / name) for name in sorted(_EVIDENCE_FILES)},
        }
        (stage / "manifest.json").write_text(json.dumps(outer, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _verified_dataset_evidence_v2(stage)
        if verify_dataset_manifest_v2(manifest_path, root, policy_path) != source_result:
            raise ParisonError("dataset v2 sources changed during publication")
        _rename_no_replace(stage, target)
        stage = None
        return outer
    except ParisonError:
        raise
    except OSError as exc:
        raise ParisonError(f"cannot publish dataset v2 evidence bundle: {exc}") from exc
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def _verify_manifest_result(result: Any, manifest: dict[str, Any]) -> None:
    required = {
        "manifest_result_version",
        "outcome",
        "complete",
        "manifest_sha256",
        "policy",
        "counts",
        "reason_codes",
        "resources",
        "diagnostic_sha256",
        "semantic_result",
    }
    if (
        not isinstance(result, dict)
        or set(result) != required
        or result.get("manifest_result_version") != 1
        or result.get("complete") is not True
    ):
        raise ParisonError("dataset evidence result is incomplete or unsupported")
    resources = result.get("resources")
    if not isinstance(resources, list) or len(resources) != len(manifest["resources"]):
        raise ParisonError("dataset evidence result resources do not match manifest")
    expected_identity = [
        (item["id"], item["role"], item["format"], item["bytes"], item["sha256"], item.get("schema_sha256"))
        for item in manifest["resources"]
    ]
    if [
        (
            item.get("id"),
            item.get("role"),
            item.get("format"),
            item.get("bytes"),
            item.get("sha256"),
            item.get("schema_sha256"),
        )
        for item in resources
        if isinstance(item, dict)
    ] != expected_identity:
        raise ParisonError("dataset evidence result resources do not match manifest")
    statuses = [item.get("status") for item in resources]
    allowed = {"matched", "missing", "size-mismatch", "digest-mismatch"}
    allowed_resource_fields = {"id", "role", "format", "bytes", "sha256", "schema_sha256", "status"}
    if any(
        set(item) - allowed_resource_fields or not {"id", "role", "format", "bytes", "sha256", "status"} <= set(item)
        for item in resources
    ) or any(status not in allowed for status in statuses):
        raise ParisonError("dataset evidence result has invalid resource statuses")
    counts = {
        "declared": len(resources),
        "matched": statuses.count("matched"),
        "missing": statuses.count("missing"),
        "undeclared": result.get("counts", {}).get("undeclared") if isinstance(result.get("counts"), dict) else None,
        "size_mismatch": statuses.count("size-mismatch"),
        "digest_mismatch": statuses.count("digest-mismatch"),
    }
    reasons = sorted(
        {
            {
                "missing": "resource-missing",
                "size-mismatch": "resource-size-mismatch",
                "digest-mismatch": "resource-digest-mismatch",
            }[status]
            for status in statuses
            if status != "matched"
        }
    )
    if type(counts["undeclared"]) is not int or counts["undeclared"] < 0:
        raise ParisonError("dataset evidence result has invalid undeclared count")
    if counts["undeclared"]:
        reasons.append("resource-undeclared")
    outcome = "PASS" if counts["matched"] == counts["declared"] and not counts["undeclared"] else "FAIL"
    semantic = result["semantic_result"]
    if (
        not isinstance(semantic, dict)
        or set(semantic) != {"kind", "outcome", "manifest_sha256"}
        or semantic.get("kind") not in {"suite", "reconciliation"}
        or semantic.get("outcome") not in {"PASS", "FAIL", "INCONCLUSIVE", "ERROR", "INTERRUPTED"}
        or not isinstance(result.get("diagnostic_sha256"), str)
    ):
        raise ParisonError("dataset evidence result has invalid semantic or diagnostic binding")
    if (
        result["counts"] != counts
        or result["reason_codes"] != reasons
        or result["outcome"] != outcome
        or result["manifest_sha256"] != manifest["manifest_sha256"]
        or result["policy"] != manifest["policy"]
    ):
        raise ParisonError("dataset evidence result metadata is inconsistent")


def _verify_manifest_result_v2(result: Any, manifest: dict[str, Any], *, published: bool) -> None:
    fields = "manifest_result_version complete outcome manifest_sha256 policy files bindings closed_scope_status reason_codes diagnostic_sha256 semantic_result"
    result = _closed_object(result, fields, "dataset v2 manifest result")
    if (
        type(result["manifest_result_version"]) is not int
        or result["manifest_result_version"] != 2
        or result["complete"] is not True
    ):
        raise ParisonError("dataset v2 manifest result is incomplete or unsupported")
    if (
        result["manifest_sha256"] != _digest(manifest, b"parison:dataset-manifest-v2\0")
        or result["policy"] != manifest["policy"]
    ):
        raise ParisonError("dataset v2 manifest result policy or fingerprint differs")
    observations = result["files"]
    if not isinstance(observations, list) or len(observations) != len(manifest["files"]):
        raise ParisonError("dataset v2 file observations do not match inventory")
    statuses, reasons = {}, set()
    for item, expected in zip(observations, manifest["files"], strict=True):
        item = _closed_object(
            item, "path expected_bytes expected_sha256 observed_bytes observed_sha256 status", "file observation"
        )
        if type(item["expected_bytes"]) is not int or (
            item["path"],
            item["expected_bytes"],
            item["expected_sha256"],
        ) != (
            expected["path"],
            expected["bytes"],
            expected["sha256"],
        ):
            raise ParisonError("dataset v2 file observation differs from inventory")
        size, digest = item["observed_bytes"], item["observed_sha256"]
        if size is None and digest is None:
            status = "missing"
            reasons.add("missing-resource")
        elif type(size) is int and size >= 0 and isinstance(digest, str) and _SHA256.fullmatch(digest):
            status = (
                "size-mismatch"
                if size != expected["bytes"]
                else "digest-mismatch"
                if digest != expected["sha256"]
                else "match"
            )
            if status != "match":
                reasons.add(status)
        else:
            raise ParisonError("dataset v2 file observation has invalid observed identity")
        if item["status"] != status:
            raise ParisonError("dataset v2 file observation status is inconsistent")
        statuses[expected["path"]] = status
    bindings = result["bindings"]
    if not isinstance(bindings, list) or len(bindings) != len(manifest["bindings"]):
        raise ParisonError("dataset v2 binding observations do not match declaration")
    for item, expected in zip(bindings, manifest["bindings"], strict=True):
        item = _closed_object(item, "id role source_sha256 status", "binding observation")
        if (item["id"], item["role"], item["source_sha256"]) != (
            expected["id"],
            expected["role"],
            expected["source_sha256"],
        ) or item["status"] not in ("match", "member-mismatch"):
            raise ParisonError("dataset v2 binding observation differs from declaration")
        if item["status"] == "match" and any(statuses[member] != "match" for member in expected["members"]):
            raise ParisonError("dataset v2 binding cannot match a changed member")
        if item["status"] != "match":
            reasons.add("logical-member-mismatch")
    if result["closed_scope_status"] not in ("match", "undeclared-members"):
        raise ParisonError("dataset v2 closed scope status is invalid")
    if result["closed_scope_status"] == "undeclared-members":
        reasons.add("undeclared-members")
    outcome = "FAIL" if reasons else "PASS"
    if result["reason_codes"] != sorted(reasons) or result["outcome"] != outcome:
        raise ParisonError("dataset v2 result outcome or reasons are inconsistent")
    semantic, diagnostic = result["semantic_result"], result["diagnostic_sha256"]
    if published:
        if (
            outcome != "PASS"
            or not isinstance(semantic, dict)
            or set(semantic) != {"kind", "outcome", "manifest_sha256", "input_bindings_sha256"}
            or semantic.get("kind") != manifest["policy"]["kind"]
            or semantic.get("outcome") not in ("PASS", "FAIL", "INCONCLUSIVE")
        ):
            raise ParisonError("dataset v2 published semantic result is invalid")
        for name in ("manifest_sha256", "input_bindings_sha256"):
            _sha256(semantic[name], name)
        _sha256(diagnostic, "diagnostic_sha256")
    elif semantic is not None or diagnostic is not None:
        raise ParisonError("standalone dataset v2 source result must have null publication bindings")


def _verified_dataset_evidence(directory: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    root = Path(directory)
    opened = _open_scope(root, ".")
    lock = _windows_directory_lock(root) if isinstance(opened, Path) and os.name == "nt" else None
    try:
        if set(os.listdir(opened)) != _EVIDENCE_FILES | {"manifest.json", "semantic-result"}:
            raise ParisonError("dataset evidence bundle has unexpected file membership")
        manifest_bytes = _read_regular_at(opened, "manifest.json", "dataset evidence manifest")
        outer = json.loads(manifest_bytes, object_pairs_hook=_object)
    except ParisonError:
        if isinstance(opened, int):
            os.close(opened)
        if lock is not None:
            lock[0](lock[1])
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        if isinstance(opened, int):
            os.close(opened)
        if lock is not None:
            lock[0](lock[1])
        raise ParisonError(f"cannot read dataset evidence manifest: {exc}") from exc
    try:
        required = {
            "schema_version",
            "kind",
            "complete",
            "outcome",
            "manifest_sha256",
            "diagnostic_sha256",
            "semantic_result",
            "policy",
            "files",
        }
        if (
            not isinstance(outer, dict)
            or set(outer) != required
            or outer.get("schema_version") != 1
            or outer.get("kind") != "dataset-evidence"
            or outer.get("complete") is not True
            or outer.get("outcome") not in {"PASS", "FAIL"}
        ):
            raise ParisonError("dataset evidence manifest is incomplete or unsupported")
        files = outer.get("files")
        if not isinstance(files, dict) or set(files) != _EVIDENCE_FILES:
            raise ParisonError("dataset evidence manifest has invalid file membership")
        values: dict[str, bytes] = {}
        for name, expected in files.items():
            values[name] = _read_regular_at(opened, name, f"dataset evidence file {name}")
            if (
                not isinstance(expected, str)
                or not _SHA256.fullmatch(expected)
                or hashlib.sha256(values[name]).hexdigest() != expected
            ):
                raise ParisonError(f"dataset evidence file failed integrity check: {name}")

        def decoded(name: str, label: str) -> dict[str, Any]:
            try:
                value = json.loads(values[name], object_pairs_hook=_object)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ParisonError(f"cannot decode {label}: {exc}") from exc
            if not isinstance(value, dict):
                raise ParisonError(f"{label} must be a JSON object")
            return value

        declaration = normalize_dataset_manifest(decoded("dataset-manifest.json", "dataset manifest"))
        declaration["manifest_sha256"] = _digest(declaration, b"parison:dataset-manifest-v1\0")
        diagnostic = normalize_reproducibility_diagnostic(
            decoded("reproducibility-diagnostic.json", "reproducibility diagnostic")
        )
        result = decoded("manifest-result.json", "dataset manifest result")
        policy = decoded("effective-policy.json", "effective policy")
        _verify_manifest_result(result, declaration)
        diagnostic_sha256 = _digest(diagnostic, b"parison:reproducibility-diagnostic-v1\0")
        with tempfile.TemporaryDirectory(prefix="parison-semantic-verify-") as temporary:
            snapshot = Path(temporary) / "semantic-result"
            if isinstance(opened, int):
                flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
                try:
                    semantic_fd = os.open("semantic-result", flags, dir_fd=opened)
                except OSError as exc:
                    raise ParisonError("semantic result bundle is missing or unsafe") from exc
                try:
                    _copy_bundle_snapshot(semantic_fd, snapshot)
                finally:
                    os.close(semantic_fd)
            else:
                _copy_bundle_snapshot(root / "semantic-result", snapshot)
            semantic_result = _semantic_result_metadata(snapshot, declaration)
        if (
            outer["manifest_sha256"] != declaration["manifest_sha256"]
            or outer["diagnostic_sha256"] != diagnostic_sha256
            or result["diagnostic_sha256"] != diagnostic_sha256
            or diagnostic["manifest_sha256"] != declaration["manifest_sha256"]
            or outer["policy"] != declaration["policy"]
            or outer["outcome"] != result["outcome"]
            or outer["semantic_result"] != semantic_result
            or result["semantic_result"] != semantic_result
            or _effective_policy_fingerprint(outer["policy"]["kind"], policy) != outer["policy"]["sha256"]
        ):
            raise ParisonError("dataset evidence bundle metadata is inconsistent")
        if _read_regular_at(opened, "manifest.json", "dataset evidence manifest") != manifest_bytes or set(
            os.listdir(opened)
        ) != _EVIDENCE_FILES | {"manifest.json", "semantic-result"}:
            raise ParisonError("dataset evidence bundle changed during verification")
        return outer, result, diagnostic, hashlib.sha256(manifest_bytes).hexdigest()
    finally:
        if isinstance(opened, int):
            os.close(opened)
        if lock is not None:
            lock[0](lock[1])


def _dataset_evidence_version(directory: str | Path) -> int:
    opened = _open_scope(Path(directory), ".")
    try:
        try:
            value = json.loads(
                _read_regular_at(opened, "manifest.json", "dataset evidence manifest"), object_pairs_hook=_object
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ParisonError(f"cannot decode dataset evidence manifest: {exc}") from exc
        version = value.get("schema_version") if isinstance(value, dict) else None
        if type(version) is not int or version not in (1, 2):
            raise ParisonError("dataset evidence schema version must be 1 or 2")
        return version
    finally:
        if isinstance(opened, int):
            os.close(opened)


def _verified_dataset_evidence_v2(directory: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    root = Path(directory)
    opened = _open_scope(root, ".")
    lock = _windows_directory_lock(root) if isinstance(opened, Path) and os.name == "nt" else None
    expected_members = _EVIDENCE_FILES | {"manifest.json", "semantic-result"}
    try:
        if set(os.listdir(opened)) != expected_members:
            raise ParisonError("dataset v2 evidence bundle has unexpected membership")
        manifest_bytes = _read_regular_at(opened, "manifest.json", "dataset v2 evidence manifest")
        try:
            outer = json.loads(manifest_bytes, object_pairs_hook=_object)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ParisonError(f"cannot decode dataset v2 evidence manifest: {exc}") from exc
        outer = _closed_object(
            outer,
            "schema_version kind complete outcome manifest_sha256 diagnostic_sha256 semantic_result policy files",
            "dataset v2 evidence manifest",
        )
        if (
            type(outer["schema_version"]) is not int
            or outer["schema_version"] != 2
            or outer["kind"] != "dataset-evidence"
            or outer["complete"] is not True
        ):
            raise ParisonError("dataset v2 evidence manifest is incomplete or unsupported")
        files = outer["files"]
        if not isinstance(files, dict) or set(files) != _EVIDENCE_FILES:
            raise ParisonError("dataset v2 evidence manifest has invalid file membership")
        values = {}
        for name in sorted(files):
            values[name] = _read_regular_at(opened, name, f"dataset v2 evidence file {name}")
            if _sha256(files[name], f"{name} sha256") != hashlib.sha256(values[name]).hexdigest():
                raise ParisonError(f"dataset v2 evidence file failed integrity check: {name}")

        def decoded(name: str) -> dict[str, Any]:
            try:
                value = json.loads(values[name], object_pairs_hook=_object)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ParisonError(f"cannot decode dataset v2 {name}: {exc}") from exc
            if not isinstance(value, dict):
                raise ParisonError(f"dataset v2 {name} must be a JSON object")
            return value

        declaration = normalize_dataset_manifest_v2(decoded("dataset-manifest.json"))
        if values["dataset-manifest.json"] != canonical_dataset_manifest_v2_bytes(declaration):
            raise ParisonError("dataset v2 manifest member is not canonical")
        manifest_sha = _digest(declaration, b"parison:dataset-manifest-v2\0")
        result = decoded("manifest-result.json")
        _verify_manifest_result_v2(result, declaration, published=True)
        diagnostic = normalize_reproducibility_diagnostic_v2(decoded("reproducibility-diagnostic.json"))
        diagnostic_bytes = json.dumps(diagnostic, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        if values["reproducibility-diagnostic.json"] != diagnostic_bytes:
            raise ParisonError("dataset v2 diagnostic member is not canonical")
        diagnostic_sha = _digest(diagnostic, b"parison:reproducibility-diagnostic-v2\0")
        policy = decoded("effective-policy.json")
        if _effective_policy_fingerprint(declaration["policy"]["kind"], policy) != declaration["policy"]["sha256"]:
            raise ParisonError("dataset v2 effective policy does not match manifest")
        with tempfile.TemporaryDirectory(prefix="parison-semantic-verify-") as temporary:
            snapshot = Path(temporary) / "semantic-result"
            if isinstance(opened, int):
                flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
                try:
                    semantic_fd = os.open("semantic-result", flags, dir_fd=opened)
                except OSError as exc:
                    raise ParisonError("semantic result bundle is missing or unsafe") from exc
                try:
                    _copy_bundle_snapshot(semantic_fd, snapshot)
                finally:
                    os.close(semantic_fd)
            else:
                _copy_bundle_snapshot(root / "semantic-result", snapshot)
            semantic = _semantic_result_metadata_v2(snapshot, declaration)
        if (
            outer["outcome"] != result["outcome"]
            or outer["manifest_sha256"] != manifest_sha
            or outer["policy"] != declaration["policy"]
            or diagnostic["manifest_sha256"] != manifest_sha
            or outer["diagnostic_sha256"] != diagnostic_sha
            or result["diagnostic_sha256"] != diagnostic_sha
            or outer["semantic_result"] != semantic
            or result["semantic_result"] != semantic
        ):
            raise ParisonError("dataset v2 evidence bundle metadata is inconsistent")
        if (
            _read_regular_at(opened, "manifest.json", "dataset v2 evidence manifest") != manifest_bytes
            or set(os.listdir(opened)) != expected_members
        ):
            raise ParisonError("dataset v2 evidence bundle changed during verification")
        for name in sorted(files):
            if _read_regular_at(opened, name, f"dataset v2 evidence file {name}") != values[name]:
                raise ParisonError("dataset v2 evidence member changed during verification")
        return outer, result, diagnostic, hashlib.sha256(manifest_bytes).hexdigest()
    finally:
        if isinstance(opened, int):
            os.close(opened)
        if lock is not None:
            lock[0](lock[1])


def verify_dataset_evidence_bundle(directory: str | Path) -> dict[str, Any]:
    return (
        _verified_dataset_evidence_v2(directory)
        if _dataset_evidence_version(directory) == 2
        else _verified_dataset_evidence(directory)
    )[0]


def inspect_dataset_evidence_bundle(directory: str | Path) -> dict[str, Any]:
    if _dataset_evidence_version(directory) == 2:
        manifest, result, diagnostic, bundle_sha256 = _verified_dataset_evidence_v2(directory)
        return {
            "kind": "dataset-evidence",
            "schema_version": 2,
            "outcome": result["outcome"],
            "complete": True,
            "manifest_sha256": manifest["manifest_sha256"],
            "diagnostic_sha256": manifest["diagnostic_sha256"],
            "semantic_result": manifest["semantic_result"],
            "policy": manifest["policy"],
            "file_count": len(result["files"]),
            "binding_count": len(result["bindings"]),
            "status_counts": {
                status: sum(item["status"] == status for item in result["files"])
                for status in ("match", "missing", "size-mismatch", "digest-mismatch")
            },
            "reason_codes": result["reason_codes"],
            "runtime": diagnostic["runtime"],
            "observations": diagnostic["observations"],
            "bundle_sha256": bundle_sha256,
            "manifest_files": sorted(manifest["files"]),
        }
    manifest, result, diagnostic, bundle_sha256 = _verified_dataset_evidence(directory)
    return {
        "kind": "dataset-evidence",
        "schema_version": 1,
        "outcome": result["outcome"],
        "complete": True,
        "manifest_sha256": manifest["manifest_sha256"],
        "diagnostic_sha256": manifest["diagnostic_sha256"],
        "semantic_result": manifest["semantic_result"],
        "policy": manifest["policy"],
        "counts": result["counts"],
        "reason_codes": result["reason_codes"],
        "runtime": diagnostic["runtime"],
        "observations": diagnostic["observations"],
        "bundle_sha256": bundle_sha256,
        "manifest_files": sorted(manifest["files"]),
    }
