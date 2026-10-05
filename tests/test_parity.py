import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parity.cli import main
from parity.core import ParityError, compare, load_recipe, verify_bundle


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["order_id"],
    "scope": {"snapshot": "synthetic-orders-v1", "cutoff": "2026-10-01T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "columns": {
        "order_id": {"type": "string", "comparison": "exact"},
        "status": {"type": "string", "comparison": "exact"},
        "total": {
            "type": "decimal",
            "comparison": "numeric",
            "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"},
        },
    },
    "output": {"sensitivity": "summary"},
}


class ParityTests(unittest.TestCase):
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
        with self.assertRaisesRegex(ParityError, "unknown recipe"):
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

    def test_report_surfaces_scope_fields_exclusions_limits_and_runtime(self):
        value = dict(RECIPE, excluded_columns={"updated_at": "nondeterministic metadata"})
        self.recipe.write_text(json.dumps(value), encoding="utf-8")
        left = self.root / "left.csv"
        right = self.root / "right.csv"
        contents = "order_id,status,total,updated_at\n001,ok,1,old\n"
        left.write_text(contents, encoding="utf-8")
        right.write_text(contents.replace("old", "new"), encoding="utf-8")
        output = self.root / "report-run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output)]), 0)
        report = (output / "report.html").read_text(encoding="utf-8")
        for expected in ("synthetic-orders-v1", "status", "updated_at", "nondeterministic metadata", "max input bytes", "keyed-v1", "SHA-256"):
            self.assertIn(expected, report)

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
        self.assertEqual(json.loads((output / "manifest.json").read_text())["sensitivity"], "raw")

    def test_ragged_csv_and_symlinks_are_rejected_as_errors(self):
        good = self.csv("good.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        ragged = self.root / "ragged.csv"
        ragged.write_text("order_id,status,total\n001,ok,1,unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(ParityError, "ragged CSV row"):
            compare(self.recipe, good, ragged)
        link = self.root / "linked.csv"
        link.symlink_to(good)
        with self.assertRaisesRegex(ParityError, "must not be a symlink"):
            compare(self.recipe, link, good)

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

    def test_bundle_verification_detects_tampering(self):
        left = self.csv("left.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        right = self.csv("right.csv", [{"order_id": "001", "status": "ok", "total": "1"}])
        output = self.root / "run"
        self.assertEqual(main(["compare", "--recipe", str(self.recipe), "--baseline", str(left), "--candidate", str(right), "--output", str(output)]), 0)
        self.assertTrue(verify_bundle(output)["complete"])
        (output / "result.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ParityError, "failed integrity"):
            verify_bundle(output)

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
        with patch("parity.cli.compare", side_effect=KeyboardInterrupt):
            code = main(["compare", "--recipe", str(self.recipe), "--baseline", "unused-a.csv", "--candidate", "unused-b.csv", "--output", str(output)])
        self.assertEqual(code, 130)
        result = json.loads((output / "result.json").read_text())
        self.assertEqual(result["outcome"], "INTERRUPTED")
        self.assertFalse(result["complete"])

    def test_row_limit_stops_csv_comparison(self):
        rows = [{"order_id": str(i), "status": "ok", "total": "1"} for i in range(2)]
        left = self.csv("left.csv", rows)
        right = self.csv("right.csv", rows)
        with self.assertRaisesRegex(ParityError, "row count.*exceeds limit 1"):
            compare(self.recipe, left, right, max_rows=1)


if __name__ == "__main__":
    unittest.main()
