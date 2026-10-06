import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / "examples" / "github-actions" / "parison.yml"


class GitHubActionsReference(unittest.TestCase):
    def test_upload_precedes_restored_exit_code(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        capture = workflow.index('echo "exit-code=$code" >> "$GITHUB_OUTPUT"')
        upload = workflow.index("uses: actions/upload-artifact@v6")
        restore = workflow.index('run: exit "${{ steps.compare.outputs.exit-code }}"')
        self.assertLess(capture, upload)
        self.assertLess(upload, restore)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("if: always()", workflow)

    def test_reference_rejects_raw_artifacts_and_uses_unique_output(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("['output']['sensitivity'] == 'summary'", workflow)
        self.assertIn("github.run_id", workflow)
        self.assertIn("github.run_attempt", workflow)
        self.assertNotIn("pull_request_target:", workflow)


if __name__ == "__main__":
    unittest.main()
