"""Synthetic Windows-only handle-disposition experiment; not product qualification.

Run: python -m unittest tests.test_partition_disposition_native
No repository/runtime imports. Creates and removes only a temporary workspace.
"""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

LIMIT = 1_048_576


def native():
    from ctypes import wintypes as w

    class Info(ctypes.Structure):
        _fields_ = [
            ("attrs", w.DWORD),
            ("created", w.FILETIME),
            ("accessed", w.FILETIME),
            ("written", w.FILETIME),
            ("volume", w.DWORD),
            ("size_high", w.DWORD),
            ("size_low", w.DWORD),
            ("links", w.DWORD),
            ("index_high", w.DWORD),
            ("index_low", w.DWORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    kernel.GetFileInformationByHandle.argtypes = [w.HANDLE, ctypes.POINTER(Info)]
    kernel.GetFileInformationByHandle.restype = w.BOOL
    kernel.SetFileInformationByHandle.argtypes = [w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD]
    kernel.SetFileInformationByHandle.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL

    def opened(path, access, sharing=3):
        # OPEN_EXISTING; open reparse itself. Directory pins allow READ|WRITE.
        handle = kernel.CreateFileW(str(path), access, sharing, None, 3, 0x02200000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def close(handle):
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def slot(path):
        # Deny new WRITE/DELETE handles; incompatible existing handles also fail.
        # This probe does not qualify preexisting writable memory mappings.
        handle = opened(path, 0x80010080, 1)  # GENERIC_READ|DELETE|READ_ATTRIBUTES
        info = Info()
        try:
            if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
                raise ctypes.WinError(ctypes.get_last_error())
            if info.attrs & (0x400 | 0x10) or (info.size_high << 32 | info.size_low) > LIMIT:
                raise ValueError("refused slot type or size")
        except BaseException:
            close(handle)
            raise
        return handle

    def dispose(handle):
        delete = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO contains BOOLEAN.
        if not kernel.SetFileInformationByHandle(handle, 4, ctypes.byref(delete), 1):
            raise ctypes.WinError(ctypes.get_last_error())

    return opened, slot, dispose, close


def worker(root, phase):
    opened, slot, dispose, close = native()
    pin = opened(root, 0x81)  # LIST_DIRECTORY|READ_ATTRIBUTES
    handle = None
    try:
        handle = slot(root / "session.next")
        if phase == "marked":
            dispose(handle)
        print("READY", flush=True)
        command = sys.stdin.readline().strip()
        if command == "delete":
            dispose(handle)
        elif command != "close":
            raise ValueError("invalid worker command")
    finally:
        if handle is not None:
            close(handle)
        close(pin)


def operations(root):
    def write():
        with (root / "session.next").open("r+b") as stream:
            stream.write(b"X")

    def truncate():
        with (root / "session.next").open("r+b") as stream:
            stream.truncate(0)

    return (
        lambda: os.unlink(root / "session.next"),
        lambda: os.replace(root / "session.next", root / "moved"),
        lambda: os.replace(root / "replacement", root / "session.next"),
        write,
        truncate,
    )


def interfere(root, control=False):
    # This is a separate process, deliberately taking no Parison lock.
    errors = []
    for operation in operations(root):
        if control:
            (root / "session.next").write_bytes(b"uncommitted synthetic journal\n")
            (root / "replacement").write_bytes(b"unrelated replacement\n")
        try:
            operation()
        except OSError as exc:
            if control:
                raise AssertionError("unpinned control operation failed") from exc
            errors.append(exc.winerror)
        else:
            if not control:
                raise AssertionError("namespace/content interference unexpectedly succeeded")
    assert all(code in {5, 32, 33} for code in errors), errors
    print(json.dumps(errors))


def check():
    opened, slot, dispose, close = native()
    script = str(Path(__file__).resolve())
    passed = 0
    with tempfile.TemporaryDirectory(prefix="parison-disposition-probe-") as directory:
        root = Path(directory)
        primary = root / "session.json"
        primary.write_bytes(b"synthetic committed primary\n")
        next_slot = root / "session.next"
        replacement = root / "replacement"
        control = subprocess.run(
            [sys.executable, script, "control", str(root)], capture_output=True, text=True, timeout=20
        )
        assert control.returncode == 0, "unpinned interference controls failed: " + control.stderr[-1200:]
        (root / "moved").unlink()
        next_slot.unlink()
        passed += 1
        for phase, command, should_exist in (
            ("opened", "close", True),
            ("opened", "kill", True),
            ("opened", "delete", False),
            ("marked", "close", False),
            ("marked", "kill", False),
        ):
            next_slot.write_bytes(b"uncommitted synthetic journal\n")
            replacement.write_bytes(b"unrelated replacement\n")
            process = subprocess.Popen(
                [sys.executable, script, "worker", str(root), phase],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                # communicate cannot be used until interference finishes; readiness
                # is bounded by the subprocess timeout in the separate reader below.
                ready = []
                reader = threading.Thread(
                    target=lambda process=process, ready=ready: ready.append(process.stdout.readline()), daemon=True
                )
                reader.start()
                reader.join(20)
                assert not reader.is_alive() and ready == ["READY\n"], "worker did not become ready"
                result = subprocess.run(
                    [sys.executable, script, "interfere", str(root)], capture_output=True, text=True, timeout=20
                )
                assert result.returncode == 0, (
                    f"interference probe failed ({phase}/{command}): " + result.stderr[-1200:]
                )
                assert replacement.read_bytes() == b"unrelated replacement\n"
                assert not (root / "moved").exists()
                if command == "kill":
                    process.kill()
                    process.communicate(timeout=20)
                else:
                    _, error = process.communicate(command + "\n", timeout=20)
                    assert process.returncode == 0, "worker close/disposition failed: " + error[-400:]
                assert next_slot.exists() == should_exist, "unexpected close/kill disposition"
                if should_exist:
                    assert next_slot.read_bytes() == b"uncommitted synthetic journal\n"
                    # Retry acquires a new handle only after process death/close.
                    handle = slot(next_slot)
                    try:
                        dispose(handle)
                    finally:
                        close(handle)
                    assert not next_slot.exists(), "retry did not delete owned slot"
                assert primary.read_bytes() == b"synthetic committed primary\n"
                # A subsequent independent entry must survive: disposition is
                # attached to the now-closed old handle, not future slot names.
                next_slot.write_bytes(b"post-close unrelated entry\n")
                assert next_slot.read_bytes() == b"post-close unrelated entry\n"
                next_slot.unlink()
                passed += 1
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=20)

        # Existing access/sharing conflicts must refuse admission before any
        # disposition; a prior writer remains incompatible even if it shares all.
        for access, sharing in ((0x40000000, 7), (0x80000000, 1)):
            next_slot.write_bytes(b"preexisting handle bytes\n")
            previous = opened(next_slot, access, sharing)
            try:
                try:
                    unexpected = slot(next_slot)
                except OSError as exc:
                    assert exc.winerror == 32, "expected sharing violation"
                else:
                    close(unexpected)
                    raise AssertionError("incompatible preexisting handle accepted")
            finally:
                close(previous)
            assert next_slot.read_bytes() == b"preexisting handle bytes\n"
            next_slot.unlink()
            passed += 1

        # A prior read-only handle sharing DELETE is compatible. Basic
        # disposition stays pending until the last handle closes (Microsoft
        # DeleteFile documentation); do not call slot-close alone deletion success.
        next_slot.write_bytes(b"reader-delayed deletion\n")
        previous = opened(next_slot, 0x80000000, 5)  # SHARE_READ|SHARE_DELETE
        try:
            handle = slot(next_slot)
            try:
                dispose(handle)
            finally:
                close(handle)
            assert "session.next" in os.listdir(root), "pending entry unexpectedly vanished"
            try:
                unexpected = slot(next_slot)
            except OSError as exc:
                assert exc.winerror in {5, 32}, "expected delete-pending refusal"
            else:
                close(unexpected)
                raise AssertionError("delete-pending entry reopened")
        finally:
            close(previous)
        assert not next_slot.exists(), "last-reader close did not finish deletion"
        assert primary.read_bytes() == b"synthetic committed primary\n"
        passed += 1

        # Refusals never call disposition and preserve the object and primary.
        for kind in ("oversized", "directory", "junction"):
            if kind == "oversized":
                next_slot.write_bytes(b"x" * (LIMIT + 1))
            elif kind == "directory":
                next_slot.mkdir()
            else:
                target = root / "junction-target"
                target.mkdir()
                (target / "sentinel").write_bytes(b"preserve target")
                made = subprocess.run(
                    ["cmd", "/d", "/c", "mklink", "/J", str(next_slot), str(target)],
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                assert made.returncode == 0, "junction construction failed; probe incomplete"
                assert next_slot.lstat().st_file_attributes & 0x400
            try:
                handle = slot(next_slot)
            except ValueError:
                pass
            else:
                close(handle)
                raise AssertionError("unsafe slot accepted")
            assert next_slot.exists()
            assert primary.read_bytes() == b"synthetic committed primary\n"
            if kind == "oversized":
                assert next_slot.stat().st_size == LIMIT + 1
                next_slot.unlink()
            else:
                next_slot.rmdir()
                if kind == "junction":
                    assert (target / "sentinel").read_bytes() == b"preserve target"
            passed += 1
        target_file = root / "symlink-target"
        target_file.write_bytes(b"preserve file target")
        try:
            next_slot.symlink_to(target_file)
        except OSError as exc:
            if exc.winerror != 1314:
                raise
            print("SKIP: file symlink refusal (Windows privilege absent); junction exercised")
        else:
            try:
                handle = slot(next_slot)
            except ValueError:
                pass
            else:
                close(handle)
                raise AssertionError("file reparse slot accepted")
            assert next_slot.is_symlink()
            assert target_file.read_bytes() == b"preserve file target"
            next_slot.unlink()
            passed += 1
    print(f"PASS: {passed} synthetic native disposition cases; not product qualification")
    print("OUTSTANDING: writable mappings, close failure, filesystem/platform matrix")


@unittest.skipUnless(os.name == "nt", "Windows native disposition experiment")
class NativeDispositionExperiment(unittest.TestCase):
    def test_synthetic_handle_disposition_lifecycle(self):
        check()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "worker":
        worker(Path(sys.argv[2]), sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "interfere":
        interfere(Path(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "control":
        interfere(Path(sys.argv[2]), control=True)
    else:
        unittest.main()
