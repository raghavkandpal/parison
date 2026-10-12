import csv
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from parison.cli import main
from parison.core import verify_bundle


WORKFLOW = Path(__file__).parents[1] / "examples" / "github-actions" / "parison.yml"
SUITE_WORKFLOW = Path(__file__).parents[1] / "examples" / "github-actions" / "parison-suite-v2.yml"
SIGNING_WORKFLOW = Path(__file__).parents[1] / "examples" / "github-actions" / "parison-evidence-signing.yml"


class GitHubActionsReference(unittest.TestCase):
    def test_suite_reference_shards_then_verifies_assembly(self):
        workflow = SUITE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("local-concurrent:", workflow)
        self.assertIn("--jobs 2", workflow)
        self.assertIn("matrix:\n        shard: [0, 1]", workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertLess(workflow.index("run-suite"), workflow.index("upload-artifact@v6"))
        self.assertLess(workflow.index("download-artifact@v7"), workflow.index("assemble-suite"))
        self.assertLess(workflow.index("assemble-suite"), workflow.index("report-ci"))
        self.assertIn('>> "$GITHUB_STEP_SUMMARY"', workflow)
        self.assertNotIn("pull_request_target:", workflow)

    def test_upload_precedes_restored_exit_code(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        capture = workflow.index('echo "exit-code=$code" >> "$GITHUB_OUTPUT"')
        verify = workflow.index('parison verify "$PARISON_RUN"')
        upload = workflow.index("uses: actions/upload-artifact@v6")
        restore = workflow.index('run: exit "${{ steps.compare.outputs.exit-code }}"')
        self.assertLess(capture, verify)
        self.assertLess(verify, upload)
        self.assertLess(capture, upload)
        self.assertLess(upload, restore)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("if: always()", workflow)

    def test_reference_rejects_raw_artifacts_and_uses_unique_output(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("['output']['sensitivity'] == 'summary'", workflow)
        self.assertIn("github.run_id", workflow)
        self.assertIn("github.run_attempt", workflow)
        self.assertIn("releases/download/0.15.0/parison-0.15.0-py3-none-any.whl", workflow)
        self.assertNotIn("pull_request_target:", workflow)

    def test_installed_wheel_ci_runs_initialized_project_quickstart(self):
        workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        for command in ("parison init", "parison validate-recipe", "parison validate-inputs", "parison compare", "parison verify"):
            self.assertGreaterEqual(workflow.count(command), 2)
        self.assertIn("platform-smoke:", workflow)
        platform = workflow[workflow.index("platform-smoke:"):]
        self.assertIn("python -m build", platform)
        self.assertIn("dist/parison-*.whl", platform)
        self.assertNotIn("pip install '.[parquet,test]'", platform)

    def test_signing_reference_pins_tools_and_checks_exact_identity(self):
        workflow = SIGNING_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("id-token: write", workflow)
        self.assertIn("sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6", workflow)
        self.assertIn("cosign-release: v3.1.3", workflow)
        self.assertIn('identity="https://github.com/${GITHUB_WORKFLOW_REF}"', workflow)
        self.assertIn('--certificate-identity "$identity"', workflow)
        self.assertIn("--certificate-oidc-issuer https://token.actions.githubusercontent.com", workflow)
        self.assertLess(workflow.index("parison statement"), workflow.index("cosign sign-blob"))
        self.assertLess(workflow.index("cosign verify-blob"), workflow.index("parison verify-statement"))
        self.assertLess(workflow.index("parison verify-statement"), workflow.index("actions/upload-artifact"))

    def test_every_ci_outcome_publishes_a_verifiable_bundle(self):
        recipe = {
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["id"],
            "scope": {"snapshot": "ci-contract", "cutoff": "2026-10-06T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "nulls_equal": True,
            "columns": {"id": {"type": "string", "comparison": "exact"}, "value": {"type": "string", "comparison": "exact"}},
            "output": {"sensitivity": "summary"},
        }
        cases = {
            "PASS": (0, [("1", "same")], [("1", "same")]),
            "FAIL": (1, [("1", "old")], [("1", "new")]),
            "INCONCLUSIVE": (3, [("1", "same"), ("1", "same")], [("1", "same")]),
            "ERROR": (2, [("1", "same", "extra")], [("1", "same")]),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe_path = root / "recipe.json"
            recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
            for outcome, (expected_code, baseline_rows, candidate_rows) in cases.items():
                with self.subTest(outcome=outcome):
                    paths = []
                    for name, rows in (("baseline", baseline_rows), ("candidate", candidate_rows)):
                        path = root / f"{outcome}-{name}.csv"
                        with path.open("w", newline="", encoding="utf-8") as handle:
                            writer = csv.writer(handle)
                            writer.writerow(["id", "value"])
                            writer.writerows(rows)
                        paths.append(path)
                    output = root / f"run-{outcome}"
                    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                        code = main(["compare", "--recipe", str(recipe_path), "--baseline", str(paths[0]), "--candidate", str(paths[1]), "--output", str(output)])
                    self.assertEqual(code, expected_code)
                    self.assertEqual(verify_bundle(output)["outcome"], outcome)


if __name__ == "__main__":
    unittest.main()
