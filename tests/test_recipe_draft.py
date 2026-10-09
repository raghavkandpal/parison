import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from parison.cli import main, parser
from parison.core import ParisonError, draft_recipe, load_recipe


class RecipeDraft(unittest.TestCase):
    def test_cli_writes_reviewable_recipe_with_suggestions(self):
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
            self.assertIn("inferred suggestions", stderr.getvalue())
            self.assertIn("validate-recipe", stderr.getvalue())
            draft = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(list(draft["columns"]), ["id", "amount"])
            self.assertEqual(draft["excluded_columns"], {
                "baseline_note": "present only in baseline",
                "candidate_note": "present only in candidate",
            })
            self.assertEqual(draft["keys"], ["id"])
            self.assertEqual(draft["columns"], {
                "id": {"type": "string", "comparison": "exact"},
                "amount": {"type": "integer", "comparison": "exact"},
            })
            self.assertEqual(draft["scope"]["completeness"], "full")
            self.assertFalse(draft["scope"]["expected_empty"])
            self.assertEqual(draft["output"], {"sensitivity": "summary"})
            self.assertNotIn("secret", output.read_text(encoding="utf-8"))
            self.assertNotIn("private", output.read_text(encoding="utf-8"))
            self.assertEqual(load_recipe(output), draft)

    def test_draft_help_lists_required_review_choices(self):
        stdout = StringIO()
        with self.assertRaises(SystemExit), redirect_stdout(stdout):
            parser().parse_args(["draft-recipe", "--help"])
        help_text = stdout.getvalue()
        for expected in ("suggested keys", "data types", "starting points", "symmetric-v1", "validate-recipe"):
            self.assertIn(expected, help_text)

    def test_draft_refuses_no_shared_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("left\n1\n", encoding="utf-8")
            candidate.write_text("right\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "no shared columns"):
                draft_recipe(baseline, candidate)

    def test_draft_suggestions_form_a_valid_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("id,value,left_only\n1,same,x\n", encoding="utf-8")
            candidate.write_text("id,value,right_only\n1,same,y\n", encoding="utf-8")
            draft_path = root / "draft.json"
            draft_path.write_text(json.dumps(draft_recipe(baseline, candidate)), encoding="utf-8")
            draft = json.loads(draft_path.read_text(encoding="utf-8"))
            self.assertEqual(load_recipe(draft_path), draft)

    def test_explicit_aggregate_draft_suggests_groups_and_measures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            contents = "region,amount,order_id\neast,10.50,1\neast,2.00,2\nwest,3.00,3\n"
            baseline.write_text(contents, encoding="utf-8")
            candidate.write_text(contents, encoding="utf-8")
            draft = draft_recipe(baseline, candidate, aggregate=True)
            self.assertEqual(draft["recipe_version"], 2)
            self.assertEqual(draft["comparison_mode"], "aggregate")
            self.assertEqual(draft["group_by"], ["region"])
            self.assertEqual(draft["measures"]["rows"], {"operator": "count"})
            self.assertEqual(draft["measures"]["sum_amount"], {"operator": "sum", "column": "amount", "nulls": "reject"})
            path = root / "aggregate.json"
            path.write_text(json.dumps(draft), encoding="utf-8")
            self.assertEqual(load_recipe(path), draft)

    def test_aggregate_draft_requires_explicit_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.csv", root / "draft.json"
            source.write_text("region,amount\neast,1\neast,2\nwest,3\n", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(["draft-recipe", "--aggregate", "--baseline", str(source), "--candidate", str(source), "--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["comparison_mode"], "aggregate")

    def test_explicit_multiset_draft_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.csv", root / "draft.json"
            source.write_text("region,amount\neast,1\neast,1\nwest,2\n", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(["draft-recipe", "--multiset", "--baseline", str(source), "--candidate", str(source), "--output", str(output)]), 0)
            draft = json.loads(output.read_text())
            self.assertEqual(draft["recipe_version"], 3)
            self.assertEqual(load_recipe(output), draft)

    def test_header_only_draft_is_deterministic_and_uses_safe_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("id,value\n", encoding="utf-8")
            candidate.write_text("value,id\n", encoding="utf-8")
            first = draft_recipe(baseline, candidate)
            second = draft_recipe(baseline, candidate)
            self.assertEqual(first, second)
            self.assertEqual(first["columns"], {
                "id": {"type": "string", "comparison": "exact"},
                "value": {"type": "string", "comparison": "exact"},
            })
            self.assertEqual(first["keys"], ["id"])
            self.assertTrue(first["scope"]["expected_empty"])

    def test_draft_infers_composite_identifier_keys_and_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            contents = "tenant_code,item_id,amount,active,day\na,1,10.50,true,2026-10-01\na,2,11.00,false,2026-10-02\nb,1,12.25,true,2026-10-03\nb,2,13.00,false,2026-10-04\n"
            baseline.write_text(contents, encoding="utf-8")
            candidate.write_text(contents, encoding="utf-8")
            draft = draft_recipe(baseline, candidate)
            self.assertEqual(draft["keys"], ["tenant_code", "item_id"])
            self.assertEqual(draft["columns"]["amount"], {"type": "decimal", "comparison": "exact", "scale": 2})
            self.assertEqual(draft["columns"]["active"]["type"], "boolean")
            self.assertEqual(draft["columns"]["day"]["type"], "date")

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
