"""Frozen collection wire examples; acquisition and verification come later."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.analysis import _canonical
from parison.core import load_schema
from parison.source_receipt import verify_postgres_export

FIXTURE = Path(__file__).parent / "fixtures" / "postgres_collection"
EXPECTED = FIXTURE / "expected"


def _read(path):
    return json.loads(path.read_bytes())


def _sha(data):
    return hashlib.sha256(data).hexdigest()


class CollectionWire(unittest.TestCase):
    def test_canonical_examples_and_child_bindings(self):
        plan = _read(FIXTURE / "plan.json")
        receipt = _read(EXPECTED / "receipt.json")
        summary = _read(EXPECTED / "summary.json")
        manifest = _read(EXPECTED / "manifest.json")
        for kind, value in (("plan", plan), ("receipt", receipt), ("summary", summary), ("manifest", manifest)):
            schema = load_schema(f"postgres-collection-{kind}")
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
            path = FIXTURE / "plan.json" if kind == "plan" else EXPECTED / f"{kind}.json"
            self.assertEqual(path.read_bytes(), _canonical(value) + b"\n")
        self.assertEqual(receipt["collection_plan_sha256"], _sha(_canonical(plan)))
        self.assertEqual(summary["receipt_sha256"], _sha((EXPECTED / "receipt.json").read_bytes()))
        self.assertEqual(manifest["table_manifests"], receipt["table_manifests"])
        for name, digest in manifest["files"].items():
            self.assertEqual(digest, _sha((EXPECTED / name).read_bytes()))
        rows = size = 0
        for table_id, selection in plan["tables"].items():
            child = EXPECTED / "tables" / table_id
            verify_postgres_export(child)
            source = _read(child / "receipt.json")
            derived = {"plan_version": 1, "source_id": plan["source_id"], **selection, "limits": plan["limits"]}
            self.assertEqual(source["plan_sha256"], _sha(_canonical(derived)))
            self.assertEqual(receipt["table_manifests"][table_id], _sha((child / "manifest.json").read_bytes()))
            self.assertEqual(source["observed"]["elapsed_ms"], receipt["observed"]["elapsed_ms"])
            rows += source["observed"]["local_rows"]
            size += source["observed"]["output_bytes"]
            # Reused released children must stay byte-identical, including CSV CRLF.
            released = FIXTURE.parent / "postgres_pair" / "tables" / table_id
            for member in child.iterdir():
                self.assertEqual(member.read_bytes(), (released / member.name).read_bytes())
        self.assertEqual((rows, size), (receipt["observed"]["rows"], receipt["observed"]["bytes"]))
        self.assertEqual((summary["rows"], summary["bytes"], summary["tables"]), (rows, size, len(plan["tables"])))

    def test_negative_schema_corpus(self):
        for case in _read(FIXTURE / "schema-negative.json"):
            with self.subTest(case=case["case"]):
                validator = Draft202012Validator(load_schema(f"postgres-collection-{case['schema']}"))
                self.assertFalse(validator.is_valid(case["value"]))

    def test_one_and_sixteen_table_structural_boundaries(self):
        plan = _read(FIXTURE / "plan.json")
        selection = plan["tables"]["orders"]
        validator = Draft202012Validator(load_schema("postgres-collection-plan"))
        for count in (1, 16):
            value = copy.deepcopy(plan)
            value["tables"] = {f"t{i}": {**selection, "table": f"table_{i}"} for i in range(count)}
            validator.validate(value)

    def test_semantic_negative_corpus_requires_runtime_validation(self):
        # These deliberately pass schemas. The future runtime gate must reject
        # each one; schema validation alone must never be called verification.
        cases = _read(FIXTURE / "semantic-negative.json")
        self.assertEqual(len(cases), 7)
        for case in cases:
            with self.subTest(case=case["case"]):
                Draft202012Validator(load_schema(f"postgres-collection-{case['schema']}")).validate(case["value"])


if __name__ == "__main__":
    unittest.main()
