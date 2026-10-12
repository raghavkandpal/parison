import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, evidence_statement, export_statement, load_schema, report_cutover, run_suite, verify_statement


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "statement-fixture",
        "cutoff": "2026-10-12T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {"id": {"type": "string"}, "value": {"type": "integer"}},
    "output": {"sensitivity": "summary"},
}


class StatementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        self.baseline = self.root / "baseline.csv"
        self.candidate = self.root / "candidate.csv"
        self.baseline.write_text("id,value\na,1\n", encoding="utf-8")
        self.candidate.write_text("id,value\na,1\n", encoding="utf-8")
        self.bundle = self.root / "run"
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(main([
                "compare", "--recipe", str(self.recipe), "--baseline", str(self.baseline),
                "--candidate", str(self.candidate), "--output", str(self.bundle),
            ]), 0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_run_statement_is_canonical_safe_schema_valid_and_verifiable(self):
        output = self.root / "nested" / "parison-statement.json"
        exported = export_statement(self.bundle, output)
        statement = json.loads(output.read_text(encoding="utf-8"))
        Draft202012Validator(load_schema("statement")).validate(statement)
        self.assertEqual(statement, evidence_statement(self.bundle))
        self.assertEqual(statement["predicate"]["bundleKind"], "run")
        self.assertEqual(statement["predicate"]["outcome"], "PASS")
        self.assertEqual(statement["predicate"]["contract"], "keyed-v1")
        self.assertEqual(statement["subject"][0]["digest"]["sha256"], exported["bundle_sha256"])
        self.assertEqual(
            output.read_bytes(),
            (json.dumps(statement, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        )
        encoded = output.read_text(encoding="utf-8")
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("2026-10-12T", encoded)
        self.assertEqual(verify_statement(self.bundle, output)["status"], "valid")
        with self.assertRaisesRegex(ParisonError, "already exists"):
            export_statement(self.bundle, output)

    def test_checked_in_statement_fixture_is_byte_exact(self):
        repository = Path(__file__).parents[1]
        output = self.root / "fixture.json"
        export_statement(repository / "examples" / "output", output)
        self.assertEqual(output.read_bytes(), (repository / "examples" / "0.17" / "parison-statement.json").read_bytes())

    def test_statement_rejects_semantic_or_bundle_substitution(self):
        output = self.root / "statement.json"
        export_statement(self.bundle, output)
        changed = json.loads(output.read_text(encoding="utf-8"))
        changed["predicate"]["outcome"] = "FAIL"
        mismatch = self.root / "mismatch.json"
        mismatch.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "does not match"):
            verify_statement(self.bundle, mismatch)
        (self.bundle / "report.html").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "failed integrity check"):
            verify_statement(self.bundle, output)

    def test_statement_rejects_ambiguous_json(self):
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"_type":"first","_type":"second"}', encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "duplicate JSON field"):
            verify_statement(self.bundle, duplicate)

    def test_statement_rejects_bundle_change_during_projection(self):
        original = Path.read_bytes
        changed = False

        def mutate_result(path):
            nonlocal changed
            value = original(path)
            if path.name == "result.json" and not changed:
                changed = True
                path.write_text("{}", encoding="utf-8")
            return value

        with patch.object(Path, "read_bytes", mutate_result):
            with self.assertRaisesRegex(ParisonError, "changed while preparing Statement"):
                evidence_statement(self.bundle)

    def test_suite_statement_has_suite_policy_and_scope(self):
        plan = self.root / "suite.json"
        plan.write_text(json.dumps({
            "suite_version": 2,
            "cases": [{
                "id": "orders", "recipe": "recipe.json", "baseline": "baseline.csv", "candidate": "candidate.csv",
            }],
        }), encoding="utf-8")
        suite = self.root / "suite-run"
        run_suite(plan, suite)
        statement = evidence_statement(suite)
        Draft202012Validator(load_schema("statement")).validate(statement)
        predicate = statement["predicate"]
        self.assertEqual(predicate["bundleKind"], "suite")
        self.assertEqual(predicate["suiteVersion"], 2)
        self.assertTrue(predicate["scopeComplete"])
        self.assertRegex(predicate["suitePolicySha256"], "^[0-9a-f]{64}$")
        self.assertNotIn("cases", predicate)

    def test_cli_names_external_authentication_boundary(self):
        output = self.root / "statement.json"
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["statement", str(self.bundle), "--output", str(output)]), 0)
        self.assertIn("unsigned Statement", stderr.getvalue())
        with redirect_stdout(stdout := StringIO()), redirect_stderr(stderr := StringIO()):
            self.assertEqual(main(["verify-statement", str(self.bundle), str(output)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "valid")
        self.assertIn("signature authentication is external", stderr.getvalue())

    def test_cutover_report_is_safe_deterministic_and_no_overwrite(self):
        output = self.root / "reports" / "cutover.md"
        metadata = report_cutover(self.bundle, output)
        report = output.read_text(encoding="utf-8")
        self.assertIn("# Parison cutover evidence", report)
        self.assertIn("| Outcome | PASS |", report)
        self.assertIn("| Comparison contract | keyed-v1 |", report)
        self.assertIn(metadata["bundle_sha256"], report)
        self.assertIn("evidence, not cutover approval", report)
        self.assertNotIn(str(self.root), report)
        self.assertNotIn("statement-fixture", report)
        with self.assertRaisesRegex(ParisonError, "already exists"):
            report_cutover(self.bundle, output)

    def test_suite_cutover_report_lists_ordered_cases_and_scope(self):
        plan = self.root / "report-suite.json"
        plan.write_text(json.dumps({
            "suite_version": 2,
            "cases": [{
                "id": "orders", "recipe": "recipe.json", "baseline": "baseline.csv", "candidate": "candidate.csv",
            }],
        }), encoding="utf-8")
        suite = self.root / "report-suite"
        run_suite(plan, suite)
        output = self.root / "suite-cutover.md"
        report_cutover(suite, output)
        report = output.read_text(encoding="utf-8")
        self.assertIn("| Bundle kind | suite |", report)
        self.assertIn("| Scope complete | true |", report)
        self.assertIn("| orders | PASS | true |", report)


if __name__ == "__main__":
    unittest.main()
