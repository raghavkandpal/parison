import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import ParisonError, compare, draft_recipe, load_schema, load_suite, validate_inputs

RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["p:id"],
    "scope": {
        "snapshot": "xml-test",
        "cutoff": "2026-10-18T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "input_projection": "semantic-scalar-v1",
    "columns": {
        "p:id": {"type": "string", "comparison": "exact"},
        "p:value": {"type": "integer", "comparison": "exact"},
        "p:active": {"type": "boolean", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class XmlInput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.recipe.write_text(json.dumps(RECIPE), encoding="utf-8")
        self.document = self.root / "records.xml"
        self.document.write_text(
            '<p:root xmlns:p="https://example.com/v1"><p:records>'
            "<p:record><p:id>001</p:id><p:value>10</p:value><p:active>true</p:active></p:record>"
            "<p:record><p:active>false</p:active><p:value>2</p:value><p:id>002</p:id></p:record>"
            "</p:records></p:root>",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def source(self):
        return f"xml:{self.document}#p:root/p:records/p:record?ns=p,https%3A%2F%2Fexample.com%2Fv1"

    def test_explicit_path_compares_drafts_and_records_metadata(self):
        result = compare(self.recipe, self.source, self.source)
        self.assertEqual(result["outcome"], "PASS")
        metadata = result["inputs"]["baseline"]
        self.assertEqual(metadata["format"], "xml")
        self.assertEqual(metadata["record_path"], "p:root/p:records/p:record")
        self.assertEqual(metadata["namespaces"], {"p": "https://example.com/v1"})
        self.assertNotIn(str(self.document), json.dumps(result))
        self.assertEqual(draft_recipe(self.source, self.source)["input_projection"], "semantic-scalar-v1")

        field_recipe = deepcopy(RECIPE)
        field_recipe["keys"] = ["q:id"]
        field_recipe["columns"] = {"q:id": {"type": "string", "comparison": "exact"}}
        self.recipe.write_text(json.dumps(field_recipe), encoding="utf-8")
        self.document.write_text(
            '<root xmlns:q="urn:fields"><record><q:id>001</q:id></record></root>', encoding="utf-8"
        )
        field_source = f"xml:{self.document}#root/record?ns=q,urn%3Afields"
        self.assertEqual(compare(self.recipe, field_source, field_source)["outcome"], "PASS")

    def test_all_modes_preflight_and_portable_suite(self):
        keyed = validate_inputs(self.recipe, self.source, self.source, validate_records=True)
        self.assertEqual(keyed["schema_version"], 10)
        Draft202012Validator(load_schema("preflight-v10")).validate(keyed)

        aggregate = deepcopy(RECIPE)
        aggregate.update(
            recipe_version=2,
            comparison_mode="aggregate",
            group_by=["p:active"],
            measures={"total": {"operator": "sum", "column": "p:value", "nulls": "reject", "comparison": "exact"}},
        )
        for key in ("keys", "identity", "nulls_equal"):
            aggregate.pop(key)
        self.recipe.write_text(json.dumps(aggregate), encoding="utf-8")
        self.assertEqual(compare(self.recipe, self.source, self.source)["outcome"], "PASS")
        aggregate_result = validate_inputs(self.recipe, self.source, self.source)
        self.assertEqual(aggregate_result["schema_version"], 11)
        Draft202012Validator(load_schema("preflight-v11")).validate(aggregate_result)

        multiset = deepcopy(RECIPE)
        multiset.update(recipe_version=3, comparison_mode="multiset")
        for key in ("keys", "identity", "nulls_equal"):
            multiset.pop(key)
        self.recipe.write_text(json.dumps(multiset), encoding="utf-8")
        self.assertEqual(compare(self.recipe, self.source, self.source)["outcome"], "PASS")
        multiset_result = validate_inputs(self.recipe, self.source, self.source)
        self.assertEqual(multiset_result["schema_version"], 12)
        Draft202012Validator(load_schema("preflight-v12")).validate(multiset_result)

        suite = self.root / "suite.json"
        portable = "xml:records.xml#p:root/p:records/p:record?ns=p,https%3A%2F%2Fexample.com%2Fv1"
        suite.write_text(
            json.dumps(
                {
                    "suite_version": 2,
                    "cases": [{"id": "xml", "recipe": "recipe.json", "baseline": portable, "candidate": portable}],
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(load_suite(suite)["cases"][0]["baseline"], self.source)

    def test_rejects_unsafe_ambiguous_and_unbounded_projection(self):
        with self.assertRaisesRegex(ParisonError, "row count.*exceeds limit 1"):
            validate_inputs(self.recipe, self.source, self.source, max_rows=1)
        bad_documents = (
            ('<!DOCTYPE root [<!ENTITY x "value">]><root/>', "forbidden DTD"),
            (
                '<p:root xmlns:p="https://example.com/v1"><p:records><p:record id="1"><p:id>1</p:id><p:value>1</p:value><p:active>true</p:active></p:record></p:records></p:root>',
                "attributes or mixed text",
            ),
            (
                '<p:root xmlns:p="https://example.com/v1"><p:records><p:record><p:id><p:nested/></p:id><p:value>1</p:value><p:active>true</p:active></p:record></p:records></p:root>',
                "attribute-free text element",
            ),
        )
        for index, (content, message) in enumerate(bad_documents):
            with self.subTest(index=index):
                self.document.write_text(content, encoding="utf-8")
                with self.assertRaisesRegex(ParisonError, message):
                    compare(self.recipe, self.source, self.source)
        self.document.write_bytes('<!DOCTYPE root [<!ENTITY x "value">]><root/>'.encode("utf-16"))
        with self.assertRaisesRegex(ParisonError, "UTF-8 encoding"):
            compare(self.recipe, self.source, self.source)
        with self.assertRaisesRegex(ParisonError, "prefixes must be declared"):
            compare(self.recipe, f"xml:{self.document}#p:root/p:record", self.source)
        open_recipe = dict(RECIPE)
        open_recipe.pop("input_projection")
        self.recipe.write_text(json.dumps(open_recipe), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "require input_projection"):
            validate_inputs(self.recipe, self.source, self.source)


if __name__ == "__main__":
    unittest.main()
