"""Exact hash discovery, bounded snapshots and adversarial publication gates."""

import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from parison import partition_discovery as discovery
from parison.analysis import _canonical
from parison.comparison import compare
from parison.core import ParisonError

FIXTURE = Path(__file__).parent / "fixtures" / "partition_hash"


class HashExecution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("recipe.json", "plan.json", "baseline.csv", "candidate.csv"):
            shutil.copyfile(FIXTURE / name, self.root / name)
        self.plan = json.loads((self.root / "plan.json").read_bytes())
        self.recipe = json.loads((self.root / "recipe.json").read_bytes())
        self.output = self.root / "evidence"

    def run_discovery(self):
        (self.root / "plan.json").write_bytes(_canonical(self.plan) + b"\n")
        (self.root / "recipe.json").write_bytes(_canonical(self.recipe) + b"\n")
        return discovery.discover(
            *(self.root / name for name in ("plan.json", "recipe.json", "baseline.csv", "candidate.csv")), self.output
        )

    def replay(self):
        return discovery.verify(
            self.output, *(self.root / name for name in ("recipe.json", "baseline.csv", "candidate.csv"))
        )

    def assert_clean(self):
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".evidence-*")))

    def test_production_matches_every_golden_byte_and_exact_replay(self):
        context = json.loads((FIXTURE / "expected" / "receipt.json").read_bytes())["normalization_runtime"]
        with patch.object(discovery, "_execution_context", return_value=context):
            summary = self.run_discovery()
            for name in ("plan", "receipt", "summary", "manifest"):
                self.assertEqual(
                    (self.output / f"{name}.json").read_bytes(), (FIXTURE / "expected" / f"{name}.json").read_bytes()
                )
            self.assertEqual(self.replay(), {**summary, "verification": "exact-source-backed"})
        self.assertEqual(
            {p.name for p in self.output.iterdir()},
            {f"{name}.json" for name in ("plan", "receipt", "summary", "manifest")},
        )

    def test_production_key_vectors_and_inclusive_frame_budget(self):
        for vector in json.loads((FIXTURE / "key-vectors.json").read_bytes()):
            names = [f"k{i}" for i in range(len(vector["values"]))]
            recipe = {
                "keys": names,
                "columns": {name: {"type": kind} for name, kind in zip(names, vector["types"], strict=True)},
            }
            parsed = dict(zip(names, vector["values"], strict=True))
            encoded = bytes.fromhex(vector["hex"])
            self.assertEqual(discovery._hash_key(parsed, recipe, len(encoded)), encoded)
            with self.assertRaises(ParisonError):
                discovery._hash_key(parsed, recipe, len(encoded) - 1)
            for count, bucket in vector["buckets"].items():
                self.assertEqual(discovery._hash_bucket(encoded, int(count)), bucket)
        recipe = {"keys": ["k"], "columns": {"k": {"type": "string"}}}
        overhead = len(discovery._hash_key({"k": ""}, recipe, 65536))
        for value in ("a" * (65536 - overhead), "é" * ((65536 - overhead) // 2)):
            self.assertLessEqual(len(discovery._hash_key({"k": value}, recipe, 65536)), 65536)
            with self.assertRaises(ParisonError):
                discovery._hash_key({"k": value + "aa"}, recipe, 65536)
        with self.assertRaises(UnicodeError):
            discovery._hash_key({"k": "\ud800"}, recipe, 65536)

    def test_every_bucket_count_and_forced_collision_preserve_exact_oracle(self):
        oracle = compare(
            self.root / "recipe.json", self.root / "baseline.csv", self.root / "candidate.csv", sample_limit=0
        )
        self.plan["limits"]["max_staged_bytes"] = 100000
        for buckets in range(2, 129):
            self.plan["routing"]["buckets"] = buckets
            result = self.run_discovery()
            for name in ("counts", "outcome", "complete", "discrepancy_count"):
                self.assertEqual(result[name], oracle[name], (buckets, name))
            shutil.rmtree(self.output)
        with patch.object(discovery, "_hash_bucket", return_value=0):
            result = self.run_discovery()
            self.assertEqual(result["counts"], oracle["counts"])
            self.assertEqual(self.replay()["verification"], "exact-source-backed")
        with self.assertRaises(ParisonError):
            self.replay()

    def test_empty_null_duplicate_and_permuted_inputs_match_full_engine(self):
        header = b"tenant,id,amount\r\n"
        cases = (
            (b"", b""),
            (b"", b"a,1,1.00\r\n"),
            (b"NULL,1,1.00\r\n", b"MISSING,1,1.00\r\n"),
            (b"A,1,1.00\r\na,1,1.00\r\n", b"a,1,1.00\r\n"),
            (b"a,1,1.00\r\n", b"A,1,1.00\r\na,1,1.00\r\n"),
            (b"b,2,2.00\r\na,1,1.00\r\n", b"A,1,1.00\r\nB,2,2.00\r\n"),
            (b",1,1.00\r\n", b",1,1.00\r\n"),
        )
        for expected_empty in (False, True):
            self.recipe["scope"]["expected_empty"] = expected_empty
            for left, right in cases:
                (self.root / "baseline.csv").write_bytes(header + left)
                (self.root / "candidate.csv").write_bytes(header + right)
                result = self.run_discovery()
                receipt = json.loads((self.output / "receipt.json").read_bytes())
                oracle = compare(
                    self.root / "recipe.json", self.root / "baseline.csv", self.root / "candidate.csv", sample_limit=0
                )
                for name in ("counts", "field_counts", "discrepancy_count", "outcome", "complete"):
                    self.assertEqual(receipt[name], oracle[name], (expected_empty, left, right, name))
                self.assertEqual(self.replay()["outcome"], result["outcome"])
                shutil.rmtree(self.output)

    def test_each_budget_rejects_without_publication_or_sensitive_staging(self):
        for name, value in (
            ("max_input_bytes", 10),
            ("max_rows_per_input", 1),
            ("max_rows_per_partition_side", 1),
            ("max_partition_bytes", 1),
            ("max_staged_bytes", 1),
            ("max_key_bytes", 1),
        ):
            original = copy.deepcopy(self.plan)
            self.plan["limits"][name] = value
            with patch.object(discovery, "_hash_bucket", return_value=0):
                with self.assertRaisesRegex(ParisonError, discovery._HASH_ERROR):
                    self.run_discovery()
            self.assert_clean()
            self.plan = original

    def test_source_recipe_snapshot_and_bucket_mutations_abort(self):
        original_compare = discovery.compare
        for kind in ("source", "recipe", "snapshot", "bucket", "membership"):

            def mutate(*args, kind=kind, **kwargs):
                workspace = Path(args[0]).parent
                if kind == "membership":
                    (workspace / "unexpected").write_bytes(b"private")
                else:
                    path = {
                        "source": self.root / "baseline.csv",
                        "recipe": self.root / "recipe.json",
                        "snapshot": workspace / "snapshot-baseline.csv",
                        "bucket": workspace / "baseline-0.csv",
                    }[kind]
                    data = path.read_bytes()
                    path.write_bytes(data + b" ")
                    path.write_bytes(data)  # ABA bytes still changes the pinned stamp.
                return original_compare(*args, **kwargs)

            with self.subTest(kind=kind), patch.object(discovery, "compare", side_effect=mutate):
                with self.assertRaises(ParisonError):
                    self.run_discovery()
                self.assert_clean()

    def test_replay_rejects_changed_sources_recipe_and_evidence_during_execution(self):
        self.run_discovery()
        for name in ("baseline.csv", "candidate.csv", "recipe.json"):
            path = self.root / name
            data = path.read_bytes()
            if name == "recipe.json":
                changed = json.loads(data)
                changed["scope"]["snapshot"] = "changed-source-claim"
                path.write_bytes(_canonical(changed))
            else:
                path.write_bytes(data + b" ")
            with self.assertRaises(ParisonError):
                self.replay()
            path.write_bytes(data)
        original_compare = discovery.compare

        def mutate(*args, **kwargs):
            path = self.output / "receipt.json"
            data = path.read_bytes()
            path.write_bytes(data + b" ")
            path.write_bytes(data)
            return original_compare(*args, **kwargs)

        with patch.object(discovery, "compare", side_effect=mutate), self.assertRaises(ParisonError):
            self.replay()

    def test_source_and_snapshot_replacement_during_routing_abort(self):
        original_rows = discovery._iter_input_rows
        for kind in ("source", "snapshot"):

            def replace(path, *args, kind=kind, **kwargs):
                changed = self.root / "baseline.csv" if kind == "source" else Path(path)
                saved = changed.with_name(changed.name + ".saved")
                changed.rename(saved)
                changed.write_bytes(saved.read_bytes())
                changed.unlink()
                saved.rename(changed)
                yield from original_rows(path, *args, **kwargs)

            with patch.object(discovery, "_iter_input_rows", side_effect=replace), self.assertRaises(ParisonError):
                self.run_discovery()
            self.assert_clean()

    def test_maximum_arity_and_column_count_use_original_exact_policy(self):
        template = self.recipe["columns"]["tenant"]
        self.recipe["columns"] = {f"k{i:03}": copy.deepcopy(template) for i in range(100)}
        self.recipe["keys"] = list(reversed(list(self.recipe["columns"])[:16]))
        header = ",".join(reversed(self.recipe["columns"])) + "\r\n"
        for side in ("baseline", "candidate"):
            (self.root / f"{side}.csv").write_text(
                header + ",".join(["A" if side == "baseline" else "a"] * 100) + "\r\n", newline=""
            )
        self.plan["limits"].update(max_input_bytes=10000, max_staged_bytes=100000, max_partition_bytes=10000)
        self.assertEqual(self.run_discovery()["outcome"], "PASS")
        self.assertEqual(self.replay()["outcome"], "PASS")

    def test_source_symlink_and_oversized_recipe_are_rejected(self):
        source = self.root / "baseline.csv"
        saved = self.root / "saved.csv"
        source.rename(saved)
        try:
            source.symlink_to(saved)
        except OSError:
            saved.rename(source)
        else:
            with self.assertRaises(ParisonError):
                self.run_discovery()
            self.assert_clean()
            source.unlink()
            saved.rename(source)
        (self.root / "recipe.json").write_bytes(b" " * 262145)
        with self.assertRaises(ParisonError):
            discovery.discover(
                self.root / "plan.json",
                self.root / "recipe.json",
                self.root / "baseline.csv",
                self.root / "candidate.csv",
                self.output,
            )
        self.assert_clean()

    def test_runtime_mismatch_and_partial_arguments_do_not_open_sources(self):
        self.run_discovery()
        for arguments in (("secret", None, None), ("secret", "left", "right")):
            with (
                patch.object(
                    discovery,
                    "_execution_context",
                    return_value={"implementation": "CPython", "python_version": "3.15.0", "unicode_version": "16.0.0"},
                ),
                patch.object(discovery, "_pinned_hash_input", side_effect=AssertionError("source opened")),
            ):
                with self.assertRaises(ParisonError):
                    discovery.verify(self.output, *arguments)
        with patch.object(discovery.platform, "python_implementation", return_value="PyPy"):
            with self.assertRaises(ParisonError):
                self.replay()

    def test_interruption_in_each_phase_and_raced_target_are_clean(self):
        for seam in (
            "_directory",
            "_pinned_hash_input",
            "_iter_input_rows",
            "compare",
            "_verified_hash_evidence",
            "rename_no_replace",
        ):
            with self.subTest(seam=seam), patch.object(discovery, seam, side_effect=KeyboardInterrupt):
                with self.assertRaises(discovery._HashInterrupted):
                    self.run_discovery()
                self.assert_clean()
        original = discovery.rename_no_replace

        def race(stage, target):
            target.mkdir()
            (target / "owner").write_text("keep")
            original(stage, target)

        with patch.object(discovery, "rename_no_replace", side_effect=race):
            with self.assertRaises(ParisonError):
                self.run_discovery()
        self.assertEqual((self.output / "owner").read_text(), "keep")
        self.assertFalse(list(self.root.glob(".evidence-*")))

    def test_cli_status_and_safe_error(self):
        self.run_discovery()
        shutil.rmtree(self.output)
        args = [
            "discover",
            "--plan",
            str(self.root / "plan.json"),
            "--recipe",
            str(self.root / "recipe.json"),
            "--baseline",
            str(self.root / "baseline.csv"),
            "--candidate",
            str(self.root / "candidate.csv"),
            "--output",
            str(self.output),
        ]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(discovery.main(args), 1)
        self.assertEqual(json.loads(out.getvalue())["outcome"], "FAIL")
        self.assertEqual(err.getvalue(), "")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(discovery.main(args), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "parison-partitions: " + discovery._HASH_ERROR + "\n")

    def test_owned_stage_cleanup_preserves_replacement_and_removes_snapshots(self):
        original_run = discovery._run_hash
        for path_mode in (False, True):
            moved = self.root / "moved-stage"
            replacement = None

            def replace(*args, moved=moved, **kwargs):
                nonlocal replacement
                result = original_run(*args, **kwargs)
                replacement = Path(args[4]).parent
                replacement.rename(moved)
                replacement.mkdir()
                (replacement / "owner").write_bytes(b"keep")
                return result

            with patch.object(discovery, "_run_hash", side_effect=replace):
                if path_mode:
                    with patch.object(discovery, "_directory", return_value=None), self.assertRaises(ParisonError):
                        self.run_discovery()
                else:
                    with self.assertRaises(ParisonError):
                        self.run_discovery()
            if not replacement.exists():
                self.assert_clean()  # Windows rejects the stage rename while owned.
                self.assertFalse(moved.exists())
                continue
            self.assertEqual((replacement / "owner").read_bytes(), b"keep")
            self.assertFalse(list(moved.rglob("snapshot-*.csv")))
            self.assertFalse(self.output.exists())
            shutil.rmtree(replacement)
            if moved.exists():
                shutil.rmtree(moved)

    def test_stage_substitution_cannot_write_metadata_into_unrelated_directory(self):
        unrelated = self.root / "unrelated"
        unrelated.mkdir()
        (unrelated / "owner").write_bytes(b"keep")
        original_remove = discovery.shutil.rmtree
        substituted = False

        def replace(path, *args, **kwargs):
            nonlocal substituted
            result = original_remove(path, *args, **kwargs)
            if not substituted and Path(path).name == "temporary":
                substituted = True
                stage = next(self.root.glob(".evidence-*"))
                stage.rename(self.root / "moved-stage")
                try:
                    stage.symlink_to(unrelated, target_is_directory=True)
                except OSError:
                    stage.mkdir()
                    (stage / "owner").write_bytes(b"keep")
            return result

        with patch.object(discovery.shutil, "rmtree", side_effect=replace), self.assertRaises(ParisonError):
            self.run_discovery()
        self.assertEqual({p.name for p in unrelated.iterdir()}, {"owner"})
        self.assertFalse(self.output.exists())
        self.assertFalse(list((self.root / "moved-stage").rglob("snapshot-*.csv")))

    def test_partial_snapshot_interruption_and_candidate_only_failure_clean_sensitive_files(self):
        original_pin = discovery._pinned_hash_input
        for side in ("baseline", "candidate"):

            def interrupt(stack, path, limit, side=side):
                handle, check = original_pin(stack, path, limit)
                if Path(path).name != f"{side}.csv":
                    return handle, check

                class PartialRead:
                    reads = 0

                    def read(self, size):
                        self.reads += 1
                        if self.reads > 1:
                            raise KeyboardInterrupt
                        return handle.read(5)

                return PartialRead(), check

            with (
                patch.object(discovery, "_pinned_hash_input", side_effect=interrupt),
                self.assertRaises(discovery._HashInterrupted),
            ):
                self.run_discovery()
            self.assert_clean()
        self.plan["limits"]["max_rows_per_input"] = 3
        candidate = self.root / "candidate.csv"
        candidate.write_bytes(candidate.read_bytes() + b"extra,8,8.00\r\n")
        with self.assertRaises(ParisonError):
            self.run_discovery()
        self.assert_clean()

    def test_path_mode_replay_rejects_directory_substitution_with_identical_hardlinks(self):
        self.run_discovery()
        clone = self.root / "clone"
        clone.mkdir()
        for path in self.output.iterdir():
            try:
                (clone / path.name).hardlink_to(path)
            except OSError:
                self.skipTest("hardlinks unavailable")
        original_compare = discovery.compare
        replaced = False

        def replace(*args, **kwargs):
            nonlocal replaced
            if not replaced:
                replaced = True
                self.output.rename(self.root / "saved")
                clone.rename(self.output)
            return original_compare(*args, **kwargs)

        with (
            patch.object(discovery, "_directory", return_value=None),
            patch.object(discovery, "compare", side_effect=replace),
            self.assertRaises(ParisonError),
        ):
            self.replay()

    def test_stage_substitution_before_workspace_creation_cannot_chmod_unrelated_directory(self):
        unrelated = self.root / "unrelated-mode"
        unrelated.mkdir(mode=0o755)
        original = discovery._directory
        before = unrelated.stat().st_mode
        changed = False

        def replace(stack, path, *args, **kwargs):
            nonlocal changed
            result = original(stack, path, *args, **kwargs)
            if not changed and Path(path).name.startswith(".evidence-"):
                changed = True
                Path(path).rename(self.root / "moved-before-workspace")
                try:
                    Path(path).symlink_to(unrelated, target_is_directory=True)
                except OSError:
                    Path(path).mkdir()
            return result

        with patch.object(discovery, "_directory", side_effect=replace), self.assertRaises(ParisonError):
            self.run_discovery()
        self.assertEqual(unrelated.stat().st_mode, before)
        self.assertEqual(list(unrelated.iterdir()), [])

    @unittest.skipUnless(discovery.os.name == "posix", "POSIX fallback capability reacquisition")
    def test_cleanup_fallback_reacquires_identity_after_deletion_boundary_substitution(self):
        stage = self.root / "cleanup-owned"
        stage.mkdir()
        (stage / "snapshot.csv").write_bytes(b"private")
        identity = stage.stat().st_dev, stage.stat().st_ino
        moved = self.root / "cleanup-moved"
        original = discovery.os.open
        changed = False

        def replace(path, *args, **kwargs):
            nonlocal changed
            if not changed and Path(path) == stage:
                changed = True
                stage.rename(moved)
                stage.mkdir()
                (stage / "owner").write_bytes(b"keep")
            return original(path, *args, **kwargs)

        with patch.object(discovery.os, "open", side_effect=replace):
            discovery._cleanup_hash_stage(stage, identity, None)
        self.assertEqual((stage / "owner").read_bytes(), b"keep")
        self.assertFalse((moved / "snapshot.csv").exists())

    @unittest.skipUnless(discovery.os.name == "nt", "native Windows directory delete-share lock")
    def test_windows_directory_pin_prevents_directory_rename(self):
        from contextlib import ExitStack

        stage = self.root / "windows-owned"
        stage.mkdir()
        (stage / "snapshot.csv").write_bytes(b"private")
        with ExitStack() as stack:
            discovery._windows_directory_pin(stack, stage)
            with self.assertRaises(OSError):
                stage.rename(self.root / "windows-moved")
        identity = stage.stat().st_dev, stage.stat().st_ino
        discovery._cleanup_hash_stage(stage, identity, None)
        self.assertFalse(stage.exists())

    @unittest.skipUnless(discovery.os.name == "posix", "POSIX metadata uses a verified directory capability")
    def test_metadata_open_substitution_cannot_redirect_even_with_path_mode_reader(self):
        unrelated = self.root / "unrelated-metadata"
        unrelated.mkdir()
        original = discovery.os.open
        changed = False

        def replace(path, flags, *args, **kwargs):
            nonlocal changed
            if not changed and Path(path).name == "plan.json" and flags & discovery.os.O_EXCL:
                changed = True
                stage = next(self.root.glob(".evidence-*"))
                stage.rename(self.root / "moved-at-open")
                stage.symlink_to(unrelated, target_is_directory=True)
            return original(path, flags, *args, **kwargs)

        with (
            patch.object(discovery, "_directory", return_value=None),
            patch.object(discovery.os, "open", side_effect=replace),
            self.assertRaises(ParisonError),
        ):
            self.run_discovery()
        self.assertTrue(changed)
        self.assertEqual(list(unrelated.iterdir()), [])
        self.assertFalse(list((self.root / "moved-at-open").iterdir()))

    @unittest.skipUnless(discovery.os.name == "nt", "native Windows metadata ownership pin")
    def test_windows_metadata_write_holds_directory_rename_lock(self):
        original = discovery.os.open
        checked = False

        def attempt(path, flags, *args, **kwargs):
            nonlocal checked
            if not checked and Path(path).name == "plan.json" and flags & discovery.os.O_EXCL:
                checked = True
                stage = next(self.root.glob(".evidence-*"))
                with self.assertRaises(OSError):
                    stage.rename(self.root / "windows-metadata-moved")
            return original(path, flags, *args, **kwargs)

        with patch.object(discovery.os, "open", side_effect=attempt):
            self.assertEqual(self.run_discovery()["outcome"], "FAIL")
        self.assertTrue(checked)
        self.assertEqual(self.replay()["verification"], "exact-source-backed")

    @unittest.skipUnless(discovery.os.name == "nt", "native Windows sensitive workspace ownership pin")
    def test_windows_snapshot_and_bucket_writes_hold_workspace_rename_lock(self):
        original = discovery.os.open
        checked = set()

        def attempt(path, flags, *args, **kwargs):
            name = Path(path).name
            if name in {"snapshot-baseline.csv", "baseline-0.csv"} and flags & discovery.os.O_EXCL:
                checked.add(name)
                workspace = Path(path).parent
                with self.assertRaises(OSError):
                    workspace.rename(self.root / "windows-workspace-moved")
            return original(path, flags, *args, **kwargs)

        with patch.object(discovery.os, "open", side_effect=attempt):
            self.assertEqual(self.run_discovery()["outcome"], "FAIL")
        self.assertEqual(checked, {"snapshot-baseline.csv", "baseline-0.csv"})
        self.assertEqual(self.replay()["verification"], "exact-source-backed")

    def test_replay_setup_root_substitution_preserves_unrelated_replacement(self):
        original = discovery._hash_directory
        replacement = None

        def replace(stack, root):
            nonlocal replacement
            result = original(stack, root)
            if root.name.startswith("parison-hash-replay-"):
                root.rename(self.root / "replay-moved")
                root.mkdir()
                (root / "owner").write_bytes(b"keep")
                replacement = root
                self.addCleanup(shutil.rmtree, root)
            return result

        with patch.object(discovery, "_hash_directory", side_effect=replace), self.assertRaises(ParisonError):
            with discovery._hash_replay_workspace():
                self.fail("substituted replay root admitted")
        self.assertEqual({p.name for p in replacement.iterdir()}, {"owner"})
        self.assertFalse(list((self.root / "replay-moved").rglob("snapshot-*.csv")))
