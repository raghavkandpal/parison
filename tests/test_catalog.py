import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from parison.catalog import add, diff, history, list_runs, remove, show
from parison.cli import main
from parison.core import ParisonError, compare, publish, run_suite


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
        policy = show(self.database, self.bundle)["metadata"]["policy_sha256"]
        self.assertEqual(len(list_runs(self.database, policy_sha256=policy, state="current")), 1)
        self.assertEqual(len(list_runs(self.database, state="modified")), 1)
        self.assertEqual(len(list_runs(self.database, state="missing")), 1)
        self.assertEqual(list_runs(self.database, policy_sha256="0" * 64), [])

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
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["catalog", "remove", "--database", str(self.database), str(self.bundle)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "removed")
        self.assertTrue(self.bundle.is_dir())
        self.assertEqual(list_runs(self.database), [])

    def test_remove_changes_only_the_disposable_index(self):
        add(self.database, self.bundle)
        self.assertEqual(remove(self.database, self.bundle)["status"], "removed")
        self.assertTrue(self.bundle.is_dir())
        with self.assertRaisesRegex(ParisonError, "not in catalog"):
            remove(self.database, self.bundle)

    def test_history_orders_same_policy_runs_and_reports_transitions(self):
        passing = self.root / "passing-run"
        publish(passing, compare(self.recipe, self.baseline, self.baseline), RECIPE)
        add(self.database, self.bundle)
        add(self.database, passing)
        policy = show(self.database, self.bundle)["metadata"]["policy_sha256"]
        result = history(self.database, policy)
        self.assertEqual([Path(run["path"]).name for run in result["runs"]], ["run", "passing-run"])
        self.assertEqual([run["catalog_order"] for run in result["runs"]], [1, 2])
        self.assertEqual(result["transitions"], [{
            "from_catalog_order": 1,
            "to_catalog_order": 2,
            "outcome": {"before": "FAIL", "after": "PASS"},
            "discrepancy_count": {"before": 1, "after": 0, "delta": -1},
        }])
        self.assertEqual(result["runs"][0]["input_sha256"]["baseline"], result["runs"][1]["input_sha256"]["baseline"])

    def test_catalog_order_survives_deletion_and_vacuum(self):
        copies = [self.root / f"run-{index}" for index in range(3)]
        for copy in copies:
            shutil.copytree(self.bundle, copy)
            add(self.database, copy)
        policy = show(self.database, copies[0])["metadata"]["policy_sha256"]
        remove(self.database, copies[1])
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("VACUUM")
        fourth = self.root / "run-3"
        shutil.copytree(self.bundle, fourth)
        add(self.database, fourth)
        self.assertEqual([run["catalog_order"] for run in history(self.database, policy)["runs"]], [1, 3, 4])

    def test_paths_are_lexically_normalized_without_resolving_symlinks(self):
        (self.root / "unused").mkdir()
        result = add(self.database, self.root / "unused" / ".." / "run")
        self.assertEqual(result["path"], str(self.bundle))
        self.assertEqual(show(self.database, self.bundle)["path"], str(self.bundle))

    def test_live_state_hashes_integrity_without_reinspection(self):
        add(self.database, self.bundle)
        with patch("parison.catalog.inspect_bundle", side_effect=AssertionError("must not parse result evidence")):
            self.assertEqual(list_runs(self.database)[0]["state"], "current")

    def test_schema_v1_catalog_migrates_to_explicit_order(self):
        add(self.database, self.bundle)
        metadata = show(self.database, self.bundle)["metadata"]
        self.database.unlink()
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript("""
                CREATE TABLE runs (
                    path TEXT PRIMARY KEY, bundle_sha256 TEXT NOT NULL, kind TEXT NOT NULL,
                    outcome TEXT NOT NULL, metadata TEXT NOT NULL
                );
                PRAGMA user_version = 1;
            """)
            connection.execute(
                "INSERT INTO runs(path, bundle_sha256, kind, outcome, metadata) VALUES (?, ?, ?, ?, ?)",
                (str(self.bundle), metadata["bundle_sha256"], "run", metadata["outcome"], json.dumps(metadata)),
            )
        self.assertEqual(show(self.database, self.bundle)["state"], "current")
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT catalog_order FROM runs").fetchone()[0], 1)

    def test_diff_is_safe_and_requires_matching_run_policies(self):
        passing = self.root / "passing-run"
        publish(passing, compare(self.recipe, self.baseline, self.baseline), RECIPE)
        add(self.database, self.bundle)
        add(self.database, passing)
        result = diff(self.database, self.bundle, passing)
        self.assertTrue(result["changed"])
        self.assertEqual(result["changes"]["outcome"], {"before": "FAIL", "after": "PASS"})
        self.assertNotIn("secret", json.dumps(result))

        other_recipe = self.root / "other-recipe.json"
        changed_recipe = {**RECIPE, "scope": {**RECIPE["scope"], "snapshot": "other"}}
        other_recipe.write_text(json.dumps(changed_recipe), encoding="utf-8")
        other = self.root / "other-run"
        publish(other, compare(other_recipe, self.baseline, self.baseline), changed_recipe)
        add(self.database, other)
        with self.assertRaisesRegex(ParisonError, "matching policy"):
            diff(self.database, self.bundle, other)

    def test_policy_filter_finds_matching_cases_inside_suites(self):
        plan = self.root / "suite.json"
        plan.write_text(json.dumps({
            "suite_version": 1,
            "cases": [{
                "id": "raw-difference", "recipe": "recipe.json",
                "baseline": "baseline.csv", "candidate": "candidate.csv",
            }],
        }), encoding="utf-8")
        suite = self.root / "suite-run"
        run_suite(plan, suite)
        add(self.database, suite)
        policy = show(self.database, suite)["metadata"]["cases"][0]["policy_sha256"]
        matches = list_runs(self.database, policy_sha256=policy)
        self.assertEqual([entry["path"] for entry in matches], [str(suite)])

    def test_cli_history_and_diff_emit_machine_readable_results(self):
        passing = self.root / "passing-run"
        publish(passing, compare(self.recipe, self.baseline, self.baseline), RECIPE)
        add(self.database, self.bundle)
        add(self.database, passing)
        policy = show(self.database, self.bundle)["metadata"]["policy_sha256"]
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["catalog", "history", "--database", str(self.database), "--policy-sha256", policy]), 0)
        self.assertEqual(len(json.loads(stdout.getvalue())["runs"]), 2)
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["catalog", "diff", "--database", str(self.database), str(self.bundle), str(passing)]), 0)
        self.assertTrue(json.loads(stdout.getvalue())["changed"])

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
        with closing(sqlite3.connect(future)) as connection, connection:
            connection.execute("PRAGMA user_version = 99")
        with self.assertRaisesRegex(ParisonError, "version is unsupported"):
            list_runs(future)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("UPDATE runs SET metadata = 'not-json'")
        with self.assertRaisesRegex(ParisonError, "invalid metadata"):
            list_runs(self.database)
        with self.assertRaisesRegex(ParisonError, "lowercase SHA-256"):
            list_runs(self.root / "other.sqlite", policy_sha256="INVALID")


if __name__ == "__main__":
    unittest.main()
