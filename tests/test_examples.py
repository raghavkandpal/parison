import json
import unittest
from pathlib import Path

from parity.core import compare, verify_bundle


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
