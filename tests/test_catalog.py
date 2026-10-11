import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from parison.catalog import add, list_runs, show
from parison.cli import main
from parison.core import ParisonError, compare, publish


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {"snapshot": "catalog-test", "cutoff": "2026-10-11T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {"id": {"type": "string"}, "value": {"type": "string"}},
    "output": {"sensitivity": "raw"},
}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.baseline = self.root / "baseline.csv"
        self.candidate = self.root / "candidate.csv"
        self.bundle = self.root / "run"
        self.database = self.root / "catalog.sqlite"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        self.baseline.write_text("id,value\nsecret-key,secret-baseline\n", encoding="utf-8")
        self.candidate.write_text("id,value\nsecret-key,secret-candidate\n", encoding="utf-8")
        publish(self.bundle, compare(self.recipe, self.baseline, self.candidate), RECIPE)

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_is_explicit_idempotent_and_stores_only_safe_inspection_metadata(self):
        first = add(self.database, self.bundle)
        second = add(self.database, self.bundle)
        self.assertEqual(first["status"], "added")
        self.assertEqual(second["status"], "unchanged")
        entry = show(self.database, self.bundle)
        self.assertEqual(entry["state"], "current")
        self.assertEqual(entry["outcome"], "FAIL")
        self.assertEqual(entry["metadata"]["discrepancy_sample_size"], 1)
        stored = self.database.read_bytes()
        self.assertNotIn(b"secret-key", stored)
        self.assertNotIn(b"secret-baseline", stored)
        self.assertNotIn(b"secret-candidate", stored)
        self.assertNotIn("metadata", list_runs(self.database)[0])

    def test_list_reports_duplicate_modified_and_missing_paths_deterministically(self):
        copied = self.root / "copied-run"
        missing = self.root / "missing-run"
        shutil.copytree(self.bundle, copied)
        shutil.copytree(self.bundle, missing)
        for path in (self.bundle, copied, missing):
            add(self.database, path)
        (copied / "report.html").write_text("tampered", encoding="utf-8")
        shutil.rmtree(missing)
        entries = list_runs(self.database, outcome="FAIL", kind="run")
        self.assertEqual([entry["path"] for entry in entries], sorted(entry["path"] for entry in entries))
        self.assertEqual({Path(entry["path"]).name: entry["state"] for entry in entries}, {
            "run": "current", "copied-run": "modified", "missing-run": "missing",
        })
        self.assertTrue(all(entry["duplicate_paths"] == 3 for entry in entries))
        self.assertEqual(list_runs(self.database, outcome="PASS"), [])

    def test_cli_add_list_and_show_emit_machine_readable_results(self):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            self.assertEqual(main(["catalog", "add", "--database", str(self.database), str(self.bundle)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "added")
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["catalog", "list", "--database", str(self.database), "--outcome", "FAIL"]), 0)
        self.assertEqual(len(json.loads(stdout.getvalue())["runs"]), 1)
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["catalog", "show", "--database", str(self.database), str(self.bundle)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["state"], "current")

    def test_catalog_rejects_unverified_bundles_unknown_entries_and_unsafe_database(self):
        with self.assertRaises(ParisonError):
            add(self.database, self.root / "missing")
        with self.assertRaisesRegex(ParisonError, "outside the indexed bundle"):
            add(self.bundle / "catalog.sqlite", self.bundle)
        add(self.database, self.bundle)
        with self.assertRaisesRegex(ParisonError, "not in catalog"):
            show(self.database, self.root / "other")
        unsafe = self.root / "unsafe.sqlite"
        unsafe.symlink_to(self.database)
        with self.assertRaisesRegex(ParisonError, "not a regular file"):
            list_runs(unsafe)
        future = self.root / "future.sqlite"
        with sqlite3.connect(future) as connection:
            connection.execute("PRAGMA user_version = 99")
        with self.assertRaisesRegex(ParisonError, "version is unsupported"):
            list_runs(future)
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE runs SET metadata = 'not-json'")
        with self.assertRaisesRegex(ParisonError, "invalid metadata"):
            list_runs(self.database)


if __name__ == "__main__":
    unittest.main()
