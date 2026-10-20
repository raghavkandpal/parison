from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from parison.cli import main
from parison.core import ParisonError, compare, load_recipe, publish
from parison.workbench import publish_workbench, render_workbench


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

    def test_cli_can_open_the_generated_application(self):
        output = self.root / "application"
        with (
            patch("parison.cli.webbrowser.open", return_value=True) as opened,
            redirect_stdout(StringIO()) as stdout,
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(["workbench", str(self.bundle), "--output", str(output), "--open"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["verified"], True)
        opened.assert_called_once_with((output / "index.html").resolve().as_uri())


if __name__ == "__main__":
    unittest.main()
