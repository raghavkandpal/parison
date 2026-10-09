import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import ParisonError, compare, explain_recipe, load_recipe, load_schema


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

    def test_execution_is_not_exposed_as_a_partial_feature(self):
        with self.assertRaisesRegex(ParisonError, "not implemented yet"):
            compare(self.path, "baseline.csv", "candidate.csv")


if __name__ == "__main__":
    unittest.main()
