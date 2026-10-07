import csv
import json
import tempfile
import unittest
from pathlib import Path

from parison.core import ParisonError, compare, draft_recipe


RECIPE = {
    "recipe_version": 1, "comparison_mode": "keyed", "keys": ["id"],
    "scope": {"snapshot": "jsonl-test", "cutoff": "2026-10-06T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"}, "nulls_equal": True,
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "amount": {"type": "decimal", "scale": 2, "comparison": "numeric", "tolerance": {"formula": "symmetric-v1", "absolute": "0.05", "relative": "0"}},
        "active": {"type": "boolean", "comparison": "exact"}},
    "output": {"sensitivity": "summary"},
}


class JsonLinesInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_mixed_csv_jsonl_matches_accuracy_oracle(self):
        baseline = self.root / "baseline.csv"
        with baseline.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "amount", "active"])
            writer.writeheader()
            writer.writerows([{"id": "001", "amount": "10.00", "active": "true"}, {"id": "002", "amount": "2.00", "active": "false"}])
        candidate = self.root / "candidate.jsonl"
        candidate.write_text('{"active":true,"amount":10.05,"id":"001"}\n{"id":"002","amount":2.00,"active":false}\n', encoding="utf-8")
        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 1)
        self.assertEqual(result["counts"]["matched_within_tolerance"], 1)

    def test_mixed_inputs_use_canonical_column_mappings(self):
        spec = json.loads(json.dumps(RECIPE))
        spec["column_mappings"] = {
            "id": {"baseline": "legacy_id", "candidate": "id"},
            "amount": {"baseline": "legacy_amount", "candidate": "amount"},
        }
        self.recipe.write_text(json.dumps(spec), encoding="utf-8")
        baseline = self.root / "baseline.csv"
        baseline.write_text("legacy_id,legacy_amount,active\n001,10.00,true\n", encoding="utf-8")
        candidate = self.root / "candidate.jsonl"
        candidate.write_text('{"id":"001","amount":10.00,"active":true}\n', encoding="utf-8")
        self.assertEqual(compare(self.recipe, baseline, candidate)["outcome"], "PASS")

    def test_jsonl_drafting_uses_names_without_inference(self):
        left, right = self.root / "left.jsonl", self.root / "right.ndjson"
        left.write_text('{"id":"secret","value":1}\n', encoding="utf-8")
        right.write_text('{"value":2,"id":"secret"}\n', encoding="utf-8")
        draft = draft_recipe(left, right)
        self.assertEqual(list(draft["columns"]), ["id", "value"])
        self.assertEqual(draft["columns"]["value"]["type"], "integer")

    def test_jsonl_rejects_duplicate_missing_nested_and_nonfinite_values(self):
        bad_lines = (
            '{"id":"1","id":"2","amount":1,"active":true}\n',
            '{"id":"1","amount":1}\n',
            '{"id":"1","amount":[1],"active":true}\n',
            '{"id":"1","amount":NaN,"active":true}\n',
        )
        good = self.root / "good.jsonl"
        good.write_text('{"id":"1","amount":1,"active":true}\n', encoding="utf-8")
        for index, line in enumerate(bad_lines):
            with self.subTest(index=index):
                bad = self.root / f"bad-{index}.jsonl"
                bad.write_text(line, encoding="utf-8")
                with self.assertRaises(ParisonError):
                    compare(self.recipe, good, bad)


if __name__ == "__main__":
    unittest.main()
