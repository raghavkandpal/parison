"""Frozen hash discovery structures, key vectors and future verification obligations."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.analysis import _canonical
from parison.comparison import _multiset_encoding, compare
from parison.core import _checked_policy_sha256, _parse_row, load_recipe, load_schema
from parison.partition_discovery import validate_plan

ROOT = Path(__file__).parent / "fixtures" / "partition_hash"
PREFIX = b"parison-key-v1\0"


def _read(path):
    return json.loads(path.read_bytes())


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _encoded(values, types):
    names = [f"k{i}" for i in range(len(values))]
    recipe = {"columns": {name: {"type": kind} for name, kind in zip(names, types, strict=True)}}
    return PREFIX + len(values).to_bytes(2, "big") + _multiset_encoding(tuple(values), names, recipe)


class HashDiscoveryWire(unittest.TestCase):
    def test_standalone_schemas_canonical_examples_and_bindings(self):
        for kind in ("plan", "receipt", "summary", "manifest"):
            schema = load_schema(f"partition-{kind}-v2")
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(_read(ROOT / "expected" / f"{kind}.json"))
        for path in ROOT.rglob("*.json"):
            with self.subTest(path=path.name):
                self.assertEqual(path.read_bytes(), _canonical(_read(path)) + b"\n")
        plan, receipt, summary, manifest = (
            _read(ROOT / "expected" / f"{name}.json") for name in ("plan", "receipt", "summary", "manifest")
        )
        self.assertEqual(plan, _read(ROOT / "plan.json"))
        self.assertEqual(receipt["plan_sha256"], _sha(_canonical(plan)))
        self.assertEqual(receipt["routing"], plan["routing"])
        self.assertEqual(receipt["policy_sha256"], _checked_policy_sha256(load_recipe(ROOT / "recipe.json")))
        self.assertEqual(
            summary,
            {k: v for k, v in receipt.items() if k not in {"partitions", "field_counts", "derived_recipe_bytes"}},
        )
        self.assertNotIn("tenant", summary)
        for name, digest in manifest["files"].items():
            self.assertEqual(digest, _sha((ROOT / "expected" / name).read_bytes()))
        total = receipt["derived_recipe_bytes"]
        for side in ("baseline", "candidate"):
            source = (ROOT / f"{side}.csv").read_bytes()
            self.assertEqual(receipt["inputs"][side], {"sha256": _sha(source), "bytes": len(source)})
            self.assertIn(b"\r\n", source)
            total += len(source)
            self.assertEqual(receipt["route_rows"][side], sum(p[side]["rows"] for p in receipt["partitions"]))
        for index, partition in enumerate(receipt["partitions"]):
            self.assertEqual(partition["bucket"], index)
            self.assertNotIn("upper", partition)
            total += sum(partition[side]["bytes"] for side in ("baseline", "candidate"))
        self.assertEqual(total, receipt["staged_bytes"])

    def test_exact_engine_oracle_for_expected_aggregate(self):
        reference = compare(ROOT / "recipe.json", ROOT / "baseline.csv", ROOT / "candidate.csv", sample_limit=0)
        expected = _read(ROOT / "expected" / "receipt.json")
        for name in ("outcome", "complete", "counts", "field_counts", "discrepancy_count"):
            self.assertEqual(expected[name], reference[name])
        for name, count in expected["counts"].items():
            self.assertEqual(count, sum(p["counts"][name] for p in expected["partitions"]))
        derived = load_recipe(ROOT / "recipe.json")
        derived["scope"]["expected_empty"] = True
        self.assertEqual(expected["derived_recipe_bytes"], len(_canonical(derived)))

    def test_key_byte_digest_and_bucket_vectors(self):
        seen = set()
        for vector in _read(ROOT / "key-vectors.json"):
            with self.subTest(case=vector["case"]):
                encoded = _encoded(vector["values"], vector["types"])
                self.assertEqual(encoded.hex(), vector["hex"])
                self.assertEqual(_sha(encoded), vector["sha256"])
                self.assertNotIn(encoded, seen)
                seen.add(encoded)
                digest = hashlib.sha256(encoded).digest()
                self.assertEqual(int.from_bytes(digest, "big"), int(vector["sha256"], 16))
                self.assertEqual(int.from_bytes(digest, "big"), int.from_bytes(digest[::-1], "little"))
                for count, expected in vector["buckets"].items():
                    self.assertEqual(int.from_bytes(digest, "big") % int(count), expected)

    def test_normalization_vectors_reuse_released_parser(self):
        for vector in _read(ROOT / "normalization-vectors.json"):
            with self.subTest(case=vector["case"]):
                names = [f"k{i}" for i in range(len(vector["raw"]))]
                recipe = {
                    "columns": {
                        name: {"type": kind, "normalize": rules}
                        for name, kind, rules in zip(names, vector["types"], vector["normalize"], strict=True)
                    }
                }
                parsed = _parse_row(dict(zip(names, vector["raw"], strict=True)), recipe, "baseline")
                values = [parsed[name] for name in names]
                self.assertEqual(values, vector["values"])
                encoded = _encoded(values, vector["types"])
                self.assertEqual(encoded.hex(), vector["hex"])
                self.assertEqual(_sha(encoded), vector["sha256"])

    def test_schema_negative_and_future_semantic_gate(self):
        for case in _read(ROOT / "schema-negative.json"):
            with self.subTest(case=case["case"]):
                validator = Draft202012Validator(load_schema(f"partition-{case['schema']}-v2"))
                self.assertFalse(validator.is_valid(case["value"]))
        cases = _read(ROOT / "semantic-negative.json")
        self.assertEqual(len(cases), 8)
        for case in cases:
            with self.subTest(case=case["case"]):
                Draft202012Validator(load_schema(f"partition-{case['schema']}-v2")).validate(case["value"])

    def test_runtime_descriptor_structure_does_not_grant_replay(self):
        original = _read(ROOT / "expected" / "receipt.json")
        validator = Draft202012Validator(load_schema("partition-receipt-v2"))
        for case in _read(ROOT / "runtime-cases.json"):
            value = copy.deepcopy(original)
            value["normalization_runtime"] = case["context"]
            validator.validate(value)
            minor = tuple(map(int, case["context"]["python_version"].split(".")[:2]))
            self.assertEqual(case["execution_minor_admitted"], minor in {(3, 11), (3, 12), (3, 13), (3, 14)})
        # Source-backed replay must additionally match the exact full context.
        # This structural gate is not a producer or evidence verifier.
        self.assertEqual(validate_plan(_read(ROOT / "plan.json")), _read(ROOT / "plan.json"))


if __name__ == "__main__":
    unittest.main()
