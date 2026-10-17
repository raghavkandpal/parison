"""Private cross-platform primitives for safe local publication."""

from __future__ import annotations

import ctypes
import errno
import os
import sys
import tempfile
from pathlib import Path

from .core import ParisonError


def check_output_parent(parent: Path) -> None:
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


def rename_no_replace(source: Path, target: Path) -> None:
    """Atomically publish a staged directory without replacing a raced target."""
    if sys.platform == "linux":
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        status = rename(-100, os.fsencode(source), -100, os.fsencode(target), 1)
    elif sys.platform == "darwin":
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        status = rename(os.fsencode(source), os.fsencode(target), 4)
    else:
        # Windows os.rename fails when the destination exists.
        os.rename(source, target)
        return
    if status:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(error, os.strerror(error), target)
        raise OSError(error, os.strerror(error), target)
