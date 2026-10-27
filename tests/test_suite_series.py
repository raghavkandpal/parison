"""Suite-series producer, preserved-summary verifier and compatibility fixtures."""

import copy
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

from parison.analysis import _canonical, publish_analysis, verify_analysis_bundle
from parison.cli import main
from parison.core import ParisonError, load_schema
from parison.suite_series import analyze_suite_series, validate_suite_series
from parison.suites import run_suite

ROOT = Path(__file__).parents[1]


class SuiteSeriesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in (
            "payout-suite.json",
            "payout-keyed.recipe.json",
            "payout-aggregate.recipe.json",
            "processor.csv",
            "ledger.csv",
        ):
            shutil.copy2(ROOT / "examples/0.15" / name, self.root / name)
        self.plan = self.root / "payout-suite.json"

    def parents(self):
        original = (self.root / "ledger.csv").read_text()
        parents = []
        for index, content in enumerate(
            (original, original.replace("100.00", "101.00"), original + "\n", original.replace("100.00", "102.00"))
        ):
            (self.root / "ledger.csv").write_text(content, encoding="utf-8")
            output = self.root / f"run-{index}"
            run_suite(self.plan, output)
            parents.append(output)
        return parents

    def test_mixed_modes_order_identity_and_source_free_roundtrip(self):
        parents = self.parents()
        series = analyze_suite_series(parents)
        Draft202012Validator(load_schema("suite-series")).validate(series)
        self.assertEqual(len(series["runs"]), 4)
        self.assertEqual({case["comparison_mode"] for case in series["cases"]}, {"keyed", "aggregate"})
        for case in series["cases"]:
            self.assertTrue(all(change["candidate_changed"] for change in case["input_transitions"]))
        reversed_series = analyze_suite_series(reversed(parents))
        self.assertEqual(reversed_series["runs"], list(reversed(series["runs"])))
        for secret in (
            str(self.root),
            "ledger",
            "processor",
            "payout_id",
            "amount",
            "effective-recipe",
            "policy_references",
        ):
            self.assertNotIn(secret, json.dumps(series))
        output = self.root / "analysis"
        publish_analysis(output, series)
        with self.assertRaises(ParisonError):
            publish_analysis(output, series)
        for parent in parents:
            shutil.rmtree(parent)
        self.assertEqual(verify_analysis_bundle(output)["schema_version"], 2)
        with redirect_stdout(StringIO()) as stdout:
            self.assertEqual(main(["verify-analysis", str(output)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["analysis_kind"], "suite-series")

    def test_released_suite_v1_parents_remain_readable(self):
        for name in ("orders.recipe.json", "baseline.csv", "candidate.csv"):
            shutil.copy2(ROOT / "examples" / name, self.root / name)
        for version, names in (
            ("0.7", ("revenue.recipe.json", "baseline.csv", "candidate.jsonl")),
            ("0.8", ("multiset.recipe.json", "baseline.csv", "candidate.jsonl")),
        ):
            folder = self.root / version
            folder.mkdir()
            for name in names:
                shutil.copy2(ROOT / "examples" / version / name, folder / name)
        folder = self.root / "0.10"
        folder.mkdir()
        shutil.copy2(ROOT / "examples/0.10/mixed-suite.json", folder / "mixed-suite.json")
        plan = folder / "mixed-suite.json"
        left, right = self.root / "v1-left", self.root / "v1-right"
        run_suite(plan, left)
        source = self.root / "candidate.csv"
        source.write_bytes(source.read_bytes() + b"\n")
        run_suite(plan, right)
        result = analyze_suite_series([left, right])
        self.assertEqual(result["suite_version"], 1)
        self.assertEqual({case["comparison_mode"] for case in result["cases"]}, {"keyed", "aggregate", "multiset"})
        self.assertEqual(result["selection_sha256"], hashlib.sha256(b"null").hexdigest())

    def test_case_scoping_all_three_modes_and_incomplete_parent(self):
        recipe = json.loads((self.root / "payout-keyed.recipe.json").read_text())
        multiset = {
            "recipe_version": 3,
            "comparison_mode": "multiset",
            "scope": recipe["scope"],
            "columns": {
                name: {key: value for key, value in column.items() if key not in {"comparison", "tolerance"}}
                for name, column in recipe["columns"].items()
            },
            "output": {"sensitivity": "summary"},
        }
        (self.root / "multiset.json").write_text(json.dumps(multiset), encoding="utf-8")
        plan = json.loads(self.plan.read_text())
        duplicate = {**plan["cases"][1], "id": "second-keyed"}
        plan["cases"].extend(
            [
                duplicate,
                {"id": "multiset", "recipe": "multiset.json", "baseline": "processor.csv", "candidate": "ledger.csv"},
            ]
        )
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        parents = self.parents()
        series = analyze_suite_series(parents)
        self.assertEqual({case["comparison_mode"] for case in series["cases"]}, {"keyed", "aggregate", "multiset"})
        first, second = [case for case in series["cases"] if case["comparison_mode"] == "keyed"]
        self.assertEqual(
            {group["source_group_id"] for group in first["groups"]},
            {group["source_group_id"] for group in second["groups"]},
        )
        self.assertFalse(
            {group["group_id"] for group in first["groups"]} & {group["group_id"] for group in second["groups"]}
        )
        plan["cases"][0]["limits"] = {"max_rows": 1}
        self.plan.write_text(json.dumps(plan), encoding="utf-8")
        incomplete = self.root / "incomplete"
        run_suite(self.plan, incomplete)
        with self.assertRaises(ParisonError):
            analyze_suite_series([parents[0], incomplete])

    def test_cli_creation_matches_service(self):
        parents = self.parents()
        direct = analyze_suite_series(parents)
        output = self.root / "cli-series"
        with redirect_stdout(StringIO()) as stdout:
            self.assertEqual(main(["analyze-suites", *(str(parent) for parent in parents), "--output", str(output)]), 0)
        self.assertEqual(json.loads((output / "analysis.json").read_bytes()), direct)
        self.assertEqual(
            json.loads(stdout.getvalue())["manifest_sha256"],
            hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest(),
        )

    def test_frozen_bytes_and_recomputed_digest_attacks(self):
        payload = (ROOT / "tests/fixtures/suite-series-v1.canonical.json").read_bytes()
        fixture = json.loads(payload)
        validate_suite_series(fixture)
        Draft202012Validator(load_schema("suite-series")).validate(fixture)
        output = self.root / "fixture"
        publish_analysis(output, fixture)
        self.assertEqual((output / "analysis.json").read_bytes(), payload)
        mutations = (
            lambda value: value.update(suite_series_version=True),
            lambda value: value["runs"][0].update(outcome="FAIL"),
            lambda value: value["cases"][0]["groups"][0]["counts"].__setitem__(0, True),
            lambda value: value["cases"][0]["groups"][0]["transitions"][0].update(delta=99),
            lambda value: value["cases"][0]["input_transitions"][0].update(candidate_changed=False),
            lambda value: value["cases"][0]["groups"][0].update(kind="measure"),
            lambda value: value["cases"][0]["groups"][0].update(group_id="0" * 64),
            lambda value: value["cases"].append(copy.deepcopy(value["cases"][0])),
            lambda value: value["runs"].__setitem__(1, value["runs"][0]),
            lambda value: value["cases"][0].update(private_name="secret"),
        )
        for mutation in mutations:
            changed = copy.deepcopy(fixture)
            mutation(changed)
            forged = _canonical(changed) + b"\n"
            manifest = json.loads((output / "manifest.json").read_bytes())
            digest = hashlib.sha256(forged).hexdigest()
            manifest["analysis_sha256"] = digest
            manifest["files"]["analysis.json"] = digest
            (output / "analysis.json").write_bytes(forged)
            (output / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
            with self.assertRaises(ParisonError):
                verify_analysis_bundle(output)

    def test_rejects_duplicate_shard_incomplete_policy_selection_and_tampering(self):
        parents = self.parents()
        for selected in ([parents[0]], [parents[0], parents[0]], parents * 5):
            with self.assertRaises(ParisonError):
                analyze_suite_series(selected)
        shard = self.root / "shard"
        run_suite(self.plan, shard, shard_index=0, shard_count=2)
        with self.assertRaises(ParisonError):
            analyze_suite_series([parents[0], shard])
        plan = json.loads(self.plan.read_text())
        selected = self.root / "selected"
        run_suite(self.plan, selected, case_ids=[plan["cases"][0]["id"]])
        with self.assertRaises(ParisonError):
            analyze_suite_series([parents[0], selected])
        recipe = self.root / "payout-keyed.recipe.json"
        document = json.loads(recipe.read_text())
        document["scope"]["snapshot"] = "changed"
        recipe.write_text(json.dumps(document), encoding="utf-8")
        changed = self.root / "changed"
        run_suite(self.plan, changed)
        with self.assertRaises(ParisonError):
            analyze_suite_series([parents[0], changed])
        (parents[0] / "cases" / plan["cases"][0]["id"] / "result.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ParisonError):
            analyze_suite_series(parents)

    def test_publisher_cleans_interrupted_staging(self):
        fixture = json.loads((ROOT / "tests/fixtures/suite-series-v1.canonical.json").read_bytes())
        output = self.root / "interrupted"
        with patch("parison.analysis.rename_no_replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                publish_analysis(output, fixture)
        self.assertFalse(output.exists())
        self.assertFalse(list(self.root.glob(".interrupted-*")))
