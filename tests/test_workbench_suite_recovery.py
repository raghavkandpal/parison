"""Retained Workbench suites preserve verified output and ownership."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from parison.core import ParisonError, verify_bundle
from parison.suites import preview_suite_recovery
from parison.workbench import execute_suite_run
from parison.workbench_suite_recovery import recovery_selection, require_owned_workspace, workspace_owner

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

    def test_cancel_later_member_then_resume_and_invalidate_checkpoints(self):
        from parison.suites import _execute_suite_case

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
            plan, retained = root / "payout-suite.json", root / "retained"
            document = json.loads(plan.read_text())
            identifiers = [case["id"] for case in document["cases"]]
            calls = []

            def interrupt(case, *args):
                calls.append(case["id"])
                if len(calls) == 2:
                    raise ParisonError("workbench run cancelled")
                return _execute_suite_case(case, *args)

            with patch("parison.suites._execute_suite_case", side_effect=interrupt):
                with self.assertRaisesRegex(ParisonError, "suite cancelled"):
                    execute_suite_run(root, plan, root / "cancelled", [], [], None, None, retained_workspace=retained)
            self.assertFalse((root / "cancelled").exists())
            context = recovery_selection([], [], None, None)
            preview = preview_suite_recovery(plan, retained, checkpoint_context=context)
            self.assertEqual([case["reusable"] for case in preview["cases"]], [True, False])
            calls.clear()

            def counted(case, *args):
                calls.append(case["id"])
                return _execute_suite_case(case, *args)

            with patch("parison.suites._execute_suite_case", side_effect=counted):
                execute_suite_run(
                    root, plan, root / "resumed", [], [], None, None, retained_workspace=retained, resume=True
                )
            self.assertEqual(calls, identifiers[1:])
            changed_selection = recovery_selection([identifiers[0]], [], None, None)
            self.assertFalse(
                preview_suite_recovery(plan, retained, case_ids=[identifiers[0]], checkpoint_context=changed_selection)[
                    "cases"
                ][0]["reusable"]
            )
            calls.clear()
            with patch("parison.suites._execute_suite_case", side_effect=counted):
                execute_suite_run(
                    root,
                    plan,
                    root / "selection",
                    [identifiers[0]],
                    [],
                    None,
                    None,
                    retained_workspace=retained,
                    resume=True,
                )
            self.assertEqual(calls, identifiers[:1])
            checkpoint = retained / "checkpoints" / (identifiers[1] + ".json")
            checkpoint.write_text("{}", encoding="utf-8")
            self.assertFalse(preview_suite_recovery(plan, retained, checkpoint_context=context)["cases"][1]["reusable"])
            recipe = root / document["cases"][1]["recipe"]
            recipe_document = json.loads(recipe.read_text())
            recipe_document["output"]["sensitivity"] = "raw"
            recipe.write_text(json.dumps(recipe_document), encoding="utf-8")
            self.assertFalse(
                any(
                    case["reusable"]
                    for case in preview_suite_recovery(plan, retained, checkpoint_context=context)["cases"]
                )
            )
            calls.clear()
            with patch("parison.suites._execute_suite_case", side_effect=counted):
                execute_suite_run(root, plan, root / "restart", [], [], None, None, retained_workspace=root / "fresh")
            self.assertEqual(calls, identifiers)

    def test_owner_rejects_parent_symlink_and_normalized_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (root / "link").symlink_to(outside, target_is_directory=True)
            for path in (root / "link/state", root / "../outside/state", root):
                with self.assertRaises(ParisonError):
                    workspace_owner(root, path)
