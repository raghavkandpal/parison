import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.generate_aggregate_cases import PROFILES as AGGREGATE_PROFILES
from benchmarks.generate_aggregate_cases import generate as generate_aggregate
from benchmarks.generate_cases import generate
from benchmarks.generate_matrix import PROFILES
from benchmarks.generate_matrix import generate as generate_profile
from benchmarks.generate_spill_cases import generate as generate_spill
from benchmarks.run_cases import measure
from benchmarks.run_spill_cases import measure as measure_spill
from benchmarks.run_suite_cases import measure_suite_scale
from parison.core import compare


class GeneratedBenchmarks(unittest.TestCase):
    def test_suite_orchestration_measurement_verifies_all_paths(self):
        result = measure_suite_scale(Path(__file__).parents[1], 2, 2)
        self.assertEqual(result["accuracy"], "verified")
        self.assertEqual(result["cases"], 2)
        for name in ("clean_seconds", "jobs_2_seconds", "jobs_4_seconds", "sequential_shard_execution_seconds", "assembly_seconds", "resume_seconds"):
            self.assertGreater(result[name], 0)

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
            measurement = measure(root / "rows-10", sample_limit=10)
            self.assertGreater(measurement["peak_python_bytes"], 0)
            self.assertGreater(measurement["elapsed_seconds"], 0)
            self.assertGreater(measurement["result_json_bytes"], 0)
            if measurement["peak_rss_bytes"] is not None:
                self.assertGreater(measurement["peak_rss_bytes"], 0)

    def test_aggregate_profiles_match_oracles_and_measure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for profile in AGGREGATE_PROFILES:
                case = generate_aggregate(root, profile, 100)
                expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
                result = compare(case / "recipe.json", case / "baseline.csv", case / "candidate.csv")
                self.assertEqual(result["counts"], expected["counts"], profile)
                measurement = measure(case)
                self.assertGreater(measurement["elapsed_seconds"], 0)

    def test_spill_case_matches_memory_and_reports_temporary_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = generate_spill(Path(temporary), 100)
            memory = measure_spill(case, "memory")
            sqlite = measure_spill(case, "sqlite")
            self.assertEqual(memory["counts"], sqlite["counts"])
            self.assertEqual(memory["temporary_bytes"], 0)
            self.assertGreater(sqlite["temporary_bytes"], 0)
            self.assertGreater(sqlite["elapsed_seconds"], 0)

    def test_keyed_spill_case_matches_memory_and_reports_temporary_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = generate_spill(Path(temporary), 100, "keyed")
            memory = measure_spill(case, "memory")
            sqlite = measure_spill(case, "sqlite")
            self.assertEqual(memory["counts"], sqlite["counts"])
            self.assertEqual(memory["temporary_bytes"], 0)
            self.assertGreater(sqlite["temporary_bytes"], 0)

    def test_adversarial_profiles_match_their_oracles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for profile in PROFILES:
                case = generate_profile(root, profile, 100)
                expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
                result = compare(case / "recipe.json", case / "baseline.csv", case / "candidate.csv")
                self.assertEqual(result["counts"], expected["counts"], profile)
                self.assertEqual(result["field_discrepancy_count"], expected["field_discrepancy_count"], profile)

    def test_raw_adversarial_profile_respects_sample_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            case = generate_profile(Path(temporary), "high-mismatch", 100, sensitivity="raw")
            result = compare(case / "recipe.json", case / "baseline.csv", case / "candidate.csv", sample_limit=10)
            self.assertEqual(result["sensitivity"], "raw")
            self.assertEqual(result["discrepancy_sample_limit"], 10)


if __name__ == "__main__":
    unittest.main()
