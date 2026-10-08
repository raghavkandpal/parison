import gzip
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
        "snapshot": "delimiters",
        "cutoff": "2026-10-08T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "delimiters": {"baseline": "\t", "candidate": "|"},
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "integer", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class DelimitedTextInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_asymmetric_delimiters_are_applied_and_recorded(self):
        baseline = self.root / "baseline.tsv.gz"
        with gzip.open(baseline, "wt", encoding="utf-8", newline="") as handle:
            handle.write("id\tvalue\n001\t10\n")
        candidate = self.root / "candidate.csv"
        candidate.write_text("value|id\n10|001\n", encoding="utf-8")

        preflight = validate_inputs(self.recipe, baseline, candidate)
        self.assertEqual(preflight["status"], "valid")
        self.assertEqual(preflight["inputs"]["baseline"]["format"], "tsv")
        self.assertEqual(preflight["inputs"]["baseline"]["delimiter"], "\t")
        self.assertEqual(preflight["inputs"]["candidate"]["delimiter"], "|")

        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["policy"]["delimiters"], RECIPE["delimiters"])
        self.assertEqual(result["inputs"]["baseline"]["delimiter"], "\t")
        explained = explain_recipe(self.recipe)
        self.assertEqual(explained["delimiters"], RECIPE["delimiters"])
        changed = {**RECIPE, "delimiters": {"baseline": ",", "candidate": "|"}}
        changed_path = self.root / "changed.json"
        changed_path.write_text(json.dumps(changed), encoding="utf-8")
        self.assertNotEqual(explained["policy_sha256"], explain_recipe(changed_path)["policy_sha256"])

    def test_drafting_suggests_extension_delimiters(self):
        baseline = self.root / "baseline.tsv"
        candidate = self.root / "candidate.csv"
        baseline.write_text("id\tvalue\n001\t10\n", encoding="utf-8")
        candidate.write_text("id,value\n001,10\n", encoding="utf-8")

        draft = draft_recipe(baseline, candidate)
        self.assertEqual(draft["delimiters"], {"baseline": "\t", "candidate": ","})
        draft_path = self.root / "draft.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        self.assertEqual(load_recipe(draft_path), draft)
        self.assertEqual(compare(draft_path, baseline, candidate)["outcome"], "PASS")

    def test_old_recipes_default_to_commas(self):
        recipe = dict(RECIPE)
        recipe.pop("delimiters")
        path = self.root / "old.json"
        path.write_text(json.dumps(recipe), encoding="utf-8")
        self.assertEqual(load_recipe(path)["delimiters"], {"baseline": ",", "candidate": ","})

    def test_invalid_delimiters_are_rejected(self):
        invalid = ({"baseline": ","}, {"baseline": "::", "candidate": ","}, {"baseline": '"', "candidate": ","})
        for delimiters in invalid:
            with self.subTest(delimiters=delimiters):
                recipe = {**RECIPE, "delimiters": delimiters}
                path = self.root / "invalid.json"
                path.write_text(json.dumps(recipe), encoding="utf-8")
                with self.assertRaisesRegex(ParisonError, "delimiters"):
                    load_recipe(path)

    def test_csv_and_tsv_cannot_share_a_partition_directory(self):
        baseline = self.root / "baseline"
        baseline.mkdir()
        (baseline / "a.csv").write_text("id,value\n001,10\n", encoding="utf-8")
        (baseline / "b.tsv").write_text("id\tvalue\n002\t20\n", encoding="utf-8")
        candidate = self.root / "candidate.csv"
        candidate.write_text("id|value\n001|10\n002|20\n", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "one supported file format"):
            compare(self.recipe, baseline, candidate)


if __name__ == "__main__":
    unittest.main()
