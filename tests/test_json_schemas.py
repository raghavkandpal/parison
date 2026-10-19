import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

from parison.cli import main
from parison.core import ParisonError, compare, error_result, export_editor_schemas, load_schema, validate_inputs

ROOT = Path(__file__).parents[1]


class JsonSchemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe_schema = load_schema("recipe")
        cls.recipe_authoring_schema = load_schema("recipe-authoring")
        cls.recipe_v2_schema = load_schema("recipe-v2")
        cls.recipe_v3_schema = load_schema("recipe-v3")
        cls.result_schema = load_schema("result")
        cls.result_v2_schema = load_schema("result-v2")
        cls.result_v3_schema = load_schema("result-v3")
        cls.manifest_schema = load_schema("manifest")
        cls.preflight_schema = load_schema("preflight")
        cls.preflight_v2_schema = load_schema("preflight-v2")
        cls.preflight_v3_schema = load_schema("preflight-v3")
        cls.preflight_v4_schema = load_schema("preflight-v4")
        cls.preflight_v5_schema = load_schema("preflight-v5")
        cls.preflight_v6_schema = load_schema("preflight-v6")
        cls.preflight_v7_schema = load_schema("preflight-v7")
        cls.preflight_v8_schema = load_schema("preflight-v8")
        cls.preflight_v9_schema = load_schema("preflight-v9")
        cls.preflight_v10_schema = load_schema("preflight-v10")
        cls.preflight_v11_schema = load_schema("preflight-v11")
        cls.preflight_v12_schema = load_schema("preflight-v12")
        cls.preflight_v13_schema = load_schema("preflight-v13")
        cls.preflight_v14_schema = load_schema("preflight-v14")
        cls.preflight_v15_schema = load_schema("preflight-v15")
        cls.suite_schema = load_schema("suite")
        cls.suite_v2_schema = load_schema("suite-v2")
        cls.suite_authoring_schema = load_schema("suite-authoring")
        cls.statement_schema = load_schema("statement")
        cls.schema_evolution_schema = load_schema("schema-evolution")
        cls.policy_diff_schema = load_schema("policy-diff")
        cls.time_alignment_schema = load_schema("time-alignment")
        cls.reconciliation_schema = load_schema("reconciliation")
        cls.alignment_preflight_schema = load_schema("alignment-preflight")
        cls.relationship_result_schema = load_schema("relationship-result")
        cls.conservation_result_schema = load_schema("conservation-result")
        cls.reconciliation_result_schema = load_schema("reconciliation-result")
        cls.discrepancy_analysis_schema = load_schema("discrepancy-analysis")
        Draft202012Validator.check_schema(cls.recipe_schema)
        Draft202012Validator.check_schema(cls.recipe_v2_schema)
        Draft202012Validator.check_schema(cls.recipe_v3_schema)
        Draft202012Validator.check_schema(cls.result_schema)
        Draft202012Validator.check_schema(cls.result_v2_schema)
        Draft202012Validator.check_schema(cls.result_v3_schema)
        Draft202012Validator.check_schema(cls.manifest_schema)
        Draft202012Validator.check_schema(cls.preflight_schema)
        Draft202012Validator.check_schema(cls.preflight_v2_schema)
        Draft202012Validator.check_schema(cls.preflight_v3_schema)
        Draft202012Validator.check_schema(cls.preflight_v4_schema)
        Draft202012Validator.check_schema(cls.preflight_v5_schema)
        Draft202012Validator.check_schema(cls.preflight_v6_schema)
        Draft202012Validator.check_schema(cls.preflight_v7_schema)
        Draft202012Validator.check_schema(cls.preflight_v8_schema)
        Draft202012Validator.check_schema(cls.preflight_v9_schema)
        Draft202012Validator.check_schema(cls.preflight_v10_schema)
        Draft202012Validator.check_schema(cls.preflight_v11_schema)
        Draft202012Validator.check_schema(cls.preflight_v12_schema)
        Draft202012Validator.check_schema(cls.preflight_v13_schema)
        Draft202012Validator.check_schema(cls.preflight_v14_schema)
        Draft202012Validator.check_schema(cls.preflight_v15_schema)
        Draft202012Validator.check_schema(cls.recipe_authoring_schema)
        Draft202012Validator.check_schema(cls.suite_authoring_schema)
        Draft202012Validator.check_schema(cls.statement_schema)
        Draft202012Validator.check_schema(cls.schema_evolution_schema)
        Draft202012Validator.check_schema(cls.policy_diff_schema)
        Draft202012Validator.check_schema(cls.time_alignment_schema)
        Draft202012Validator.check_schema(cls.reconciliation_schema)
        Draft202012Validator.check_schema(cls.alignment_preflight_schema)
        Draft202012Validator.check_schema(cls.relationship_result_schema)
        Draft202012Validator.check_schema(cls.conservation_result_schema)
        Draft202012Validator.check_schema(cls.reconciliation_result_schema)
        Draft202012Validator.check_schema(cls.discrepancy_analysis_schema)
        cls.schema_store = {
            schema["$id"]: schema
            for schema in (
                cls.recipe_schema,
                cls.recipe_v2_schema,
                cls.recipe_v3_schema,
                cls.suite_schema,
                cls.suite_v2_schema,
            )
        }

    def test_committed_recipes_match_recipe_schema(self):
        recipes = sorted(ROOT.glob("examples/**/*.recipe.json"))
        self.assertTrue(recipes)
        for path in recipes:
            with self.subTest(path=path):
                value = json.loads(path.read_text(encoding="utf-8"))
                schema = (
                    self.recipe_v2_schema
                    if value.get("recipe_version") == 2
                    else self.recipe_v3_schema
                    if value.get("recipe_version") == 3
                    else self.recipe_schema
                )
                Draft202012Validator(schema).validate(value)

    def test_authoring_schemas_resolve_offline_and_cover_all_examples(self):
        recipe_validator = Draft202012Validator(
            self.recipe_authoring_schema,
            resolver=RefResolver.from_schema(self.recipe_authoring_schema, store=self.schema_store),
        )
        for path in sorted(ROOT.glob("examples/**/*.recipe.json")):
            with self.subTest(path=path):
                recipe_validator.validate(json.loads(path.read_text(encoding="utf-8")))
        suite_validator = Draft202012Validator(
            self.suite_authoring_schema,
            resolver=RefResolver.from_schema(self.suite_authoring_schema, store=self.schema_store),
        )
        plans = sorted(ROOT.glob("examples/**/*suite.json"))
        self.assertTrue(plans)
        for path in plans:
            with self.subTest(path=path):
                suite_validator.validate(json.loads(path.read_text(encoding="utf-8")))
        for schema in (self.recipe_authoring_schema, self.suite_authoring_schema):
            self.assertTrue(schema["description"])
            self.assertTrue(schema["examples"])
            self.assertIn("raw.githubusercontent.com", schema["$id"])

    def test_complete_and_terminal_results_match_result_schema(self):
        validator = Draft202012Validator(self.result_schema)
        validator.validate(json.loads((ROOT / "examples/output/result.json").read_text(encoding="utf-8")))
        validator.validate(
            compare(
                ROOT / "examples/0.3/migration.recipe.json",
                ROOT / "examples/0.3/baseline",
                ROOT / "examples/0.3/candidate.jsonl",
            )
        )
        validator.validate(error_result("safe diagnostic"))

    def test_committed_manifest_matches_manifest_schema(self):
        Draft202012Validator(self.manifest_schema).validate(
            json.loads((ROOT / "examples/output/manifest.json").read_text(encoding="utf-8"))
        )

    def test_example_preflight_matches_preflight_schema(self):
        result = validate_inputs(
            ROOT / "examples/orders.recipe.json",
            ROOT / "examples/baseline.csv",
            ROOT / "examples/candidate.csv",
            validate_records=True,
        )
        Draft202012Validator(self.preflight_schema).validate(result)

    def test_xlsx_preflight_schemas_keep_nested_results_closed(self):
        keyed = Draft202012Validator(self.preflight_v4_schema)
        aggregate = Draft202012Validator(self.preflight_v5_schema)
        for validator, definition in (
            (keyed, self.preflight_v4_schema["$defs"]["input"]),
            (aggregate, self.preflight_v5_schema["$defs"]["input"]),
        ):
            with self.subTest(schema=validator.schema["$id"]):
                self.assertFalse(validator.evolve(schema=definition["properties"]["schema"]).is_valid({}))
                self.assertFalse(validator.evolve(schema=definition["properties"]["records"]).is_valid({}))

    def test_json_preflight_schemas_keep_nested_results_closed(self):
        for schema in (
            self.preflight_v7_schema,
            self.preflight_v8_schema,
            self.preflight_v9_schema,
            self.preflight_v10_schema,
            self.preflight_v11_schema,
            self.preflight_v12_schema,
            self.preflight_v13_schema,
            self.preflight_v14_schema,
            self.preflight_v15_schema,
        ):
            definition = schema["$defs"]["input"]
            validator = Draft202012Validator(schema)
            with self.subTest(schema=schema["$id"]):
                self.assertFalse(validator.evolve(schema=definition["properties"]["schema"]).is_valid({}))
                self.assertFalse(validator.evolve(schema=definition["properties"]["records"]).is_valid({}))

    def test_cli_prints_installed_schemas(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["schema", "recipe-authoring"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["title"], "Parison recipe")

    def test_editor_schema_export_is_atomic_complete_and_offline(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "schemas"
            exported = export_editor_schemas(output)
            self.assertEqual(len(exported["files"]), 7)
            recipe_schema = json.loads((output / "recipe.schema.json").read_text(encoding="utf-8"))
            suite_schema = json.loads((output / "suite.schema.json").read_text(encoding="utf-8"))
            self.assertNotIn("$id", recipe_schema)
            self.assertNotIn("$id", json.loads((output / "recipe-v1.schema.json").read_text(encoding="utf-8")))
            recipe_validator = Draft202012Validator(
                recipe_schema,
                resolver=RefResolver((output / "recipe.schema.json").as_uri(), recipe_schema),
            )
            suite_validator = Draft202012Validator(
                suite_schema,
                resolver=RefResolver((output / "suite.schema.json").as_uri(), suite_schema),
            )
            recipe_validator.validate(json.loads((ROOT / "examples/orders.recipe.json").read_text(encoding="utf-8")))
            suite_validator.validate(
                json.loads((ROOT / "examples/0.11/scalable-suite.json").read_text(encoding="utf-8"))
            )
            with self.assertRaisesRegex(ParisonError, "already exists"):
                export_editor_schemas(output)
            cli_output, stdout = Path(temporary) / "cli-schemas", StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["export-editor-schemas", "--output", str(cli_output)]), 0)
            self.assertEqual(len(json.loads(stdout.getvalue())["files"]), 7)


if __name__ == "__main__":
    unittest.main()
