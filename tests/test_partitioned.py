import json
import tempfile
import unittest
from pathlib import Path

try:
    import polars as pl
except ImportError:
    pl = None

from parison.core import ParisonError, compare, draft_recipe


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {"snapshot": "partitions", "cutoff": "2026-10-07T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "integer", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class PartitionedInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def directory(self, name, files):
        directory = self.root / name
        directory.mkdir()
        for filename, contents in files.items():
            (directory / filename).write_text(contents, encoding="utf-8")
        return directory

    def test_csv_directory_is_one_logical_input(self):
        baseline = self.directory("baseline", {
            "b.csv": "id,value\n002,20\n",
            "a.csv": "value,id\n10,001\n",
        })
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value\n001,10\n002,20\n", encoding="utf-8")
        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["baseline"], 2)
        self.assertEqual(result["inputs"]["baseline"]["partitions"], 2)
        self.assertEqual(result["inputs"]["baseline"]["format"], "csv")
        self.assertNotIn(str(baseline), json.dumps(result))
        draft = draft_recipe(baseline, candidate)
        self.assertEqual(draft["keys"], ["id"])
        self.assertEqual(draft["columns"]["value"]["type"], "integer")

    def test_jsonl_partitions_mix_with_csv(self):
        baseline = self.directory("jsonl", {
            "a.jsonl": '{"id":"001","value":10}\n',
            "b.ndjson": '{"value":20,"id":"002"}\n',
        })
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value\n001,10\n002,20\n", encoding="utf-8")
        self.assertEqual(compare(self.recipe, baseline, candidate)["outcome"], "PASS")

    def test_cross_partition_duplicates_and_total_row_limit(self):
        duplicate = self.directory("duplicate", {
            "a.csv": "id,value\n001,10\n",
            "b.csv": "id,value\n001,10\n",
        })
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value\n001,10\n", encoding="utf-8")
        result = compare(self.recipe, duplicate, candidate)
        self.assertEqual(result["outcome"], "INCONCLUSIVE")
        self.assertIn("duplicate key", result["problems"][0])
        with self.assertRaisesRegex(ParisonError, "row count.*exceeds limit 1"):
            compare(self.recipe, duplicate, candidate, max_rows=1)

    def test_partition_boundaries_are_rejected(self):
        empty = self.directory("empty", {})
        mixed = self.directory("mixed", {"a.csv": "id,value\n1,1\n", "b.jsonl": '{"id":"2","value":2}\n'})
        inconsistent = self.directory("inconsistent", {"a.csv": "id,value\n1,1\n", "b.csv": "id,other\n2,2\n"})
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value\n1,1\n", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "no files"):
            compare(self.recipe, empty, candidate)
        with self.assertRaisesRegex(ParisonError, "one supported file format"):
            compare(self.recipe, mixed, candidate)
        with self.assertRaisesRegex(ParisonError, "schema mismatch"):
            compare(self.recipe, inconsistent, candidate)
        linked = self.root / "linked"
        linked.mkdir()
        (linked / "part.csv").symlink_to(candidate)
        with self.assertRaisesRegex(ParisonError, "non-symlink"):
            compare(self.recipe, linked, candidate)

    @unittest.skipUnless(pl, "Polars optional dependency is not installed")
    def test_parquet_directory_is_supported(self):
        baseline = self.root / "parquet"
        baseline.mkdir()
        pl.DataFrame({"id": ["001"], "value": [10]}).write_parquet(baseline / "a.parquet")
        pl.DataFrame({"id": ["002"], "value": [20]}).write_parquet(baseline / "b.pq")
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value\n001,10\n002,20\n", encoding="utf-8")
        self.assertEqual(compare(self.recipe, baseline, candidate)["outcome"], "PASS")


if __name__ == "__main__":
    unittest.main()
