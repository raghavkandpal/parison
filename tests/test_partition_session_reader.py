"""Owned preview recognizes retained bytes, never sources or cached execution truth."""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from parison import partition_discovery as discovery
from parison import partition_sessions as sessions
from parison.analysis import _canonical
from parison.cli import main
from parison.core import ParisonError

ROOT = Path(__file__).parent / "fixtures/partition_session"
PROFILES = ("range-original", "range-reordered", "hash", "hash-pass", "hash-inconclusive")


def write(path, value):
    path.write_bytes(_canonical(value) + b"\n")


def read(path):
    return json.loads(path.read_bytes())


class SessionReader(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "session"

    def materialize(self, profile="hash", state="ready"):
        if self.root.exists():
            shutil.rmtree(self.root)
        source = ROOT / profile
        self.root.mkdir()
        (self.root / ".lock").write_bytes(b"\0")
        shutil.copyfile(source / "plan.json", self.root / "plan.json")
        shutil.copyfile(source / f"journals/{state}.json", self.root / "session.json")
        journal = read(self.root / "session.json")
        (self.root / "routing").mkdir()
        (self.root / "results").mkdir()
        if journal["routing"] is not None:
            for name in journal["routing"]["files"]:
                shutil.copyfile(source / "routing" / name, self.root / "routing" / name)
        for index, item in enumerate(journal["results"]):
            if item is not None:
                shutil.copyfile(source / f"results/{index}.json", self.root / f"results/{index}.json")
        return journal

    def assert_invalid(self):
        with self.assertRaisesRegex(ParisonError, "^invalid partition session$"):
            sessions.preview(self.root)

    def test_recognition_borrows_writer_lock_and_closes_before_mutation(self):
        for profile in PROFILES:
            with self.subTest(profile=profile):
                expected = self.materialize(profile)
                with sessions._write_owner(self.root) as (fd, native, owned):
                    with patch.object(sessions, "_acquire", side_effect=AssertionError("recursive ownership")):
                        journal, plan, used = sessions._recognize_owned(self.root, fd, native, owned)
                    self.assertEqual(journal, expected)
                    self.assertEqual(used, sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()))
                    self.assertEqual(plan, read(self.root / "plan.json"))
                    # Recognition's child pins must close, including on Windows.
                    child = self.root / "routing" / "derived-recipe.json"
                    child.unlink()
                    child.write_bytes(b"replacement after recognition")
                    owned()

    def test_recognition_rejects_changed_root_under_writer_ownership(self):
        self.materialize()
        original = sessions._metadata
        changed = False

        def mutate(data):
            nonlocal changed
            if not changed:
                changed = True
                (self.root / "session.next").write_bytes(b"uncommitted")
            return original(data)

        with sessions._write_owner(self.root) as (fd, native, owned):
            with patch.object(sessions, "_metadata", side_effect=mutate):
                with self.assertRaises(ParisonError):
                    sessions._recognize_owned(self.root, fd, native, owned)
            owned()

    def stage_abandoning(self, check=None):
        with sessions._write_owner(self.root) as (fd, native, owned):
            return sessions._stage_abandoning(self.root, fd, native, check or owned)

    def test_abandonment_staging_preserves_primary_and_all_profiles_states(self):
        for profile in PROFILES:
            for state in ("initializing", "routed", "comparing", "ready", "published", "abandoning"):
                with self.subTest(profile=profile, state=state):
                    journal = self.materialize(profile, state)
                    before = {
                        str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
                    }
                    stamp = self.stage_abandoning()
                    self.assertEqual(stamp, discovery._named_file_stamp(self.root / "session.next"))
                    self.assertEqual(
                        (self.root / "session.next").read_bytes(), _canonical(journal | {"state": "abandoning"}) + b"\n"
                    )
                    for name, data in before.items():
                        self.assertEqual((self.root / name).read_bytes(), data)
                    self.assertEqual(sessions.preview(self.root)["state"], state)
                    if state == "ready":
                        self.assertEqual(
                            (self.root / "session.next").read_bytes(),
                            (ROOT / profile / "journals/abandoning.json").read_bytes(),
                        )

    def test_abandonment_staging_storage_reservation_before_slot_creation(self):
        for extra in (-1, 0):
            with self.subTest(extra=extra):
                journal = self.materialize()
                for _ in range(4):
                    write(self.root / "session.json", journal)
                    total = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
                    proposed = _canonical(journal | {"state": "abandoning"}) + b"\n"
                    journal["max_session_bytes"] = total + len(proposed) + extra
                write(self.root / "session.json", journal)
                if extra == -1:
                    with self.assertRaises(ParisonError):
                        self.stage_abandoning()
                    self.assertFalse((self.root / "session.next").exists())
                else:
                    self.stage_abandoning()
                    self.assertEqual(
                        sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()), journal["max_session_bytes"]
                    )

    def test_abandonment_staging_never_overwrites_existing_slot(self):
        for data in (b"", b'{"partial":', (ROOT / "hash/journals/published.json").read_bytes()):
            self.materialize()
            slot = self.root / "session.next"
            slot.write_bytes(data)
            with self.assertRaises(ParisonError):
                self.stage_abandoning()
            self.assertEqual(slot.read_bytes(), data)
            self.assertEqual(sessions.preview(self.root)["state"], "ready")

    def test_abandonment_staging_interruption_and_storage_failure_leave_primary(self):
        for failure in (KeyboardInterrupt(), OSError("disk full")):
            self.materialize()
            primary = (self.root / "session.json").read_bytes()
            with patch.object(sessions.os, "fsync", side_effect=failure):
                with self.assertRaises(type(failure) if isinstance(failure, KeyboardInterrupt) else ParisonError):
                    self.stage_abandoning()
            self.assertEqual((self.root / "session.json").read_bytes(), primary)
            self.assertEqual(sessions.preview(self.root)["state"], "ready")

    def test_abandonment_staging_interruption_before_write_leaves_bounded_empty_slot(self):
        self.materialize()
        with sessions._write_owner(self.root) as (fd, native, owned):

            def interrupt():
                owned()
                if (self.root / "session.next").exists():
                    raise KeyboardInterrupt

            with self.assertRaises(KeyboardInterrupt):
                sessions._stage_abandoning(self.root, fd, native, interrupt)
        self.assertEqual((self.root / "session.next").read_bytes(), b"")
        self.assertEqual(sessions.preview(self.root)["state"], "ready")

    def test_abandonment_staging_rejects_primary_changes_during_write(self):
        self.materialize()
        primary = self.root / "session.json"
        original = primary.read_bytes()
        sync = sessions.os.fsync

        def change(descriptor):
            sync(descriptor)
            primary.write_bytes(original)

        with patch.object(sessions.os, "fsync", side_effect=change):
            with self.assertRaises(ParisonError):
                self.stage_abandoning()
        self.assertEqual(primary.read_bytes(), original)
        self.assertEqual(sessions.preview(self.root)["state"], "ready")

    def test_abandonment_staging_detects_corruption_before_returning_identity(self):
        self.materialize()
        sync = sessions.os.fsync

        def corrupt(descriptor):
            sync(descriptor)
            slot = self.root / "session.next"
            data = slot.read_bytes()
            slot.write_bytes(data.replace(b"abandoning", b"corrupted"))

        with patch.object(sessions.os, "fsync", side_effect=corrupt):
            with self.assertRaises(ParisonError):
                self.stage_abandoning()
        self.assertEqual(sessions.preview(self.root)["state"], "ready")

    def test_abandonment_staging_rejects_malformed_primary_and_symlink_slot(self):
        self.materialize()
        (self.root / "session.json").write_bytes(b"invalid")
        with self.assertRaises(ParisonError):
            self.stage_abandoning()
        self.assertFalse((self.root / "session.next").exists())
        self.materialize()
        outside = self.parent / "outside"
        outside.write_bytes(b"preserve")
        try:
            (self.root / "session.next").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ParisonError):
            self.stage_abandoning()
        self.assertEqual(outside.read_bytes(), b"preserve")

    def test_all_profiles_states_are_safe_read_only_queries(self):
        for profile in PROFILES:
            for state in ("initializing", "routed", "comparing", "ready", "published", "abandoning"):
                with self.subTest(profile=profile, state=state):
                    self.materialize(profile, state)
                    before = {
                        str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()
                    }
                    with (
                        patch.object(discovery, "compare", side_effect=AssertionError("comparison")),
                        patch.object(discovery, "_source", side_effect=AssertionError("original input")),
                        patch.object(discovery, "load_recipe", side_effect=AssertionError("original recipe")),
                    ):
                        response = sessions.preview(self.root)
                    self.assertEqual(response, read(ROOT / profile / "responses/preview.json") | {"state": state})
                    self.assertEqual(
                        before,
                        {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()},
                    )

    def test_only_primary_journal_is_authority_and_next_is_unchanged(self):
        for data in (b'{"partial":', (ROOT / "hash/journals/published.json").read_bytes()):
            self.materialize(state="comparing")
            (self.root / "session.next").write_bytes(data)
            self.assertEqual(sessions.preview(self.root)["state"], "comparing")
            self.assertEqual((self.root / "session.next").read_bytes(), data)
        for data in (None, b'{"partial":', b'{"state":"ready","state":"published"}\n'):
            self.materialize()
            (self.root / "session.next").write_bytes((ROOT / "hash/journals/published.json").read_bytes())
            if data is None:
                (self.root / "session.json").unlink()
            else:
                (self.root / "session.json").write_bytes(data)
            self.assert_invalid()

    def test_partial_initializing_and_uncommitted_comparing_files(self):
        self.materialize(state="initializing")
        (self.root / "routing/snapshot-baseline.csv").write_bytes(b"partial")
        (self.root / "routing/derived-recipe.json").write_bytes(b'{"part')
        self.assertEqual(sessions.preview(self.root)["state"], "initializing")
        journal = self.materialize(state="comparing")
        index = next(i for i, item in enumerate(journal["results"]) if item is None)
        (self.root / f"results/{index}.json").write_bytes(b'{"part')
        self.assertEqual(sessions.preview(self.root)["state"], "comparing")

    def test_missing_malformed_changed_committed_members_reject(self):
        for member, data in (
            ("routing/baseline-0.csv", None),
            ("results/0.json", b'{"part'),
            ("routing/snapshot-baseline.csv", b"changed"),
            ("routing/derived-recipe.json", b"{}"),
            ("plan.json", b"{}\n"),
        ):
            with self.subTest(member=member):
                self.materialize()
                path = self.root / member
                if data is None:
                    path.unlink()
                else:
                    path.write_bytes(data)
                self.assert_invalid()

    def test_unexpected_members_directories_and_reparse_entries_reject(self):
        for member in ("secret", "routing/foreign", "results/003.json", "results/128.json"):
            self.materialize()
            (self.root / member).write_bytes(b"do not expose")
            self.assert_invalid()
        for member in ("session.next", "routing/baseline-0.csv", "results/0.json"):
            self.materialize()
            path = self.root / member
            if path.exists():
                path.unlink()
            path.mkdir()
            self.assert_invalid()

    def test_storage_bound_includes_lock_journal_plan_next_and_uncommitted_bytes(self):
        journal = self.materialize()

        def set_budget(bound):
            journal["max_session_bytes"] = bound
            write(self.root / "session.json", journal)

        set_budget(10000)
        total = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
        set_budget(total)
        # Iterate to include the budget token's own canonical serialized size.
        total = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
        set_budget(total)
        self.assertEqual(total, sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()))
        sessions.preview(self.root)
        (self.root / "session.next").write_bytes(b"x")
        self.assert_invalid()
        self.assertEqual((self.root / "session.next").read_bytes(), b"x")

    def test_caps_apply_even_to_uncommitted_members(self):
        for member, size, state in (
            ("session.next", 1048577, "ready"),
            ("routing/derived-recipe.json", 262145, "initializing"),
            ("routing/snapshot-baseline.csv", 1001, "initializing"),
            ("results/1.json", 1048577, "comparing"),
        ):
            self.materialize(state=state)
            with (self.root / member).open("wb") as handle:
                handle.truncate(size)
            self.assert_invalid()

    def test_abandoning_recognizes_missing_known_files_without_reuse(self):
        for profile in ("range-original", "hash", "hash-inconclusive"):
            self.materialize(profile, "abandoning")
            for member in (
                "routing/snapshot-baseline.csv",
                "routing/derived-recipe.json",
                "plan.json",
                "results/0.json",
            ):
                (self.root / member).unlink()
                with self.subTest(profile=profile, missing=member):
                    self.assertEqual(sessions.preview(self.root)["state"], "abandoning")
            shutil.rmtree(self.root / "routing")
            shutil.rmtree(self.root / "results")
            self.assertEqual(sessions.preview(self.root)["state"], "abandoning")

    def test_coherent_forgery_is_only_not_executed_preview(self):
        journal = self.materialize()
        forged = read(ROOT / "coherent-forgery.json")
        index = forged["child"]["index"]
        write(self.root / f"results/{index}.json", forged["child"])
        journal["results"][index] = forged["descriptor"]
        write(self.root / "session.json", journal)
        self.assertEqual(sessions.preview(self.root)["execution_assurance"], "not-executed")

    def test_competing_owner_and_interruption_release(self):
        self.materialize()
        with sessions._read_owner(self.root):
            self.assert_invalid()
        with patch.object(sessions, "_derived", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                sessions.preview(self.root)
        sessions.preview(self.root)

    def test_transient_cached_file_changes_are_detected(self):
        self.materialize()
        actual = sessions._checkpoint

        def change(*args):
            path = self.root / "routing/baseline-0.csv"
            original = path.read_bytes()
            path.write_bytes(original.replace(b"1", b"2"))
            path.write_bytes(original)
            return actual(*args)

        with patch.object(sessions, "_checkpoint", side_effect=change):
            self.assert_invalid()

    def test_symlink_members_are_not_followed(self):
        self.materialize()
        outside = self.parent / "outside"
        outside.write_bytes(b"private")
        for member in ("session.next", "routing/baseline-0.csv", "results/0.json"):
            self.materialize()
            path = self.root / member
            if path.exists():
                path.unlink()
            try:
                path.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assert_invalid()
            self.assertEqual(outside.read_bytes(), b"private")

    def test_canonical_and_alias_cli_safe_response_errors_and_interruption(self):
        self.materialize(state="published")
        for invoke, argv in (
            (main, ["partitions", "session", "preview", str(self.root)]),
            (discovery.main, ["session", "preview", str(self.root)]),
        ):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(invoke(argv), 0)
            self.assertEqual(json.loads(out.getvalue()), sessions.preview(self.root))
            self.assertEqual(err.getvalue(), "")
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(sessions, "_derived", side_effect=KeyboardInterrupt),
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            self.assertEqual(main(["partitions", "session", "preview", str(self.root)]), 130)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn(str(self.root), err.getvalue())
        (self.root / "secret").write_bytes(b"secret-value")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main(["partitions", "session", "preview", str(self.root)]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "parison-partitions: invalid partition session\n")

    @unittest.skipUnless(sys.platform != "win32", "POSIX descriptor-limit qualification")
    def test_128_partition_preview_under_64_descriptor_limit(self):
        journal = self.materialize()
        plan = read(self.root / "plan.json")
        plan["routing"]["buckets"] = 128
        plan["limits"]["max_staged_bytes"] = 200000
        write(self.root / "plan.json", plan)
        journal["identity"]["plan_sha256"] = hashlib.sha256(_canonical(plan)).hexdigest()
        journal["max_session_bytes"] = 1000000
        routing = journal["routing"]
        header = b'"amount","id","tenant"\r\n'
        # Metadata claims here are synthetic, not fresh routing assertions.
        for index in range(3, 128):
            record = {"bucket": index}
            for side in ("baseline", "candidate"):
                path = self.root / f"routing/{side}-{index}.csv"
                path.write_bytes(header)
                descriptor = {"bytes": len(header), "sha256": hashlib.sha256(header).hexdigest()}
                routing["files"][path.name] = descriptor
                record[side] = descriptor | {"rows": 0}
            routing["receipt"]["partitions"].append(record)
            child = read(self.root / "results/0.json")
            child["index"] = index
            child["inputs"] = {side: record[side] for side in ("baseline", "candidate")}
            result = child["result"]
            result["counts"] = dict.fromkeys(result["counts"], 0)
            result["field_counts"] = {name: dict.fromkeys(value, 0) for name, value in result["field_counts"].items()}
            result.update(discrepancy_count=0, outcome="PASS")
            data = _canonical(child) + b"\n"
            (self.root / f"results/{index}.json").write_bytes(data)
            journal["results"].append({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        routing["receipt"]["staged_bytes"] = sum(value["bytes"] for value in routing["files"].values())
        write(self.root / "session.json", journal)
        command = "import resource,sys; from parison.partition_sessions import preview; resource.setrlimit(resource.RLIMIT_NOFILE,(64,64)); assert preview(sys.argv[1])['execution_assurance']=='not-executed'"
        result = subprocess.run(
            [sys.executable, "-c", command, str(self.root)], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_transient_nested_directory_rename_is_denied_or_detected(self):
        self.materialize()
        actual = sessions._checkpoint
        attempted = False
        denied = False

        def rename(*args):
            nonlocal attempted, denied
            if not attempted:
                attempted = True
                path = self.root / "routing"
                saved = self.root / "saved"
                try:
                    path.rename(saved)
                except PermissionError:
                    denied = True
                else:
                    saved.rename(path)
            return actual(*args)

        detected = False
        with patch.object(sessions, "_checkpoint", side_effect=rename):
            try:
                sessions.preview(self.root)
            except ParisonError:
                detected = True
        self.assertTrue(attempted and (denied or detected))
        sessions.preview(self.root)

    @unittest.skipUnless(os.name == "nt", "native Windows junction qualification")
    def test_windows_nested_junction_is_rejected_and_preserved(self):
        self.materialize()
        original = self.parent / "original-routing"
        (self.root / "routing").rename(original)
        junction = self.root / "routing"
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(original)], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        try:
            self.assert_invalid()
            self.assertTrue((original / "snapshot-baseline.csv").exists())
        finally:
            os.rmdir(junction)
        original.rename(self.root / "routing")

    def test_recorded_foreign_context_does_not_establish_current_eligibility(self):
        journal = self.materialize(state="initializing")
        journal["identity"]["normalization_runtime"]["python_version"] = "3.11.1"
        journal["identity"]["engine"]["package_sha256"] = "a" * 64
        write(self.root / "session.json", journal)
        with patch.object(discovery, "_execution_context", side_effect=AssertionError("current admission")):
            self.assertEqual(sessions.preview(self.root)["execution_assurance"], "not-executed")

    def test_namespace_enumeration_stops_at_fixed_member_count(self):
        self.materialize()

        class TooMany:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def __iter__(self):
                for index in range(7):
                    yield type("Entry", (), {"name": f"unexpected-{index}"})()
                raise AssertionError("enumeration exceeded the fixed root bound")

        with patch.object(sessions.os, "scandir", return_value=TooMany()):
            self.assert_invalid()

    def test_initializing_enforces_plan_cumulative_staged_cap(self):
        self.materialize(state="initializing")
        for side in ("baseline", "candidate"):
            for index in range(3):
                (self.root / f"routing/{side}-{index}.csv").write_bytes(b"x" * 1500)
        self.assert_invalid()

    def test_range_initializing_staged_accounting_excludes_snapshots_and_recipe(self):
        self.materialize("range-original", "initializing")
        plan = read(self.root / "plan.json")
        plan["limits"]["max_staged_bytes"] = 100
        write(self.root / "plan.json", plan)
        journal = read(self.root / "session.json")
        journal["identity"]["plan_sha256"] = hashlib.sha256(_canonical(plan)).hexdigest()
        write(self.root / "session.json", journal)
        (self.root / "routing/snapshot-baseline.csv").write_bytes(b"x" * 1000)
        (self.root / "routing/derived-recipe.json").write_bytes(b"x" * 1000)
        (self.root / "routing/baseline-0.csv").write_bytes(b"x" * 100)
        sessions.preview(self.root)
        (self.root / "routing/candidate-0.csv").write_bytes(b"x")
        self.assert_invalid()
