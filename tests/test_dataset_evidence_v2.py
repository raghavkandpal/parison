"""Complete local dataset v2 publication from fresh semantic execution."""

import hashlib
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, inspect_bundle, load_schema, load_suite, run_suite, verify_bundle
from parison.manifesting import (
    canonical_dataset_manifest_v2_bytes,
    create_dataset_manifest_v2,
    publish_dataset_evidence_bundle_v2,
)

ROOT = Path(__file__).parents[1]


class DatasetEvidenceV2(unittest.TestCase):
    def test_complete_suite_publication_and_source_free_verification(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            example = ROOT / "examples/0.15"
            for name in (
                "payout-suite.json",
                "payout-aggregate.recipe.json",
                "payout-keyed.recipe.json",
                "processor.csv",
                "ledger.csv",
            ):
                shutil.copy2(example / name, root / name)
            plan = root / "payout-suite.json"
            suite = load_suite(plan)
            child = root / "suite-run"
            run_suite(plan, child, input_bindings=True)
            inventory = []
            for name in ("processor.csv", "ledger.csv"):
                content = (root / name).read_bytes()
                inventory.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
            bindings = []
            for case in suite["cases"]:
                for role, name in (("baseline", "processor.csv"), ("candidate", "ledger.csv")):
                    bindings.append(
                        {
                            "id": case["id"],
                            "role": role,
                            "source_kind": "file",
                            "source": name,
                            "members": [name],
                            "source_sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                            "policy_sha256": case["policy_sha256"],
                        }
                    )
            declaration = {
                "manifest_version": 2,
                "collection_id": "payouts",
                "policy": {"kind": "suite", "sha256": suite["suite_policy_sha256"]},
                "closed_scopes": [],
                "files": inventory,
                "bindings": bindings,
            }
            draft = root / "draft.json"
            draft.write_text(json.dumps(declaration), encoding="utf-8")
            manifest_path = root / "dataset-manifest.json"
            create_dataset_manifest_v2(root, draft, manifest_path, plan)
            self.assertEqual(manifest_path.read_bytes(), canonical_dataset_manifest_v2_bytes(declaration))
            output = root / "dataset-evidence"
            publish_dataset_evidence_bundle_v2(output, manifest_path, root, plan, child)
            cli_output = root / "dataset-evidence-cli"
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "publish-dataset-evidence",
                            "--output",
                            str(cli_output),
                            "--manifest",
                            str(manifest_path),
                            "--root",
                            str(root),
                            "--policy-file",
                            str(plan),
                            "--result-bundle",
                            str(child),
                        ]
                    ),
                    0,
                )
            self.assertEqual(verify_bundle(cli_output)["schema_version"], 2)
            outer = verify_bundle(output)
            self.assertEqual(outer["schema_version"], 2)
            Draft202012Validator(load_schema("dataset-evidence-v2")).validate(outer)
            Draft202012Validator(load_schema("manifest-result-v2")).validate(
                json.loads((output / "manifest-result.json").read_text())
            )
            safe = inspect_bundle(output)
            self.assertEqual(safe["file_count"], 2)
            self.assertEqual(safe["binding_count"], 4)
            for secret in ("processor.csv", "ledger.csv", "category-conservation", str(root)):
                self.assertNotIn(secret, json.dumps(safe))
            for name in ("processor.csv", "ledger.csv", "payout-suite.json"):
                (root / name).unlink()
            self.assertEqual(verify_bundle(output)["schema_version"], 2)
            member = output / "manifest-result.json"
            forged_result = json.loads(member.read_text())
            forged_result["files"][0]["expected_bytes"] = float(forged_result["files"][0]["expected_bytes"])
            member.write_text(json.dumps(forged_result), encoding="utf-8")
            manifest_file = output / "manifest.json"
            forged_outer = json.loads(manifest_file.read_text())
            forged_outer["files"]["manifest-result.json"] = hashlib.sha256(member.read_bytes()).hexdigest()
            manifest_file.write_text(json.dumps(forged_outer), encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "file observation differs from inventory"):
                verify_bundle(output)


if __name__ == "__main__":
    unittest.main()
