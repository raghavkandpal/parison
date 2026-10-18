import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.core import ParisonError, compare, draft_recipe, load_schema, load_suite, validate_inputs
from parison.inputs import _json_rows

RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "json-document-test",
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
        "value": {
            "type": "decimal",
            "scale": 2,
            "comparison": "numeric",
            "tolerance": {"formula": "symmetric-v1", "absolute": "0", "relative": "0"},
        },
        "active": {"type": "boolean", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class JsonDocumentInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        self.document = self.root / "records.json"
        self.document.write_text(
            '{"exports":{"records":[{"id":"001","value":10.00,"active":true},{"active":false,"value":2,"id":"002"}]}}',
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def source(self):
        return f"json:{self.document}#/exports/records"

    def test_pointer_projection_compares_and_records_metadata(self):
        result = compare(self.recipe, self.source, self.source)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 2)
        self.assertEqual(result["inputs"]["baseline"]["format"], "json")
        self.assertEqual(result["inputs"]["baseline"]["pointer"], "/exports/records")
        self.assertNotIn(str(self.document), json.dumps(result))

    def test_pointer_escaping_root_and_exact_numbers(self):
        self.document.write_text('{"a/b":{"~rows":[{"id":"001","value":1.20,"active":true}]}}', encoding="utf-8")
        source = f"json:{self.document}#/a~1b/~0rows"
        self.assertEqual(compare(self.recipe, source, source)["outcome"], "PASS")
        self.document.write_text('[{"id":"001","value":1.20,"active":true}]', encoding="utf-8")
        self.assertEqual(compare(self.recipe, f"json:{self.document}#", f"json:{self.document}#")["outcome"], "PASS")

    def test_all_modes_drafting_preflight_and_portable_suite(self):
        draft = draft_recipe(self.source, self.source)
        self.assertEqual(draft["input_projection"], "semantic-scalar-v1")
        keyed = validate_inputs(self.recipe, self.source, self.source, validate_records=True)
        self.assertEqual(keyed["schema_version"], 7)
        Draft202012Validator(load_schema("preflight-v7")).validate(keyed)

        aggregate = deepcopy(RECIPE)
        aggregate["columns"]["value"] = {"type": "decimal", "scale": 2, "comparison": "exact"}
        aggregate.update(
            recipe_version=2,
            comparison_mode="aggregate",
            group_by=["active"],
            measures={"total": {"operator": "sum", "column": "value", "nulls": "reject", "comparison": "exact"}},
        )
        for key in ("keys", "identity", "nulls_equal"):
            aggregate.pop(key)
        self.recipe.write_text(json.dumps(aggregate), encoding="utf-8")
        self.assertEqual(compare(self.recipe, self.source, self.source)["outcome"], "PASS")
        aggregate_result = validate_inputs(self.recipe, self.source, self.source)
        self.assertEqual(aggregate_result["schema_version"], 8)
        Draft202012Validator(load_schema("preflight-v8")).validate(aggregate_result)

        multiset = deepcopy(RECIPE)
        multiset["columns"]["value"] = {"type": "decimal", "scale": 2, "comparison": "exact"}
        multiset.update(recipe_version=3, comparison_mode="multiset")
        for key in ("keys", "identity", "nulls_equal"):
            multiset.pop(key)
        self.recipe.write_text(json.dumps(multiset), encoding="utf-8")
        self.assertEqual(compare(self.recipe, self.source, self.source)["outcome"], "PASS")
        multiset_result = validate_inputs(self.recipe, self.source, self.source)
        self.assertEqual(multiset_result["schema_version"], 9)
        Draft202012Validator(load_schema("preflight-v9")).validate(multiset_result)

        suite = self.root / "suite.json"
        suite.write_text(
            json.dumps(
                {
                    "suite_version": 2,
                    "cases": [
                        {
                            "id": "json",
                            "recipe": "recipe.json",
                            "baseline": "json:records.json#/exports/records",
                            "candidate": "json:records.json#/exports/records",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        case = load_suite(suite)["cases"][0]
        self.assertEqual(case["baseline"], self.source)

    def test_schema_preflight_enforces_row_limit_and_all_record_shapes(self):
        with self.assertRaisesRegex(ParisonError, "row count.*exceeds limit 1"):
            validate_inputs(self.recipe, self.source, self.source, max_rows=1)
        self.document.write_text(
            '{"exports":{"records":[{"id":"001","value":1,"active":true},{"id":"002","value":2}]}}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ParisonError, "inconsistent JSON fields"):
            validate_inputs(self.recipe, self.source, self.source)

    def test_rejects_implicit_open_or_malformed_documents(self):
        cases = (
            ('{"records":[{"id":"1","id":"2","value":1,"active":true}]}', "duplicate JSON key"),
            ('{"records":[{"id":"1","value":[],"active":true}]}', "nested value"),
            ('{"records":[{"id":"1","value":NaN,"active":true}]}', "cannot parse JSON"),
            ('{"records":[{"id":"1","value":1,"active":true},{"id":"2","value":2}]}', "inconsistent JSON fields"),
        )
        for index, (content, message) in enumerate(cases):
            with self.subTest(index=index):
                self.document.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(ParisonError, message):
                    compare(self.recipe, f"json:{self.document}#/records", f"json:{self.document}#/records")
        with self.assertRaisesRegex(ParisonError, "JSON or XLSX locator"):
            compare(self.recipe, self.document, self.source)
        with self.assertRaisesRegex(ParisonError, "does not resolve"):
            compare(self.recipe, f"json:{self.document}#/missing", self.source)
        with self.assertRaisesRegex(ParisonError, "invalid escape"):
            compare(self.recipe, f"json:{self.document}#/bad~2pointer", self.source)
        self.document.write_text('{"records":[[{"id":"1","value":1,"active":true}]]}', encoding="utf-8")
        for token in ("\u0660", "1" * 5000):
            with self.subTest(pointer_token=token), self.assertRaisesRegex(ParisonError, "does not resolve"):
                compare(self.recipe, f"json:{self.document}#/records/{token}", f"json:{self.document}#/records/{token}")
        with (
            patch("parison.inputs.json.loads", side_effect=RecursionError),
            self.assertRaisesRegex(ParisonError, "cannot parse JSON document"),
        ):
            next(_json_rows(self.source, None))
        self.document.write_text('{"records":[]}', encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "input has no schema"):
            compare(self.recipe, f"json:{self.document}#/records", f"json:{self.document}#/records")
        self.document.write_text('{"records":[1]}', encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "must be an object"):
            compare(self.recipe, f"json:{self.document}#/records", f"json:{self.document}#/records")
        self.document.write_text('{"records":{"id":"1"}}', encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "must select an array"):
            compare(self.recipe, f"json:{self.document}#/records", f"json:{self.document}#/records")
        self.document.write_text('{"records":[{"id":"1","value":1,"active":true}]}', encoding="utf-8")
        link = self.root / "link.json"
        link.symlink_to(self.document)
        with self.assertRaisesRegex(ParisonError, "non-symlink"):
            compare(self.recipe, f"json:{link}#/records", self.source)
        open_recipe = dict(RECIPE)
        open_recipe.pop("input_projection")
        self.recipe.write_text(json.dumps(open_recipe), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "require input_projection"):
            compare(self.recipe, self.source, self.source)


if __name__ == "__main__":
    unittest.main()
