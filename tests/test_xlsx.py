import csv
import json
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import (
    ParisonError,
    compare,
    draft_recipe,
    load_schema,
    load_suite,
    publish,
    validate_inputs,
    verify_bundle,
)

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "xlsx-test",
        "cutoff": "2026-10-18T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "input_projection": "semantic-scalar-v1",
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "integer", "comparison": "exact"},
        "day": {"type": "date", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


@unittest.skipUnless(Workbook, "openpyxl optional dependency is not installed")
class XlsxInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        self.workbook = self.root / "records.xlsx"
        self._write_workbook(
            [
                ["ignored"],
                ["id", "value", "day"],
                ["001", 10, date(2026, 10, 17)],
                ["002", 20, date(2026, 10, 18)],
            ]
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _write_workbook(self, rows):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Export"
        for row in rows:
            worksheet.append(row)
        workbook.save(self.workbook)
        workbook.close()

    @property
    def source(self):
        return f"xlsx:{self.workbook}#Export!A2:C4"

    def test_explicit_range_compares_and_records_bounded_source_metadata(self):
        result = compare(self.recipe, self.source, self.source)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 2)
        metadata = result["inputs"]["baseline"]
        self.assertEqual(metadata["format"], "xlsx")
        self.assertEqual(metadata["worksheet"], "Export")
        self.assertEqual(metadata["range"], "A2:C4")
        self.assertEqual(metadata["compression"], "zip")
        self.assertGreater(metadata["decoded_bytes"], metadata["bytes"])
        self.assertNotIn(str(self.workbook), json.dumps(result))

    def test_xlsx_result_publishes_as_a_verifiable_existing_bundle(self):
        output = self.root / "run"
        result = compare(self.recipe, self.source, self.source)
        publish(output, result, RECIPE)
        verify_bundle(output)
        published = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(published["outcome"], "PASS")
        self.assertEqual(published["inputs"]["baseline"]["format"], "xlsx")

    def test_draft_recipe_preserves_closed_projection(self):
        draft = draft_recipe(self.source, self.source)
        self.assertEqual(draft["input_projection"], "semantic-scalar-v1")
        self.assertEqual(draft["keys"], ["id"])
        self.assertEqual(draft["columns"]["value"]["type"], "integer")
        self.assertEqual(draft["columns"]["day"]["type"], "date")

    def test_preflight_uses_new_schema_without_changing_released_schema(self):
        result = validate_inputs(self.recipe, self.source, self.source, validate_records=True)
        self.assertEqual(result["schema_version"], 4)
        self.assertEqual(result["inputs"]["baseline"]["worksheet"], "Export")
        Draft202012Validator(load_schema("preflight-v4")).validate(result)

    def test_all_modes_and_mixed_text_use_the_same_values(self):
        baseline = self.root / "records.csv"
        with baseline.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(
                (["id", "value", "day"], ["001", "10", "2026-10-17"], ["002", "20", "2026-10-18"])
            )
        self.assertEqual(compare(self.recipe, baseline, self.source)["outcome"], "PASS")

        aggregate = deepcopy(RECIPE)
        aggregate.update(
            recipe_version=2,
            comparison_mode="aggregate",
            group_by=["id"],
            measures={"value_sum": {"operator": "sum", "column": "value", "nulls": "reject"}},
        )
        for key in ("keys", "identity", "nulls_equal"):
            aggregate.pop(key)
        self.recipe.write_text(json.dumps(aggregate), encoding="utf-8")
        self.assertEqual(compare(self.recipe, baseline, self.source)["outcome"], "PASS")
        aggregate_preflight = validate_inputs(self.recipe, baseline, self.source, validate_records=True)
        Draft202012Validator(load_schema("preflight-v5")).validate(aggregate_preflight)

        multiset = deepcopy(RECIPE)
        multiset.update(recipe_version=3, comparison_mode="multiset")
        for key in ("keys", "identity", "nulls_equal"):
            multiset.pop(key)
        self.recipe.write_text(json.dumps(multiset), encoding="utf-8")
        self.assertEqual(compare(self.recipe, baseline, self.source)["outcome"], "PASS")
        multiset_preflight = validate_inputs(self.recipe, baseline, self.source, validate_records=True)
        Draft202012Validator(load_schema("preflight-v6")).validate(multiset_preflight)

    def test_sqlite_engines_match_memory_results(self):
        memory = compare(self.recipe, self.source, self.source)
        sqlite = compare(self.recipe, self.source, self.source, engine="sqlite")
        self.assertEqual(sqlite["outcome"], memory["outcome"])
        self.assertEqual(sqlite["counts"], memory["counts"])

        multiset = deepcopy(RECIPE)
        multiset.update(recipe_version=3, comparison_mode="multiset")
        for key in ("keys", "identity", "nulls_equal"):
            multiset.pop(key)
        self.recipe.write_text(json.dumps(multiset), encoding="utf-8")
        memory = compare(self.recipe, self.source, self.source)
        sqlite = compare(self.recipe, self.source, self.source, engine="sqlite")
        self.assertEqual(sqlite["outcome"], memory["outcome"])
        self.assertEqual(sqlite["counts"], memory["counts"])

    def test_suite_resolves_portable_xlsx_locators(self):
        suite = self.root / "suite.json"
        portable = "xlsx:records.xlsx#Export!A2:C4"
        suite.write_text(
            json.dumps(
                {
                    "suite_version": 2,
                    "cases": [
                        {
                            "id": "xlsx-values",
                            "recipe": "recipe.json",
                            "baseline": portable,
                            "candidate": portable,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        case = load_suite(suite)["cases"][0]
        self.assertEqual(case["baseline"], f"xlsx:{self.workbook}#Export!A2:C4")
        self.assertEqual(case["candidate"], case["baseline"])

    def test_rejects_implicit_selection_formulas_errors_and_open_projection(self):
        with self.assertRaisesRegex(ParisonError, "XLSX locator"):
            compare(self.recipe, self.workbook, self.source)
        with self.assertRaisesRegex(ParisonError, "worksheet does not exist"):
            compare(self.recipe, self.source.replace("#Export", "#Missing"), self.source)
        with self.assertRaisesRegex(ParisonError, "bounded rectangle"):
            compare(self.recipe, self.source.replace("A2:C4", "A:C"), self.source)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Export"
        worksheet.append(["id", "value", "day"])
        worksheet.append(["001", "=5+5", date(2026, 10, 17)])
        workbook.save(self.workbook)
        workbook.close()
        formula_source = f"xlsx:{self.workbook}#Export!A1:C2"
        with self.assertRaisesRegex(ParisonError, "formula cell"):
            compare(self.recipe, formula_source, formula_source)

        open_recipe = dict(RECIPE)
        open_recipe.pop("input_projection")
        self.recipe.write_text(json.dumps(open_recipe), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "require input_projection"):
            compare(self.recipe, formula_source, formula_source)

    def test_rejects_row_and_decoded_size_overruns(self):
        with self.assertRaisesRegex(ParisonError, "row count"):
            compare(self.recipe, self.source, self.source, max_rows=1)
        with self.assertRaisesRegex(ParisonError, "decoded input size"):
            compare(self.recipe, self.source, self.source, max_decoded_bytes=1)


if __name__ == "__main__":
    unittest.main()
