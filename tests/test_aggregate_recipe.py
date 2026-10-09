import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import ParisonError, compare, explain_recipe, load_recipe, load_schema, publish, validate_inputs, verify_bundle


RECIPE = {
    "recipe_version": 2,
    "comparison_mode": "aggregate",
    "group_by": ["region"],
    "measures": {
        "rows": {"operator": "count"},
        "revenue": {
            "operator": "sum",
            "column": "amount",
            "nulls": "reject",
            "comparison": "numeric",
            "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
        },
        "last_order": {"operator": "max", "column": "ordered_at", "nulls": "ignore"},
    },
    "scope": {
        "snapshot": "orders-v4",
        "cutoff": "2026-10-08T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "columns": {
        "region": {"type": "string", "normalize": ["trim", "casefold"]},
        "amount": {"type": "decimal", "scale": 2},
        "ordered_at": {"type": "timestamp", "timezone": "require-aware"},
    },
    "output": {"sensitivity": "summary"},
}


class AggregateRecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "recipe.json"
        self.path.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")

    def test_schema_and_runtime_validation_accept_same_recipe(self):
        schema = load_schema("recipe-v2")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(RECIPE)
        loaded = load_recipe(self.path)
        self.assertEqual(loaded["comparison_mode"], "aggregate")
        self.assertEqual(loaded["delimiters"], {"baseline": ",", "candidate": ","})
        self.assertEqual(loaded["null_tokens"], {"baseline": [], "candidate": []})

    def test_explain_is_explicit_and_stable(self):
        explained = explain_recipe(self.path)
        self.assertEqual(explained["schema_version"], 2)
        self.assertEqual(explained["aggregate_contract"], "aggregate-v1")
        self.assertEqual(explained["group_nulls"], "reject")
        self.assertTrue(explained["columns"]["region"]["group_by"])
        self.assertEqual(explained["measures"]["last_order"]["comparison"], "exact")
        self.assertRegex(explained["policy_sha256"], r"^[0-9a-f]{64}$")
        reordered = Path(self.tmp.name) / "reordered.json"
        reordered.write_text(json.dumps(RECIPE, sort_keys=True, indent=2), encoding="utf-8")
        self.assertEqual(explain_recipe(reordered)["policy_sha256"], explained["policy_sha256"])

    def test_rejects_ambiguous_measure_contracts(self):
        cases = [
            ("count measure rows accepts only operator", {"rows": {"operator": "count", "column": "amount"}}),
            ("requires an integer or decimal", {"bad": {"operator": "sum", "column": "region", "nulls": "reject"}}),
            ("nulls must be", {"bad": {"operator": "max", "column": "ordered_at"}}),
        ]
        for message, measures in cases:
            with self.subTest(message=message):
                value = json.loads(json.dumps(RECIPE))
                value["measures"] = measures
                self.write(value)
                with self.assertRaisesRegex(ParisonError, message):
                    load_recipe(self.path)

    def test_group_columns_are_exact_configured_and_unique(self):
        value = json.loads(json.dumps(RECIPE))
        value["group_by"] = ["missing"]
        self.write(value)
        with self.assertRaisesRegex(ParisonError, "every group_by"):
            load_recipe(self.path)
        value["group_by"] = ["region", "region"]
        self.write(value)
        with self.assertRaisesRegex(ParisonError, "unique"):
            load_recipe(self.path)

    def csv(self, name, body):
        path = Path(self.tmp.name) / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_grouped_aggregate_passes_under_reordering_and_tolerance(self):
        left = self.csv("left.csv", "region,amount,ordered_at\n East ,10.00,2026-01-01T00:00:00Z\nwest,4.00,2026-01-02T00:00:00Z\neast,-1.00,2026-01-03T00:00:00Z\n")
        right = self.csv("right.csv", "region,amount,ordered_at\nWEST,4.00,2026-01-02T00:00:00Z\neast,-0.99,2026-01-03T00:00:00Z\neast,10.00,2026-01-01T00:00:00Z\n")
        result = compare(self.path, left, right)
        Draft202012Validator(load_schema("result-v2")).validate(result)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["counts"]["common_groups"], 2)
        self.assertEqual(result["measure_counts"]["revenue"]["within_tolerance"], 1)
        self.assertNotIn("east", json.dumps(result).lower())

    def test_offsetting_groups_and_measure_differences_fail(self):
        left = self.csv("left.csv", "region,amount,ordered_at\neast,1.00,2026-01-01T00:00:00Z\nwest,2.00,2026-01-01T00:00:00Z\n")
        right = self.csv("right.csv", "region,amount,ordered_at\neast,3.00,2026-01-01T00:00:00Z\nnorth,0.00,2026-01-01T00:00:00Z\n")
        result = compare(self.path, left, right)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["counts"]["baseline_only_groups"], 1)
        self.assertEqual(result["counts"]["candidate_only_groups"], 1)
        self.assertEqual(result["measure_counts"]["revenue"]["different"], 1)

    def test_decimal_cancellation_is_order_independent(self):
        value = json.loads(json.dumps(RECIPE))
        value["group_by"] = []
        value["columns"]["amount"]["scale"] = 2
        value["measures"] = {"total": {"operator": "sum", "column": "amount", "nulls": "reject"}}
        value["columns"].pop("region")
        value["columns"].pop("ordered_at")
        self.write(value)
        left = self.csv("left.csv", "amount\n999999999999.99\n-999999999999.99\n0.01\n")
        right = self.csv("right.csv", "amount\n0.01\n-999999999999.99\n999999999999.99\n")
        self.assertEqual(compare(self.path, left, right)["outcome"], "PASS")

    def test_null_group_and_rejected_measure_are_inconclusive(self):
        left = self.csv("left.jsonl", '{"region":null,"amount":"1.00","ordered_at":"2026-01-01T00:00:00Z"}\n{"region":"east","amount":null,"ordered_at":"2026-01-01T00:00:00Z"}\n')
        result = compare(self.path, left, left)
        self.assertEqual(result["outcome"], "INCONCLUSIVE")
        self.assertFalse(result["complete"])
        self.assertTrue(any("null group" in item for item in result["problems"]))
        self.assertTrue(any("rejected null" in item for item in result["problems"]))

    def test_global_empty_shape_and_group_limit(self):
        value = json.loads(json.dumps(RECIPE))
        value["group_by"] = []
        value["scope"]["expected_empty"] = True
        self.write(value)
        empty = self.csv("empty.csv", "region,amount,ordered_at\n")
        result = compare(self.path, empty, empty)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["baseline_groups"], 1)
        value["group_by"] = ["region"]
        self.write(value)
        rows = self.csv("rows.csv", "region,amount,ordered_at\neast,1,2026-01-01T00:00:00Z\nwest,1,2026-01-01T00:00:00Z\n")
        with self.assertRaisesRegex(ParisonError, "group count exceeds limit 1"):
            compare(self.path, rows, rows, max_groups=1)

    def test_raw_evidence_and_bundle_are_verifiable(self):
        value = json.loads(json.dumps(RECIPE))
        value["output"] = {"sensitivity": "raw"}
        self.write(value)
        left = self.csv("left.csv", "region,amount,ordered_at\neast,1.00,2026-01-01T00:00:00Z\n")
        right = self.csv("right.csv", "region,amount,ordered_at\neast,2.00,2026-01-01T00:00:00Z\n")
        result = compare(self.path, left, right, sample_limit=1)
        self.assertEqual(result["discrepancy_sample"][0]["group"], ["east"])
        output = Path(self.tmp.name) / "run"
        publish(output, result, load_recipe(self.path))
        self.assertEqual(verify_bundle(output)["outcome"], "FAIL")
        self.assertIn("Aggregate equality does not prove row equality", (output / "report.html").read_text())

    def test_record_preflight_is_privacy_safe_and_schema_valid(self):
        source = self.csv("records.jsonl", '{"region":"east","amount":"1.00","ordered_at":"2026-01-01T00:00:00Z"}\n{"region":"west","amount":"2.00","ordered_at":"2026-01-02T00:00:00Z"}\n')
        result = validate_inputs(self.path, source, source, validate_records=True)
        Draft202012Validator(load_schema("preflight-v2")).validate(result)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["inputs"]["baseline"]["records"]["groups"], 2)
        self.assertNotIn("east", json.dumps(result))

    def test_record_preflight_reports_group_and_null_failures(self):
        source = self.csv("invalid.jsonl", '{"region":null,"amount":"secret","ordered_at":"2026-01-01T00:00:00Z"}\n{"region":"east","amount":null,"ordered_at":"2026-01-02T00:00:00Z"}\n{"region":"west","amount":"1.00","ordered_at":"2026-01-02T00:00:00Z"}\n')
        result = validate_inputs(self.path, source, source, validate_records=True, max_groups=1)
        records = result["inputs"]["baseline"]["records"]
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(records["invalid_fields"], {"amount": 1})
        self.assertEqual(records["null_group_rows"], 1)
        self.assertEqual(records["rejected_null_measure_values"], 1)
        self.assertTrue(records["group_limit_exceeded"])
        self.assertNotIn("secret", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
