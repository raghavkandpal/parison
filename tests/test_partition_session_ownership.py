"""Kernel exclusion and namespace ownership before any session metadata admission."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from parison.core import ParisonError
from parison.partition_sessions import _read_owner, _write_owner


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

    @unittest.skipUnless(os.name == "posix", "POSIX injected directory-clock qualification")
    def test_namespace_addition_rejects_even_with_unchanged_directory_metadata(self):
        original = self.root.stat()
        actual = os.fstat

        def delayed(descriptor):
            info = actual(descriptor)
            return original if (info.st_dev, info.st_ino) == (original.st_dev, original.st_ino) else info

        with patch("parison.partition_sessions.os.fstat", side_effect=delayed):
            with self.assertRaises(ParisonError):
                with _read_owner(self.root):
                    (self.root / "session.next").write_bytes(b"partial")
        self.assertEqual((self.root / "session.next").read_bytes(), b"partial")

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
        for name in ("_read_owner", "_write_owner"):
            marker = self.parent / name
            script = (
                "import sys,time;from pathlib import Path;"
                "from parison import partition_sessions as sessions;"
                "context=getattr(sessions,sys.argv[3])(sys.argv[1]);context.__enter__();"
                "Path(sys.argv[2]).write_text('ready');time.sleep(60)"
            )
            child = subprocess.Popen(
                [sys.executable, "-c", script, str(self.root), str(marker), name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                deadline = time.monotonic() + 15
                while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(marker.exists(), "child ownership startup failed")
                for owner in (_read_owner, _write_owner):
                    started = time.monotonic()
                    with self.assertRaises(ParisonError):
                        with owner(self.root):
                            self.fail("competing process admitted")
                    self.assertLess(time.monotonic() - started, 2)
                child.kill()
                child.communicate(timeout=15)
                with _write_owner(self.root) as (_, _, check):
                    check()
                self.assertEqual((self.root / ".lock").read_bytes(), b"\0")
            finally:
                if child.poll() is None:
                    child.kill()
                child.communicate(timeout=15)


class SessionWriteOwnership(unittest.TestCase):
    setUp = SessionReadOwnership.setUp

    def test_namespace_changes_require_a_separate_mutating_context(self):
        with _write_owner(self.root) as (descriptor, native, check):
            self.assertEqual(descriptor is None, os.name == "nt")
            self.assertEqual(native is not None, os.name == "nt")
            (self.root / "session.next").write_bytes(b"partial")
            check()
        self.assertEqual((self.root / "session.next").read_bytes(), b"partial")

    def test_write_and_read_owners_exclude_each_other(self):
        for first, second in ((_read_owner, _write_owner), (_write_owner, _read_owner), (_write_owner, _write_owner)):
            with first(self.root):
                with self.assertRaises(ParisonError):
                    with second(self.root):
                        self.fail("competing owner admitted")

    def test_mutating_exceptions_release_without_creating_or_removing_files(self):
        for error in (RuntimeError, KeyboardInterrupt):
            with self.assertRaises(error):
                with _write_owner(self.root):
                    raise error
            with _write_owner(self.root) as (_, _, check):
                check()
        self.assertEqual({p.name for p in self.root.iterdir()}, {".lock", "session.json"})

    def test_writer_root_and_lock_substitution_reject_or_native_pin_denies(self):
        for kind in ("root", "lock"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "session"
                root.mkdir()
                (root / ".lock").write_bytes(b"\0")
                path = root if kind == "root" else root / ".lock"
                saved = Path(temporary) / "saved" if kind == "root" else root / "saved"
                denied = detected = False
                try:
                    with _write_owner(root) as (_, _, check):
                        (root / "session.next").write_bytes(b"partial")
                        check()
                        try:
                            path.rename(saved)
                        except PermissionError:
                            denied = True
                        else:
                            if kind == "root":
                                root.mkdir()
                                (root / "unrelated").write_bytes(b"keep")
                            else:
                                path.write_bytes(b"\0")
                            check()
                except ParisonError:
                    detected = True
                self.assertTrue(denied or detected)
                if kind == "root" and not denied:
                    self.assertEqual((root / "unrelated").read_bytes(), b"keep")

    def test_transient_writer_root_substitution_rejects_or_native_pin_denies(self):
        moved = self.parent / "saved-root"
        denied = detected = False
        try:
            with _write_owner(self.root) as (_, _, check):
                (self.root / "session.next").write_bytes(b"partial")
                check()
                try:
                    self.root.rename(moved)
                except PermissionError:
                    denied = True
                else:
                    self.root.mkdir()
                    self.root.rmdir()
                    moved.rename(self.root)
                    check()
        except ParisonError:
            detected = True
        self.assertTrue(denied or detected)
        self.assertEqual((self.root / "session.next").read_bytes(), b"partial")

    def test_writer_current_directory_uses_actual_parent_guard(self):
        original = Path.cwd()
        try:
            os.chdir(self.root)
            with _write_owner(".") as (_, _, check):
                Path("session.next").write_bytes(b"partial")
                check()
        finally:
            os.chdir(original)
