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
    explain_recipe,
    load_recipe,
    load_schema,
    load_suite,
    run_suite,
    validate_inputs,
    verify_bundle,
)

RECIPE = {
    "recipe_version": 4,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {
        "snapshot": "json-field-test",
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
            "kind": "json-pointer-v1",
            "fields": {"id": "/identity/id", "value": "/totals/net", "label": "/meta/a~1b"},
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


class JsonFieldProjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.recipe = self.root / "recipe.json"
        self.document = self.root / "records.json"
        self.candidate = self.root / "candidate.csv"
        self._write_recipe(RECIPE)
        self._write_document(
            [
                {"identity": {"id": "001"}, "totals": {"net": 10}, "meta": {"a/b": "first"}},
                {"identity": {"id": "002"}, "totals": {"net": 20}, "meta": {"a/b": "second"}},
            ]
        )
        with self.candidate.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows((("record_id", "amount", "description"), ("001", 10, "first"), ("002", 20, "second")))

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def source(self):
        return f"json:{self.document}#/records"

    def _write_recipe(self, recipe):
        self.recipe.write_text(json.dumps(recipe), encoding="utf-8")

    def _write_document(self, records):
        self.document.write_text(json.dumps({"records": records}), encoding="utf-8")

    def test_keyed_projection_policy_preflight_suite_and_summary_safety(self):
        loaded = load_recipe(self.recipe)
        self.assertEqual(loaded["recipe_version"], 4)
        policy = explain_recipe(self.recipe)
        self.assertEqual(policy["field_projection"], RECIPE["field_projection"])
        self.assertEqual(policy["columns"]["id"]["baseline_column"], "id")
        self.assertEqual(policy["columns"]["id"]["candidate_column"], "record_id")

        result = compare(self.recipe, self.source, self.candidate)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["matched_exact"], 2)
        self.assertEqual(compare(self.recipe, self.source, self.candidate, engine="sqlite")["outcome"], "PASS")
        self.assertNotIn("/identity/id", json.dumps(result))

        preflight = validate_inputs(self.recipe, self.source, self.candidate, validate_records=True)
        self.assertEqual(preflight["schema_version"], 16)
        self.assertEqual(preflight["field_projection"], RECIPE["field_projection"])
        Draft202012Validator(load_schema("preflight-v16")).validate(preflight)

        suite = self.root / "suite.json"
        suite.write_text(
            json.dumps(
                {
                    "suite_version": 2,
                    "cases": [
                        {
                            "id": "nested-json",
                            "recipe": "recipe.json",
                            "baseline": "json:records.json#/records",
                            "candidate": "candidate.csv",
                            "execution": {"engine": "sqlite", "max_temp_bytes": 1_000_000},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.assertEqual(load_suite(suite)["cases"][0]["baseline"], self.source)
        suite_output = self.root / "suite-output"
        self.assertEqual(run_suite(suite, suite_output)["outcome"], "PASS")
        self.assertEqual(verify_bundle(suite_output)["kind"], "suite")

    def test_projection_supports_aggregate_and_multiset_under_both_engines(self):
        aggregate = deepcopy(RECIPE)
        aggregate.update(
            recipe_version=5,
            comparison_mode="aggregate",
            group_by=["label"],
            measures={"value_sum": {"operator": "sum", "column": "value", "nulls": "reject"}},
        )
        for name in ("keys", "identity", "nulls_equal"):
            aggregate.pop(name)
        self._write_recipe(aggregate)
        for engine in ("memory", "sqlite"):
            self.assertEqual(compare(self.recipe, self.source, self.candidate, engine=engine)["outcome"], "PASS")
        aggregate_preflight = validate_inputs(self.recipe, self.source, self.candidate)
        self.assertEqual(aggregate_preflight["schema_version"], 17)
        Draft202012Validator(load_schema("preflight-v17")).validate(aggregate_preflight)

        multiset = deepcopy(RECIPE)
        multiset.update(recipe_version=6, comparison_mode="multiset")
        for name in ("keys", "identity", "nulls_equal"):
            multiset.pop(name)
        self._write_recipe(multiset)
        for engine in ("memory", "sqlite"):
            self.assertEqual(compare(self.recipe, self.source, self.candidate, engine=engine)["outcome"], "PASS")
        multiset_preflight = validate_inputs(self.recipe, self.source, self.candidate)
        self.assertEqual(multiset_preflight["schema_version"], 18)
        Draft202012Validator(load_schema("preflight-v18")).validate(multiset_preflight)

    def test_projection_rejects_invalid_policy_and_source_pairing(self):
        cases = []
        missing_side = deepcopy(RECIPE)
        missing_side["field_projection"].pop("candidate")
        cases.append((missing_side, "exactly version, baseline and candidate"))
        incomplete = deepcopy(RECIPE)
        incomplete["field_projection"]["baseline"]["fields"].pop("label")
        cases.append((incomplete, "must name exactly"))
        duplicate = deepcopy(RECIPE)
        duplicate["field_projection"]["baseline"]["fields"]["label"] = "/identity/id"
        cases.append((duplicate, "must be unique"))
        invalid_escape = deepcopy(RECIPE)
        invalid_escape["field_projection"]["baseline"]["fields"]["label"] = "/meta/~2"
        cases.append((invalid_escape, "invalid JSON pointer escape"))
        old_mapping = deepcopy(RECIPE)
        old_mapping["column_mappings"] = {}
        cases.append((old_mapping, "replaces column_mappings"))
        for recipe, message in cases:
            with self.subTest(message=message):
                self._write_recipe(recipe)
                with self.assertRaisesRegex(ParisonError, message):
                    load_recipe(self.recipe)

        self._write_recipe(RECIPE)
        with self.assertRaisesRegex(ParisonError, "must use json-pointer-v1"):
            compare(self.recipe, self.source, self.source)
        with self.assertRaisesRegex(ParisonError, "must use json-pointer-v1"):
            validate_inputs(self.recipe, self.source, self.source)
        with self.assertRaisesRegex(ParisonError, "requires a JSON document locator"):
            compare(self.recipe, self.candidate, self.candidate)
        with self.assertRaisesRegex(ParisonError, "requires a JSON document locator"):
            validate_inputs(self.recipe, self.candidate, self.candidate)

        surrogate = deepcopy(RECIPE)
        surrogate["field_projection"]["baseline"]["fields"]["label"] = "\ud800"
        self._write_recipe(surrogate)
        with self.assertRaisesRegex(ParisonError, "nonempty selectors up to 1024 bytes"):
            load_recipe(self.recipe)

    def test_projection_limits_fingerprint_and_direct_xml_preflight(self):
        original_fingerprint = explain_recipe(self.recipe)["policy_sha256"]
        changed = deepcopy(RECIPE)
        changed["field_projection"]["baseline"]["fields"]["label"] = "/meta/a~0b"
        self._write_recipe(changed)
        self.assertNotEqual(explain_recipe(self.recipe)["policy_sha256"], original_fingerprint)

        for selector, message in (
            ("/" + "/".join(["x"] * 33), "at most 32 tokens"),
            ("/" + "x" * 1024, "up to 1024 bytes"),
        ):
            invalid = deepcopy(RECIPE)
            invalid["field_projection"]["baseline"]["fields"]["label"] = selector
            self._write_recipe(invalid)
            with self.subTest(selector_length=len(selector)), self.assertRaisesRegex(ParisonError, message):
                load_recipe(self.recipe)

        xml = self.root / "records.xml"
        xml.write_text(
            "<root><record><id>001</id><value>10</value><label>first</label></record>"
            "<record><id>002</id><value>20</value><label>second</label></record></root>",
            encoding="utf-8",
        )
        xml_source = f"xml:{xml}#root/record"
        for version, schema_name in ((4, "preflight-v16"), (5, "preflight-v17"), (6, "preflight-v18")):
            recipe = deepcopy(RECIPE)
            recipe["field_projection"]["candidate"]["fields"] = {
                "id": "id",
                "value": "value",
                "label": "label",
            }
            if version == 5:
                recipe.update(
                    recipe_version=5,
                    comparison_mode="aggregate",
                    group_by=["label"],
                    measures={"value_sum": {"operator": "sum", "column": "value", "nulls": "reject"}},
                )
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            elif version == 6:
                recipe.update(recipe_version=6, comparison_mode="multiset")
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            self._write_recipe(recipe)
            preflight = validate_inputs(self.recipe, self.source, xml_source)
            with self.subTest(version=version):
                Draft202012Validator(load_schema(schema_name)).validate(preflight)

    def test_projection_rejects_missing_container_and_noncanonical_array_index(self):
        for pointer, message in (
            ("/missing", "does not resolve"),
            ("/identity", "selects a container"),
            ("/items/01", "does not resolve"),
        ):
            recipe = deepcopy(RECIPE)
            recipe["field_projection"]["baseline"]["fields"]["label"] = pointer
            self._write_recipe(recipe)
            records = [
                {
                    "identity": {"id": "001"},
                    "totals": {"net": 10},
                    "meta": {"a/b": "first"},
                    "items": ["zero", "one"],
                }
            ]
            self._write_document(records)
            with self.subTest(pointer=pointer), self.assertRaisesRegex(ParisonError, message):
                compare(self.recipe, self.source, self.candidate)

    def test_new_recipe_schemas_are_strict_and_released_schemas_reject_new_versions(self):
        for name, version in (("recipe-v4", 4), ("recipe-v5", 5), ("recipe-v6", 6)):
            recipe = deepcopy(RECIPE)
            if version == 5:
                recipe.update(
                    recipe_version=5,
                    comparison_mode="aggregate",
                    group_by=[],
                    measures={"rows": {"operator": "count"}},
                )
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            elif version == 6:
                recipe.update(recipe_version=6, comparison_mode="multiset")
                for key in ("keys", "identity", "nulls_equal"):
                    recipe.pop(key)
            Draft202012Validator(load_schema(name)).validate(recipe)
        self.assertFalse(Draft202012Validator(load_schema("recipe")).is_valid(RECIPE))


if __name__ == "__main__":
    unittest.main()
