import json
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from datetime import date, datetime, timezone

from jsonschema import Draft202012Validator

from parison.core import ParisonError, _multiset_encoding, compare, error_result, export_evidence, explain_recipe, inspect_bundle, load_recipe, load_schema, publish, validate_inputs, verify_bundle


RECIPE = {
    "recipe_version": 3,
    "comparison_mode": "multiset",
    "scope": {"snapshot": "orders-v5", "cutoff": "2026-10-09T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "columns": {
        "region": {"type": "string", "normalize": ["trim", "casefold"]},
        "amount": {"type": "decimal", "scale": 2},
    },
    "column_mappings": {"region": {"baseline": "region", "candidate": "area"}},
    "output": {"sensitivity": "summary"},
}


class MultisetRecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "recipe.json"
        self.path.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_schema_runtime_and_policy_agree(self):
        schema = load_schema("recipe-v3")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(RECIPE)
        self.assertEqual(load_recipe(self.path)["comparison_mode"], "multiset")
        policy = explain_recipe(self.path)
        self.assertEqual(policy["multiset_contract"], "multiset-v1")
        self.assertEqual(policy["column_order"], ["amount", "region"])
        self.assertTrue(policy["nulls_equal"])
        self.assertRegex(policy["policy_sha256"], r"^[0-9a-f]{64}$")

    def test_rejects_cross_mode_fields_and_tolerance(self):
        for field, value in (("keys", ["region"]), ("group_by", ["region"]), ("measures", {"rows": {"operator": "count"}})):
            recipe = json.loads(json.dumps(RECIPE))
            recipe[field] = value
            self.path.write_text(json.dumps(recipe), encoding="utf-8")
            with self.subTest(field=field), self.assertRaisesRegex(ParisonError, "unknown recipe field"):
                load_recipe(self.path)
        recipe = json.loads(json.dumps(RECIPE))
        recipe["columns"]["amount"]["comparison"] = "numeric"
        self.path.write_text(json.dumps(recipe), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "multiset column amount must use exact comparison"):
            load_recipe(self.path)

    def test_duplicate_multiplicity_is_compared_exactly(self):
        left = Path(self.tmp.name) / "left.csv"
        right = Path(self.tmp.name) / "right.csv"
        left.write_text("region,amount\nEast,1.00\neast,1.00\nwest,2.00\n", encoding="utf-8")
        right.write_text("area,amount\nWEST,2.00\neast,1.00\nwest,2.00\n", encoding="utf-8")
        result = compare(self.path, left, right)
        Draft202012Validator(load_schema("result-v3")).validate(result)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["counts"]["common_occurrences"], 2)
        self.assertEqual(result["counts"]["baseline_only_occurrences"], 1)
        self.assertEqual(result["counts"]["candidate_only_occurrences"], 1)
        self.assertNotIn("east", json.dumps(result).lower())

    def test_raw_evidence_is_bounded_and_distinct_row_limit_is_hard(self):
        recipe = json.loads(json.dumps(RECIPE))
        recipe["output"]["sensitivity"] = "raw"
        self.path.write_text(json.dumps(recipe), encoding="utf-8")
        left = Path(self.tmp.name) / "left.csv"
        right = Path(self.tmp.name) / "right.csv"
        left.write_text("region,amount\na,1.00\nb,2.00\n", encoding="utf-8")
        right.write_text("area,amount\na,1.00\nc,3.00\n", encoding="utf-8")
        result = compare(self.path, left, right, sample_limit=1)
        self.assertEqual(len(result["discrepancy_sample"]), 1)
        output = Path(self.tmp.name) / "run"
        publish(output, result, load_recipe(self.path))
        self.assertEqual(verify_bundle(output)["outcome"], "FAIL")
        summary = inspect_bundle(output)
        self.assertEqual(summary["outcome"], "FAIL")
        self.assertNotIn("discrepancy_sample", json.dumps(summary))
        exported = Path(self.tmp.name) / "evidence.jsonl"
        metadata = export_evidence(output, exported, limit=1)
        self.assertEqual(metadata["items"], 1)
        lines = exported.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["_parison_export"]["schema_version"], 3)
        summary_recipe = json.loads(json.dumps(RECIPE))
        summary_recipe_path = Path(self.tmp.name) / "summary-recipe.json"
        summary_recipe_path.write_text(json.dumps(summary_recipe), encoding="utf-8")
        summary_result = compare(summary_recipe_path, left, right)
        summary_output = Path(self.tmp.name) / "summary-run"
        publish(summary_output, summary_result, load_recipe(summary_recipe_path))
        with self.assertRaisesRegex(ParisonError, "raw-sensitivity"):
            export_evidence(summary_output, Path(self.tmp.name) / "summary-evidence.jsonl")
        self.assertIn("Parison multiset report", (output / "report.html").read_text(encoding="utf-8"))
        Draft202012Validator(load_schema("result-v3")).validate(error_result("safe failure", load_recipe(self.path)))
        with self.assertRaisesRegex(ParisonError, "distinct row count"):
            compare(self.path, left, right, max_distinct_rows=1)

    def test_encoding_is_tagged_length_prefixed_and_canonical(self):
        recipe = load_recipe(self.path)
        names = ["amount", "region"]
        first = _multiset_encoding((Decimal("1.00"), "a\x00b"), names, recipe)
        second = _multiset_encoding((Decimal("1.0"), "a\x00b"), names, recipe)
        self.assertEqual(first, second)
        self.assertEqual(first[:1], b"\x03")
        self.assertEqual(int.from_bytes(first[1:9], "big"), 4)
        self.assertNotEqual(first, _multiset_encoding((Decimal("1.01"), "a\x00b"), names, recipe))

    def test_record_preflight_counts_distinct_rows_and_enforces_limit(self):
        left = Path(self.tmp.name) / "left.csv"
        right = Path(self.tmp.name) / "right.csv"
        left.write_text("region,amount\neast,1.00\neast,1.00\nwest,2.00\n", encoding="utf-8")
        right.write_text("area,amount\neast,1.00\nwest,2.00\n", encoding="utf-8")
        result = validate_inputs(self.path, left, right, validate_records=True)
        Draft202012Validator(load_schema("preflight-v3")).validate(result)
        self.assertEqual(result["inputs"]["baseline"]["records"]["distinct_rows"], 2)
        limited = validate_inputs(self.path, left, right, validate_records=True, max_distinct_rows=1)
        self.assertEqual(limited["status"], "invalid")
        self.assertTrue(limited["inputs"]["baseline"]["records"]["distinct_row_limit_exceeded"])

    def test_encoding_golden_scalar_tags(self):
        recipe = json.loads(json.dumps(RECIPE))
        recipe["columns"] = {
            "a_bool": {"type": "boolean"}, "b_int": {"type": "integer"}, "c_decimal": {"type": "decimal", "scale": 2},
            "d_float": {"type": "float"}, "e_date": {"type": "date"}, "f_timestamp": {"type": "timestamp", "timezone": "require-aware"}, "g_string": {"type": "string"},
        }
        names = sorted(recipe["columns"])
        encoded = _multiset_encoding((True, 7, Decimal("1.20"), 1.5, date(2026, 10, 9), datetime(2026, 10, 9, tzinfo=timezone.utc), "é"), names, recipe)
        tags = []
        offset = 0
        while offset < len(encoded):
            tags.append(encoded[offset])
            offset += 1 + 8 + int.from_bytes(encoded[offset + 1:offset + 9], "big")
        self.assertEqual(tags, [1, 2, 3, 7, 5, 6, 4])
        self.assertIn("2026-10-09T00:00:00.000000Z".encode(), encoded)

    def test_raw_evidence_is_invariant_under_row_order(self):
        recipe = json.loads(json.dumps(RECIPE))
        recipe["output"]["sensitivity"] = "raw"
        self.path.write_text(json.dumps(recipe), encoding="utf-8")
        left = Path(self.tmp.name) / "left.csv"
        right = Path(self.tmp.name) / "right.csv"
        left.write_text("region,amount\nb,2.00\na,1.00\nc,3.00\n", encoding="utf-8")
        right.write_text("area,amount\nc,3.01\na,1.00\nb,2.01\n", encoding="utf-8")
        first = compare(self.path, left, right, sample_limit=2)
        right.write_text("area,amount\nb,2.01\nc,3.01\na,1.00\n", encoding="utf-8")
        second = compare(self.path, left, right, sample_limit=2)
        self.assertEqual(first["discrepancy_sample"], second["discrepancy_sample"])


if __name__ == "__main__":
    unittest.main()
