import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.analysis import (
    analyze_bundle,
    analyze_catalog,
    analyze_series,
    drill_down,
    export_drilldown,
    publish_analysis,
    verify_analysis_bundle,
    verify_drilldown,
)
from parison.catalog import add as catalog_add
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

    def make_run(self, name, candidate_rows, recipe=None, *, sample_limit=100, engine="memory"):
        recipe = copy.deepcopy(recipe or RECIPE)
        recipe_path = self.root / f"{name}-recipe.json"
        recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
        baseline = self.root / f"{name}-baseline.csv"
        candidate = self.root / f"{name}-candidate.csv"
        baseline.write_text("order_id,status,total\n1,ok,10.00\n2,ok,20.00\n", encoding="utf-8")
        candidate.write_text("order_id,status,total\n" + "\n".join(candidate_rows) + "\n", encoding="utf-8")
        result = compare(recipe_path, baseline, candidate, sample_limit=sample_limit, engine=engine)
        output = self.root / name
        publish(output, result, recipe)
        return output

    def test_keyed_analysis_is_exhaustive_deterministic_and_summary_safe(self):
        bundle = self.make_run("first", ["1,bad,10.01", "3,ok,20.00"])
        first = analyze_bundle(bundle)
        second = analyze_bundle(bundle)
        self.assertEqual(first, second)
        Draft202012Validator(load_schema("discrepancy-analysis")).validate(first)
        counts = {
            (g["descriptor"].get("logical_name"), g["descriptor"]["classification"]): g["count"]
            for g in first["groups"]
        }
        self.assertEqual(counts[(None, "baseline_only")], 1)
        self.assertEqual(counts[(None, "candidate_only")], 1)
        self.assertEqual(counts[("status", "different")], 1)
        self.assertEqual(
            next(
                g["group_id"]
                for g in first["groups"]
                if g["descriptor"].get("logical_name") == "status" and g["descriptor"]["classification"] == "different"
            ),
            "cccab954d219b6e5aa12b1a5edc68f5503dc45b68967f0965bad28405fc70960",
        )
        self.assertEqual(counts[("total", "within_tolerance")], 1)
        encoded = json.dumps(first, sort_keys=True)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn('"bad"', encoded)
        self.assertEqual(sum(group["count"] for group in first["groups"]), 4)
        status = next(group for group in first["groups"] if group["descriptor"].get("logical_name") == "status")
        self.assertEqual(
            status["policy_references"],
            [
                {"path": "/policy/nulls_equal", "value": True},
                {"path": "/column_policies/status/type", "value": "string"},
                {"path": "/column_policies/status/comparison", "value": "exact"},
            ],
        )

    def test_series_preserves_order_and_classifies_exact_transitions(self):
        first = self.make_run("first", ["1,bad,10.00", "2,ok,20.00"])
        second = self.make_run("second", ["1,ok,10.00", "2,ok,20.01"])
        series = analyze_series([first, second])
        Draft202012Validator(load_schema("discrepancy-analysis")).validate(series)
        statuses = {
            (g["descriptor"].get("logical_name"), g["descriptor"]["classification"]): g["counts"]
            for g in series["groups"]
        }
        self.assertEqual(statuses[("status", "different")], [1, 0])
        self.assertEqual(statuses[("total", "within_tolerance")], [0, 1])
        self.assertIn("resolved", {transition["status"] for transition in series["transitions"]})
        self.assertIn("introduced", {transition["status"] for transition in series["transitions"]})
        reversed_series = analyze_series([second, first])
        self.assertEqual(reversed_series["runs"], list(reversed(series["runs"])))
        self.assertEqual(
            [group["counts"] for group in reversed_series["groups"]],
            [list(reversed(group["counts"])) for group in series["groups"]],
        )

    def test_series_rejects_duplicates_and_policy_changes(self):
        first = self.make_run("first", ["1,ok,10.00", "2,ok,20.00"])
        with self.assertRaisesRegex(ParisonError, "distinct"):
            analyze_series([first, first])
        changed = copy.deepcopy(RECIPE)
        changed["nulls_equal"] = False
        second = self.make_run("second", ["1,ok,10.00", "2,ok,20.00"], changed)
        with self.assertRaisesRegex(ParisonError, "exact policy"):
            analyze_series([first, second])

    def test_three_run_series_emits_all_exact_transition_labels(self):
        first = self.make_run("labels-first", ["1,bad,10.00", "2,ok,20.00"])
        second = self.make_run("labels-second", ["1,bad,10.01", "2,bad,20.00"])
        third = self.make_run("labels-third", ["1,bad,10.00", "2,ok,20.02"])
        statuses = {transition["status"] for transition in analyze_series([first, second, third])["transitions"]}
        self.assertEqual(statuses, {"introduced", "resolved", "increased", "decreased", "unchanged"})

    def test_catalog_analysis_requires_current_unique_bundle_identities(self):
        first = self.make_run("first", ["1,bad,10.00", "2,ok,20.00"])
        second = self.make_run("second", ["1,ok,10.00", "2,ok,20.01"])
        database = self.root / "catalog.sqlite"
        catalog_add(database, first)
        catalog_add(database, second)
        policy = analyze_bundle(first)["policy_sha256"]
        self.assertEqual(analyze_catalog(database, policy), analyze_series([first, second]))

        (first / "result.json").write_bytes((first / "result.json").read_bytes() + b" ")
        with self.assertRaisesRegex(ParisonError, "current bundle integrity"):
            analyze_catalog(database, policy)

    def test_catalog_analysis_rejects_missing_symlinked_and_aliased_runs(self):
        for failure in ("missing", "symlink", "alias"):
            with self.subTest(failure=failure):
                root = self.root / failure
                root.mkdir()
                first = self.make_run(f"{failure}-first", ["1,bad,10.00", "2,ok,20.00"])
                second = self.make_run(f"{failure}-second", ["1,ok,10.00", "2,ok,20.01"])
                database = root / "catalog.sqlite"
                catalog_add(database, first)
                catalog_add(database, second)
                policy = analyze_bundle(first)["policy_sha256"]
                if failure == "missing":
                    shutil.rmtree(first)
                    message = "current bundle integrity"
                elif failure == "symlink":
                    target = root / "moved"
                    first.rename(target)
                    os.symlink(target, first)
                    message = "current bundle integrity"
                else:
                    alias = root / "alias"
                    shutil.copytree(first, alias)
                    catalog_add(database, alias)
                    message = "aliased bundle identities"
                with self.assertRaisesRegex(ParisonError, message):
                    analyze_catalog(database, policy)

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

        invalid = analyze_bundle(bundle)
        invalid["groups"][0]["policy_references"][0]["value"] = {"raw": "secret"}
        with self.assertRaisesRegex(ParisonError, "invalid group evidence"):
            publish_analysis(self.root / "invalid-analysis", invalid)
        nonfinite = analyze_bundle(bundle)
        tolerance = next(
            reference
            for group in nonfinite["groups"]
            for reference in group["policy_references"]
            if reference["path"].endswith("/tolerance")
        )
        tolerance["value"]["absolute"] = float("nan")
        with self.assertRaisesRegex(ParisonError, "invalid group evidence"):
            publish_analysis(self.root / "nonfinite-analysis", nonfinite)
        tolerance["value"]["absolute"] = "secret raw value"
        with self.assertRaisesRegex(ParisonError, "invalid group evidence"):
            publish_analysis(self.root / "nonnumeric-analysis", nonfinite)

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
        self.assertEqual({group["descriptor"]["kind"] for group in aggregate["groups"]}, {"group", "measure"})
        self.assertEqual(multiset["comparison_mode"], "multiset")
        self.assertEqual(
            {group["descriptor"]["classification"] for group in multiset["groups"]},
            {"baseline_surplus", "candidate_surplus"},
        )

    def test_aggregate_and_multiset_nonzero_groups_are_exact(self):
        aggregate_recipe = Path(__file__).parents[1] / "examples" / "0.7" / "revenue.recipe.json"
        baseline = self.root / "aggregate-baseline.csv"
        candidate = self.root / "aggregate-candidate.csv"
        baseline.write_text("region,amount\neast,10.00\nwest,4.00\n", encoding="utf-8")
        candidate.write_text("region,amount\neast,11.00\nnorth,2.00\n", encoding="utf-8")
        recipe = json.loads(aggregate_recipe.read_text(encoding="utf-8"))
        aggregate_bundle = self.root / "aggregate-matrix"
        publish(aggregate_bundle, compare(aggregate_recipe, baseline, candidate), recipe)
        counts = {
            (
                group["descriptor"]["kind"],
                group["descriptor"]["classification"],
                group["descriptor"].get("logical_name"),
            ): group["count"]
            for group in analyze_bundle(aggregate_bundle)["groups"]
        }
        self.assertEqual(counts[("group", "baseline_only", None)], 1)
        self.assertEqual(counts[("group", "candidate_only", None)], 1)
        self.assertEqual(counts[("measure", "different", "revenue")], 1)

        multiset_recipe = Path(__file__).parents[1] / "examples" / "0.8" / "multiset.recipe.json"
        multiset_candidate = self.root / "multiset-candidate.jsonl"
        multiset_candidate.write_text(
            '{"area":"east","amount":"10.00"}\n{"area":"north","amount":"2.00"}\n', encoding="utf-8"
        )
        multiset = json.loads(multiset_recipe.read_text(encoding="utf-8"))
        multiset_bundle = self.root / "multiset-matrix"
        publish(
            multiset_bundle,
            compare(
                multiset_recipe, Path(__file__).parents[1] / "examples" / "0.8" / "baseline.csv", multiset_candidate
            ),
            multiset,
        )
        surplus = {
            group["descriptor"]["classification"]: group["count"] for group in analyze_bundle(multiset_bundle)["groups"]
        }
        self.assertEqual(surplus, {"baseline_surplus": 2, "candidate_surplus": 1})

    def test_keyed_null_boundary_is_counted_independently_of_samples(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["null_tokens"] = {"baseline": ["NULL"], "candidate": ["NULL"]}
        bundle = self.make_run("null-boundary", ["1,ok,NULL", "2,ok,20.00"], recipe, sample_limit=0)
        group = next(
            group
            for group in analyze_bundle(bundle)["groups"]
            if group["descriptor"].get("logical_name") == "total"
            and group["descriptor"]["classification"] == "different"
        )
        self.assertEqual(group["count"], 1)

    def test_string_normalization_materially_prevents_a_difference(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["columns"]["status"]["normalize"] = ["trim", "casefold"]
        bundle = self.make_run("normalized", ["1, OK ,10.00", "2,ok,20.00"], recipe)
        analysis = analyze_bundle(bundle)
        group = next(
            group
            for group in analysis["groups"]
            if group["descriptor"].get("logical_name") == "status"
            and group["descriptor"]["classification"] == "different"
        )
        self.assertEqual(group["count"], 0)
        self.assertIn(
            {"path": "/column_policies/status/normalize", "value": ["trim", "casefold"]},
            group["policy_references"],
        )

    def test_released_aggregate_analysis_is_byte_exact(self):
        fixtures = Path(__file__).parent / "fixtures"
        analysis = analyze_bundle(fixtures / "compatibility" / "aggregate-0.7.0")
        expected = (fixtures / "analysis" / "aggregate-run.json").read_bytes()
        self.assertEqual(
            (json.dumps(analysis, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            expected,
        )

    def test_drilldown_reads_only_bounded_published_raw_samples(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["output"]["sensitivity"] = "raw"
        bundle = self.make_run("raw", ["1,bad,10.00", "2,ok,20.00"], recipe)
        analysis = analyze_bundle(bundle)
        group_id = next(
            group["group_id"]
            for group in analysis["groups"]
            if group["descriptor"].get("logical_name") == "status"
            and group["descriptor"]["classification"] == "different"
        )
        result = drill_down([bundle], group_id, 1, 1)
        Draft202012Validator(load_schema("discrepancy-drilldown")).validate(result)
        self.assertEqual(result["returned_size"], 1)
        self.assertEqual(result["runs"][0]["population_count"], 1)
        self.assertEqual(result["items"][0]["item"]["candidate"], "bad")
        output = self.root / "drilldown.json"
        export_drilldown(output, result)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)
        self.assertEqual(verify_drilldown(output)["returned_size"], 1)
        failed_output = self.root / "failed-drilldown.json"
        with patch("parison.evidence.os.link", side_effect=OSError("injected publication failure")):
            with self.assertRaisesRegex(ParisonError, "cannot export discrepancy drill-down"):
                export_drilldown(failed_output, result)
        self.assertFalse(failed_output.exists())
        self.assertEqual(list(self.root.glob(".failed-drilldown.json-*")), [])
        with self.assertRaisesRegex(ParisonError, "already exists"):
            export_drilldown(output, result)
        attributed = copy.deepcopy(result)
        attributed["runs"].append(copy.deepcopy(attributed["runs"][0]))
        attributed["runs"][0]["returned_size"] = 0
        with self.assertRaisesRegex(ParisonError, "counts do not reconcile"):
            export_drilldown(self.root / "attributed.json", attributed)
        impossible = copy.deepcopy(result)
        impossible["items"][0]["sample_index"] = impossible["runs"][0]["published_sample_size"]
        with self.assertRaisesRegex(ParisonError, "invalid sample items"):
            export_drilldown(self.root / "impossible.json", impossible)
        with self.assertRaisesRegex(ParisonError, "positive limits"):
            drill_down([bundle], group_id, 0, 1)
        self.assertFalse((self.root / "partial.json").exists())

    def test_drilldown_strict_verification_and_unsampled_group_coverage(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["output"]["sensitivity"] = "raw"
        bundle = self.make_run("truncated", ["1,bad,10.00", "2,ok,20.02"], recipe, sample_limit=1)
        analysis = analyze_bundle(bundle)
        group_id = next(
            group["group_id"]
            for group in analysis["groups"]
            if group["descriptor"].get("logical_name") == "total"
            and group["descriptor"]["classification"] == "different"
        )
        drilldown = drill_down([bundle], group_id, 2, 2)
        self.assertEqual(drilldown["runs"][0]["population_count"], 1)
        self.assertEqual(drilldown["runs"][0]["matched_sample_size"], 0)
        self.assertFalse(drilldown["runs"][0]["sample_complete"])
        self.assertEqual(drilldown["returned_size"], 0)

        artifact = self.root / "strict.json"
        export_drilldown(artifact, drilldown)
        duplicate = artifact.read_text(encoding="utf-8").replace(
            '{"drilldown_version":1', '{"drilldown_version":1,"drilldown_version":1', 1
        )
        artifact.write_text(duplicate, encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "duplicate JSON member"):
            verify_drilldown(artifact)

        invalid = copy.deepcopy(drilldown)
        invalid["unknown"] = True
        with self.assertRaisesRegex(ParisonError, "incomplete or unsupported"):
            export_drilldown(self.root / "unknown.json", invalid)
        self.assertFalse((self.root / "unknown.json").exists())

    def test_series_and_drilldown_canonical_byte_fixtures(self):
        recipe = copy.deepcopy(RECIPE)
        recipe["output"]["sensitivity"] = "raw"
        first = self.make_run("fixture-a", ["1,bad,10.00", "2,ok,20.00"], recipe)
        second = self.make_run("fixture-b", ["1,ok,10.00", "2,ok,20.01"], recipe)
        series = analyze_series([first, second])
        group_id = next(
            group["group_id"]
            for group in analyze_bundle(first)["groups"]
            if group["descriptor"].get("logical_name") == "status"
            and group["descriptor"]["classification"] == "different"
        )
        drilldown = drill_down([first, second], group_id, 2, 1)
        fixture_root = Path(__file__).parent / "fixtures" / "analysis"
        for name, value in (("series.json", series), ("drilldown.json", drilldown)):
            value = copy.deepcopy(value)
            for index, run in enumerate(value["runs"], 1):
                run["bundle_sha256"] = f"{index:064x}"
            if name == "series.json":
                published = self.root / "normalized-series"
                publish_analysis(published, value)
                verify_analysis_bundle(published)
            else:
                published = self.root / "normalized-drilldown.json"
                export_drilldown(published, value)
                verify_drilldown(published)
            actual = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
            self.assertEqual(actual, (fixture_root / name).read_bytes())

    def test_memory_and_sqlite_produce_identical_analysis_groups(self):
        memory = self.make_run("memory", ["1,bad,10.01", "3,ok,20.00"])
        sqlite = self.make_run("sqlite", ["1,bad,10.01", "3,ok,20.00"], engine="sqlite")
        self.assertEqual(analyze_bundle(memory)["groups"], analyze_bundle(sqlite)["groups"])

    def test_policy_references_preserve_unicode_mapping_normalization_and_pointer_escaping(self):
        recipe = copy.deepcopy(RECIPE)
        policy = recipe["columns"].pop("status")
        policy["normalize"] = ["trim"]
        name = "a~/é"
        recipe["columns"][name] = policy
        recipe["column_mappings"] = {name: {"baseline": "status", "candidate": "status"}}
        bundle = self.make_run("unicode", ["1,bad,10.00", "2,ok,20.00"], recipe)
        group = next(
            group
            for group in analyze_bundle(bundle)["groups"]
            if group["descriptor"].get("logical_name") == name and group["descriptor"]["classification"] == "different"
        )
        self.assertEqual(group["descriptor"]["logical_name"], name)
        self.assertEqual(
            group["policy_references"],
            [
                {"path": "/policy/nulls_equal", "value": True},
                {"path": "/column_policies/a~0~1é/type", "value": "string"},
                {"path": "/column_policies/a~0~1é/normalize", "value": ["trim"]},
                {"path": "/column_policies/a~0~1é/comparison", "value": "exact"},
                {
                    "path": "/column_mappings/a~0~1é",
                    "value": {"baseline": "status", "candidate": "status"},
                },
            ],
        )

    def test_drilldown_rejects_summary_bundles(self):
        bundle = self.make_run("summary", ["1,bad,10.00", "2,ok,20.00"])
        group_id = next(
            group["group_id"]
            for group in analyze_bundle(bundle)["groups"]
            if group["descriptor"].get("logical_name") == "status"
            and group["descriptor"]["classification"] == "different"
        )
        with self.assertRaisesRegex(ParisonError, "raw-sensitivity"):
            drill_down([bundle], group_id, 1, 1)

    def test_three_run_rehearsal_tracks_resolution_and_regression(self):
        example = Path(__file__).parents[1] / "examples" / "1.5"
        recipe = json.loads((example / "orders.recipe.json").read_text(encoding="utf-8"))
        bundles = []
        for index in range(1, 4):
            result = compare(
                example / "orders.recipe.json", example / "baseline.csv", example / f"rehearsal-{index}.csv"
            )
            bundle = self.root / f"rehearsal-{index}"
            publish(bundle, result, recipe)
            bundles.append(bundle)
        series = analyze_series(bundles)
        counts = {
            (group["descriptor"].get("logical_name"), group["descriptor"]["classification"]): group["counts"]
            for group in series["groups"]
        }
        self.assertEqual(counts[(None, "baseline_only")], [1, 0, 0])
        self.assertEqual(counts[(None, "candidate_only")], [1, 0, 0])
        self.assertEqual(counts[("status", "different")], [1, 2, 0])
        self.assertEqual(counts[("total", "different")], [0, 1, 0])
        self.assertEqual(counts[("total", "within_tolerance")], [1, 0, 1])
        status_group = next(
            group
            for group in series["groups"]
            if group["descriptor"].get("logical_name") == "status"
            and group["descriptor"]["classification"] == "different"
        )
        raw = drill_down(bundles[:2], status_group["group_id"], 10, 5)
        self.assertEqual(raw["returned_size"], 3)
        per_run = analyze_bundle(bundles[0])
        self.assertIn({"path": "/scope/snapshot", "value": "rehearsal-orders-v1"}, per_run["scope_references"])
        self.assertIn(
            {"path": "/column_policies/status/normalize", "value": ["trim"]},
            next(
                group["policy_references"]
                for group in per_run["groups"]
                if group["descriptor"].get("logical_name") == "status"
            ),
        )


if __name__ == "__main__":
    unittest.main()
