"""Private read ownership; no session validation, reuse, mutation or CLI yet."""

from __future__ import annotations

import os
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path

from . import partition_discovery as discovery
from ._safe_fs import check_output_parent
from .core import ParisonError

_ERROR = "invalid or busy partition session ownership"


def _acquire(handle):
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

        def unlock():
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        def unlock():
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    return unlock


@contextmanager
def _read_owner(directory):
    """Yield a directory capability and recheck callback under exclusive read ownership.

    Callers must validate pinned journal/cache bytes AFTER acquiring this context.
    It recognizes only the root and fixed lock; it grants no cache reuse authority.
    Namespace changes are rejected, so this is not a mutating-session context.
    """
    try:
        root = Path(directory)
        with ExitStack() as stack:
            check_output_parent(root)
            original = root.lstat()
            fd = discovery._hash_directory(stack, root)
            native = discovery._windows_directory_pin(stack, root) if os.name == "nt" else None

            def root_identity():
                check_output_parent(root)
                info = root.lstat()
                if (
                    not stat.S_ISDIR(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                    or (info.st_dev, info.st_ino) != (original.st_dev, original.st_ino)
                ):
                    raise ParisonError(_ERROR)

            root_identity()
            path = root / ".lock"
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400:
                raise ParisonError(_ERROR)
            descriptor = os.open(
                ".lock" if fd is not None else path,
                os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0),
                dir_fd=fd,
            )
            handle = stack.enter_context(os.fdopen(descriptor, "r+b"))
            info = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_size != 1
                or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
            ):
                raise ParisonError(_ERROR)
            stack.callback(_acquire(handle))
            root_identity()
            handle.seek(0)
            if handle.read(2) != b"\x00":
                raise ParisonError(_ERROR)
            lock_stamp = discovery._file_stamp(handle)

            def root_stamp():
                info = os.fstat(fd) if fd is not None else root.lstat()
                change = discovery._windows_change_time(native) if native is not None else info.st_ctime_ns
                return (*discovery._stat_stamp(info)[:-1], change)

            # Only post-lock state can be authoritative; another owner may have just exited.
            directory_stamp = root_stamp()

            def unchanged():
                root_identity()
                if (
                    root_stamp() != directory_stamp
                    or discovery._file_stamp(handle) != lock_stamp
                    or discovery._named_file_stamp(path) != lock_stamp
                ):
                    raise ParisonError(_ERROR)

            unchanged()
            yield fd, unchanged
            unchanged()
    except (ParisonError, OSError, UnicodeError, ValueError, TypeError, OverflowError):
        raise ParisonError(_ERROR) from None
