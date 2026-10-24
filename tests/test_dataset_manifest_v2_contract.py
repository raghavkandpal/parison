"""Structural acceptance gates; runtime binding verification is separate."""

import copy
import hashlib
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

    def test_semantic_binding_record_selection_is_closed(self):
        schema = json.loads((ROOT / "src/parison/schemas/input-bindings-v1.schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        fixtures = list((ROOT / "tests/fixtures/2.2").glob("input-bindings-v1.*.canonical.json"))
        self.assertEqual(len(fixtures), 4)
        for fixture in fixtures:
            record = json.loads(fixture.read_bytes())
            validator.validate(record)
            self.assertEqual(fixture.read_bytes(), json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
        path = ROOT / "tests/fixtures/2.2/input-bindings-v1.shared-workbook.canonical.json"
        value = json.loads(path.read_bytes())
        validator.validate(value)
        self.assertEqual(path.read_bytes(), json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
        for mutation in ("path", "kind", "partition"):
            invalid = copy.deepcopy(value)
            binding = invalid["bindings"][0]
            if mutation == "path":
                binding["selection"]["path"] = "sensitive/source.xlsx"
            elif mutation == "kind":
                binding["selection"]["kind"] = "inferred"
            else:
                binding["source_kind"] = "partition"
            self.assertFalse(validator.is_valid(invalid), mutation)

    def test_artifact_examples_bind_the_canonical_member_bytes(self):
        root = ROOT / "tests/fixtures/2.2"
        names = {
            "dataset-manifest.json": "dataset-manifest-v2.shared-workbook.canonical.json",
            "manifest-result.json": "manifest-result-v2.canonical.json",
            "reproducibility-diagnostic.json": "reproducibility-diagnostic-v2.canonical.json",
        }
        outer = json.loads((root / "dataset-evidence-v2.outer.canonical.json").read_bytes())
        members = {}
        for name, fixture in names.items():
            data = (root / fixture).read_bytes()
            members[name] = json.loads(data)
            self.assertEqual(data, json.dumps(members[name], sort_keys=True, separators=(",", ":")).encode())
            self.assertEqual(outer["files"][name], hashlib.sha256(data).hexdigest())
        manifest_digest = hashlib.sha256(
            b"parison:dataset-manifest-v2\0" + (root / names["dataset-manifest.json"]).read_bytes()
        ).hexdigest()
        diagnostic_digest = hashlib.sha256(
            b"parison:reproducibility-diagnostic-v2\0" + (root / names["reproducibility-diagnostic.json"]).read_bytes()
        ).hexdigest()
        self.assertEqual(outer["manifest_sha256"], manifest_digest)
        self.assertEqual(outer["diagnostic_sha256"], diagnostic_digest)
        self.assertEqual(members["manifest-result.json"]["manifest_sha256"], manifest_digest)
        self.assertEqual(members["reproducibility-diagnostic.json"]["manifest_sha256"], manifest_digest)
        self.assertEqual(members["manifest-result.json"]["diagnostic_sha256"], diagnostic_digest)

    def test_artifact_schemas_are_closed(self):
        for name, fixture in (
            ("dataset-evidence-v2", "dataset-evidence-v2.outer.canonical.json"),
            ("manifest-result-v2", "manifest-result-v2.canonical.json"),
            ("manifest-result-v2", "manifest-result-v2.standalone-fail.canonical.json"),
            ("reproducibility-diagnostic-v2", "reproducibility-diagnostic-v2.canonical.json"),
        ):
            with self.subTest(schema=name):
                schema = json.loads((ROOT / f"src/parison/schemas/{name}.schema.json").read_text())
                Draft202012Validator.check_schema(schema)
                validator = Draft202012Validator(schema)
                value = json.loads((ROOT / "tests/fixtures/2.2" / fixture).read_bytes())
                validator.validate(value)
                if name == "manifest-result-v2" and value["semantic_result"] is not None:
                    for field in ("semantic_result", "diagnostic_sha256"):
                        mixed = copy.deepcopy(value)
                        mixed[field] = None
                        self.assertFalse(validator.is_valid(mixed), field)
                invalid = copy.deepcopy(value)
                invalid["approved"] = True
                self.assertFalse(validator.is_valid(invalid))
                invalid = copy.deepcopy(value)
                del invalid["manifest_sha256"]
                self.assertFalse(validator.is_valid(invalid))
