import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import compare, error_result, load_schema, validate_inputs


ROOT = Path(__file__).parents[1]


class JsonSchemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe_schema = load_schema("recipe")
        cls.recipe_v2_schema = load_schema("recipe-v2")
        cls.result_schema = load_schema("result")
        cls.result_v2_schema = load_schema("result-v2")
        cls.manifest_schema = load_schema("manifest")
        cls.preflight_schema = load_schema("preflight")
        cls.preflight_v2_schema = load_schema("preflight-v2")
        Draft202012Validator.check_schema(cls.recipe_schema)
        Draft202012Validator.check_schema(cls.recipe_v2_schema)
        Draft202012Validator.check_schema(cls.result_schema)
        Draft202012Validator.check_schema(cls.result_v2_schema)
        Draft202012Validator.check_schema(cls.manifest_schema)
        Draft202012Validator.check_schema(cls.preflight_schema)
        Draft202012Validator.check_schema(cls.preflight_v2_schema)

    def test_committed_recipes_match_recipe_schema(self):
        validator = Draft202012Validator(self.recipe_schema)
        recipes = sorted(ROOT.glob("examples/**/*.recipe.json"))
        self.assertTrue(recipes)
        for path in recipes:
            with self.subTest(path=path):
                value = json.loads(path.read_text(encoding="utf-8"))
                (Draft202012Validator(self.recipe_v2_schema) if value.get("recipe_version") == 2 else validator).validate(value)

    def test_complete_and_terminal_results_match_result_schema(self):
        validator = Draft202012Validator(self.result_schema)
        validator.validate(json.loads((ROOT / "examples/output/result.json").read_text(encoding="utf-8")))
        validator.validate(compare(
            ROOT / "examples/0.3/migration.recipe.json",
            ROOT / "examples/0.3/baseline",
            ROOT / "examples/0.3/candidate.jsonl",
        ))
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

    def test_cli_prints_installed_schemas(self):
        from contextlib import redirect_stdout
        from io import StringIO

        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(["schema", "manifest"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["title"], "Parison manifest v1")


if __name__ == "__main__":
    unittest.main()
