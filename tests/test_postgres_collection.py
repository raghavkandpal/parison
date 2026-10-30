"""Offline collection trust-boundary regressions."""

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

from parison import cli, source_collection
from parison.analysis import _canonical
from parison.core import ParisonError

FIXTURE = Path(__file__).parent / "fixtures" / "postgres_collection"


class CollectionVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / "collection"
        shutil.copytree(FIXTURE / "expected", self.bundle)

    def read(self, name):
        return json.loads((self.bundle / name).read_bytes())

    def write(self, name, value):
        (self.bundle / name).write_bytes(_canonical(value) + b"\n")

    def rehash(self):
        receipt = self.read("receipt.json")
        data = (self.bundle / "receipt.json").read_bytes()
        self.write("summary.json", source_collection.collection_summary(receipt, data))
        self.rehash_manifest()

    def rehash_manifest(self):
        manifest = self.read("manifest.json")
        for name in manifest["files"]:
            manifest["files"][name] = hashlib.sha256((self.bundle / name).read_bytes()).hexdigest()
        self.write("manifest.json", manifest)

    def test_golden_offline_and_compact_cli(self):
        expected = self.read("summary.json")
        self.assertEqual(source_collection.verify_postgres_collection(self.bundle), expected)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli.main(["verify-postgres-collection", str(self.bundle)]), 0)
        self.assertEqual(out.getvalue().encode(), _canonical(expected) + b"\n")
        self.assertEqual(err.getvalue(), "")
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            cli.main(["verify-postgres-collection", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(out.getvalue(), (FIXTURE / "verify-help.txt").read_text())

    def test_semantic_negative_corpus(self):
        for case in json.loads((FIXTURE / "semantic-negative.json").read_bytes()):
            with self.subTest(case=case["case"]):
                if case["schema"] == "plan":
                    with self.assertRaises(ParisonError):
                        source_collection.validate_postgres_collection_plan(case["value"])
                else:
                    shutil.rmtree(self.bundle)
                    shutil.copytree(FIXTURE / "expected", self.bundle)
                    self.write(case["schema"] + ".json", case["value"])
                    if case["schema"] == "receipt":
                        self.rehash()
                    elif case["schema"] == "summary":
                        self.rehash_manifest()
                    with self.assertRaises(ParisonError):
                        source_collection.verify_postgres_collection(self.bundle)

    def test_parent_integer_tokens_and_bindings(self):
        original = self.read("receipt.json")
        for value in (True, 1.0, None, [], "1"):
            for field in ("postgres_collection_receipt_version", "observed.rows", "observed.elapsed_ms"):
                with self.subTest(field=field, value=value):
                    receipt = copy.deepcopy(original)
                    if "." in field:
                        receipt["observed"][field.split(".")[1]] = value
                    else:
                        receipt[field] = value
                    self.write("receipt.json", receipt)
                    self.rehash()
                    with self.assertRaises(ParisonError):
                        source_collection.verify_postgres_collection(self.bundle)
        self.write("receipt.json", original)
        for field, value in (("snapshot", "wrong"), ("read_only", False)):
            receipt = copy.deepcopy(original)
            receipt["transaction"][field] = value
            self.write("receipt.json", receipt)
            self.rehash()
            with self.assertRaises(ParisonError):
                source_collection.verify_postgres_collection(self.bundle)

    def test_child_profile_and_only_semantics_cannot_be_relabelled(self):
        receipt = self.read("receipt.json")
        receipt["capability_profile"] = source_collection.ONLY_PROFILE
        self.write("receipt.json", receipt)
        self.rehash()
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)
        shutil.rmtree(self.bundle)
        shutil.copytree(FIXTURE / "only-expected", self.bundle)
        child = self.bundle / "tables" / "orders" / "receipt.json"
        value = json.loads(child.read_bytes())
        value["selection"]["sql"] = value["selection"]["sql"].replace(" FROM ONLY ", " FROM ")
        child.write_bytes(_canonical(value) + b"\n")
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)

    def test_only_child_summary_requires_exact_types(self):
        from parison.source_receipt import verify_postgres_export

        for field, value in (("postgres_source_summary_version", 1.0), ("rows", True), ("complete", 1)):
            shutil.rmtree(self.bundle)
            shutil.copytree(FIXTURE / "only-expected", self.bundle)
            child = self.bundle / "tables" / "orders"
            summary = json.loads((child / "summary.json").read_bytes())
            summary[field] = value
            data = _canonical(summary) + b"\n"
            (child / "summary.json").write_bytes(data)
            manifest = json.loads((child / "manifest.json").read_bytes())
            manifest["files"]["summary.json"] = hashlib.sha256(data).hexdigest()
            (child / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
            with self.assertRaises(ParisonError):
                verify_postgres_export(child)

    def test_limits_and_noncanonical_or_extra_files(self):
        receipt = self.read("receipt.json")
        receipt["limits"]["max_output_bytes"] = 1
        self.write("receipt.json", receipt)
        self.rehash()
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)
        shutil.rmtree(self.bundle)
        shutil.copytree(FIXTURE / "expected", self.bundle)
        (self.bundle / "receipt.json").write_text('{"a":1,"a":2}\n')
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)
        (self.bundle / "unexpected").write_text("private")
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)

    @unittest.skipUnless(os.name == "posix", "POSIX links and FIFO")
    def test_unsafe_fifo_and_symlink_rejected_without_reading(self):
        child = self.bundle / "tables" / "orders" / "data.csv"
        child.unlink()
        os.mkfifo(child)
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)
        child.unlink()
        child.symlink_to(FIXTURE.resolve() / "expected/tables/orders/data.csv")
        with self.assertRaises(ParisonError):
            source_collection.verify_postgres_collection(self.bundle)

    def test_mutation_during_pinned_verification(self):
        real = source_collection._verify_handles

        def mutate(handles):
            result = real(handles)
            with (self.bundle / "receipt.json").open("ab") as handle:
                handle.write(b" ")
            return result

        with patch.object(source_collection, "_verify_handles", side_effect=mutate):
            with self.assertRaises(ParisonError):
                source_collection.verify_postgres_collection(self.bundle)

    def test_cli_errors_do_not_echo_private_values(self):
        for args in ([str(self.bundle), "--bad", "private-token"], ["private-path"], []):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(cli.main(["verify-postgres-collection", *args]), 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(
                err.getvalue(), "parison verify-postgres-collection: invalid or incomplete collection evidence\n"
            )
        with patch.object(source_collection, "verify_postgres_collection", side_effect=KeyboardInterrupt):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(cli.main(["verify-postgres-collection", str(self.bundle)]), 130)
            self.assertEqual(err.getvalue(), "parison verify-postgres-collection: interrupted\n")

    def test_late_directory_members_rejected(self):
        real = source_collection._verify_handles
        for parent in (self.bundle, self.bundle / "tables", self.bundle / "tables" / "orders"):
            with self.subTest(parent=parent.name):
                extra = parent / "unexpected"

                def mutate(handles, extra=extra):
                    result = real(handles)
                    extra.write_text("unbound")
                    return result

                with patch.object(source_collection, "_verify_handles", side_effect=mutate):
                    with self.assertRaises(ParisonError):
                        source_collection.verify_postgres_collection(self.bundle)
                extra.unlink()
