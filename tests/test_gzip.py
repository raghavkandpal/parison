import gzip
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from parison import core
from parison.cli import main
from parison.core import ParisonError, compare, draft_recipe, validate_inputs


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {"snapshot": "gzip", "cutoff": "2026-10-08T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "integer", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class GzipInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def compressed(self, name, text):
        path = self.root / name
        with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return path

    def test_mixed_gzip_csv_and_jsonl_compare_and_preflight(self):
        baseline_text = "id,value\n001,10\n002,20\n"
        candidate_text = '{"id":"002","value":20}\n{"id":"001","value":10}\n'
        baseline = self.compressed("baseline.csv.gz", baseline_text)
        candidate = self.compressed("candidate.jsonl.gz", candidate_text)

        preflight = validate_inputs(self.recipe, baseline, candidate)
        self.assertEqual(preflight["status"], "valid")
        self.assertEqual(preflight["inputs"]["baseline"]["format"], "csv")
        self.assertEqual(preflight["inputs"]["candidate"]["format"], "jsonl")
        self.assertEqual(preflight["inputs"]["baseline"]["compression"], "gzip")
        self.assertEqual(preflight["inputs"]["baseline"]["decoded_bytes"], len(baseline_text.encode()))

        result = compare(self.recipe, baseline, candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["inputs"]["candidate"]["compression"], "gzip")
        self.assertEqual(result["inputs"]["candidate"]["decoded_bytes"], len(candidate_text.encode()))

    def test_decoded_limit_rejects_preflight_draft_and_compare(self):
        left = self.compressed("left.csv.gz", "id,value\n001,10\n")
        right = self.compressed("right.csv.gz", "id,value\n001,10\n")
        for operation in (
            lambda: validate_inputs(self.recipe, left, right, max_decoded_bytes=1),
            lambda: draft_recipe(left, right, max_decoded_bytes=1),
            lambda: compare(self.recipe, left, right, max_decoded_bytes=1),
        ):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ParisonError, "decoded input size exceeds limit"):
                    operation()

        stderr = StringIO()
        with redirect_stderr(stderr):
            code = main([
                "validate-inputs", "--recipe", str(self.recipe), "--baseline", str(left),
                "--candidate", str(right), "--max-decoded-bytes", "1",
            ])
        self.assertEqual(code, 2)
        self.assertIn("decoded input size exceeds limit", stderr.getvalue())

        dense = self.compressed("dense.csv.gz", "id,value\n" + "0" * 100_000)
        self.assertLess(dense.stat().st_size, 1_000)
        with self.assertRaisesRegex(ParisonError, "decoded input size exceeds limit"):
            compare(self.recipe, dense, right, max_decoded_bytes=10_000)

    def test_gzip_partitions_and_recipe_drafting(self):
        baseline = self.root / "baseline"
        baseline.mkdir()
        for name, row in (("a.csv.gz", "001,10"), ("b.csv.gz", "002,20")):
            with gzip.open(baseline / name, "wt", encoding="utf-8", newline="") as handle:
                handle.write(f"id,value\n{row}\n")
        candidate = self.root / "candidate.csv"
        candidate.write_text("id,value\n002,20\n001,10\n", encoding="utf-8")

        self.assertEqual(compare(self.recipe, baseline, candidate)["outcome"], "PASS")
        draft = draft_recipe(baseline, candidate)
        self.assertEqual(draft["keys"], ["id"])
        self.assertEqual(draft["columns"]["value"]["type"], "integer")

    def test_malformed_gzip_is_rejected(self):
        bad = self.root / "bad.csv.gz"
        bad.write_bytes(b"not gzip")
        good = self.compressed("good.csv.gz", "id,value\n001,10\n")
        with self.assertRaisesRegex(ParisonError, "cannot decompress"):
            compare(self.recipe, bad, good)

    def test_drafting_rejects_input_changed_during_row_inspection(self):
        left = self.compressed("left.csv.gz", "id,value\n001,10\n")
        right = self.compressed("right.csv.gz", "id,value\n001,10\n")
        original_read = core._read

        def changing_read(*args, **kwargs):
            rows = original_read(*args, **kwargs)
            if Path(args[0]) == left:
                with gzip.open(left, "at", encoding="utf-8") as handle:
                    handle.write("002,20\n")
            return rows

        with patch("parison.core._read", side_effect=changing_read):
            with self.assertRaisesRegex(ParisonError, "input changed while it was being inspected"):
                draft_recipe(left, right)


if __name__ == "__main__":
    unittest.main()
