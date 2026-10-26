"""Workbench ownership checks for deliberately retained suite workspaces."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from .core import ParisonError


def workspace_owner(root: Path, workspace: Path) -> str:
    root, workspace = root.absolute(), workspace.absolute()
    if workspace == root or not workspace.is_relative_to(root):
        raise ParisonError("retained suite workspace must stay inside the Workbench workspace")
    identity = f"parison-workbench-suite-v1\n{root}\n{workspace.relative_to(root)}\n".encode()
    return hashlib.sha256(identity).hexdigest()


def require_owned_workspace(root: Path, workspace: Path) -> None:
    expected = workspace_owner(root, workspace)
    marker = workspace / ".workbench-owner"
    if workspace.is_symlink() or not workspace.is_dir() or marker.is_symlink() or not marker.is_file():
        raise ParisonError("retained suite workspace is missing or unsafe")
    try:
        if marker.read_text(encoding="ascii") != expected + "\n":
            raise ParisonError("retained suite workspace is not owned by this Workbench")
    except (OSError, UnicodeError) as exc:
        raise ParisonError("cannot verify retained suite workspace ownership") from exc


def abandon_owned_workspace(root: Path, workspace: Path) -> None:
    """Remove only an exact owned workspace with no symlink descendants."""
    require_owned_workspace(root, workspace)
    for current, directories, files in os.walk(workspace, followlinks=False):
        if any((Path(current) / name).is_symlink() for name in directories + files):
            raise ParisonError("retained suite workspace contains a symlink")
    try:
        shutil.rmtree(workspace)
    except OSError as exc:
        raise ParisonError("cannot abandon retained suite workspace") from exc
