import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from parison.cli import main
from parison.core import ParisonError, explain_recipe, validate_inputs

try:
    import polars as pl
except ImportError:
    pl = None


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {"snapshot": "preflight", "cutoff": "2026-10-07T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "integer", "comparison": "exact"},
    },
    "column_mappings": {"value": {"baseline": "old_value", "candidate": "value"}},
    "excluded_columns": {"note": "not compared"},
    "output": {"sensitivity": "summary"},
}


class InputValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_preflight_validates_mapped_schemas_without_record_values(self):
        baseline = self.root / "baseline.csv"
        candidate = self.root / "candidate.jsonl"
        baseline.write_text("id,old_value,note\nsecret,10,private\n", encoding="utf-8")
        candidate.write_text('{"id":"secret","value":10,"note":"private"}\n', encoding="utf-8")
        result = validate_inputs(self.recipe, baseline, candidate)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["inputs"]["baseline"]["format"], "csv")
        self.assertEqual(result["inputs"]["candidate"]["format"], "jsonl")
        self.assertEqual(result["canonical_columns"], 2)
        self.assertEqual(result["policy_sha256"], explain_recipe(self.recipe)["policy_sha256"])
        self.assertEqual(result["inputs"]["baseline"]["schema"], {
            "missing": [],
            "unexpected": [],
            "mapped": {"value": "old_value"},
            "excluded_present": ["note"],
        })
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("private", json.dumps(result))

    def test_preflight_policy_lock_runs_before_inputs(self):
        expected = explain_recipe(self.recipe)["policy_sha256"]
        with self.assertRaisesRegex(ParisonError, "does not match expected"):
            validate_inputs(self.recipe, "missing-left.csv", "missing-right.csv", expected_policy_sha256="0" * 64)
        with self.assertRaisesRegex(ParisonError, "64 lowercase hexadecimal"):
            validate_inputs(self.recipe, "missing-left.csv", "missing-right.csv", expected_policy_sha256="INVALID")
        self.assertRegex(expected, "^[0-9a-f]{64}$")

    def test_preflight_rejects_schema_mismatch_and_byte_overrun(self):
        baseline = self.root / "baseline.csv"
        candidate = self.root / "candidate.csv"
        baseline.write_text("id,wrong\n1,10\n", encoding="utf-8")
        candidate.write_text("id,value\n1,10\n", encoding="utf-8")
        result = validate_inputs(self.recipe, baseline, candidate)
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["inputs"]["baseline"]["schema"]["missing"], ["old_value"])
        self.assertEqual(result["inputs"]["baseline"]["schema"]["unexpected"], ["wrong"])
        self.assertEqual(result["inputs"]["candidate"]["schema"]["missing"], [])
        with self.assertRaisesRegex(ParisonError, "exceeds limit"):
            validate_inputs(self.recipe, baseline, candidate, max_input_bytes=1)

    def test_cli_emits_json_for_invalid_schemas(self):
        baseline = self.root / "baseline.csv"
        candidate = self.root / "candidate.csv"
        baseline.write_text("id,wrong\n1,10\n", encoding="utf-8")
        candidate.write_text("id,value\n1,10\n", encoding="utf-8")
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["validate-inputs", "--recipe", str(self.recipe), "--baseline", str(baseline), "--candidate", str(candidate)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "invalid")
        self.assertIn("JSON diagnostics", stderr.getvalue())

    def test_cli_reports_partition_metadata(self):
        baseline = self.root / "baseline"
        baseline.mkdir()
        (baseline / "a.csv").write_text("id,old_value,note\n1,10,x\n", encoding="utf-8")
        (baseline / "b.csv").write_text("note,old_value,id\ny,20,2\n", encoding="utf-8")
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value,note\n1,10,x\n", encoding="utf-8")
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["validate-inputs", "--recipe", str(self.recipe), "--baseline", str(baseline), "--candidate", str(candidate)])
        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["inputs"]["baseline"]["partitions"], 2)
        self.assertIn("Validated input schemas", stderr.getvalue())

    def test_sqlite_schema_is_inspected_read_only(self):
        database = self.root / "input.sqlite"
        with closing(sqlite3.connect(database)) as connection:
            connection.execute("CREATE TABLE baseline (id TEXT, old_value INTEGER, note TEXT)")
            connection.execute("INSERT INTO baseline VALUES ('secret', 10, 'private')")
            connection.execute("CREATE TABLE candidate (id TEXT, value INTEGER, note TEXT)")
            connection.execute("INSERT INTO candidate VALUES ('secret', 10, 'private')")
            connection.commit()
        result = validate_inputs(self.recipe, f"sqlite:{database}#baseline", f"sqlite:{database}#candidate")
        self.assertEqual(result["inputs"]["baseline"]["format"], "sqlite")
        self.assertEqual(result["inputs"]["candidate"]["table"], "candidate")
        self.assertNotIn("secret", json.dumps(result))

    @unittest.skipUnless(pl, "Polars optional dependency is not installed")
    def test_parquet_schema_is_supported(self):
        baseline = self.root / "baseline.parquet"
        candidate = self.root / "candidate.parquet"
        pl.DataFrame({"id": ["secret"], "old_value": [10], "note": ["private"]}).write_parquet(baseline)
        pl.DataFrame({"id": ["secret"], "value": [10], "note": ["private"]}).write_parquet(candidate)
        result = validate_inputs(self.recipe, baseline, candidate)
        self.assertEqual(result["inputs"]["baseline"]["format"], "parquet")
        self.assertNotIn("private", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
