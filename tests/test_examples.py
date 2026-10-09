import json
import unittest
from pathlib import Path

from parison.core import compare, load_schema, verify_bundle
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

    def test_committed_output_bundle_is_complete_and_verified(self):
        root = Path(__file__).parents[1]
        output = root / "examples/output"
        manifest = verify_bundle(output)
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["outcome"], "PASS")
        self.assertEqual(result["outcome"], "PASS")
        self.assertTrue(result["complete"])
        self.assertEqual(result["counts"]["matched_within_tolerance"], 1)


if __name__ == "__main__":
    unittest.main()
