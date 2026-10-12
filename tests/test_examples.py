import json
import unittest
from pathlib import Path

from parison.core import assemble_suite, compare, export_evidence, load_schema, publish, report_ci, run_suite, verify_bundle
from jsonschema import Draft202012Validator


class CheckedInExamples(unittest.TestCase):
    def test_orders_example_is_a_tolerated_pass(self):
        root = Path(__file__).parents[1]
        result = compare(
            root / "examples/orders.recipe.json",
            root / "examples/baseline.csv",
            root / "examples/candidate.csv",
        )
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 1)
        self.assertEqual(result["counts"]["matched_within_tolerance"], 1)

    def test_0_3_migration_example_combines_new_capabilities(self):
        root = Path(__file__).parents[1]
        result = compare(
            root / "examples/0.3/migration.recipe.json",
            root / "examples/0.3/baseline",
            root / "examples/0.3/candidate.jsonl",
        )
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 2)
        self.assertEqual(result["inputs"]["baseline"]["partitions"], 2)
        self.assertRegex(result["policy_sha256"], r"^[0-9a-f]{64}$")

    def test_0_5_example_combines_real_world_export_policies(self):
        root = Path(__file__).parents[1]
        result = compare(
            root / "examples/0.5/migration.recipe.json",
            root / "examples/0.5/baseline.tsv.gz",
            root / "examples/0.5/candidate.csv",
        )
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 2)
        self.assertEqual(result["inputs"]["baseline"]["compression"], "gzip")
        self.assertEqual(result["inputs"]["baseline"]["delimiter"], "\t")
        self.assertEqual(result["inputs"]["candidate"]["delimiter"], "|")
        self.assertEqual(result["policy"]["null_tokens"]["candidate"], ["\\N"])

    def test_0_7_aggregate_example_is_a_cross_format_pass(self):
        root = Path(__file__).parents[1]
        result = compare(
            root / "examples/0.7/revenue.recipe.json",
            root / "examples/0.7/baseline.csv",
            root / "examples/0.7/candidate.jsonl",
        )
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["common_groups"], 2)
        self.assertEqual(result["measure_counts"]["revenue"], {"exact": 1, "within_tolerance": 1, "different": 0})

    def test_0_8_multiset_example_is_a_cross_format_pass(self):
        root = Path(__file__).parents[1] / "examples" / "0.8"
        result = compare(root / "multiset.recipe.json", root / "baseline.csv", root / "candidate.jsonl")
        Draft202012Validator(load_schema("result-v3")).validate(result)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["common_occurrences"], 3)

    def test_0_8_raw_example_exports_bounded_evidence(self):
        root = Path(__file__).parents[1] / "examples" / "0.8"
        result = compare(root / "multiset-raw.recipe.json", root / "baseline.csv", root / "candidate.jsonl")
        self.assertEqual(result["sensitivity"], "raw")
        with __import__("tempfile").TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            publish(output, result, json.loads((root / "multiset-raw.recipe.json").read_text(encoding="utf-8")))
            evidence = Path(directory) / "evidence.jsonl"
            self.assertEqual(export_evidence(output, evidence, limit=10)["items"], 0)

    def test_committed_output_bundle_is_complete_and_verified(self):
        root = Path(__file__).parents[1]
        output = root / "examples/output"
        manifest = verify_bundle(output)
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["outcome"], "PASS")
        self.assertEqual(result["outcome"], "PASS")
        self.assertTrue(result["complete"])
        self.assertEqual(result["counts"]["matched_within_tolerance"], 1)

    def test_0_10_mixed_suite_runs_all_comparison_modes(self):
        root = Path(__file__).parents[1]
        with __import__("tempfile").TemporaryDirectory() as directory:
            output = Path(directory) / "suite"
            result = run_suite(root / "examples/0.10/mixed-suite.json", output)
            self.assertEqual(result["outcome"], "PASS")
            self.assertEqual([case["contract"] for case in result["cases"]], ["keyed-v1", "aggregate-v1", "multiset-v1"])
            self.assertEqual(verify_bundle(output)["kind"], "suite")

    def test_0_11_suite_shards_assemble_and_export_ci(self):
        root = Path(__file__).parents[1]
        plan = root / "examples/0.11/scalable-suite.json"
        with __import__("tempfile").TemporaryDirectory() as directory:
            temporary = Path(directory)
            shards = [temporary / "shard-0", temporary / "shard-1"]
            for index, output in enumerate(shards):
                result = run_suite(plan, output, shard_index=index, shard_count=2)
                self.assertEqual(result["kind"], "suite-shard")
            assembled = temporary / "assembled"
            result = assemble_suite(plan, list(reversed(shards)), assembled)
            self.assertEqual(result["outcome"], "PASS")
            self.assertTrue(result["scope_complete"])
            report_ci(assembled, temporary / "summary.md", "markdown")
            report_ci(assembled, temporary / "junit.xml", "junit")

    def test_0_14_backfill_suite_uses_aggregate_and_sqlite_multiset_layers(self):
        root = Path(__file__).parents[1]
        with __import__("tempfile").TemporaryDirectory() as directory:
            output = Path(directory) / "backfill"
            result = run_suite(root / "examples/0.14/backfill-suite.json", output)
            self.assertEqual(result["outcome"], "PASS")
            aggregate = json.loads((output / "cases/aggregate-conservation/result.json").read_text(encoding="utf-8"))
            multiset = json.loads((output / "cases/all-rows-exactly-once/result.json").read_text(encoding="utf-8"))
            self.assertEqual(aggregate["counts"]["common_groups"], 2)
            self.assertEqual(multiset["runtime"]["execution_engine"], "sqlite")
            self.assertEqual(multiset["counts"]["common_occurrences"], 3)
            verify_bundle(output)

    def test_0_15_payout_suite_passes_and_bad_ledger_fails_both_layers(self):
        root = Path(__file__).parents[1] / "examples" / "0.15"
        with __import__("tempfile").TemporaryDirectory() as directory:
            output = Path(directory) / "payout"
            result = run_suite(root / "payout-suite.json", output)
            self.assertEqual(result["outcome"], "PASS")
            self.assertEqual(result["outcome_counts"]["PASS"], 2)
            verify_bundle(output)
        aggregate = compare(root / "payout-aggregate.recipe.json", root / "processor.csv", root / "ledger-with-error.csv")
        keyed = compare(root / "payout-keyed.recipe.json", root / "processor.csv", root / "ledger-with-error.csv")
        self.assertEqual(aggregate["outcome"], "FAIL")
        self.assertEqual(keyed["outcome"], "FAIL")
        self.assertEqual(aggregate["measure_counts"]["net_amount"]["different"], 1)
        self.assertEqual(keyed["discrepancy_count"], 1)

    def test_0_15_feature_pipeline_suite_layers_tolerance_and_occurrence_parity(self):
        root = Path(__file__).parents[1] / "examples" / "0.15" / "features"
        with __import__("tempfile").TemporaryDirectory() as directory:
            output = Path(directory) / "features"
            result = run_suite(root / "feature-suite.json", output)
            self.assertEqual(result["outcome"], "PASS")
            keyed = json.loads((output / "cases/entity-feature-parity/result.json").read_text(encoding="utf-8"))
            multiset = json.loads((output / "cases/batch-occurrence-parity/result.json").read_text(encoding="utf-8"))
            self.assertEqual(keyed["counts"]["matched_within_tolerance"], 1)
            self.assertEqual(multiset["counts"]["common_occurrences"], 3)
            verify_bundle(output)


if __name__ == "__main__":
    unittest.main()
