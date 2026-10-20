import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import (
    ParisonError,
    compare,
    draft_recipe,
    explain_recipe,
    load_recipe,
    load_schema,
    run_suite,
    validate_inputs,
    verify_bundle,
)

RECIPE = {
    "recipe_version": 4,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "xml-field-test",
        "cutoff": "2026-10-19T00:00:00Z",
        "filters": [],
        "completeness": "full",
        "expected_empty": False,
    },
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "input_projection": "semantic-scalar-v1",
    "field_projection": {
        "version": 1,
        "baseline": {
            "kind": "xml-field-v1",
            "namespaces": {"o": "https://example.com/orders/v1"},
            "fields": {"id": "@id", "value": "o:totals/o:net", "label": "label"},
        },
        "candidate": {
            "kind": "direct-v1",
            "fields": {"id": "record_id", "value": "amount", "label": "description"},
        },
    },
    "columns": {
        "id": {"type": "string", "comparison": "exact"},
        "value": {"type": "integer", "comparison": "exact"},
        "label": {"type": "string", "comparison": "exact"},
    },
    "output": {"sensitivity": "summary"},
}


class XmlFieldProjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.document = self.root / "records.xml"
        self.candidate = self.root / "candidate.csv"
        self._write_recipe(RECIPE)
        self._write_xml(
            '<root xmlns:o="https://example.com/orders/v1">'
            '<record id="001"><o:totals><o:net>10</o:net></o:totals><label>first</label></record>'
            '<record id="002"><o:totals><o:net>20</o:net></o:totals><label>second</label></record>'
            "</root>"
        )
        with self.candidate.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows(
                (("record_id", "amount", "description"), ("001", 10, "first"), ("002", 20, "second"))
            )

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def source(self):
        return f"xml:{self.document}#root/record"

    def _write_recipe(self, recipe):
        self.recipe.write_text(json.dumps(recipe), encoding="utf-8")

    def _write_xml(self, value):
        self.document.write_text(value, encoding="utf-8")

    def test_all_modes_engines_preflight_and_portable_suite(self):
        for version, schema_name in ((4, "preflight-v16"), (5, "preflight-v17"), (6, "preflight-v18")):
            recipe = deepcopy(RECIPE)
            if version == 5:
                recipe.update(
                    recipe_version=5,
                    comparison_mode="aggregate",
                    group_by=["label"],
                    measures={"total": {"operator": "sum", "column": "value", "nulls": "reject"}},
                )
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            elif version == 6:
                recipe.update(recipe_version=6, comparison_mode="multiset")
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            self._write_recipe(recipe)
            with self.subTest(version=version):
                for engine in ("memory", "sqlite"):
                    self.assertEqual(
                        compare(self.recipe, self.source, self.candidate, engine=engine)["outcome"], "PASS"
                    )
                preflight = validate_inputs(self.recipe, self.source, self.candidate, validate_records=True)
                Draft202012Validator(load_schema(schema_name)).validate(preflight)
                self.assertNotIn("o:totals", json.dumps(compare(self.recipe, self.source, self.candidate)))

        self._write_recipe(RECIPE)
        plan = self.root / "suite.json"
        plan.write_text(
            json.dumps(
                {
                    "suite_version": 2,
                    "cases": [
                        {
                            "id": "nested-xml",
                            "recipe": "recipe.json",
                            "baseline": "xml:records.xml#root/record",
                            "candidate": "candidate.csv",
                            "execution": {"engine": "sqlite", "max_temp_bytes": 1_000_000},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        output = self.root / "suite-output"
        self.assertEqual(run_suite(plan, output)["outcome"], "PASS")
        self.assertEqual(verify_bundle(output)["kind"], "suite")

    def test_closed_shape_missing_repeated_and_mixed_content_fail(self):
        cases = (
            (
                '<record id="001" extra="x"><o:totals><o:net>10</o:net></o:totals><label>x</label></record>',
                "attributes do not match",
            ),
            (
                '<record id="001"><o:totals><o:net>10</o:net></o:totals><label>x</label><extra>y</extra></record>',
                "unselected element",
            ),
            (
                '<record id="001"><o:totals><o:net>10</o:net><o:net>11</o:net></o:totals><label>x</label></record>',
                "repeated",
            ),
            ('<record id="001"><o:totals></o:totals><label>x</label></record>', "does not resolve"),
            (
                '<record id="001"><o:totals>mixed<o:net>10</o:net></o:totals><label>x</label></record>',
                "only selected children",
            ),
            (
                '<record id="001"><o:totals><o:net>10</o:net>SECRET</o:totals><label>x</label></record>',
                "mixed tail text",
            ),
            (
                '<record id="001"><o:totals><o:net>10</o:net></o:totals>SECRET<label>x</label></record>',
                "mixed tail text",
            ),
            (
                '<record id="001"><o:totals><o:net unit="x">10</o:net></o:totals><label>x</label></record>',
                "attribute-free",
            ),
            (
                '<record id="001"><o:totals><o:net>10</o:net></o:totals><label>x</label></record>SECRET',
                "mixed tail text",
            ),
        )
        for record, message in cases:
            self._write_xml(f'<root xmlns:o="https://example.com/orders/v1">{record}</root>')
            with self.subTest(message=message), self.assertRaisesRegex(ParisonError, message):
                compare(self.recipe, self.source, self.candidate)

    def test_namespace_identity_policy_and_source_pairing_are_strict(self):
        invalid = []
        unused = deepcopy(RECIPE)
        unused["field_projection"]["baseline"]["namespaces"]["unused"] = "urn:unused"
        invalid.append((unused, "exactly match namespaces"))
        nested_attribute = deepcopy(RECIPE)
        nested_attribute["field_projection"]["baseline"]["fields"]["label"] = "@a/b"
        invalid.append((nested_attribute, "attribute or 1 to 32"))
        overlap = deepcopy(RECIPE)
        overlap["field_projection"]["baseline"]["fields"]["label"] = "o:totals"
        invalid.append((overlap, "must not overlap"))
        for recipe, message in invalid:
            self._write_recipe(recipe)
            with self.subTest(message=message), self.assertRaisesRegex(ParisonError, message):
                load_recipe(self.recipe)

        self._write_recipe(RECIPE)
        with self.assertRaisesRegex(ParisonError, "must use xml-field-v1"):
            validate_inputs(self.recipe, self.source, self.source)
        with self.assertRaisesRegex(ParisonError, "requires an XML document locator"):
            validate_inputs(self.recipe, self.candidate, self.candidate)

        default_confusion = deepcopy(RECIPE)
        default_confusion["field_projection"]["baseline"]["fields"]["value"] = "totals/o:net"
        self._write_recipe(default_confusion)
        self._write_xml(
            '<root><record id="001"><totals xmlns="https://example.com/orders/v1">'
            "<net>10</net></totals><label>x</label></record></root>"
        )
        with self.assertRaisesRegex(ParisonError, "unselected element"):
            compare(self.recipe, self.source, self.candidate)

        qualified_attribute = deepcopy(RECIPE)
        qualified_attribute["field_projection"]["baseline"]["fields"]["id"] = "@o:id"
        self._write_recipe(qualified_attribute)
        self._write_xml(
            '<root xmlns:o="https://example.com/orders/v1"><record o:id="001">'
            "<o:totals><o:net>10</o:net></o:totals><label>first</label></record>"
            '<record o:id="002"><o:totals><o:net>20</o:net></o:totals><label>second</label></record></root>'
        )
        self.assertEqual(compare(self.recipe, self.source, self.candidate)["outcome"], "PASS")

    def test_policy_identity_and_drafting_non_invention(self):
        original = explain_recipe(self.recipe)["policy_sha256"]
        changed = deepcopy(RECIPE)
        changed["field_projection"]["baseline"]["fields"]["label"] = "meta/label"
        self._write_recipe(changed)
        self.assertNotEqual(explain_recipe(self.recipe)["policy_sha256"], original)
        self._write_recipe(RECIPE)
        self._write_xml(
            '<root xmlns:o="https://example.com/orders/v1"><record>'
            "<o:totals><o:net>10</o:net></o:totals><label>first</label></record></root>"
        )
        with self.assertRaisesRegex(ParisonError, "attribute-free text element"):
            draft_recipe(self.source, self.candidate)

    def test_locator_bindings_empty_leaf_and_parser_guards_remain_independent(self):
        recipe = deepcopy(RECIPE)
        recipe["field_projection"]["baseline"]["fields"]["label"] = "o:label"
        self._write_recipe(recipe)
        self._write_xml(
            '<p:root xmlns:p="https://example.com/orders/v1"><p:record id="001">'
            "<p:totals><p:net>10</p:net></p:totals><p:label/>\n</p:record></p:root>"
        )
        source = f"xml:{self.document}#p:root/p:record?ns=p,https%3A%2F%2Fexample.com%2Forders%2Fv1"
        with self.candidate.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle).writerows((("record_id", "amount", "description"), ("001", 10, "")))
        self.assertEqual(compare(self.recipe, source, self.candidate)["outcome"], "PASS")

        self._write_xml('<!DOCTYPE root [<!ENTITY x "value">]><root/>')
        with self.assertRaisesRegex(ParisonError, "forbidden DTD"):
            compare(self.recipe, source, self.candidate)
        self._write_xml("<root>" + "<x>" * 100 + "</x>" * 100 + "</root>")
        with self.assertRaisesRegex(ParisonError, "depth limit 100"):
            compare(self.recipe, self.source, self.candidate)
        self._write_xml(
            '<root xmlns:o="https://example.com/orders/v1"><record id="001"><o:totals><o:net>'
            + "x" * (1024 * 1024 + 1)
            + "</o:net></o:totals><label>x</label></record></root>"
        )
        self._write_recipe(RECIPE)
        with self.assertRaisesRegex(ParisonError, "text exceeds 1048576 byte limit"):
            compare(self.recipe, self.source, self.candidate)

    def test_recipe_schemas_admit_xml_projection(self):
        for name, version in (("recipe-v4", 4), ("recipe-v5", 5), ("recipe-v6", 6)):
            recipe = deepcopy(RECIPE)
            if version == 5:
                recipe.update(
                    recipe_version=5, comparison_mode="aggregate", group_by=[], measures={"rows": {"operator": "count"}}
                )
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            elif version == 6:
                recipe.update(recipe_version=6, comparison_mode="multiset")
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            Draft202012Validator(load_schema(name)).validate(recipe)


if __name__ == "__main__":
    unittest.main()
