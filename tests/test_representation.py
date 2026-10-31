"""Collection-v2 offline trust boundary and native-fact replay regressions."""

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

from parison import cli, postgres_collection, source_collection
from parison.analysis import _canonical
from parison.core import ParisonError

FIXTURE = Path(__file__).parent / "fixtures" / "postgres_representation"


class RepresentationVerification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "collection"
        shutil.copytree(FIXTURE / "candidate", self.root)

    def read(self, name):
        return json.loads((self.root / name).read_bytes())

    def write(self, name, value):
        (self.root / name).write_bytes(_canonical(value) + b"\n")

    def rehash(self):
        receipt = self.read("receipt.json")
        metadata = (self.root / "representation.json").read_bytes()
        receipt["representation_sha256"] = hashlib.sha256(metadata).hexdigest()
        receipt["observed"]["representation_bytes"] = len(metadata)
        self.write("receipt.json", receipt)
        self.write(
            "summary.json", source_collection.collection_summary(receipt, (self.root / "receipt.json").read_bytes())
        )
        manifest = self.read("manifest.json")
        manifest["files"] = {
            name: hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in manifest["files"]
        }
        self.write("manifest.json", manifest)

    def verify(self):
        return source_collection.verify_postgres_collection(self.root)

    def mutate(self, path, value):
        metadata = self.read("representation.json")
        at = metadata
        for key in path[:-1]:
            at = at[key]
        at[path[-1]] = value
        self.write("representation.json", metadata)
        self.rehash()

    def test_both_golden_profiles_and_safe_existing_cli(self):
        for side in ("baseline", "candidate"):
            root = FIXTURE / side
            self.assertEqual(
                source_collection.verify_postgres_collection(root), json.loads((root / "summary.json").read_bytes())
            )
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli.main(["verify-postgres-collection", str(self.root)]), 0)
        self.assertEqual(out.getvalue().encode(), _canonical(self.read("summary.json")) + b"\n")
        self.assertEqual(err.getvalue(), "")
        for private in ("public", "orders", "database-a", "reader", "source-a", "id", "note"):
            self.assertNotIn(f'"{private}"', out.getvalue())

    def test_frozen_metadata_runtime_rejections_after_rehash(self):
        cases = json.loads((FIXTURE / "semantic-negative.json").read_bytes())
        for case in cases:
            if case["schema"] != "postgres-representation-v1":
                continue
            with self.subTest(case=case["case"]):
                self.write("representation.json", case["value"])
                self.rehash()
                with self.assertRaises(ParisonError):
                    self.verify()

    def test_exact_tokens_unknown_members_and_byte_caps(self):
        original = self.read("representation.json")
        column = ["tables", "orders", "columns", 0]
        cases = [
            (["representation_version"], 1.0),
            (["source", "server_version_num"], 180006.0),
            (["transaction", "read_only"], 1),
            ([*column, "ordinal"], True),
            ([*column, "numeric", "precision"], 32.0),
            ([*column, "materialization", "has_default"], 0),
            ([*column, "type", "oid"], True),
            ([*column, "type", "typmod"], -1.0),
            ([*column, "type", "display"], "é" * 257),
            ([*column, "extra"], "secret"),
            (["session", "sql"], "secret"),
        ]
        for path, value in cases:
            with self.subTest(path=path):
                self.write("representation.json", original)
                self.mutate(path, value)
                with self.assertRaises(ParisonError):
                    self.verify()

    def test_replays_signed_numeric_length_and_datetime(self):
        original = self.read("representation.json")
        column = copy.deepcopy(original["tables"]["orders"]["columns"][1])
        column.update(name="amount", ordinal=3, selected=False)
        column["collation"] = copy.deepcopy(original["tables"]["orders"]["columns"][0]["collation"])
        column["type"].update(name="numeric", oid=1700, typmod=133121, display="numeric(2,-3)")
        column["numeric"].update(state="known", precision=2, radix=10, scale=-3, raw_scale=2045)
        column["characters"]["state"] = "not-applicable"
        original["tables"]["orders"]["columns"].append(column)
        self.write("representation.json", original)
        self.rehash()
        self.verify()
        for key, value in (("scale", -2), ("raw_scale", -3), ("precision", 3)):
            with self.subTest(key=key):
                self.write("representation.json", original)
                self.mutate(["tables", "orders", "columns", 2, "numeric", key], value)
                with self.assertRaises(ParisonError):
                    self.verify()
        for kind, typmod, dimension, facts in (
            (
                "numeric",
                -1,
                "numeric",
                {"state": "unbounded", "precision": None, "radix": 10, "scale": None, "raw_scale": None},
            ),
            ("varchar", 16, "characters", {"state": "known", "max_length": 12}),
            ("timestamp", -1, "datetime", {"state": "known", "precision": 6, "timezone": "naive"}),
            ("timestamptz", 0, "datetime", {"state": "known", "precision": 0, "timezone": "aware"}),
        ):
            with self.subTest(kind=kind):
                metadata = copy.deepcopy(original)
                fact = metadata["tables"]["orders"]["columns"][2]
                fact["type"].update(name=kind, typmod=typmod)
                fact["numeric"] = {
                    "state": "not-applicable",
                    "precision": None,
                    "radix": None,
                    "scale": None,
                    "raw_scale": None,
                }
                fact[dimension] = facts
                if kind == "varchar":
                    fact["collation"] = copy.deepcopy(metadata["tables"]["orders"]["columns"][1]["collation"])
                self.write("representation.json", metadata)
                self.rehash()
                self.verify()
                wrong = copy.deepcopy(facts)
                wrong[next(k for k in wrong if k not in {"state", "radix", "timezone", "raw_scale", "scale"})] = 7
                self.mutate(["tables", "orders", "columns", 2, dimension], wrong)
                with self.assertRaises(ParisonError):
                    self.verify()

    def test_pg18_unknown_not_null_and_unsupported_inventory(self):
        metadata = self.read("representation.json")
        note = metadata["tables"]["orders"]["columns"][1]
        note["nullability"] = {
            "declared_not_null": True,
            "information_schema_nullable": "NO",
            "constraints": [{"name": "note_nn", "validated": False, "enforced": True}],
            "guarantee": "unknown",
        }
        self.write("representation.json", metadata)
        self.rehash()
        self.verify()
        extra = copy.deepcopy(note)
        extra.update(name="opaque", ordinal=3, selected=False)
        extra["type"].update(schema="private", name="domain", supported=False)
        extra["nullability"]["guarantee"] = "unknown"
        extra["numeric"]["state"] = "unsupported"
        extra["characters"]["state"] = "unsupported"
        extra["datetime"]["state"] = "unsupported"
        metadata["tables"]["orders"]["columns"].append(extra)
        self.write("representation.json", metadata)
        self.rehash()
        self.verify()
        self.mutate(["tables", "orders", "columns", 2, "nullability", "guarantee"], "non-null")
        with self.assertRaises(ParisonError):
            self.verify()

    def test_builtin_provider_version_profiles(self):
        original = self.read("representation.json")
        metadata = copy.deepcopy(original)
        collation = metadata["tables"]["orders"]["columns"][1]["collation"]
        collation.update(provider="builtin", origin="explicit", name="pg_c", collate=None, ctype=None, locale="C")
        for key in ("recorded_version", "actual_version"):
            collation[key] = {"state": "known", "value": "1"}
        known = copy.deepcopy(collation)
        self.write("representation.json", metadata)
        self.rehash()
        self.verify()
        # Missing observations stay unknown; they cannot claim not-versioned.
        for key in ("recorded_version", "actual_version"):
            collation[key] = {"state": "unknown", "value": None}
        self.write("representation.json", metadata)
        self.rehash()
        self.verify()
        collation["actual_version"] = {"state": "not-versioned", "value": None}
        self.write("representation.json", metadata)
        self.rehash()
        with self.assertRaises(ParisonError):
            self.verify()
        # The native builtin provider was introduced after the PG16 profile.
        shutil.rmtree(self.root)
        shutil.copytree(FIXTURE / "baseline", self.root)
        self.mutate(["tables", "orders", "columns", 1, "collation"], known)
        with self.assertRaises(ParisonError):
            self.verify()

    def test_metadata_over_old_json_limit_and_physical_inventory_cap(self):
        metadata = self.read("representation.json")
        table = metadata["tables"]["orders"]
        template = table["columns"][1]
        for ordinal in range(3, 101):
            column = copy.deepcopy(template)
            column.update(name=f"extra_{ordinal}", ordinal=ordinal, selected=False)
            column["collation"]["rules"] = "x" * 4096
            table["columns"].append(column)
        self.write("representation.json", metadata)
        self.rehash()
        self.assertGreater((self.root / "representation.json").stat().st_size, 256 * 1024)
        self.verify()
        column = copy.deepcopy(template)
        column.update(name="overflow", ordinal=101, selected=False)
        table["columns"].append(column)
        self.write("representation.json", metadata)
        self.rehash()
        with self.assertRaises(ParisonError):
            self.verify()

    def test_version_membership_and_metadata_resource_limits(self):
        receipt = self.read("receipt.json")
        for version in (True, 1.0, 3):
            with self.subTest(version=version):
                self.write("receipt.json", {**receipt, "postgres_collection_receipt_version": version})
                with self.assertRaises(ParisonError):
                    self.verify()
        self.write("receipt.json", receipt)
        self.write("receipt.json", {**receipt, "limits": {**receipt["limits"], "max_representation_bytes": 1}})
        with patch("parison.source_collection._verify_handles") as children:
            with self.assertRaises(ParisonError):
                self.verify()
            children.assert_not_called()
        self.write("receipt.json", receipt)
        (self.root / "representation.json").unlink()
        with self.assertRaises(ParisonError):
            self.verify()

    @unittest.skipUnless(os.name == "posix", "POSIX symlink and pinned-directory checks")
    def test_representation_symlink_and_mutation_rejected(self):
        member = self.root / "representation.json"
        private = self.root.parent / "outside.json"
        member.rename(private)
        member.symlink_to(private)
        with self.assertRaises(ParisonError):
            self.verify()
        member.unlink()
        private.rename(member)
        original = source_collection.validate_representation

        def mutate(*args):
            answer = original(*args)
            with member.open("ab") as handle:
                handle.write(b" ")
            return answer

        with patch("parison.source_collection.validate_representation", side_effect=mutate):
            with self.assertRaises(ParisonError):
                self.verify()

    def test_v2_plan_validation_preserves_explicit_limits(self):
        plan = json.loads((FIXTURE / "capture-plan.json").read_bytes())
        self.assertEqual(source_collection.validate_postgres_collection_plan(plan), plan)
        self.assertEqual(postgres_collection._load_plan(FIXTURE / "capture-plan.json"), plan)
        for maximum in (False, 0, 16777217, 1.0):
            with self.subTest(maximum=maximum):
                value = copy.deepcopy(plan)
                value["limits"]["max_representation_bytes"] = maximum
                with self.assertRaises(ParisonError):
                    source_collection.validate_postgres_collection_plan(value)


if __name__ == "__main__":
    unittest.main()
