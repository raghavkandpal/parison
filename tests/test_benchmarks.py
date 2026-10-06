import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.generate_cases import generate
from benchmarks.run_cases import measure
from parity.core import compare


class GeneratedBenchmarks(unittest.TestCase):
    def test_generated_accuracy_oracle_matches_engine(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generate(root, 1_000)
            case = root / "rows-1000"
            expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
            result = compare(case / "recipe.json", case / "baseline.csv", case / "candidate.csv")
            self.assertEqual(result["outcome"], expected["outcome"])
            self.assertEqual(result["counts"], expected["counts"])
            self.assertEqual(result["field_discrepancy_count"], expected["field_discrepancy_count"])

    def test_measurement_includes_python_and_process_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generate(root, 10)
            measurement = measure(root / "rows-10")
            self.assertGreater(measurement["peak_python_bytes"], 0)
            self.assertGreater(measurement["elapsed_seconds"], 0)
            if measurement["peak_rss_bytes"] is not None:
                self.assertGreater(measurement["peak_rss_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
