"""Structural acceptance gates; runtime binding verification is separate."""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.core import ParisonError, load_schema
from parison.manifesting import (
    _verify_manifest_result_v2,
    canonical_dataset_manifest_v2_bytes,
    canonical_input_bindings_bytes,
    normalize_dataset_manifest_v2,
    normalize_input_bindings,
    normalize_reproducibility_diagnostic_v2,
    verify_dataset_input_bindings,
)

ROOT = Path(__file__).parents[1]


class DatasetManifestV2Contract(unittest.TestCase):
    def test_source_free_result_validator_accepts_pinned_pass_and_fail(self):
        fixtures = ROOT / "tests/fixtures/2.2"
        manifest = json.loads((fixtures / "dataset-manifest-v2.shared-workbook.canonical.json").read_text())
        for name in ("manifest-result-v2.canonical.json", "manifest-result-v2.standalone-fail.canonical.json"):
            with self.subTest(name=name):
                result = json.loads((fixtures / name).read_text())
                _verify_manifest_result_v2(result, manifest, published=result["semantic_result"] is not None)

    def test_preserved_result_requires_exact_integer_expected_size(self):
        fixtures = ROOT / "tests/fixtures/2.2"
        manifest = json.loads((fixtures / "dataset-manifest-v2.shared-workbook.canonical.json").read_text())
        result = json.loads((fixtures / "manifest-result-v2.canonical.json").read_text())
        for size in (100.0, True):
            with self.subTest(size=size):
                changed_manifest, changed_result = copy.deepcopy(manifest), copy.deepcopy(result)
                changed_manifest["files"][0]["bytes"] = 1 if size is True else 100
                changed_result["files"][0]["expected_bytes"] = size
                changed_result["files"][0]["observed_bytes"] = changed_manifest["files"][0]["bytes"]
                changed_result["manifest_sha256"] = hashlib.sha256(
                    b"parison:dataset-manifest-v2\0" + canonical_dataset_manifest_v2_bytes(changed_manifest)
                ).hexdigest()
                with self.assertRaises(ParisonError):
                    _verify_manifest_result_v2(changed_result, changed_manifest, published=True)

    def test_v2_diagnostic_malformed_values_have_controlled_errors(self):
        fixture = ROOT / "tests/fixtures/2.2/reproducibility-diagnostic-v2.canonical.json"
        value = json.loads(fixture.read_text())
        for mutation in ("surrogate", "array", "object"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(value)
                if mutation == "surrogate":
                    changed["runtime"]["os_family"] = "\ud800"
                else:
                    changed["observations"] = [[]] if mutation == "array" else [{}]
                with self.assertRaises(ParisonError):
                    normalize_reproducibility_diagnostic_v2(changed)

    def test_versioned_schemas_are_available_through_public_loader(self):
        for name in (
            "dataset-manifest-v2",
            "input-bindings-v1",
            "manifest-result-v2",
            "dataset-evidence-v2",
            "reproducibility-diagnostic-v2",
            "suite-manifest-v3",
            "reconciliation-manifest-v2",
        ):
            with self.subTest(name=name):
                Draft202012Validator.check_schema(load_schema(name))

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

    def test_semantic_bundle_versions_require_binding_record(self):
        for kind, version in (("suite", 3), ("reconciliation", 2)):
            with self.subTest(kind=kind):
                name = f"{kind}-manifest-v{version}"
                schema = json.loads((ROOT / f"src/parison/schemas/{name}.schema.json").read_text())
                Draft202012Validator.check_schema(schema)
                validator = Draft202012Validator(schema)
                path = ROOT / f"tests/fixtures/2.2/{name}.canonical.json"
                value = json.loads(path.read_bytes())
                validator.validate(value)
                self.assertEqual(path.read_bytes(), json.dumps(value, sort_keys=True, separators=(",", ":")).encode())
                del value["files"]["input-bindings.json"]
                self.assertFalse(validator.is_valid(value))

    def test_authoritative_normalization_pins_bytes_and_membership(self):
        fixtures = ROOT / "tests/fixtures/2.2"
        for path in fixtures.glob("dataset-manifest-v2.*.canonical.json"):
            with self.subTest(fixture=path.name):
                value = json.loads(path.read_bytes())
                self.assertEqual(canonical_dataset_manifest_v2_bytes(value), path.read_bytes())
                reordered = copy.deepcopy(value)
                reordered["bindings"].reverse()
                reordered["files"].reverse()
                self.assertEqual(canonical_dataset_manifest_v2_bytes(reordered), path.read_bytes())
                for mutation in ("scope", "duplicate", "size", "source-digest", "member"):
                    invalid = copy.deepcopy(value)
                    if mutation == "scope":
                        invalid["closed_scopes"] = [".", "data"]
                    elif mutation == "duplicate":
                        invalid["bindings"].append(copy.deepcopy(invalid["bindings"][0]))
                    elif mutation == "size":
                        invalid["files"][0]["bytes"] = True
                    elif mutation == "source-digest":
                        invalid["bindings"][0]["source_sha256"] = "f" * 64
                    else:
                        invalid["bindings"][0]["members"] = ["../escape.csv"]
                    with self.assertRaises(ParisonError, msg=mutation):
                        normalize_dataset_manifest_v2(invalid)

    def test_authoritative_sources_reject_unsafe_paths_and_partition_substitution(self):
        root = ROOT / "tests/fixtures/2.2"
        value = json.loads((root / "dataset-manifest-v2.shared-workbook.canonical.json").read_bytes())
        for source in ("xlsx:../private.xlsx#Sheet!A1:B2", "xlsx:data//shared.xlsx#Sheet!A1:B2", "https://remote/file"):
            invalid = copy.deepcopy(value)
            invalid["bindings"][0]["source"] = source
            with self.assertRaises(ParisonError):
                normalize_dataset_manifest_v2(invalid)
        partition = json.loads((root / "dataset-manifest-v2.partition.canonical.json").read_bytes())
        partition["bindings"][0]["source_kind"] = "file"
        with self.assertRaises(ParisonError):
            normalize_dataset_manifest_v2(partition)

    def test_authoritative_records_and_hostile_cross_member_substitutions(self):
        root = ROOT / "tests/fixtures/2.2"
        for name in ("shared-workbook", "json", "xml", "partition"):
            manifest = json.loads((root / f"dataset-manifest-v2.{name}.canonical.json").read_bytes())
            path = root / f"input-bindings-v1.{name}.canonical.json"
            record = json.loads(path.read_bytes())
            self.assertEqual(canonical_input_bindings_bytes(record), path.read_bytes())
            verify_dataset_input_bindings(manifest, record)
        mutations = json.loads((root / "dataset-binding-mutations.json").read_text())
        for mutation in mutations:
            with self.subTest(mutation=mutation["id"]):
                name = mutation["fixture"]
                manifest = json.loads((root / f"dataset-manifest-v2.{name}.canonical.json").read_bytes())
                record = json.loads((root / f"input-bindings-v1.{name}.canonical.json").read_bytes())
                target = manifest if mutation["target"] == "manifest" else record
                target["bindings"][mutation["binding"]][mutation["field"]] = mutation["value"]
                with self.assertRaises(ParisonError):
                    verify_dataset_input_bindings(manifest, record)

    def test_malformed_selectors_and_utf8_have_controlled_errors(self):
        root = ROOT / "tests/fixtures/2.2"
        manifest = json.loads((root / "dataset-manifest-v2.json.canonical.json").read_bytes())
        manifest["bindings"][0]["source"] = "json:data/records.json#/bad~2escape"
        with self.assertRaises(ParisonError):
            normalize_dataset_manifest_v2(manifest)
        manifest = json.loads((root / "dataset-manifest-v2.partition.canonical.json").read_bytes())
        bad_name = "data/parts/" + chr(0xD800) + ".csv"
        manifest["files"][0]["path"] = bad_name
        for binding in manifest["bindings"]:
            binding["members"] = [bad_name]
        with self.assertRaises(ParisonError):
            normalize_dataset_manifest_v2(manifest)
        record = json.loads((root / "input-bindings-v1.xml.canonical.json").read_bytes())
        record["bindings"][0]["selection"]["namespaces"] = {"x": chr(0xD800)}
        with self.assertRaises(ParisonError):
            normalize_input_bindings(record)
