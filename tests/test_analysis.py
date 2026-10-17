import copy
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.analysis import (
    analyze_bundle,
    analyze_series,
    drill_down,
    export_drilldown,
    publish_analysis,
    verify_analysis_bundle,
)
from parison.cli import main
from parison.core import ParisonError, compare, load_schema, publish

RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["order_id"],
    "scope": {
        "snapshot": "analysis-fixture",
        "cutoff": "2026-10-17T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
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


class DiscrepancyAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make_run(self, name, candidate_rows, recipe=None):
        recipe = copy.deepcopy(recipe or RECIPE)
        recipe_path = self.root / f"{name}-recipe.json"
        recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
        baseline = self.root / f"{name}-baseline.csv"
        candidate = self.root / f"{name}-candidate.csv"
        baseline.write_text("order_id,status,total\n1,ok,10.00\n2,ok,20.00\n", encoding="utf-8")
        candidate.write_text("order_id,status,total\n" + "\n".join(candidate_rows) + "\n", encoding="utf-8")
        result = compare(recipe_path, baseline, candidate)
        output = self.root / name
        publish(output, result, recipe)
        return output

    def test_keyed_analysis_is_exhaustive_deterministic_and_summary_safe(self):
        bundle = self.make_run("first", ["1,bad,10.01", "3,ok,20.00"])
        first = analyze_bundle(bundle)
        second = analyze_bundle(bundle)
        self.assertEqual(first, second)
        Draft202012Validator(load_schema("discrepancy-analysis")).validate(first)
        counts = {(g["descriptor"].get("name"), g["descriptor"]["classification"]): g["count"] for g in first["groups"]}
        self.assertEqual(counts[(None, "baseline_only")], 1)
        self.assertEqual(counts[(None, "candidate_only")], 1)
        self.assertEqual(counts[("status", "different")], 1)
        self.assertEqual(
            next(
                g["group_id"]
                for g in first["groups"]
                if g["descriptor"].get("name") == "status" and g["descriptor"]["classification"] == "different"
            ),
            "a9602587a0e8996471299c58b60e6517be3f40ab1d4e68717d03ed34510f0e2b",
        )
        self.assertEqual(counts[("total", "within_tolerance")], 1)
        encoded = json.dumps(first, sort_keys=True)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("bad", encoded)

    def test_series_preserves_order_and_classifies_exact_transitions(self):
        first = self.make_run("first", ["1,bad,10.00", "2,ok,20.00"])
        second = self.make_run("second", ["1,ok,10.00", "2,ok,20.01"])
        series = analyze_series([first, second])
        Draft202012Validator(load_schema("discrepancy-analysis")).validate(series)
        statuses = {
            (g["descriptor"].get("name"), g["descriptor"]["classification"]): g["counts"] for g in series["groups"]
        }
        self.assertEqual(statuses[("status", "different")], [1, 0])
        self.assertEqual(statuses[("total", "within_tolerance")], [0, 1])
        self.assertIn("resolved", {transition["status"] for transition in series["transitions"]})
        self.assertIn("introduced", {transition["status"] for transition in series["transitions"]})

    def test_series_rejects_duplicates_and_policy_changes(self):
        first = self.make_run("first", ["1,ok,10.00", "2,ok,20.00"])
        with self.assertRaisesRegex(ParisonError, "distinct"):
            analyze_series([first, first])
        changed = copy.deepcopy(RECIPE)
        changed["nulls_equal"] = False
        second = self.make_run("second", ["1,ok,10.00", "2,ok,20.00"], changed)
        with self.assertRaisesRegex(ParisonError, "exact policy"):
            analyze_series([first, second])

    def test_analysis_publication_is_canonical_verified_and_no_overwrite(self):
        bundle = self.make_run("first", ["1,bad,10.00", "2,ok,20.00"])
        output = self.root / "analysis"
        metadata = publish_analysis(output, analyze_bundle(bundle))
        self.assertRegex(metadata["manifest_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual(verify_analysis_bundle(output)["analysis_kind"], "run")
        with self.assertRaisesRegex(ParisonError, "already exists"):
            publish_analysis(output, analyze_bundle(bundle))
        (output / "analysis.json").write_bytes((output / "analysis.json").read_bytes() + b" ")
        with self.assertRaisesRegex(ParisonError, "integrity"):
            verify_analysis_bundle(output)

    def test_analysis_verification_rejects_unexpected_members(self):
        bundle = self.make_run("first", ["1,ok,10.00", "2,ok,20.00"])
        output = self.root / "analysis"
        publish_analysis(output, analyze_bundle(bundle))
        (output / "unexpected").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "unexpected members"):
            verify_analysis_bundle(output)

    def test_cli_publishes_series_analysis(self):
        first = self.make_run("first", ["1,bad,10.00", "2,ok,20.00"])
        second = self.make_run("second", ["1,ok,10.00", "2,ok,20.01"])
        output = self.root / "analysis"
        self.assertEqual(main(["analyze", str(first), str(second), "--output", str(output)]), 0)
        self.assertEqual(main(["verify-analysis", str(output)]), 0)

    def test_all_released_comparison_modes_are_supported(self):
        fixtures = Path(__file__).parent / "fixtures" / "compatibility"
        aggregate = analyze_bundle(fixtures / "aggregate-0.7.0")
        multiset = analyze_bundle(fixtures / "multiset-0.8.0")
        self.assertEqual(aggregate["comparison_mode"], "aggregate")
        self.assertEqual({group["descriptor"]["kind"] for group in aggregate["groups"]}, {"missing", "measure"})
        self.assertEqual(multiset["comparison_mode"], "multiset")
        self.assertEqual(
            {group["descriptor"]["classification"] for group in multiset["groups"]},
            {"baseline_surplus", "candidate_surplus"},
        )

    def test_drilldown_reads_only_bounded_published_raw_samples(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["output"]["sensitivity"] = "raw"
        bundle = self.make_run("raw", ["1,bad,10.00", "2,ok,20.00"], recipe)
        analysis = analyze_bundle(bundle)
        group_id = next(
            group["group_id"]
            for group in analysis["groups"]
            if group["descriptor"].get("name") == "status" and group["descriptor"]["classification"] == "different"
        )
        result = drill_down([bundle], group_id, 1, 1)
        self.assertEqual(result["returned_size"], 1)
        self.assertEqual(result["runs"][0]["population_count"], 1)
        self.assertEqual(result["items"][0]["item"]["candidate"], "bad")
        output = self.root / "drilldown.json"
        export_drilldown(output, result)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)
        with self.assertRaisesRegex(ParisonError, "already exists"):
            export_drilldown(output, result)

    def test_drilldown_rejects_summary_bundles(self):
        bundle = self.make_run("summary", ["1,bad,10.00", "2,ok,20.00"])
        group_id = next(
            group["group_id"]
            for group in analyze_bundle(bundle)["groups"]
            if group["descriptor"].get("name") == "status" and group["descriptor"]["classification"] == "different"
        )
        with self.assertRaisesRegex(ParisonError, "raw-sensitivity"):
            drill_down([bundle], group_id, 1, 1)

    def test_three_run_rehearsal_tracks_resolution_and_regression(self):
        example = Path(__file__).parents[1] / "examples" / "1.5"
        recipe = json.loads((example / "orders.recipe.json").read_text(encoding="utf-8"))
        bundles = []
        for index in range(1, 4):
            result = compare(example / "orders.recipe.json", example / "baseline.csv", example / f"rehearsal-{index}.csv")
            bundle = self.root / f"rehearsal-{index}"
            publish(bundle, result, recipe)
            bundles.append(bundle)
        series = analyze_series(bundles)
        counts = {
            (group["descriptor"].get("name"), group["descriptor"]["classification"]): group["counts"]
            for group in series["groups"]
        }
        self.assertEqual(counts[(None, "baseline_only")], [1, 0, 0])
        self.assertEqual(counts[(None, "candidate_only")], [1, 0, 0])
        self.assertEqual(counts[("status", "different")], [1, 2, 0])
        self.assertEqual(counts[("total", "different")], [0, 1, 0])
        self.assertEqual(counts[("total", "within_tolerance")], [1, 0, 1])


if __name__ == "__main__":
    unittest.main()
