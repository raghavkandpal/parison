"""Kernel exclusion and namespace ownership before any session metadata admission."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from parison.core import ParisonError
from parison.partition_sessions import _read_owner


class SessionReadOwnership(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "session"
        self.root.mkdir()
        (self.root / ".lock").write_bytes(b"\0")
        (self.root / "session.json").write_bytes(b"{}\n")

    def test_exclusion_normal_release_and_no_data_mutation(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with _read_owner(self.root) as (descriptor, check):
            self.assertEqual(descriptor is None, os.name == "nt")
            check()
            with self.assertRaisesRegex(ParisonError, "invalid or busy partition session ownership"):
                with _read_owner(self.root):
                    self.fail("second owner admitted")
            check()
        with _read_owner(self.root) as (_, check):
            check()
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_exception_and_interruption_release_ownership(self):
        for error in (RuntimeError, KeyboardInterrupt):
            with self.assertRaises(error):
                with _read_owner(self.root):
                    raise error
            with _read_owner(self.root) as (_, check):
                check()

    def test_lock_is_never_created_and_requires_exact_regular_byte(self):
        lock = self.root / ".lock"
        for data in (None, b"", b"x", b"\0\0"):
            if lock.exists():
                lock.unlink()
            if data is not None:
                lock.write_bytes(data)
            with self.assertRaisesRegex(ParisonError, "invalid or busy partition session ownership"):
                with _read_owner(self.root):
                    self.fail("bad lock accepted")
            self.assertEqual(lock.read_bytes() if lock.exists() else None, data)
        lock.unlink()
        lock.mkdir()
        with self.assertRaises(ParisonError):
            with _read_owner(self.root):
                self.fail("directory used as lock")

    def test_root_replacement_preserves_unrelated_directory(self):
        moved = self.parent / "owned-moved"
        denied = False
        try:
            with _read_owner(self.root) as (_, check):
                try:
                    self.root.rename(moved)
                except PermissionError:
                    denied = True
                else:
                    self.root.mkdir()
                    (self.root / "owner").write_bytes(b"keep")
                    check()
        except ParisonError:
            pass
        if denied:
            self.assertEqual((self.root / ".lock").read_bytes(), b"\0")
        else:
            self.assertEqual((self.root / "owner").read_bytes(), b"keep")
            self.assertEqual((moved / ".lock").read_bytes(), b"\0")

    def test_transient_root_and_lock_replacement_are_denied_or_detected(self):
        for kind in ("root", "lock"):
            with self.subTest(kind=kind):
                detected = False
                denied = False
                try:
                    with _read_owner(self.root):
                        path = self.root if kind == "root" else self.root / ".lock"
                        saved = self.parent / "saved" if kind == "root" else self.root / "saved"
                        try:
                            path.rename(saved)
                        except PermissionError:
                            denied = True
                        else:
                            saved.rename(path)
                except ParisonError:
                    detected = True
                self.assertTrue(denied or detected)
                self.assertEqual((self.root / ".lock").read_bytes(), b"\0")

    def test_namespace_changes_require_a_separate_mutating_context(self):
        with self.assertRaises(ParisonError):
            with _read_owner(self.root):
                (self.root / "session.next").write_bytes(b"partial")
        self.assertEqual((self.root / "session.next").read_bytes(), b"partial")

    def test_symlink_roots_and_locks_are_not_followed(self):
        alias = self.parent / "alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks unavailable")
        with self.assertRaises(ParisonError):
            with _read_owner(alias):
                self.fail("symlink root admitted")
        lock = self.root / ".lock"
        lock.rename(self.root / "original-lock")
        lock.symlink_to(self.root / "original-lock")
        with self.assertRaises(ParisonError):
            with _read_owner(self.root):
                self.fail("symlink lock admitted")

    def test_real_process_exclusion_and_kernel_release_after_kill(self):
        marker = self.parent / "ready"
        script = (
            "import sys,time;from pathlib import Path;"
            "from parison.partition_sessions import _read_owner;"
            "root=Path(sys.argv[1]);marker=Path(sys.argv[2]);"
            "context=_read_owner(root);context.__enter__();"
            "marker.write_text('ready');time.sleep(60)"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", script, str(self.root), str(marker)], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            deadline = time.monotonic() + 15
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(marker.exists(), "child ownership startup failed")
            started = time.monotonic()
            with self.assertRaises(ParisonError):
                with _read_owner(self.root):
                    self.fail("competing process admitted")
            self.assertLess(time.monotonic() - started, 2)
            child.kill()
            child.communicate(timeout=15)
            with _read_owner(self.root) as (_, check):
                check()
            self.assertEqual((self.root / ".lock").read_bytes(), b"\0")
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=15)
