import tempfile
import unittest
from pathlib import Path

from parison.core import evidence_statement, inspect_bundle, report_cutover, verify_bundle


ROOT = Path(__file__).resolve().parents[1]


def assert_summary_safe(test: unittest.TestCase, value) -> None:
    if isinstance(value, dict):
        test.assertTrue({"source_path", "key", "value", "discrepancy_sample"}.isdisjoint(value))
        for nested in value.values():
            assert_summary_safe(test, nested)
    elif isinstance(value, list):
        for nested in value:
            assert_summary_safe(test, nested)


class HistoricalArtifactCompatibility(unittest.TestCase):
    def test_0_1_run_remains_verifiable_and_derivable(self):
        bundle = ROOT / "examples" / "output"
        manifest = verify_bundle(bundle)
        self.assertEqual(manifest["runtime"]["parison_version"], "0.1.0")
        self.assertEqual(manifest["runtime"]["contract"], "keyed-v1")

        inspected = inspect_bundle(bundle)
        self.assertEqual(inspected["bundle_sha256"], "ea1812cd643b484a5f5509b4e47f79fff18ef00e90d332b021413a2daf9081ec")
        self.assertEqual(inspected["outcome"], "PASS")
        self.assertEqual(inspected["discrepancy_sample_size"], 0)

        statement = evidence_statement(bundle)
        self.assertEqual(statement["predicate"]["parisonVersion"], "0.1.0")
        self.assertEqual(statement["predicate"]["contract"], "keyed-v1")
        self.assertEqual(statement["subject"][0]["digest"]["sha256"], inspected["bundle_sha256"])

        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "cutover.md"
            metadata = report_cutover(bundle, report)
            self.assertEqual(metadata["bundle_sha256"], inspected["bundle_sha256"])
            self.assertIn("| Produced by Parison | 0.1.0 |", report.read_text(encoding="utf-8"))

    def test_released_artifact_families_remain_readable(self):
        fixtures = ROOT / "tests" / "fixtures" / "compatibility"
        expected = {
            "aggregate-0.7.0": ("0.7.0", "aggregate-v1", "run", 2, "0b7169ee51d3dc79a4a5d22601ad37249f051948575a409e7393e4556ee4db5b"),
            "multiset-0.8.0": ("0.8.0", "multiset-v1", "run", 3, "41013f7850d9205ccde82252c070a467540126f19609b1dc6c9457670eb04f8b"),
            "suite-v1-0.10.0": ("0.10.0", "suite-v1", "suite", 1, "d5cfabab463ed7c1684cc3eea9928d41252c0d017dc6d5253bd9f4bbe6418620"),
            "suite-v2-0.11.0": ("0.11.0", "suite-v2", "suite", 2, "3f05c7904cf434ca914ef0c31fde9a3e1dc43a5a8f7cf7457b506847025256ff"),
        }
        for name, (version, contract, kind, schema, digest) in expected.items():
            with self.subTest(name=name):
                bundle = fixtures / name
                manifest = verify_bundle(bundle)
                inspected = inspect_bundle(bundle)
                self.assertEqual(manifest["runtime"]["parison_version"], version)
                self.assertEqual(manifest["runtime"]["contract"], contract)
                self.assertEqual(inspected.get("kind", "run"), kind)
                self.assertEqual(inspected["schema_version"], schema)
                self.assertEqual(inspected["outcome"], "PASS")
                self.assertEqual(inspected["bundle_sha256"], digest)
                if kind == "run":
                    self.assertEqual(inspected["sensitivity"], "summary")
                assert_summary_safe(self, inspected)
                statement = evidence_statement(bundle)
                self.assertEqual(statement["subject"][0]["digest"]["sha256"], digest)
                if kind == "run":
                    self.assertEqual(statement["predicate"]["contract"], contract)
                else:
                    self.assertEqual(statement["predicate"]["suiteVersion"], schema)
                with tempfile.TemporaryDirectory() as directory:
                    report = Path(directory) / "cutover.md"
                    metadata = report_cutover(bundle, report)
                    self.assertEqual(metadata["bundle_sha256"], digest)
                    self.assertIn(f"| Produced by Parison | {version} |", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
