"""Adversarial reference cases for exact integer-range discovery."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.comparison import compare
from parison.core import ParisonError, load_schema
from parison.partition_discovery import discover, validate_plan, verify


class PartitionDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.recipe = {
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["id"],
            "scope": {
                "snapshot": "local-test",
                "cutoff": "2026-10-28T00:00:00Z",
                "filters": [],
                "completeness": "full",
                "expected_empty": False,
            },
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "nulls_equal": True,
            "columns": {
                "id": {"type": "integer", "comparison": "exact"},
                "amount": {"type": "decimal", "scale": 2, "comparison": "exact"},
            },
            "output": {"sensitivity": "summary"},
        }
        self.plan = {
            "partition_plan_version": 1,
            "ranges": [{"upper": 100}, {"upper": 200}, {"upper": None}],
            "limits": {
                "max_input_bytes": 100000,
                "max_rows_per_input": 1000,
                "max_rows_per_partition_side": 100,
                "max_staged_bytes": 100000,
                "max_partition_bytes": 50000,
            },
        }
        self.recipe_path = self.root / "recipe.json"
        self.plan_path = self.root / "plan.json"
        self.recipe_path.write_text(json.dumps(self.recipe))
        self.plan_path.write_text(json.dumps(self.plan))
        self.left = self.root / "left.csv"
        self.right = self.root / "right.csv"
        self.output = self.root / "evidence"

    @staticmethod
    def _csv(path: Path, rows: list[tuple[object, object]]) -> None:
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "amount"])
            writer.writerows(rows)

    def _run(self, left: list[tuple[object, object]], right: list[tuple[object, object]]) -> dict:
        self._csv(self.left, left)
        self._csv(self.right, right)
        result = discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)
        reference = compare(self.recipe_path, self.left, self.right, engine="sqlite")
        self.assertEqual(result["outcome"], reference["outcome"])
        self.assertEqual(result["complete"], reference["complete"])
        self.assertEqual(result["counts"], reference["counts"])
        self.assertEqual(result["discrepancy_count"], reference["discrepancy_count"])
        private = json.loads((self.output / "receipt.json").read_text())
        self.assertEqual(private["field_counts"], reference["field_counts"])
        self.assertEqual(verify(self.output)["verification"], "integrity-only")
        self.assertEqual(
            verify(self.output, self.recipe_path, self.left, self.right)["verification"], "exact-source-backed"
        )
        return result

    def test_reference_corpus(self) -> None:
        base = [(key, "1.00") for key in range(1, 31)]
        cases = [
            (base, base),
            (base, [(key, "2.00" if key == 3 else "1.00") for key in range(1, 31)]),
            (base, [(key, "2.00" if key % 2 else "1.00") for key in range(1, 31)]),
            (
                [(key, "1.00") for key in range(1, 20)] + [(250, "1.00")],
                [(key, "2.00") for key in range(1, 20)] + [(250, "1.00")],
            ),
            (base, [(key, "1.00") for key in range(201, 231)]),
            (base, []),
            ([(1, "1.00"), (1, "2.00"), (250, "1.00")], base),
        ]
        for left, right in cases:
            with self.subTest(rows=(len(left), len(right)), first=right[:1]):
                self._run(left, right)
                shutil.rmtree(self.output)

    def test_plan_and_resource_rejection(self) -> None:
        schema = load_schema("partition-plan")
        Draft202012Validator.check_schema(schema)
        self.assertTrue(Draft202012Validator(schema).is_valid(self.plan))
        for ranges in (
            [{"upper": 100}, {"upper": 100}, {"upper": None}],
            [{"upper": 100}, {"upper": 200}],
            [{"upper": 100}, {"upper": True}, {"upper": None}],
        ):
            with self.subTest(ranges=ranges), self.assertRaises(ParisonError):
                validate_plan({**self.plan, "ranges": ranges})
        self.plan["limits"]["max_rows_per_partition_side"] = 1
        self.plan_path.write_text(json.dumps(self.plan))
        self._csv(self.left, [(1, "1.00"), (2, "1.00")])
        self._csv(self.right, [(1, "1.00")])
        with self.assertRaises(ParisonError):
            discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".evidence-*")))
        self.plan["limits"]["max_rows_per_partition_side"] = 100
        self.plan["limits"]["max_partition_bytes"] = 1
        self.plan_path.write_text(json.dumps(self.plan))
        with self.assertRaises(ParisonError):
            discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)
        self.assertFalse(self.output.exists())

    def test_null_tokens_quoted_fields_and_boundary_normalization(self) -> None:
        self.recipe["columns"]["amount"] = {"type": "string", "comparison": "exact"}
        self.recipe["null_tokens"] = {"baseline": ["NULL"], "candidate": ["missing"]}
        self.recipe_path.write_text(json.dumps(self.recipe))
        self._run([("099", "NULL"), (100, "quoted, value")], [(99, ""), (100, "quoted, value")])
        self.assertEqual(
            json.loads((self.output / "receipt.json").read_text())["counts"]["matched_with_required_difference"], 1
        )
        with self.assertRaises(ParisonError):
            discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)

    def test_projection_and_changed_recipe_rejection(self) -> None:
        self._run([(1, "1.00")], [(1, "1.00")])
        self.recipe["columns"]["amount"]["scale"] = 3
        self.recipe_path.write_text(json.dumps(self.recipe))
        with self.assertRaises(ParisonError):
            verify(self.output, self.recipe_path, self.left, self.right)
        shutil.rmtree(self.output)
        self.recipe["input_projection"] = "semantic-scalar-v1"
        self.recipe_path.write_text(json.dumps(self.recipe))
        with self.assertRaisesRegex(ParisonError, "simple summary"):
            discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)

    def test_input_substitution_and_null_key(self) -> None:
        self._run([(1, "1.00")], [(1, "1.00")])
        self._csv(self.right, [(1, "2.00")])
        with self.assertRaises(ParisonError):
            verify(self.output, self.recipe_path, self.left, self.right)
        self.output.rename(self.root / "old-evidence")
        self._csv(self.left, [("", "1.00")])
        with self.assertRaisesRegex(ParisonError, "null integer key"):
            discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)

    def test_forged_arithmetic_and_interruption(self) -> None:
        self._run([(1, "1.00")], [(1, "1.00")])
        receipt_path = self.output / "receipt.json"
        summary_path = self.output / "summary.json"
        manifest_path = self.output / "manifest.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["counts"]["common_keys"] += 1
        receipt_path.write_text(json.dumps(receipt))
        summary = json.loads(summary_path.read_text())
        summary["counts"]["common_keys"] += 1
        summary_path.write_text(json.dumps(summary))
        manifest = json.loads(manifest_path.read_text())
        for name in ("receipt.json", "summary.json"):
            manifest["files"][name] = hashlib.sha256((self.output / name).read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ParisonError, "arithmetic"):
            verify(self.output)
        self.output.rename(self.root / "old-evidence")
        with patch("parison.partition_discovery._compare_ranges", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".evidence-*")))

    def test_boolean_version_is_not_one(self) -> None:
        self._run([(1, "1.00")], [(1, "1.00")])
        path = self.output / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["partition_manifest_version"] = True
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ParisonError, "manifest"):
            verify(self.output)

    def test_staged_partition_tamper_fails(self) -> None:
        self._csv(self.left, [(1, "1.00")])
        self._csv(self.right, [(1, "1.00")])
        from parison import partition_discovery as module

        original = module._compare_ranges

        def tamper(*args):
            result = original(*args)
            workspace = args[-1]
            with (workspace / "baseline-0.csv").open("ab") as handle:
                handle.write(b"2,2.00\r\n")
            return result

        with patch("parison.partition_discovery._compare_ranges", side_effect=tamper):
            with self.assertRaisesRegex(ParisonError, "staging changed"):
                discover(self.plan_path, self.recipe_path, self.left, self.right, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
