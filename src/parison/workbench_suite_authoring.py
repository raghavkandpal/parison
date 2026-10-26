"""Explicit local suite-v2 draft review and no-replace export."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent
from .core import ParisonError
from .inputs import _source_digest, _source_path
from .policies import load_suite


def _destination(root: Path, name: Any) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ParisonError("suite draft destination must stay inside the workspace")
    target = Path(os.path.abspath(root / name))
    if not target.is_relative_to(root) or target == root or target.exists() or target.is_symlink():
        raise ParisonError("suite draft destination must be a new workspace file")
    if not target.parent.is_dir():
        raise ParisonError("suite draft destination parent must exist")
    _confined(root, target.parent)
    check_output_parent(target.parent)
    return target


def _confined(root: Path, path: Path) -> None:
    if not path.is_relative_to(root):
        raise ParisonError("suite draft reference leaves the workspace")
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            raise ParisonError("suite draft reference follows a symlink")


def _references(root: Path, target: Path, draft: dict[str, Any]) -> list[dict[str, str]]:
    cases = draft.get("cases")
    if not isinstance(cases, list):
        raise ParisonError("suite draft cases must be an array")
    identities = []
    for case in cases:
        if not isinstance(case, dict):
            raise ParisonError("suite draft case must be an object")
        for name in ("recipe", "baseline", "candidate"):
            value = case.get(name)
            if not isinstance(value, str):
                raise ParisonError("suite draft reference must be a string")
            source = Path(value) if name == "recipe" else _source_path(value)
            path = Path(os.path.abspath(target.parent / source))
            _confined(root, path)
            if not (path.is_file() or path.is_dir()):
                raise ParisonError("suite draft reference does not exist")
            identities.append({"path": str(path.relative_to(root)), "sha256": _source_digest(path)})
    return identities


def _draft_bytes(draft: Any) -> bytes:
    if not isinstance(draft, dict) or draft.get("suite_version") != 2:
        raise ParisonError("suite authoring requires a version-2 draft")
    try:
        return (json.dumps(draft, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    except (UnicodeError, TypeError, ValueError) as exc:
        raise ParisonError("suite draft must be valid UTF-8 JSON") from exc


def _stage(target: Path, content: bytes) -> Path:
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
    except OSError as exc:
        raise ParisonError("cannot stage suite draft") from exc
    stage = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as exc:
        stage.unlink(missing_ok=True)
        if isinstance(exc, OSError):
            raise ParisonError("cannot stage suite draft") from exc
        raise
    return stage


def review_suite_draft(root: Path, name: Any, draft: Any) -> dict[str, Any]:
    """Validate the exact draft at its future destination without executing it."""
    root = root.absolute()
    target = _destination(root, name)
    content = _draft_bytes(draft)
    identities = _references(root, target, draft)
    stage = _stage(target, content)
    try:
        loaded = load_suite(stage)
        fingerprint = loaded["suite_policy_sha256"]
    finally:
        stage.unlink(missing_ok=True)
    snapshot = {"destination": name, "draft_sha256": hashlib.sha256(content).hexdigest(), "references": identities}
    review_id = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "review_id": review_id,
        "suite_policy_sha256": fingerprint,
        "case_ids": [case["id"] for case in loaded["cases"]],
        "cases": draft["cases"],
        "destination": name,
        "unapproved": True,
    }


def export_suite_draft(root: Path, name: Any, draft: Any, review_id: Any) -> dict[str, Any]:
    """Recheck review identity and atomically install one unapproved draft."""
    reviewed = review_suite_draft(root, name, draft)
    if not isinstance(review_id, str) or review_id != reviewed["review_id"]:
        raise ParisonError("suite draft changed after review")
    target = _destination(root.absolute(), name)
    content = _draft_bytes(draft)
    stage = _stage(target, content)
    try:
        if review_suite_draft(root, name, draft)["review_id"] != review_id:
            raise ParisonError("suite draft references changed during export")
        try:
            os.link(stage, target)
        except FileExistsError as exc:
            raise ParisonError("suite draft destination already exists") from exc
        except OSError as exc:
            raise ParisonError("cannot publish suite draft") from exc
        return {"destination": name, "suite_policy_sha256": reviewed["suite_policy_sha256"], "unapproved": True}
    finally:
        stage.unlink(missing_ok=True)
