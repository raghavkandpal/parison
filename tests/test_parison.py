import csv
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from parison import __version__
from parison.cli import main
from parison.core import ParisonError, compare, error_result, explain_recipe, load_recipe, publish, verify_bundle


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["order_id"],
    "scope": {"snapshot": "synthetic-orders-v1", "cutoff": "2026-10-01T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {
        "order_id": {"type": "string", "comparison": "exact"},
        "status": {"type": "string", "comparison": "exact"},
        "total": {
            "type": "decimal",
            "scale": 2,
            "comparison": "numeric",
            "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
        },
    },
    "output": {"sensitivity": "summary"},
}


class ParisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def csv(self, name, rows):
        path = self.root / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["order_id", "status", "total"])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_pass_with_symmetric_tolerance_and_reordering(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "10.00"}, {"order_id": "002", "status": "ok", "total": "2"}])
        right = self.csv("right.csv", [{"order_id": "002", "status": "ok", "total": "2"}, {"order_id": "001", "status": "ok", "total": "10.01"}])
        result = compare(self.recipe, left, right)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_within_tolerance"], 1)
        self.assertEqual(result["counts"]["matched_exact"], 1)

    def test_missing_and_different_rows_fail_with_conserved_counts(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "10"}, {"order_id": "002", "status": "ok", "total": "2"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "bad", "total": "10"}, {"order_id": "003", "status": "ok", "total": "2"}])
        result = compare(self.recipe, left, right)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["counts"]["baseline"], result["counts"]["common_keys"] + result["counts"]["baseline_only"])
        self.assertEqual(result["counts"]["candidate"], result["counts"]["common_keys"] + result["counts"]["candidate_only"])

    def test_duplicate_or_empty_identity_is_inconclusive(self):
        rows = [{"order_id": "001", "status": "ok", "total": "1"}] * 2
        left = self.csv("left.csv", rows)
        right = self.csv("right.csv", rows[:1])
        self.assertEqual(compare(self.recipe, left, right)["outcome"], "INCONCLUSIVE")

    def test_strict_recipe_and_atomic_bundle(self):
        invalid = dict(RECIPE, surprise=True)
        self.recipe.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "unknown recipe"):
            load_recipe(self.recipe)
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        output = self.root / "run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output)]), 0)
        self.assertEqual({p.name for p in output.iterdir()}, {"result.json", "effective-recipe.json", "report.html", "manifest.json"})
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["outcome"], "PASS")
        self.assertEqual(manifest["runtime"]["contract"], "keyed-v1")
        self.assertIn("python", manifest["runtime"])

    def test_summary_artifacts_do_not_contain_raw_values(self):
        left = self.csv("left.csv", [{"order_id": "secret-key", "status": "secret-old", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "secret-key", "status": "secret-new", "total": "1"}])
        result = compare(self.recipe, left, right)
        encoded = json.dumps(result)
        self.assertNotIn("secret-key", encoded)
        self.assertNotIn("secret-old", encoded)
        self.assertNotIn("secret-new", encoded)

    def test_omitted_output_uses_effective_summary_default(self):
        value = json.loads(json.dumps(RECIPE))
        del value["output"]
        self.recipe.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(load_recipe(self.recipe)["output"], {"sensitivity": "summary"})
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        self.assertEqual(compare(self.recipe, left, right)["sensitivity"], "summary")

    def test_report_surfaces_scope_fields_exclusions_limits_and_runtime(self):
        value = json.loads(json.dumps(RECIPE))
        value["columns"]["status"]["normalize"] = ["trim", "casefold"]
        value["column_mappings"] = {"status": {"baseline": "legacy_status", "candidate": "status"}}
        value["excluded_columns"] = {"updated_at": "nondeterministic metadata"}
        self.recipe.write_text(json.dumps(value), encoding="utf-8")
        left = self.root / "left.csv"
        right = self.root / "right.csv"
        left.write_text("order_id,legacy_status,total,updated_at\n001,ok,1,old\n", encoding="utf-8")
        right.write_text("order_id,status,total,updated_at\n001,ok,1,new\n", encoding="utf-8")
        output = self.root / "report-run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output)]), 0)
        report = (output / "report.html").read_text(encoding="utf-8")
        for expected in ("synthetic-orders-v1", "status", "legacy_status", "Candidate column", "updated_at", "nondeterministic metadata", "nulls equal", "symmetric-v1", "trim", "casefold", "max input bytes", "keyed-v1", "SHA-256"):
            self.assertIn(expected, report)
        self.assertIn('id="field-class"', report)
        self.assertIn('id="field-count" role="status"', report)
        self.assertIn("Showing 2 of 2 fields", report)
        self.assertIn('id="field-summary"', report)
        self.assertNotIn('id="raw-evidence"', report)

    def test_explain_makes_effective_policy_explicit_without_inputs(self):
        value = json.loads(json.dumps(RECIPE))
        value["columns"]["status"]["normalize"] = ["trim", "casefold"]
        value["column_mappings"] = {"status": {"baseline": "legacy_status", "candidate": "status"}}
        value["excluded_columns"] = {"updated_at": "nondeterministic metadata"}
        self.recipe.write_text(json.dumps(value), encoding="utf-8")
        explanation = explain_recipe(self.recipe)
        self.assertEqual(explanation["schema_version"], 1)
        self.assertTrue(explanation["columns"]["order_id"]["key"])
        self.assertEqual(explanation["columns"]["order_id"]["normalize"], [])
        self.assertEqual(explanation["columns"]["status"]["baseline_column"], "legacy_status")
        self.assertEqual(explanation["columns"]["status"]["normalize"], ["trim", "casefold"])
        self.assertEqual(explanation["columns"]["total"]["comparison"], "numeric")
        self.assertRegex(explanation["policy_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn(str(self.recipe), json.dumps(explanation))

        reordered = self.root / "reordered.json"
        reordered.write_text(json.dumps(value, sort_keys=True, indent=4), encoding="utf-8")
        self.assertNotEqual(self.recipe.read_bytes(), reordered.read_bytes())
        self.assertEqual(explain_recipe(reordered)["policy_sha256"], explanation["policy_sha256"])

        value["nulls_equal"] = False
        reordered.write_text(json.dumps(value), encoding="utf-8")
        self.assertNotEqual(explain_recipe(reordered)["policy_sha256"], explanation["policy_sha256"])

    def test_explain_cli_prints_machine_readable_policy(self):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["explain", str(self.recipe)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["comparison_mode"], "keyed")
        self.assertIn("Explained effective policy", stderr.getvalue())

    def test_expected_policy_fingerprint_gates_comparison_before_inputs(self):
        expected = explain_recipe(self.recipe)["policy_sha256"]
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        self.assertEqual(compare(self.recipe, left, left, expected_policy_sha256=expected)["outcome"], "PASS")
        with self.assertRaisesRegex(ParisonError, "does not match expected"):
            compare(self.recipe, "missing-left.csv", "missing-right.csv", expected_policy_sha256="0" * 64)
        with self.assertRaisesRegex(ParisonError, "64 lowercase hexadecimal"):
            compare(self.recipe, left, left, expected_policy_sha256="INVALID")

    def test_cli_policy_fingerprint_mismatch_publishes_safe_error(self):
        output = self.root / "policy-error"
        code = main([
            "compare", "--recipe", str(self.recipe), "--baseline", "missing-left.csv",
            "--candidate", "missing-right.csv", "--output", str(output),
            "--expected-policy-sha256", "0" * 64,
        ])
        self.assertEqual(code, 2)
        result = json.loads((output / "result.json").read_text())
        self.assertEqual(result["outcome"], "ERROR")
        self.assertIn("does not match expected", result["problems"][0])

    def test_raw_evidence_is_explicit_bounded_and_html_escaped(self):
        raw_recipe = dict(RECIPE, output={"sensitivity": "raw"})
        self.recipe.write_text(json.dumps(raw_recipe), encoding="utf-8")
        left = self.csv("left.csv", [{"order_id": "001", "status": "<script>old</script>", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "new", "total": "1.02"}])
        result = compare(self.recipe, left, right, sample_limit=1)
        self.assertEqual(result["field_discrepancy_count"], 2)
        self.assertEqual(len(result["discrepancy_sample"]), 1)
        output = self.root / "raw-run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output), "--sample-limit", "1"]), 1)
        report = (output / "report.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>old</script>", report)
        self.assertIn("&lt;script&gt;old&lt;/script&gt;", report)
        for hook in ('id="raw-key"', 'id="raw-field"', 'id="raw-class"', 'id="raw-count" role="status"', 'id="raw-evidence"', 'data-class="different"', "Showing 1 of 1 sampled items"):
            self.assertIn(hook, report)
        self.assertEqual(json.loads((output / "manifest.json").read_text())["sensitivity"], "raw")
        evidence = self.root / "status-evidence.jsonl"
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["export-evidence", str(output), "--kind", "field", "--name", "status", "--output", str(evidence)]), 0)
        lines = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines[0]["_parison_export"]["name"], "status")
        self.assertEqual(lines[1]["field"], "status")

    def test_report_controls_do_not_change_canonical_result(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "old", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "new", "total": "1"}])
        result = compare(self.recipe, left, right)
        output = self.root / "filter-run"
        publish(output, result, load_recipe(self.recipe))
        self.assertEqual(json.loads((output / "result.json").read_text()), result)
        report = (output / "report.html").read_text(encoding="utf-8")
        self.assertIn("<th>status</th>", report)
        self.assertIn("<th>total</th>", report)

    def test_ragged_csv_and_symlinks_are_rejected_as_errors(self):
        good = self.csv("good.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        ragged = self.root / "ragged.csv"
        ragged.write_text("order_id,status,total\n001,ok,1,unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "ragged CSV row"):
            compare(self.recipe, good, ragged)
        link = self.root / "linked.csv"
        link.symlink_to(good)
        with self.assertRaisesRegex(ParisonError, "must not be a symlink"):
            compare(self.recipe, link, good)
        with self.assertRaisesRegex(ParisonError, "must not be a symlink"):
            compare(self.recipe, good, link)

    def test_cli_publishes_safe_error_bundle(self):
        good = self.csv("good.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        ragged = self.root / "ragged.csv"
        ragged.write_text("order_id,status,total\n001,ok,1,secret-value\n", encoding="utf-8")
        output = self.root / "error-run"
        code = main(["compare", "--recipe", str(self.recipe), "--baseline", str(good), "--candidate", str(ragged), "--output", str(output)])
        self.assertEqual(code, 2)
        result = json.loads((output / "result.json").read_text())
        self.assertEqual(result["outcome"], "ERROR")
        self.assertFalse(result["complete"])
        self.assertNotIn("secret-value", json.dumps(result))
        self.assertEqual(json.loads((output / "manifest.json").read_text())["sensitivity"], "summary")

    def test_cli_parse_error_bundle_does_not_echo_rejected_value(self):
        secret = "customer-secret-123"
        good = self.csv("good.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        invalid = self.csv("invalid.csv", [{"order_id": "001", "status": "ok", "total": secret}])
        output = self.root / "parse-error"
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main([
                "compare", "--recipe", str(self.recipe), "--baseline", str(good),
                "--candidate", str(invalid), "--output", str(output),
            ])
        evidence = json.dumps(json.loads((output / "result.json").read_text())) + stderr.getvalue()
        self.assertEqual(code, 2)
        self.assertIn("cannot parse column total as decimal", evidence)
        self.assertNotIn(secret, evidence)

    def test_publication_io_failure_is_a_controlled_error(self):
        result = error_result("test")
        with patch("parison.core.tempfile.mkdtemp", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(ParisonError, "cannot prepare bundle output: disk full"):
                publish(self.root / "run", result, None)
        self.assertFalse((self.root / "run").exists())

        stage = self.root / ".chmod-stage"
        stage.mkdir()
        with patch("parison.core.tempfile.mkdtemp", return_value=str(stage)), patch("parison.core.os.chmod", side_effect=OSError("permissions unavailable")):
            with self.assertRaisesRegex(ParisonError, "cannot prepare bundle output: permissions unavailable"):
                publish(self.root / "run", result, None)
        self.assertFalse(stage.exists())

        stage = self.root / ".run-stage"
        stage.mkdir()
        with patch("parison.core.tempfile.mkdtemp", return_value=str(stage)), patch("parison.core.os.replace", side_effect=OSError("read-only filesystem")):
            with self.assertRaisesRegex(ParisonError, "cannot publish bundle: read-only filesystem"):
                publish(self.root / "run", result, None)
        self.assertFalse(stage.exists())

    def test_bundle_verification_detects_tampering(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        output = self.root / "run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output)]), 0)
        self.assertTrue(verify_bundle(output)["complete"])
        (output / "result.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "failed integrity"):
            verify_bundle(output)

    def test_bundle_verification_rejects_incomplete_or_inconsistent_metadata(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        output = self.root / "run"
        publish(output, compare(self.recipe, left, left), load_recipe(self.recipe))
        manifest_path = output / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        del manifest["outcome"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "invalid outcome"):
            verify_bundle(output)

        manifest["outcome"] = "FAIL"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "manifest outcome does not match result"):
            verify_bundle(output)

        del manifest["files"]["result.json"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "required bundle files"):
            verify_bundle(output)

    def test_bundle_verification_rejects_symlinked_manifest(self):
        run = self.root / "run"
        run.mkdir()
        manifest = self.root / "manifest.json"
        manifest.write_text("{}", encoding="utf-8")
        (run / "manifest.json").symlink_to(manifest)
        with self.assertRaisesRegex(ParisonError, "manifest is missing or unsafe"):
            verify_bundle(run)

    def test_cli_reports_package_version(self):
        output = StringIO()
        with self.assertRaisesRegex(SystemExit, "0"), redirect_stdout(output):
            main(["--version"])
        self.assertEqual(output.getvalue(), f"parison {__version__}\n")

    def test_cli_preserves_json_stdout_and_prints_safe_summary(self):
        left = self.csv("left.csv", [{"order_id": "secret-key", "status": "old-secret", "total": "10.00"}])
        right = self.csv("right.csv", [{"order_id": "secret-key", "status": "new-secret", "total": "10.00"}])
        output = self.root / "summary-run"
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue()), {"outcome": "FAIL", "output": str(output)})
        summary = stderr.getvalue()
        for expected in ("Parison FAIL", "Rows:", "Matches:", "Sensitivity: summary", f"Bundle: {output}", "Exit 1 means the comparison completed"):
            self.assertIn(expected, summary)
        for secret in ("secret-key", "old-secret", "new-secret"):
            self.assertNotIn(secret, summary)

    def test_verify_keeps_valid_stdout_and_explains_integrity(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        output = self.root / "verify-run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(left), "--output", str(output)]), 0)
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["verify", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue(), "valid\n")
        self.assertIn("Verified bundle integrity", stderr.getvalue())
        self.assertIn("recorded outcome: PASS", stderr.getvalue())
        self.assertIn("does not change", stderr.getvalue())

        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["verify", str(output), "--json"])
        self.assertEqual(code, 0)
        metadata = json.loads(stdout.getvalue())
        self.assertEqual(metadata["outcome"], "PASS")
        self.assertEqual(metadata["sensitivity"], "summary")
        self.assertIn("result.json", metadata["files"])

    def test_raw_sample_includes_missing_keys_with_one_shared_limit(self):
        raw_recipe = dict(RECIPE, output={"sensitivity": "raw"})
        self.recipe.write_text(json.dumps(raw_recipe), encoding="utf-8")
        left = self.csv("left.csv", [{"order_id": "001", "status": "old", "total": "1"}, {"order_id": "002", "status": "ok", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "new", "total": "1"}, {"order_id": "003", "status": "ok", "total": "1"}])
        result = compare(self.recipe, left, right, sample_limit=2)
        self.assertEqual(result["discrepancy_count"], 3)
        self.assertEqual(len(result["discrepancy_sample"]), 2)
        self.assertEqual({item["classification"] for item in result["discrepancy_sample"]}, {"baseline_only", "candidate_only"})

    def test_empty_string_is_not_a_null_string(self):
        left = self.csv("left.csv", [{"order_id": "", "status": "", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "", "status": "changed", "total": "1"}])
        result = compare(self.recipe, left, right)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertFalse(result["problems"])
        self.assertEqual(result["counts"]["matched_with_required_difference"], 1)

    def test_input_byte_limit_returns_error_bundle(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        output = self.root / "limited-run"
        code = main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output), "--max-input-bytes", "1"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads((output / "result.json").read_text())["outcome"], "ERROR")

    def test_keyboard_interrupt_returns_130_and_publishes_bundle(self):
        output = self.root / "interrupted-run"
        stderr = StringIO()
        with patch("parison.cli.compare", side_effect=KeyboardInterrupt), redirect_stderr(stderr):
            code = main(["compare", "--recipe", str(self.recipe), "--baseline", "unused-a.csv", "--candidate", "unused-b.csv", "--output", str(output)])
        self.assertEqual(code, 130)
        result = json.loads((output / "result.json").read_text())
        self.assertEqual(result["outcome"], "INTERRUPTED")
        self.assertFalse(result["complete"])
        self.assertEqual(verify_bundle(output)["outcome"], "INTERRUPTED")
        self.assertIn("Parison INTERRUPTED", stderr.getvalue())
        self.assertIn(f"Bundle: {output}", stderr.getvalue())

    def test_row_limit_stops_csv_comparison(self):
        rows = [{"order_id": str(i), "status": "ok", "total": "1"} for i in range(2)]
        left = self.csv("left.csv", rows)
        right = self.csv("right.csv", rows)
        with self.assertRaisesRegex(ParisonError, "row count.*exceeds limit 1"):
            compare(self.recipe, left, right, max_rows=1)


if __name__ == "__main__":
    unittest.main()
