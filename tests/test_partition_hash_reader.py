"""Pinned hash-v2 integrity reading; production and exact replay stay disabled."""

import copy
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from parison import partition_discovery as discovery
from parison import partition_investigation as investigation
from parison.analysis import _canonical
from parison.cli import main
from parison.core import ParisonError

FIXTURE = Path(__file__).parent / "fixtures" / "partition_hash"


class HashIntegrityReader(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "hash"
        shutil.copytree(FIXTURE / "expected", self.root)

    def read(self, name):
        return json.loads((self.root / name).read_bytes())

    def write(self, name, value):
        (self.root / name).write_bytes(_canonical(value) + b"\n")

    def rehash(self):
        manifest = self.read("manifest.json")
        manifest["files"] = {
            name: hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in manifest["files"]
        }
        self.write("manifest.json", manifest)

    def test_golden_integrity_and_safe_root_legacy_aliases(self):
        expected = {**self.read("summary.json"), "verification": "integrity-only"}
        self.assertEqual(discovery.verify(self.root), expected)
        for prefix in (["partitions"],):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main([*prefix, "verify", str(self.root)]), 0)
            self.assertEqual(json.loads(out.getvalue()), expected)
            self.assertEqual(err.getvalue(), "")
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(discovery.main(["verify", str(self.root)]), 0)
        self.assertEqual(json.loads(out.getvalue()), expected)
        for private in ('"tenant"', '"amount"', '"é"', str(self.root)):
            self.assertNotIn(private, out.getvalue())

    def test_rehashed_semantic_negative_corpus_rejected(self):
        cases = json.loads((FIXTURE / "semantic-negative.json").read_bytes())
        for case in cases:
            with self.subTest(case=case["case"]):
                shutil.rmtree(self.root)
                shutil.copytree(FIXTURE / "expected", self.root)
                self.write(f"{case['schema']}.json", case["value"])
                self.rehash()
                with self.assertRaises(ParisonError):
                    discovery.verify(self.root)

    def test_exact_token_and_closed_shape_rejections(self):
        original = self.read("receipt.json")
        for path, value in (
            (["routing", "buckets"], 3.0),
            (["partitions", 0, "bucket"], False),
            (["derived_recipe_bytes"], True),
            (["normalization_runtime", "python_version"], "3.14.7\n"),
            (["extra"], "private"),
        ):
            with self.subTest(path=path):
                receipt = copy.deepcopy(original)
                target = receipt
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.write("receipt.json", receipt)
                self.rehash()
                with self.assertRaises(ParisonError):
                    discovery.verify(self.root)

    def test_unfamiliar_context_integrity_reading_never_enables_replay_or_creation(self):
        receipt = self.read("receipt.json")
        receipt["normalization_runtime"]["python_version"] = "3.15.0"
        self.write("receipt.json", receipt)
        self.write("summary.json", discovery._summary(receipt))
        self.rehash()
        self.assertEqual(discovery.verify(self.root)["normalization_runtime"]["python_version"], "3.15.0")
        with patch.object(discovery, "_run") as run, patch.object(discovery, "_source") as source:
            with self.assertRaises(ParisonError):
                discovery.verify(self.root, "private-recipe", "private-left", "private-right")
            output = self.root.parent / "output"
            with self.assertRaises(ParisonError):
                discovery.discover(self.root / "plan.json", "private-recipe", "private-left", "private-right", output)
            run.assert_not_called()
            source.assert_not_called()
            self.assertFalse(output.exists())
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main(["partitions", "verify", str(self.root), "--recipe", "private-recipe"]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "parison-partitions: invalid or incomplete hash partition evidence\n")

    def test_canonical_members_bounds_and_pinned_mutation(self):
        plan = self.root / "plan.json"
        plan.write_bytes(plan.read_bytes().rstrip(b"\n"))
        self.rehash()
        with self.assertRaises(ParisonError):
            discovery.verify(self.root)
        shutil.rmtree(self.root)
        shutil.copytree(FIXTURE / "expected", self.root)
        (self.root / "summary.json").write_bytes(b" " * (262144 + 1))
        with self.assertRaises(ParisonError):
            discovery.verify(self.root)
        shutil.rmtree(self.root)
        shutil.copytree(FIXTURE / "expected", self.root)
        actual = discovery._validate_receipt

        def changed(*args):
            actual(*args)
            with (self.root / "receipt.json").open("ab") as handle:
                handle.write(b" ")

        with patch.object(discovery, "_validate_receipt", side_effect=changed):
            with self.assertRaises(ParisonError):
                discovery.verify(self.root)

    @unittest.skipUnless(os.name == "posix", "POSIX non-following descriptors")
    def test_symlinks(self):
        path = self.root / "receipt.json"
        outside = self.root.parent / "outside.json"
        path.rename(outside)
        path.symlink_to(outside)
        with self.assertRaises(ParisonError):
            discovery.verify(self.root)
        path.unlink()
        outside.rename(path)

    def test_interruption_closes_pinned_readers_on_every_platform(self):
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(discovery, "_canonical_json", side_effect=KeyboardInterrupt),
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            self.assertEqual(main(["partitions", "verify", str(self.root)]), 130)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "parison-partitions: hash evidence verification interrupted\n")

    def test_path_mode_replacement_is_detected_without_directory_descriptors(self):
        actual = discovery._validate_receipt

        def replace(*args):
            actual(*args)
            member = self.root / "receipt.json"
            data = member.read_bytes()
            member.rename(self.root.parent / "old-receipt.json")
            member.write_bytes(data)

        with (
            patch.object(discovery, "_directory", return_value=None),
            patch.object(discovery, "_validate_receipt", side_effect=replace),
        ):
            with self.assertRaises(ParisonError):
                discovery.verify(self.root)

    def test_manifest_v1_cannot_dispatch_v2_contents_or_bypass_canonical_checks(self):
        manifest = self.read("manifest.json")
        manifest["partition_manifest_version"] = 1
        self.write("manifest.json", manifest)
        for malformed in (False, True):
            with self.subTest(malformed=malformed):
                if malformed:
                    summary = self.read("summary.json")
                    summary["counts"]["baseline"] = float(summary["counts"]["baseline"])
                    (self.root / "summary.json").write_text(json.dumps(summary, indent=2))
                    self.rehash()
                with self.assertRaises(ParisonError):
                    discovery.verify(self.root)
                with patch.object(discovery, "_run") as run, patch.object(discovery, "_source") as source:
                    with self.assertRaises(ParisonError):
                        discovery.verify(self.root, "private-recipe", "private-left", "private-right")
                    run.assert_not_called()
                    source.assert_not_called()

    def test_complete_hash_counts_must_account_for_every_source_row(self):
        receipt = self.read("receipt.json")
        for partition in receipt["partitions"]:
            partition["counts"] = {name: 1 if name in {"baseline", "candidate"} else 0 for name in partition["counts"]}
            for side in ("baseline", "candidate"):
                partition[side]["rows"] = 1
            partition["field_counts"] = {
                name: {label: 0 for label in labels} for name, labels in partition["field_counts"].items()
            }
            partition.update(complete=True, outcome="PASS")
        receipt["counts"] = {name: 3 if name in {"baseline", "candidate"} else 0 for name in receipt["counts"]}
        receipt["field_counts"] = {
            name: {label: 0 for label in labels} for name, labels in receipt["field_counts"].items()
        }
        receipt.update(complete=True, outcome="PASS", discrepancy_count=0)
        self.write("receipt.json", receipt)
        self.write("summary.json", discovery._summary(receipt))
        self.rehash()
        with self.assertRaises(ParisonError):
            discovery.verify(self.root)

    def test_investigation_v1_explicitly_rejects_hash_evidence(self):
        released = FIXTURE.parent / "partition_investigation" / "expected"
        with self.assertRaisesRegex(ParisonError, "range-v1"):
            investigation.verify_investigation(released, self.root)
        values = discovery._verified_evidence(self.root)
        with (
            patch.object(investigation, "_verified_evidence", return_value=values),
            self.assertRaisesRegex(ParisonError, "range-v1"),
        ):
            investigation._compute({}, self.root, "private-recipe", "private-left", "private-right", self.root.parent)


if __name__ == "__main__":
    unittest.main()
