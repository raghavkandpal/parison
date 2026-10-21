import json
import unittest
from pathlib import Path
from unittest.mock import patch

from parison.core import ParisonError
from parison.policies import load_recipe_text
from parison.workbench import plan_projection, plan_text_projection
from parison.workbench_plans import edit_plan, plan_controls


def edit_field(source, path, operation, value):
    return edit_plan(source, [{"path": path, "operation": operation, "value": value}])


def recipe(version):
    document = {
        "recipe_version": version,
        "comparison_mode": {1: "keyed", 2: "aggregate", 3: "multiset"}[(version - 1) % 3 + 1],
        "scope": {
            "snapshot": "explicit-test",
            "cutoff": "2026-10-21T00:00:00Z",
            "filters": [],
            "completeness": "full",
            "expected_empty": False,
        },
        "columns": {"id": {"type": "string"}, "amount": {"type": "decimal", "scale": 2}},
        "output": {"sensitivity": "summary"},
    }
    if document["comparison_mode"] == "keyed":
        document.update(keys=["id"], identity={"null_keys": "reject", "duplicates": "reject"}, nulls_equal=True)
    elif document["comparison_mode"] == "aggregate":
        document.update(group_by=["id"], measures={"total": {"operator": "sum", "column": "amount", "nulls": "reject"}})
    if version >= 4:
        document["input_projection"] = "semantic-scalar-v1"
        document["field_projection"] = {
            "version": 1,
            "baseline": {"kind": "direct-v1", "fields": {"id": "id", "amount": "amount"}},
            "candidate": {"kind": "direct-v1", "fields": {"id": "id", "amount": "amount"}},
        }
    return document


def nodes(control):
    yield control
    for child in control.get("children", []):
        yield from nodes(child)


