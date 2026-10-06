import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from parison.core import ParisonError, compare, draft_recipe


RECIPE = {
    "recipe_version": 1, "comparison_mode": "keyed", "keys": ["id"],
    "scope": {"snapshot": "sqlite-test", "cutoff": "2026-10-06T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"}, "nulls_equal": True,
    "columns": {"id": {"type": "string", "comparison": "exact"}, "value": {"type": "integer", "comparison": "exact"}},
    "output": {"sensitivity": "summary"},
}


class SqliteInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        self.database = self.root / "data.db"
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE TABLE records (id TEXT, value INTEGER)")
            connection.executemany("INSERT INTO records VALUES (?, ?)", [("001", 10), ("002", 20)])

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def source(self):
        return f"sqlite:{self.database}#records"

    def test_mixed_csv_sqlite_matches_accuracy_oracle(self):
        baseline = self.root / "baseline.csv"
        with baseline.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows((("id", "value"), ("002", "20"), ("001", "10")))
        result = compare(self.recipe, baseline, self.source)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 2)
        self.assertEqual(result["inputs"]["candidate"]["bytes"], self.database.stat().st_size)
        self.assertEqual(result["inputs"]["candidate"]["format"], "sqlite")
        self.assertEqual(result["inputs"]["candidate"]["table"], "records")
        self.assertNotIn(str(self.database), json.dumps(result))

    def test_sqlite_draft_reads_metadata_without_inference(self):
        draft = draft_recipe(self.source, self.source)
        self.assertEqual(list(draft["columns"]), ["id", "value"])
        self.assertEqual(draft["columns"]["value"]["type"], "REVIEW_REQUIRED")

    def test_sqlite_rejects_views_blobs_journals_and_row_overruns(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("CREATE VIEW record_view AS SELECT * FROM records")
            connection.execute("CREATE TABLE blobs (id TEXT, value BLOB)")
            connection.execute("INSERT INTO blobs VALUES ('001', x'00')")
        with self.assertRaisesRegex(ParisonError, "ordinary table"):
            compare(self.recipe, self.source.replace("#records", "#record_view"), self.source)
        with self.assertRaisesRegex(ParisonError, "BLOB"):
            compare(self.recipe, self.source.replace("#records", "#blobs"), self.source)
        with self.assertRaisesRegex(ParisonError, "row count"):
            compare(self.recipe, self.source, self.source, max_rows=1)
        journal = Path(str(self.database) + "-journal")
        journal.touch()
        with self.assertRaisesRegex(ParisonError, "journal sidecar"):
            compare(self.recipe, self.source, self.source)


if __name__ == "__main__":
    unittest.main()
