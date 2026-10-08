import json
import tempfile
import unittest
from pathlib import Path

from parison.core import ParisonError, compare, draft_recipe, explain_recipe, load_recipe, validate_inputs


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "null tokens",
        "cutoff": "2026-10-08T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "null_tokens": {"baseline": ["NULL"], "candidate": ["\\N"]},
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "note": {"type": "string", "comparison": "exact"},
        "amount": {"type": "integer", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class NullTokens(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def inputs(self, baseline_note="NULL", candidate_note="\\N"):
        baseline = self.root / "baseline.csv"
        candidate = self.root / "candidate.csv"
        baseline.write_text(f"id,note,amount\n001,{baseline_note},NULL\n", encoding="utf-8")
        candidate.write_text(f"id,note,amount\n001,{candidate_note},\\N\n", encoding="utf-8")
        return baseline, candidate

    def test_side_specific_tokens_map_to_typed_nulls_and_evidence(self):
        baseline, candidate = self.inputs()
        preflight = validate_inputs(self.recipe, baseline, candidate)
        self.assertEqual(preflight["inputs"]["baseline"]["null_tokens"], ["NULL"])
        self.assertEqual(preflight["inputs"]["candidate"]["null_tokens"], ["\\N"])

        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["policy"]["null_tokens"], RECIPE["null_tokens"])
        self.assertEqual(result["inputs"]["baseline"]["null_tokens"], ["NULL"])
        self.assertEqual(explain_recipe(self.recipe)["null_tokens"], RECIPE["null_tokens"])

    def test_empty_string_remains_distinct_from_null_for_strings(self):
        baseline, candidate = self.inputs(baseline_note="", candidate_note="\\N")
        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["field_counts"]["note"]["different"], 1)

    def test_drafting_and_old_recipes_choose_no_null_tokens(self):
        baseline, candidate = self.inputs(baseline_note="value", candidate_note="value")
        draft = draft_recipe(baseline, candidate)
        self.assertEqual(draft["null_tokens"], {"baseline": [], "candidate": []})

        old = dict(RECIPE)
        old.pop("null_tokens")
        old_path = self.root / "old.json"
        old_path.write_text(json.dumps(old), encoding="utf-8")
        self.assertEqual(load_recipe(old_path)["null_tokens"], {"baseline": [], "candidate": []})

    def test_invalid_null_token_policies_are_rejected(self):
        invalid = (
            {"baseline": ["NULL"]},
            {"baseline": [""], "candidate": []},
            {"baseline": ["NULL", "NULL"], "candidate": []},
        )
        for null_tokens in invalid:
            with self.subTest(null_tokens=null_tokens):
                path = self.root / "invalid.json"
                path.write_text(json.dumps({**RECIPE, "null_tokens": null_tokens}), encoding="utf-8")
                with self.assertRaisesRegex(ParisonError, "null_tokens"):
                    load_recipe(path)


if __name__ == "__main__":
    unittest.main()
