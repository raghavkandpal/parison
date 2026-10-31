"""Frozen representation structures and runtime obligations; no evaluator yet."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.analysis import _canonical
from parison.core import load_schema
from parison.source_receipt import verify_postgres_export

ROOT = Path(__file__).parent / "fixtures" / "postgres_representation"
SCHEMAS = (
    *(f"postgres-collection-{kind}-v2" for kind in ("plan", "receipt", "summary", "manifest")),
    "postgres-representation-v1",
    *(f"representation-assessment-{kind}-v1" for kind in ("plan", "result", "summary", "manifest")),
    "representation-proposal-v1",
    "representation-proposal-summary-v1",
)


def _read(path):
    return json.loads(path.read_bytes())


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _validate(schema, value):
    Draft202012Validator(load_schema(schema)).validate(value)


class RepresentationWire(unittest.TestCase):
    def test_standalone_schemas_and_canonical_fixtures(self):
        for name in SCHEMAS:
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(load_schema(name))
        for path in ROOT.rglob("*.json"):
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertEqual(path.read_bytes(), _canonical(_read(path)) + b"\n")
        _validate("postgres-collection-plan-v2", _read(ROOT / "capture-plan.json"))
        for side in ("baseline", "candidate"):
            for kind in ("receipt", "summary", "manifest"):
                _validate(f"postgres-collection-{kind}-v2", _read(ROOT / side / f"{kind}.json"))
            _validate("postgres-representation-v1", _read(ROOT / side / "representation.json"))
        for kind, filename in (
            ("plan", "effective-plan"),
            ("result", "assessment"),
            ("summary", "summary"),
            ("manifest", "manifest"),
        ):
            _validate(f"representation-assessment-{kind}-v1", _read(ROOT / "assessment" / f"{filename}.json"))
        for kind, filename in (
            ("representation-proposal-v1", "proposal"),
            ("representation-proposal-summary-v1", "proposal-summary"),
        ):
            _validate(kind, _read(ROOT / f"{filename}.json"))

    def test_capture_bytes_and_child_bindings(self):
        plan = _read(ROOT / "capture-plan.json")
        for side, major in (("baseline", 16), ("candidate", 18)):
            root = ROOT / side
            receipt, summary, manifest, metadata = (
                _read(root / f"{name}.json") for name in ("receipt", "summary", "manifest", "representation")
            )
            self.assertEqual(
                set(p.name for p in root.iterdir()),
                {"receipt.json", "summary.json", "manifest.json", "representation.json", "tables"},
            )
            self.assertEqual(receipt["collection_plan_sha256"], _sha(_canonical(plan)))
            self.assertEqual(metadata["collection_plan_sha256"], receipt["collection_plan_sha256"])
            self.assertEqual(receipt["representation_sha256"], _sha((root / "representation.json").read_bytes()))
            self.assertEqual(summary["receipt_sha256"], _sha((root / "receipt.json").read_bytes()))
            self.assertEqual(summary["representation_bytes"], (root / "representation.json").stat().st_size)
            self.assertEqual(receipt["observed"]["representation_bytes"], summary["representation_bytes"])
            self.assertEqual(metadata["normalization_profile"], f"pg{major}-representation-v1")
            for name, digest in manifest["files"].items():
                self.assertEqual(digest, _sha((root / name).read_bytes()))
            for key in ("source", "transaction", "table_manifests"):
                self.assertEqual(metadata[key], receipt[key])
            self.assertEqual(manifest["table_manifests"], receipt["table_manifests"])
            rows = size = 0
            for table_id, selection in plan["tables"].items():
                child = root / "tables" / table_id
                verify_postgres_export(child)
                source = _read(child / "receipt.json")
                derived = {
                    "plan_version": 2,
                    "source_id": plan["source_id"],
                    **selection,
                    "limits": {k: v for k, v in plan["limits"].items() if k != "max_representation_bytes"},
                }
                self.assertEqual(source["plan_sha256"], _sha(_canonical(derived)))
                self.assertEqual(receipt["table_manifests"][table_id], _sha((child / "manifest.json").read_bytes()))
                for key, value in receipt["source"].items():
                    self.assertEqual(source["source"][key], value)
                for key, value in receipt["transaction"].items():
                    self.assertEqual(source["transaction"][key], value)
                table = metadata["tables"][table_id]
                self.assertEqual(table["selected_columns"], source["source"]["columns"])
                self.assertEqual(table["primary_key"], source["source"]["primary_key"])
                self.assertEqual([c["type"]["name"] for c in table["columns"]], source["source"]["types"])
                self.assertEqual((child / "data.csv").read_bytes(), b"id,note\r\n1,hello\r\n")
                rows += source["observed"]["local_rows"]
                size += source["observed"]["output_bytes"]
            self.assertEqual((rows, size), (summary["rows"], summary["bytes"]))

    def test_assessment_and_unapproved_proposal_bindings(self):
        root = ROOT / "assessment"
        plan, result, summary, manifest = (
            _read(root / f"{name}.json") for name in ("effective-plan", "assessment", "summary", "manifest")
        )
        inputs = {side: _sha((ROOT / side / "manifest.json").read_bytes()) for side in ("baseline", "candidate")}
        self.assertEqual(result["inputs"], inputs)
        for side, digest in inputs.items():
            self.assertEqual(plan[f"{side}_manifest_sha256"], digest)
        self.assertEqual(result["plan_sha256"], _sha(_canonical(plan)))
        self.assertEqual(summary["assessment_sha256"], _sha((root / "assessment.json").read_bytes()))
        for name, digest in manifest["files"].items():
            self.assertEqual(digest, _sha((root / name).read_bytes()))
        self.assertEqual(summary["reason_counts"], {reason: 0 for reason in summary["reason_counts"]})
        self.assertEqual((summary["tables"], summary["fields"]), (2, 4))
        proposal = _read(ROOT / "proposal.json")
        self.assertEqual(proposal["inputs"], inputs)
        for i, table in enumerate(proposal["tables"], 1):
            self.assertEqual(table["id"], f"table_{i}")
            self.assertEqual(table["baseline_id"], sorted(plan["tables"])[i - 1])
            self.assertEqual([f["baseline_name"] for f in table["fields"]], ["id", "note"])
            self.assertEqual([f["id"] for f in table["fields"]], ["field_1", "field_2"])
        proposal_summary = _read(ROOT / "proposal-summary.json")
        self.assertEqual(proposal_summary["proposal_sha256"], _sha((ROOT / "proposal.json").read_bytes()))
        self.assertEqual(proposal_summary["field_suggestions"], 4)

    def test_schema_negative_and_future_runtime_obligations(self):
        for case in _read(ROOT / "schema-negative.json"):
            with self.subTest(case=case["case"]):
                self.assertFalse(Draft202012Validator(load_schema(case["schema"])).is_valid(case["value"]))
        cases = _read(ROOT / "semantic-negative.json")
        self.assertEqual(len(cases), 9)
        for case in cases:
            with self.subTest(case=case["case"]):
                _validate(case["schema"], case["value"])
                self.assertEqual(case["expected"], "ERROR2")

    def test_disjoint_thirty_two_table_assessment_plan(self):
        plan = _read(ROOT / "assessment" / "effective-plan.json")
        plan["tables"] = {
            f"{side}_{i}": {
                "baseline_id": f"t{i}" if side == "b" else None,
                "candidate_id": f"t{i}" if side == "c" else None,
                "evolution": None,
            }
            for side in ("b", "c")
            for i in range(16)
        }
        _validate("representation-assessment-plan-v1", plan)
        plan["tables"]["extra"] = copy.deepcopy(plan["tables"]["b_0"])
        self.assertFalse(Draft202012Validator(load_schema("representation-assessment-plan-v1")).is_valid(plan))

    def test_normalization_and_precedence_gate(self):
        numeric = _read(ROOT / "normalization-cases.json")["numeric_negative_scale"]
        adjusted = numeric["typmod"] - 4
        self.assertEqual((adjusted >> 16) & 65535, numeric["precision"])
        self.assertEqual(((adjusted & 2047) ^ 1024) - 1024, numeric["scale"])
        self.assertNotEqual(numeric["raw_scale"], numeric["scale"])
        for case in _read(ROOT / "precedence-cases.json"):
            expected = max(case["findings"], key={"ACCEPT": 0, "INCONCLUSIVE": 1, "DENY": 2}.get, default="ACCEPT")
            self.assertEqual(case["expected"], expected)
        cases = _read(ROOT / "rule-cases.json")
        self.assertEqual({c["expected"] for c in cases}, {"ACCEPT", "DENY", "INCONCLUSIVE"})
        self.assertEqual(len({c["case"] for c in cases}), len(cases))


if __name__ == "__main__":
    unittest.main()
