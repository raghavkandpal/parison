"""Selective raw investigation keeps exact cases bound to discovery inputs."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.comparison import compare
from parison.core import ParisonError, load_schema
from parison.partition_discovery import discover
from parison.partition_discovery import main as partition_main
from parison.partition_investigation import _population, investigate, validate_plan, verify_investigation

FIXTURE = Path(__file__).parent / "fixtures" / "partition_discovery"
INVESTIGATION_FIXTURE = Path(__file__).parent / "fixtures" / "partition_investigation"


class PartitionInvestigationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.baseline = self.root / "baseline.csv"
        self.candidate = self.root / "candidate.csv"
        self.baseline.write_bytes((FIXTURE / "baseline.csv").read_bytes())
        self.candidate.write_text("id,amount\n1,3.00\n2,4.00\n")
        self.recipe = FIXTURE / "recipe.json"
        self.discovery = self.root / "discovery"
        discover(FIXTURE / "plan.json", self.recipe, self.baseline, self.candidate, self.discovery)
        digest = hashlib.sha256((self.discovery / "manifest.json").read_bytes()).hexdigest()
        self.plan = {
            "investigation_plan_version": 1,
            "discovery_manifest_sha256": digest,
            "partition_indices": [0, 1],
            "limits": {
                "max_cases_total": 10,
                "max_cases_per_partition": 10,
                "max_staged_bytes": 1000,
                "max_output_bytes": 10000,
            },
        }
        self.plan_path = self.root / "plan.json"
        self.output = self.root / "investigation"

    def _run(self) -> dict:
        self.plan_path.write_text(json.dumps(self.plan))
        return investigate(self.plan_path, self.discovery, self.recipe, self.baseline, self.candidate, self.output)

    def test_complete_cases_match_full_raw_reference(self) -> None:
        summary = self._run()
        self.assertTrue(summary["complete"])
        self.assertEqual((summary["suspect_count"], summary["selected_count"]), (2, 2))
        self.assertEqual((summary["population_count"], summary["returned_count"]), (2, 2))
        items = json.loads((self.output / "cases.json").read_text())["items"]
        raw_recipe = json.loads(self.recipe.read_text())
        raw_recipe["output"] = {"sensitivity": "raw"}
        raw_path = self.root / "raw-recipe.json"
        raw_path.write_text(json.dumps(raw_recipe))
        full = compare(raw_path, self.baseline, self.candidate, sample_limit=100, engine="memory")
        self.assertEqual([item["item"] for item in items], full["discrepancy_sample"])
        safe = (self.output / "summary.json").read_text()
        self.assertNotIn("partition_index", safe)
        self.assertNotIn("3.00", safe)
        self.assertNotIn(str(self.baseline), safe)
        self.assertEqual(verify_investigation(self.output, self.discovery)["verification"], "integrity-only")
        self.assertEqual(
            verify_investigation(self.output, self.discovery, self.recipe, self.baseline, self.candidate)[
                "verification"
            ],
            "exact-source-backed",
        )

    def test_adversarial_range_shapes_match_full_raw_reference(self) -> None:
        scenarios = {
            "low": ([(1, 1)], [(1, 2)]),
            "high": ([(4, 1)], [(4, 2)]),
            "skew": ([(key, 1) for key in range(1, 21)], [(20, 1)]),
            "all-different": ([(key, 1) for key in range(1, 5)], [(key, 2) for key in range(1, 5)]),
        }
        routing = json.loads((FIXTURE / "plan.json").read_text())
        routing["limits"] = {name: 10000 if "bytes" in name else 40 for name in routing["limits"]}
        routing_path = self.root / "routing.json"
        routing_path.write_text(json.dumps(routing))
        raw_recipe = json.loads(self.recipe.read_text())
        raw_recipe["output"] = {"sensitivity": "raw"}
        raw_path = self.root / "raw.json"
        raw_path.write_text(json.dumps(raw_recipe))
        for name, (left, right) in scenarios.items():
            with self.subTest(name=name):
                left_path = self.root / f"{name}-left.csv"
                right_path = self.root / f"{name}-right.csv"
                for path, rows in ((left_path, left), (right_path, right)):
                    path.write_text("id,amount\n" + "".join(f"{key},{amount}.00\n" for key, amount in rows))
                discovery = self.root / f"{name}-discovery"
                discover(routing_path, self.recipe, left_path, right_path, discovery)
                receipt = json.loads((discovery / "receipt.json").read_text())
                indices = [index for index, record in enumerate(receipt["partitions"]) if _population(record)]
                plan = {
                    **self.plan,
                    "discovery_manifest_sha256": hashlib.sha256((discovery / "manifest.json").read_bytes()).hexdigest(),
                    "partition_indices": indices,
                }
                plan["limits"] = {
                    **self.plan["limits"],
                    "max_cases_total": 100,
                    "max_cases_per_partition": 100,
                    "max_staged_bytes": 10000,
                }
                plan_path = self.root / f"{name}-plan.json"
                plan_path.write_text(json.dumps(plan))
                output = self.root / f"{name}-investigation"
                investigate(plan_path, discovery, self.recipe, left_path, right_path, output)
                cases = json.loads((output / "cases.json").read_text())["items"]
                full = compare(raw_path, left_path, right_path, sample_limit=100, engine="memory")
                self.assertEqual([item["item"] for item in cases], full["discrepancy_sample"])

    def test_subset_and_truncation_never_complete(self) -> None:
        self.plan["partition_indices"] = [0]
        result = self._run()
        self.assertFalse(result["complete"])
        self.assertFalse(result["scope_complete"])
        self.assertTrue(result["enumeration_complete"])
        self.assertEqual((result["population_count"], result["returned_count"]), (1, 1))
        shutil.rmtree(self.output)
        self.plan["partition_indices"] = [0, 1]
        self.plan["limits"]["max_cases_total"] = 1
        result = self._run()
        self.assertFalse(result["complete"])
        self.assertTrue(result["scope_complete"])
        self.assertFalse(result["enumeration_complete"])
        self.assertEqual((result["population_count"], result["returned_count"]), (2, 1))

    def test_changed_input_policy_and_selection_fail(self) -> None:
        self._run()
        self.candidate.write_text("id,amount\n1,3.00\n2,5.00\n")
        with self.assertRaises(ParisonError):
            verify_investigation(self.output, self.discovery, self.recipe, self.baseline, self.candidate)
        altered = json.loads(self.recipe.read_text())
        altered["columns"]["amount"]["scale"] = 3
        changed_recipe = self.root / "changed-recipe.json"
        changed_recipe.write_text(json.dumps(altered))
        with self.assertRaises(ParisonError):
            verify_investigation(self.output, self.discovery, changed_recipe, self.baseline, self.candidate)
        shutil.rmtree(self.output)
        self.plan["partition_indices"] = [2]
        with self.assertRaises(ParisonError):
            self._run()

    def test_forged_population_and_raw_case_rejected(self) -> None:
        self._run()
        receipt_path = self.output / "receipt.json"
        manifest_path = self.output / "manifest.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["selected"][0]["population_count"] = 0
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["receipt.json"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        with self.assertRaises(ParisonError):
            verify_investigation(self.output, self.discovery)
        shutil.rmtree(self.output)
        self._run()
        cases_path = self.output / "cases.json"
        cases = json.loads(cases_path.read_text())
        cases["items"][0]["item"]["candidate"] = "999.00"
        cases_path.write_text(json.dumps(cases, sort_keys=True, separators=(",", ":")) + "\n")
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["cases.json"] = hashlib.sha256(cases_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        with self.assertRaises(ParisonError):
            verify_investigation(self.output, self.discovery, self.recipe, self.baseline, self.candidate)

    def test_limits_collision_and_interruption_cleanup(self) -> None:
        with self.assertRaises(ParisonError):
            validate_plan({**self.plan, "partition_indices": [1, 1]})
        self.plan["limits"]["max_staged_bytes"] = 1
        with self.assertRaises(ParisonError):
            self._run()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".investigation-*")))
        self.plan["limits"]["max_staged_bytes"] = 1000
        with patch("parison.partition_investigation._route", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self._run()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".investigation-*")))
        self._run()
        with self.assertRaises(ParisonError):
            self._run()

    def test_malformed_case_and_unsafe_output_rejected(self) -> None:
        self.plan["limits"]["max_output_bytes"] = 1
        with self.assertRaises(ParisonError):
            self._run()
        self.assertFalse(self.output.exists())
        self.plan["limits"]["max_output_bytes"] = 10000
        self.output.symlink_to(self.root / "other", target_is_directory=True)
        with self.assertRaises(ParisonError):
            self._run()
        self.output.unlink()
        self._run()
        cases_path = self.output / "cases.json"
        cases = json.loads(cases_path.read_text())
        cases["items"][0]["item"]["classification"] = ["different"]
        cases_path.write_text(json.dumps(cases, sort_keys=True, separators=(",", ":")) + "\n")
        manifest_path = self.output / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["cases.json"] = hashlib.sha256(cases_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        with self.assertRaises(ParisonError):
            verify_investigation(self.output, self.discovery)

    def test_canonical_fixture_schemas_and_cli(self) -> None:
        discovery = self.root / "fixture-discovery"
        discover(
            FIXTURE / "plan.json",
            INVESTIGATION_FIXTURE / "recipe.json",
            FIXTURE / "baseline.csv",
            INVESTIGATION_FIXTURE / "candidate.csv",
            discovery,
        )
        output = self.root / "fixture-investigation"
        result = investigate(
            INVESTIGATION_FIXTURE / "plan.json",
            discovery,
            INVESTIGATION_FIXTURE / "recipe.json",
            FIXTURE / "baseline.csv",
            INVESTIGATION_FIXTURE / "candidate.csv",
            output,
        )
        self.assertTrue(result["complete"])
        for name in ("plan", "receipt", "cases", "summary", "manifest"):
            with self.subTest(name=name):
                self.assertEqual(
                    (output / f"{name}.json").read_bytes(),
                    (INVESTIGATION_FIXTURE / "expected" / f"{name}.json").read_bytes(),
                )
                schema = load_schema(f"investigation-{name}")
                Draft202012Validator.check_schema(schema)
                self.assertTrue(
                    Draft202012Validator(schema).is_valid(json.loads((output / f"{name}.json").read_text()))
                )
        captured = StringIO()
        with redirect_stdout(captured):
            self.assertEqual(
                partition_main(
                    [
                        "verify-investigation",
                        str(output),
                        "--discovery",
                        str(discovery),
                        "--recipe",
                        str(INVESTIGATION_FIXTURE / "recipe.json"),
                        "--baseline",
                        str(FIXTURE / "baseline.csv"),
                        "--candidate",
                        str(INVESTIGATION_FIXTURE / "candidate.csv"),
                    ]
                ),
                0,
            )
        self.assertEqual(json.loads(captured.getvalue())["verification"], "exact-source-backed")


if __name__ == "__main__":
    unittest.main()
