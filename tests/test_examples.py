import json
import unittest
from pathlib import Path

from parison.core import compare, verify_bundle


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
