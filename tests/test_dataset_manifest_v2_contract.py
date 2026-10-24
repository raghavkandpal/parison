"""Structural acceptance gates; runtime binding verification is separate."""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[1]


class DatasetManifestV2Contract(unittest.TestCase):
    def test_canonical_inputs_and_closed_structure(self):
        schema = json.loads((ROOT / "src/parison/schemas/dataset-manifest-v2.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        fixtures = list((ROOT / "tests/fixtures/2.2").glob("dataset-manifest-v2.*.canonical.json"))
        self.assertEqual(len(fixtures), 4)
        for path in fixtures:
            with self.subTest(fixture=path.name):
                value = json.loads(path.read_bytes())
                validator.validate(value)
                self.assertEqual(path.read_bytes(), json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
                for mutation in ("unknown", "missing", "boolean-size", "unknown-kind"):
                    invalid = copy.deepcopy(value)
                    if mutation == "unknown":
                        invalid["bindings"][0]["approved"] = True
                    elif mutation == "missing":
                        del invalid["bindings"][0]["source_kind"]
                    elif mutation == "boolean-size":
                        invalid["files"][0]["bytes"] = True
                    else:
                        invalid["bindings"][0]["source_kind"] = "automatic"
                    self.assertFalse(validator.is_valid(invalid), mutation)
