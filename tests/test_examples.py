import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import (
    ParisonError,
    assemble_suite,
    compare,
    export_evidence,
    inspect_bundle,
    load_schema,
    load_suite,
    publish,
    report_ci,
    run_suite,
    verify_bundle,
)
from parison.manifesting import create_dataset_manifest, publish_dataset_evidence_bundle, verify_dataset_manifest
from parison.reconciliation import publish_reconciliation_bundle, run_reconciliation, summarize_reconciliation_result


class CheckedInExamples(unittest.TestCase):
    def reconciliation_bundle(self, root, output):
        example = root / "examples/1.3"
        inputs = {
            "payments": {"recipe": example / "payments.recipe.json", "baseline": example / "payments-baseline.csv", "candidate": example / "payments-candidate.jsonl"},
            "payouts": {"recipe": example / "payouts.recipe.json", "baseline": example / "payouts-baseline.csv", "candidate": example / "payouts-candidate.jsonl"},
        }
        result = run_reconciliation(example / "alignment.json", example / "reconciliation.json", example / "extraction-receipt.json", inputs)
        publish_reconciliation_bundle(output, result, example / "alignment.json", example / "reconciliation.json")
        return output

    def test_1_4_manifest_binds_the_reconciliation_inputs(self):
        root = Path(__file__).parents[1]
        result = verify_dataset_manifest(root / "examples/1.4/payout-dataset-manifest.json", root, root / "examples/1.3/reconciliation.json", summary=True)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"], {"declared": 5, "matched": 5, "missing": 0, "undeclared": 0, "size_mismatch": 0, "digest_mismatch": 0})

    def test_1_4_manifest_rejects_a_different_policy(self):
        root = Path(__file__).parents[1]
        manifest = json.loads((root / "examples/1.4/payout-dataset-manifest.json").read_text(encoding="utf-8"))
        manifest["policy"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "does not match"):
                verify_dataset_manifest(path, root, root / "examples/1.3/reconciliation.json")

    def test_1_4_dataset_evidence_bundle_is_self_verifying_and_summary_safe(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence"
            semantic = self.reconciliation_bundle(root, Path(directory) / "semantic")
            published = publish_dataset_evidence_bundle(output, root / "examples/1.4/payout-dataset-manifest.json", root, root / "examples/1.3/reconciliation.json", semantic)
            self.assertEqual(published["outcome"], "PASS")
            self.assertEqual(verify_bundle(output), published)
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(["verify", str(output)]), 0)
                self.assertEqual(stdout.getvalue().strip(), "valid")
            inspected = inspect_bundle(output)
            self.assertEqual(inspected["kind"], "dataset-evidence")
            self.assertEqual(inspected["counts"]["matched"], 5)
            self.assertNotIn("examples/", json.dumps(inspected))
            unexpected = output / "unexpected.txt"
            unexpected.write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "unexpected file membership"):
                verify_bundle(output)
            unexpected.unlink()
            member = output / "manifest-result.json"
            saved = member.read_bytes()
            outside = Path(directory) / "outside.json"
            outside.write_bytes(saved)
            member.unlink()
            member.symlink_to(outside)
            with self.assertRaisesRegex(ParisonError, "unsafe"):
                verify_bundle(output)
            member.unlink()
            member.write_bytes(saved)
            with self.assertRaisesRegex(ParisonError, "already exists"):
                publish_dataset_evidence_bundle(output, root / "examples/1.4/payout-dataset-manifest.json", root, root / "examples/1.3/reconciliation.json", semantic)
            (output / "manifest-result.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "integrity"):
                verify_bundle(output)
            outer = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            outer["files"]["manifest-result.json"] = hashlib.sha256(b"{}").hexdigest()
            (output / "manifest.json").write_text(json.dumps(outer), encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "incomplete or unsupported"):
                verify_bundle(output)

    def test_1_4_dataset_evidence_publication_is_no_replace_and_cleans_staging(self):
        root = Path(__file__).parents[1]
        manifest = root / "examples/1.4/payout-dataset-manifest.json"
        policy = root / "examples/1.3/reconciliation.json"
        with tempfile.TemporaryDirectory() as directory:
            parent, output = Path(directory), Path(directory) / "race"
            semantic = self.reconciliation_bundle(root, parent / "semantic")
            from parison.reconciliation import _rename_no_replace

            def race(source, target):
                target.mkdir()
                _rename_no_replace(source, target)

            with patch("parison.reconciliation._rename_no_replace", side_effect=race):
                with self.assertRaisesRegex(ParisonError, "cannot publish"):
                    publish_dataset_evidence_bundle(output, manifest, root, policy, semantic)
            self.assertTrue(output.is_dir())
            self.assertEqual(list(output.iterdir()), [])
            self.assertEqual(list(parent.glob(".race-*")), [])

            interrupted = parent / "interrupted"
            with patch("parison.reconciliation._rename_no_replace", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    publish_dataset_evidence_bundle(interrupted, manifest, root, policy, semantic)
            self.assertFalse(interrupted.exists())
            self.assertEqual(list(parent.glob(".interrupted-*")), [])

    def test_1_4_dataset_evidence_binds_a_suite_v2_policy(self):
        root = Path(__file__).parents[1]
        suite_path = root / "examples/0.11/scalable-suite.json"
        suite = load_suite(suite_path)
        suite_sha256 = suite["suite_policy_sha256"]
        with tempfile.TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "dataset-manifest.json"
            resources = []
            for case in suite["cases"]:
                for role in ("baseline", "candidate"):
                    relative = Path(case[role]).relative_to(root).as_posix()
                    format_name = "jsonl" if relative.endswith(".jsonl") else "csv"
                    resources.append((case["id"], role, format_name, relative))
            create_dataset_manifest(root, "suite-input", "suite", suite_sha256, resources, manifest_path, suite_path)
            semantic = Path(directory) / "suite"
            run_suite(suite_path, semantic)
            output = Path(directory) / "evidence"
            publish_dataset_evidence_bundle(output, manifest_path, root, suite_path, semantic)
            self.assertEqual(verify_bundle(output)["policy"], {"kind": "suite", "sha256": suite_sha256})

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

    def test_1_1_semantic_scalar_example_is_a_cross_format_pass(self):
        root = Path(__file__).parents[1] / "examples" / "1.1"
        result = compare(root / "semantic-scalar.recipe.json", root / "baseline.csv", root / "candidate.jsonl")
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["policy"]["input_projection"], "semantic-scalar-v1")

    def test_1_3_reconciliation_example_is_cross_format_and_cross_engine(self):
        root = Path(__file__).parents[1] / "examples" / "1.3"
        inputs = {
            "payments": {"recipe": root / "payments.recipe.json", "baseline": root / "payments-baseline.csv", "candidate": root / "payments-candidate.jsonl"},
            "payouts": {"recipe": root / "payouts.recipe.json", "baseline": root / "payouts-baseline.csv", "candidate": root / "payouts-candidate.jsonl"},
        }
        arguments = (root / "alignment.json", root / "reconciliation.json", root / "extraction-receipt.json", inputs)
        memory = run_reconciliation(*arguments)
        sqlite = run_reconciliation(*arguments, engine="sqlite")
        self.assertEqual(memory["outcome"], "PASS")
        self.assertEqual(summarize_reconciliation_result(memory), summarize_reconciliation_result(sqlite))
        with __import__("tempfile").TemporaryDirectory() as directory:
            output = Path(directory) / "reconciliation"
            publish_reconciliation_bundle(output, sqlite, arguments[0], arguments[1])
            self.assertEqual(verify_bundle(output)["kind"], "reconciliation")

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
