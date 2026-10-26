"""Retained Workbench suites preserve verified output and ownership."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parison.core import ParisonError, verify_bundle
from parison.workbench import execute_suite_run
from parison.workbench_suite_recovery import require_owned_workspace

EXAMPLES = Path(__file__).parents[1] / "examples/0.15"


class WorkbenchSuiteRecovery(unittest.TestCase):
    def test_retention_resume_and_catalog_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (
                "payout-suite.json",
                "payout-aggregate.recipe.json",
                "payout-keyed.recipe.json",
                "processor.csv",
                "ledger.csv",
            ):
                shutil.copy2(EXAMPLES / name, root / name)
            plan = root / "payout-suite.json"
            retained = root / "retained"
            with patch("parison.workbench.catalog_add", side_effect=ParisonError("catalog unavailable")):
                result = execute_suite_run(root, plan, root / "first", [], [], None, None, retained_workspace=retained)
            self.assertEqual(result["catalog_status"], "failed")
            self.assertEqual(verify_bundle(root / "first")["kind"], "suite")
            require_owned_workspace(root, retained)
            with patch("parison.suites.compare", side_effect=AssertionError("expected reuse")):
                resumed = execute_suite_run(
                    root, plan, root / "second", [], [], None, None, retained_workspace=retained, resume=True
                )
            self.assertEqual(verify_bundle(root / "second")["kind"], "suite")
            self.assertIn(resumed["catalog_status"], {"added", "current"})