class WorkbenchPlanControlsTests(unittest.TestCase):
    def test_pending_fields_apply_together_and_failed_batches_publish_no_draft(self):
        source = json.dumps(recipe(1))
        edits = [
            {"path": ["scope", "snapshot"], "operation": "set", "value": '"batched"'},
            {"path": ["columns", "amount", "scale"], "operation": "set", "value": "3"},
        ]
        changed = json.loads(edit_plan(source, edits)["source"])
        self.assertEqual(changed["scope"]["snapshot"], "batched")
        self.assertEqual(changed["columns"]["amount"]["scale"], 3)
        with self.assertRaises(ParisonError):
            edit_plan(source, [*edits, {"path": [], "operation": "remove", "value": None}])
        self.assertEqual(json.loads(source), recipe(1))
        for invalid in ([], edits * 65, [None], [{"path": ["scope"]}]):
            with self.subTest(edits=invalid), self.assertRaises(ParisonError):
                edit_plan(source, invalid)

    def test_import_policy_is_bound_to_the_exact_source_even_if_file_changes(self):
        source = json.dumps(recipe(1))
        changed = edit_field(source, ["scope", "snapshot"], "set", '"changed-on-disk"')["source"]
        read_text = Path.read_text
        versions = iter([source, changed, source])

        def changing_read(path, *args, **kwargs):
            return next(versions) if path.name == "recipe.json" else read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", changing_read):
            plan = plan_projection("recipe.json")
        self.assertEqual(plan["policy_sha256"], plan_text_projection(plan["source"])["policy_sha256"])

    def test_versions_round_trip_without_normalizing_omitted_policy(self):
        for version in range(1, 7):
            with self.subTest(version=version):
                original = json.dumps(recipe(version), indent=4)
                before = plan_text_projection(original)
                controls = list(nodes(before["controls"]))
                self.assertEqual(
                    {node["path"][0] for node in controls if node["path"] and node["present"]}, set(recipe(version))
                )
                self.assertTrue(any(node["path"] == ["null_tokens"] and not node["present"] for node in controls))
                self.assertIn('"delimiters"', before["effective_policy"])
                edited = edit_field(original, ["scope", "snapshot"], "set", json.dumps("changed"))["source"]
                edited = edit_field(edited, ["scope", "snapshot"], "set", json.dumps("explicit-test"))["source"]
                after = plan_text_projection(edited)
                self.assertEqual(json.loads(edited), json.loads(original))
                self.assertEqual(before["policy_sha256"], after["policy_sha256"])
                self.assertNotIn("null_tokens", json.loads(edited))

    def test_controls_cover_conditional_fields_and_schema_alternatives(self):
        document = recipe(4)
        controls = {tuple(node["path"]): node for node in nodes(plan_controls(json.dumps(document)))}
        self.assertTrue(controls[("columns", "amount", "scale")]["required"])
        self.assertNotIn(("columns", "id", "scale"), controls)
        self.assertNotIn(("column_mappings",), controls)
        self.assertIn('"xml-field-v1"', controls[("field_projection", "baseline", "kind")]["choices"])
        changed = edit_field(json.dumps(document), ["field_projection", "baseline", "kind"], "set", '"xml-field-v1"')
        self.assertTrue(
            any(node["path"] == ["field_projection", "baseline", "namespaces"] for node in nodes(changed["controls"]))
        )
        document = recipe(2)
        changed = edit_field(json.dumps(document), ["measures", "total", "operator"], "set", '"count"')
        controls = {tuple(node["path"]): node for node in nodes(changed["controls"])}
        self.assertIn('"sum"', controls[("measures", "total", "operator")]["choices"])

    def test_control_families_keep_hostile_text_and_large_numbers_as_data(self):
        source = json.dumps(recipe(1))
        hostile = '</script><img src=x onerror=alert(1)>"\\\n\u2028'
        source = edit_field(source, ["scope", "snapshot"], "set", json.dumps(hostile))["source"]
        source = edit_field(source, ["scope", "expected_empty"], "set", "true")["source"]
        source = edit_field(source, ["scope", "filters", 0], "set", json.dumps(hostile))["source"]
        source = edit_field(source, ["excluded_columns"], "set", "{}")["source"]
        source = edit_field(source, ["excluded_columns", "__proto__"], "set", json.dumps(hostile))["source"]
        source = edit_field(source, ["columns", "amount", "comparison"], "set", '"numeric"')["source"]
        source = edit_field(
            source,
            ["columns", "amount", "tolerance"],
            "set",
            '{"formula":"symmetric-v1","absolute":9007199254740993,"relative":"0"}',
        )["source"]
        source = edit_field(source, ["scope", "snapshot"], "set", '"another edit"')["source"]
        self.assertIn("9007199254740993", source)
        self.assertEqual(json.loads(source)["excluded_columns"]["__proto__"], hostile)
        self.assertEqual(json.loads(source)["scope"]["filters"], [hostile])
        load_recipe_text(source)
        source = edit_field(source, ["excluded_columns", "__proto__"], "remove", None)["source"]
        self.assertEqual(json.loads(source)["excluded_columns"], {})

    def test_bad_edits_and_bounded_controls_fail_cleanly(self):
        source = json.dumps(recipe(1))
        for path, operation, value in (
            ([], "set", "{}"),
            (["scope"], [], "{}"),
            (["missing", "value"], "set", '"x"'),
            (["scope", True], "set", "true"),
            (["scope", "filters", -1], "set", '"x"'),
            (["scope", "snapshot"], "set", "NaN"),
            (["scope", "snapshot"], "set", "1e999"),
        ):
            with self.subTest(path=path), self.assertRaises(ParisonError):
                edit_field(source, path, operation, value)
        for invalid in ("[]", '{"recipe_version":true}', '{"recipe_version":7}', '{"recipe_version":1,"x":NaN}'):
            with self.subTest(invalid=invalid), self.assertRaises(ParisonError):
                plan_controls(invalid)
        document = recipe(1)
        document["scope"]["filters"] = ["x"] * 4100
        with self.assertRaisesRegex(ParisonError, "limit"):
            plan_controls(json.dumps(document))
        projection = plan_text_projection(json.dumps(document))
        self.assertIsNone(projection["controls"])
        self.assertIn("limit", projection["controls_notice"])
        self.assertRegex(projection["policy_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
