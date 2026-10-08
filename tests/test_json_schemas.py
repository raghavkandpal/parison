import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import compare, error_result


ROOT = Path(__file__).parents[1]


class JsonSchemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe_schema = json.loads((ROOT / "schemas/recipe-v1.schema.json").read_text(encoding="utf-8"))
        cls.result_schema = json.loads((ROOT / "schemas/result-v1.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.recipe_schema)
        Draft202012Validator.check_schema(cls.result_schema)

    def test_committed_recipes_match_recipe_schema(self):
        validator = Draft202012Validator(self.recipe_schema)
        recipes = sorted(ROOT.glob("examples/**/*.recipe.json"))
        self.assertTrue(recipes)
        for path in recipes:
            with self.subTest(path=path):
                validator.validate(json.loads(path.read_text(encoding="utf-8")))

    def test_complete_and_terminal_results_match_result_schema(self):
        validator = Draft202012Validator(self.result_schema)
        validator.validate(json.loads((ROOT / "examples/output/result.json").read_text(encoding="utf-8")))
        validator.validate(compare(
            ROOT / "examples/0.3/migration.recipe.json",
            ROOT / "examples/0.3/baseline",
            ROOT / "examples/0.3/candidate.jsonl",
        ))
        validator.validate(error_result("safe diagnostic"))


if __name__ == "__main__":
    unittest.main()
