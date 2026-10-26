"""Workbench policy review preserves shared assessments and deliberate disclosure."""

import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from parison.cli import main
from parison.core import ParisonError
from parison.evolution import diff_policies, diff_policy_texts, summarize_policy_diff
from parison.suites import compare_suites, run_suite
from parison.workbench import review_policy_change

EXAMPLES = Path(__file__).parents[1] / "examples/1.2"


class WorkbenchPolicyReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for file in EXAMPLES.iterdir():
            shutil.copy2(file, self.root / file.name)
        self.paths = tuple(
            self.root / name
            for name in ("baseline.recipe.json", "candidate.recipe.json", "orders.schema-evolution.json")
        )

    def test_assessment_parity_and_summary_disclosure(self):
        original = json.loads(self.paths[1].read_text())
        mutations = {
            "rename": lambda recipe: None,
            "key": lambda recipe: recipe.update(keys=["order-id", "gross-amount"]),
            "scope": lambda recipe: recipe["scope"].update(snapshot="private-snapshot"),
            "exclusion": lambda recipe: recipe.setdefault("excluded_columns", {}).update(
                {"private-field": "private-rationale"}
            ),
            "tolerance": lambda recipe: recipe["columns"]["gross-amount"].update(
                comparison="numeric", tolerance={"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = json.loads(json.dumps(original))
                mutate(candidate)
                self.paths[1].write_text(json.dumps(candidate), encoding="utf-8")
                reviewed = review_policy_change(*self.paths)
                self.assertEqual(reviewed["summary"], summarize_policy_diff(diff_policies(*self.paths)))
                with redirect_stdout(StringIO()) as output:
                    main(
                        [
                            "diff-policy",
                            "--baseline-recipe",
                            str(self.paths[0]),
                            "--candidate-recipe",
                            str(self.paths[1]),
                            "--evolution",
                            str(self.paths[2]),
                            "--summary",
                        ]
                    )
                self.assertEqual(json.loads(output.getvalue()), reviewed["summary"])
                self.assertNotIn("details", reviewed)
                for secret in (
                    str(self.root),
                    "order_id",
                    "gross_amount",
                    "order_total",
                    "private-field",
                    "private-rationale",
                    "private-snapshot",
                ):
                    self.assertNotIn(secret, json.dumps(reviewed))
                detailed = review_policy_change(*self.paths, expected_review=reviewed["review_id"])
                self.assertEqual(detailed["details"], diff_policies(*self.paths))
        declaration = json.loads(self.paths[2].read_text())
        declaration["changes"] = declaration["changes"][:1]
        self.paths[2].write_text(json.dumps(declaration), encoding="utf-8")
        self.assertEqual(review_policy_change(*self.paths)["summary"]["compatibility"], "DENY")

    def test_exact_bytes_and_mid_assessment_changes_invalidate_review(self):
        reviewed = review_policy_change(*self.paths)
        for path in self.paths:
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ParisonError, "changed"):
                review_policy_change(*self.paths, expected_review=reviewed["review_id"])
            path.write_bytes(original)

        def changing(*sources):
            result = diff_policy_texts(*sources)
            self.paths[2].write_bytes(self.paths[2].read_bytes() + b"\n")
            return result

        with patch("parison.workbench.diff_policy_texts", side_effect=changing):
            with self.assertRaisesRegex(ParisonError, "during assessment"):
                review_policy_change(*self.paths)

    def test_transient_edits_cannot_change_the_captured_assessment(self):
        reviewed = review_policy_change(*self.paths)
        original = self.paths[1].read_bytes()

        def transient(*sources):
            changed = json.loads(original)
            changed["scope"]["snapshot"] = "unreviewed-sensitive-scope"
            self.paths[1].write_text(json.dumps(changed), encoding="utf-8")
            try:
                return diff_policy_texts(*sources)
            finally:
                self.paths[1].write_bytes(original)

        with patch("parison.workbench.diff_policy_texts", side_effect=transient):
            details = review_policy_change(*self.paths, expected_review=reviewed["review_id"])
        self.assertEqual(details["summary"], reviewed["summary"])
        self.assertEqual(details["details"], diff_policies(*self.paths))
        self.assertNotIn("unreviewed-sensitive-scope", json.dumps(details))
        self.paths[2].write_bytes(b"\xff")
        with self.assertRaisesRegex(ParisonError, "UTF-8"):
            review_policy_change(*self.paths)

    def test_accept_does_not_bypass_suite_policy_gate(self):
        self.assertEqual(review_policy_change(*self.paths)["summary"]["compatibility"], "ACCEPT")
        for index, (recipe, header) in enumerate(
            zip(self.paths[:2], ("order_id,gross_amount", "order_id,order_total,migration_batch"), strict=True)
        ):
            source = self.root / f"input-{index}.csv"
            source.write_text(header + ("\na,1\n" if index == 0 else "\na,1,batch\n"), encoding="utf-8")
            plan = self.root / f"suite-{index}.json"
            plan.write_text(
                json.dumps(
                    {
                        "suite_version": 2,
                        "cases": [
                            {"id": "orders", "recipe": recipe.name, "baseline": source.name, "candidate": source.name}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            run_suite(plan, self.root / f"run-{index}")
        with self.assertRaises(ParisonError):
            compare_suites(self.root / "run-0", self.root / "run-1")
