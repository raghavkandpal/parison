import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from parison.cli import main, parser
from parison.core import ParisonError, draft_recipe, load_recipe


class RecipeDraft(unittest.TestCase):
    def test_cli_writes_deterministic_unresolved_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline.csv"
            candidate = root / "candidate.csv"
            baseline.write_text("id,amount,baseline_note\nsecret,10,private\n", encoding="utf-8")
            candidate.write_text("amount,id,candidate_note\n11,secret,private\n", encoding="utf-8")
            output = root / "draft.json"
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["draft-recipe", "--baseline", str(baseline), "--candidate", str(candidate), "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), {"output": str(output)})
            self.assertIn("unresolved", stderr.getvalue())
            self.assertIn("validate-recipe", stderr.getvalue())
            draft = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(list(draft["columns"]), ["id", "amount"])
            self.assertEqual(draft["excluded_columns"], {"baseline_note": "", "candidate_note": ""})
            self.assertEqual(draft["keys"], [])
            self.assertEqual(draft["output"], {"sensitivity": "summary"})
            self.assertNotIn("secret", output.read_text(encoding="utf-8"))
            self.assertNotIn("private", output.read_text(encoding="utf-8"))
            with self.assertRaises(ParisonError):
                load_recipe(output)

    def test_draft_help_lists_required_review_choices(self):
        stdout = StringIO()
        with self.assertRaises(SystemExit), redirect_stdout(stdout):
            parser().parse_args(["draft-recipe", "--help"])
        help_text = stdout.getvalue()
        for expected in ("choose keys", "completeness='full'", "REVIEW_REQUIRED", "symmetric-v1", "validate-recipe"):
            self.assertIn(expected, help_text)

    def test_draft_refuses_no_shared_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("left\n1\n", encoding="utf-8")
            candidate.write_text("right\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "no shared columns"):
                draft_recipe(baseline, candidate)

    def test_draft_requires_policy_choices_before_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("id,value,left_only\n1,same,x\n", encoding="utf-8")
            candidate.write_text("id,value,right_only\n1,same,y\n", encoding="utf-8")
            draft_path = root / "draft.json"
            draft_path.write_text(json.dumps(draft_recipe(baseline, candidate)), encoding="utf-8")
            with self.assertRaises(ParisonError):
                load_recipe(draft_path)
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            draft["keys"] = ["id"]
            draft["scope"] = {"snapshot": "reviewed-export", "cutoff": "2026-10-06T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False}
            draft["nulls_equal"] = True
            draft["columns"] = {name: {"type": "string", "comparison": "exact"} for name in draft["columns"]}
            draft["excluded_columns"] = {"left_only": "source-specific metadata", "right_only": "source-specific metadata"}
            draft_path.write_text(json.dumps(draft), encoding="utf-8")
            self.assertEqual(load_recipe(draft_path), draft)

    def test_header_only_draft_is_deterministic_and_does_not_infer_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("id,value\n", encoding="utf-8")
            candidate.write_text("value,id\n", encoding="utf-8")
            first = draft_recipe(baseline, candidate)
            second = draft_recipe(baseline, candidate)
            self.assertEqual(first, second)
            self.assertEqual(first["columns"], {
                "id": {"type": "REVIEW_REQUIRED", "comparison": "exact"},
                "value": {"type": "REVIEW_REQUIRED", "comparison": "exact"},
            })

    def test_draft_rejects_duplicate_headers_symlinks_and_size_overruns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate, good = root / "duplicate.csv", root / "good.csv"
            duplicate.write_text("id,id\n1,2\n", encoding="utf-8")
            good.write_text("id\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "duplicate column"):
                draft_recipe(duplicate, good)
            with self.assertRaisesRegex(ParisonError, "exceeds limit"):
                draft_recipe(good, good, max_input_bytes=1)
            link = root / "link.csv"
            link.symlink_to(good)
            with self.assertRaisesRegex(ParisonError, "symlink"):
                draft_recipe(link, good)

    def test_cli_does_not_overwrite_an_existing_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.csv", root / "draft.json"
            source.write_text("id\n1\n", encoding="utf-8")
            output.write_text("keep me", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                code = main(["draft-recipe", "--baseline", str(source), "--candidate", str(source), "--output", str(output)])
            self.assertEqual(code, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep me")


if __name__ == "__main__":
    unittest.main()
