import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, explain_recipe, export_evidence, inspect_bundle, load_schema, load_suite, run_suite, verify_bundle


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {"snapshot": "suite-test", "cutoff": "2026-10-09T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {"id": {"type": "string"}, "value": {"type": "integer"}},
    "output": {"sensitivity": "summary"},
}


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "recipe.json").write_text(json.dumps(RECIPE), encoding="utf-8")
        (self.root / "baseline.csv").write_text("id,value\na,1\n", encoding="utf-8")
        (self.root / "candidate.csv").write_text("id,value\na,1\n", encoding="utf-8")
        (self.root / "different.csv").write_text("id,value\na,2\n", encoding="utf-8")
        (self.root / "invalid.csv").write_text("id,value\na,not-an-integer\n", encoding="utf-8")
        self.plan = self.root / "suite.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_plan(self, cases):
        self.plan.write_text(json.dumps({"suite_version": 1, "cases": cases}), encoding="utf-8")

    def case(self, identifier="orders"):
        return {"id": identifier, "recipe": "recipe.json", "baseline": "baseline.csv", "candidate": "candidate.csv"}

    def test_schema_and_loader_resolve_references(self):
        schema = load_schema("suite")
        Draft202012Validator.check_schema(schema)
        self.write_plan([self.case()])
        Draft202012Validator(schema).validate(json.loads(self.plan.read_text(encoding="utf-8")))
        loaded = load_suite(self.plan)
        self.assertEqual(loaded["cases"][0]["recipe"], str(self.root / "recipe.json"))
        self.assertEqual(loaded["cases"][0]["baseline"], str(self.root / "baseline.csv"))

    def test_policy_lock_and_cli_validation(self):
        case = self.case()
        case["expected_policy_sha256"] = explain_recipe(self.root / "recipe.json")["policy_sha256"]
        self.write_plan([case])
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["validate-suite", str(self.plan)]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"cases": 1, "status": "valid"})
        self.assertIn("Validated comparison suite", stderr.getvalue())

    def test_rejects_duplicates_unknown_fields_and_policy_drift(self):
        self.write_plan([self.case(), self.case()])
        with self.assertRaisesRegex(ParisonError, "duplicate suite case id"):
            load_suite(self.plan)
        invalid = self.case()
        invalid["command"] = "anything"
        self.write_plan([invalid])
        with self.assertRaisesRegex(ParisonError, "invalid fields"):
            load_suite(self.plan)
        locked = self.case()
        locked["expected_policy_sha256"] = "0" * 64
        self.write_plan([locked])
        with self.assertRaisesRegex(ParisonError, "does not match expected"):
            load_suite(self.plan)

    def test_rejects_unsafe_ids_and_missing_inputs(self):
        self.write_plan([self.case("../escape")])
        with self.assertRaisesRegex(ParisonError, "invalid id"):
            load_suite(self.plan)
        missing = self.case()
        missing["candidate"] = "missing.csv"
        self.write_plan([missing])
        with self.assertRaisesRegex(ParisonError, "candidate is not a regular input"):
            load_suite(self.plan)

    def test_run_suite_publishes_ordered_children_and_reduces_outcome(self):
        passing = self.case("passing")
        failing = self.case("failing")
        failing["candidate"] = "different.csv"
        self.write_plan([passing, failing])
        output = self.root / "run"
        result = run_suite(self.plan, output)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertTrue(result["complete"])
        self.assertEqual(result["outcome_counts"]["PASS"], 1)
        self.assertEqual(result["outcome_counts"]["FAIL"], 1)
        self.assertEqual([case["id"] for case in result["cases"]], ["passing", "failing"])
        self.assertTrue((output / "cases" / "passing" / "manifest.json").is_file())
        self.assertTrue((output / "cases" / "failing" / "manifest.json").is_file())
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        Draft202012Validator(load_schema("suite-result")).validate(result)
        Draft202012Validator(load_schema("suite-manifest")).validate(manifest)
        self.assertEqual(manifest["kind"], "suite")
        self.assertEqual(set(manifest["cases"]), {"passing", "failing"})
        self.assertEqual(verify_bundle(output)["kind"], "suite")
        inspection = inspect_bundle(output)
        self.assertEqual(inspection["outcome_counts"]["FAIL"], 1)
        self.assertNotIn("discrepancy_sample", json.dumps(inspection))
        with self.assertRaisesRegex(ParisonError, "requires a child run bundle"):
            export_evidence(output, self.root / "suite-evidence.jsonl")
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as verify_stderr:
            self.assertEqual(main(["verify", str(output)]), 0)
        self.assertIn("suite", verify_stderr.getvalue())
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["run-suite", "--plan", str(self.plan), "--output", str(self.root / "cli-run")]), 1)
        self.assertEqual(json.loads(stdout.getvalue())["cases"], 2)
        self.assertIn("Parison suite FAIL", stderr.getvalue())
        with self.assertRaisesRegex(ParisonError, "output already exists"):
            run_suite(self.plan, output)
        child_result = output / "cases" / "passing" / "result.json"
        child_result.write_text(child_result.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "failed integrity"):
            verify_bundle(output)

    def test_run_suite_continues_after_case_error(self):
        broken = self.case("broken")
        broken["candidate"] = "invalid.csv"
        self.write_plan([broken, self.case("passing")])
        result = run_suite(self.plan, self.root / "error-run")
        self.assertEqual(result["outcome"], "ERROR")
        self.assertEqual(result["completed_cases"], 2)
        self.assertEqual([case["outcome"] for case in result["cases"]], ["ERROR", "PASS"])

    def test_interruption_stops_after_publishing_interrupted_child(self):
        self.write_plan([self.case("first"), self.case("second")])
        output = self.root / "interrupted"
        with patch("parison.core.compare", side_effect=KeyboardInterrupt):
            result = run_suite(self.plan, output)
        self.assertEqual(result["outcome"], "INTERRUPTED")
        self.assertEqual(result["completed_cases"], 1)
        self.assertEqual(result["total_cases"], 2)
        self.assertFalse(result["complete"])
        self.assertEqual(verify_bundle(output)["outcome"], "INTERRUPTED")


if __name__ == "__main__":
    unittest.main()
