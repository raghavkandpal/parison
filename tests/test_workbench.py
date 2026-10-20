from __future__ import annotations

import html
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parison.core import ParisonError, compare, load_recipe, publish
from parison.workbench import publish_plan_builder, publish_workbench, render_workbench


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        recipe = self.root / "recipe.json"
        baseline = self.root / "secret-baseline.csv"
        candidate = self.root / "secret-candidate.csv"
        recipe.write_text(
            json.dumps(
                {
                    "recipe_version": 1,
                    "comparison_mode": "keyed",
                    "keys": ["private_id"],
                    "scope": {
                        "snapshot": "fixture",
                        "cutoff": "2026-10-20T00:00:00Z",
                        "filters": [],
                        "completeness": "full",
                        "expected_empty": False,
                    },
                    "identity": {"null_keys": "reject", "duplicates": "reject"},
                    "nulls_equal": True,
                    "columns": {
                        "private_id": {"type": "string", "comparison": "exact"},
                        "secret_value": {"type": "string", "comparison": "exact"},
                    },
                    "output": {"sensitivity": "raw"},
                }
            ),
            encoding="utf-8",
        )
        baseline.write_text("private_id,secret_value\n1,do-not-render\n", encoding="utf-8")
        candidate.write_text("private_id,secret_value\n1,do-not-render\n", encoding="utf-8")
        result, effective = compare(recipe, baseline, candidate), load_recipe(recipe)
        self.bundle = self.root / "bundle"
        publish(self.bundle, result, effective)

    def test_publishes_deterministic_summary_safe_application(self):
        first = publish_workbench(self.bundle, self.root / "first").read_text(encoding="utf-8")
        second = publish_workbench(self.bundle, self.root / "second").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertIn("Parison Workbench", first)
        self.assertIn("PASS means agreement", first)
        for secret in ("secret-baseline.csv", "private_id", "secret_value", "do-not-render"):
            self.assertNotIn(secret, first)

    def test_refuses_tampering_and_existing_output(self):
        output = self.root / "application"
        publish_workbench(self.bundle, output)
        with self.assertRaisesRegex(ParisonError, "already exists"):
            publish_workbench(self.bundle, output)
        (self.bundle / "result.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "integrity"):
            publish_workbench(self.bundle, self.root / "tampered")

    def test_escapes_hostile_text_and_cleans_interrupted_staging(self):
        page = render_workbench({"outcome": '<script>alert("x")</script>'})
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        output = self.root / "interrupted"
        with patch("parison.workbench.rename_no_replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                publish_workbench(self.bundle, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob(".interrupted-*")), [])

    def test_plan_builder_uses_validated_cli_native_recipe(self):
        recipe = self.root / "recipe.json"
        recipe.write_text(
            json.dumps(
                {
                    "recipe_version": 1,
                    "comparison_mode": "keyed",
                    "keys": ["id"],
                    "scope": {
                        "snapshot": "<reviewed>",
                        "cutoff": "2026-10-20T00:00:00Z",
                        "filters": [],
                        "completeness": "full",
                        "expected_empty": False,
                    },
                    "identity": {"null_keys": "reject", "duplicates": "reject"},
                    "nulls_equal": True,
                    "columns": {"id": {"type": "string", "comparison": "exact"}},
                    "output": {"sensitivity": "summary"},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        page = publish_plan_builder(recipe, self.root / "builder").read_text(encoding="utf-8")
        self.assertIn("Verification plan builder", page)
        self.assertIn("Download unapproved draft", page)
        self.assertIn("parison validate-recipe plan.json", page)
        self.assertIn("endsWith('\\n')", page)
        self.assertIn("&lt;reviewed&gt;", page)
        self.assertNotIn(str(recipe), page)
        embedded = re.search(r'<textarea id="plan"[^>]*>(.*?)</textarea>', page, re.DOTALL)
        self.assertIsNotNone(embedded)
        self.assertEqual(html.unescape(embedded.group(1)), recipe.read_text(encoding="utf-8"))

        invalid = self.root / "invalid.json"
        invalid.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "recipe_version"):
            publish_plan_builder(invalid, self.root / "invalid-builder")
        self.assertFalse((self.root / "invalid-builder").exists())


if __name__ == "__main__":
    unittest.main()
