"""Real local source checks, distinct from preserved-evidence verification."""

import copy
import hashlib
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError
from parison.manifesting import canonical_dataset_manifest_v2_bytes, verify_dataset_manifest_v2

ROOT = Path(__file__).parents[1]


class DatasetManifestV2Sources(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "parts").mkdir()
        self.member = self.root / "parts/a.csv"
        self.content = b"id,value\n1,10\n"
        self.member.write_bytes(self.content)
        self.policy = ROOT / "examples/1.3/reconciliation.json"
        policy_sha = json.loads((ROOT / "examples/1.4/payout-dataset-manifest.json").read_text())["policy"]["sha256"]
        digest = hashlib.sha256(self.content).hexdigest()
        source_digest = hashlib.sha256(b"a.csv\0" + bytes.fromhex(digest)).hexdigest()
        self.value = {
            "manifest_version": 2,
            "collection_id": "source-test",
            "policy": {"kind": "reconciliation", "sha256": policy_sha},
            "closed_scopes": [],
            "files": [{"path": "parts/a.csv", "bytes": len(self.content), "sha256": digest}],
            "bindings": [
                {
                    "id": "records",
                    "role": side,
                    "source_kind": "partition",
                    "source": "parts",
                    "members": ["parts/a.csv"],
                    "source_sha256": source_digest,
                    "policy_sha256": "c" * 64,
                }
                for side in ("baseline", "candidate")
            ],
        }
        self.manifest = self.root / "declaration.json"

    def verify(self, **kwargs):
        self.manifest.write_text(json.dumps(self.value), encoding="utf-8")
        return verify_dataset_manifest_v2(self.manifest, self.root, self.policy, **kwargs)

    def test_v2_cli_creation_explanation_and_source_verification(self):
        self.manifest.write_text(json.dumps(self.value), encoding="utf-8")
        output = self.root / "created.json"
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(
                main(
                    [
                        "create-dataset-manifest",
                        "--manifest-version",
                        "2",
                        "--declaration",
                        str(self.manifest),
                        "--root",
                        str(self.root),
                        "--policy-file",
                        str(self.policy),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
        self.assertEqual(output.read_bytes(), canonical_dataset_manifest_v2_bytes(self.value))
        for command in (
            ["validate-dataset-manifest", str(output)],
            ["explain-dataset-manifest", str(output)],
            [
                "verify-dataset-manifest",
                "--manifest",
                str(output),
                "--root",
                str(self.root),
                "--policy-file",
                str(self.policy),
                "--summary",
            ],
        ):
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(command), 0)

    def test_pass_result_schema_and_summary_disclosure(self):
        result = self.verify()
        self.assertEqual(result["outcome"], "PASS")
        schema = json.loads((ROOT / "src/parison/schemas/manifest-result-v2.schema.json").read_text())
        Draft202012Validator(schema).validate(result)
        summary = self.verify(summary=True)
        self.assertEqual(summary["file_count"], 1)
        self.assertEqual(summary["binding_count"], 2)
        self.assertNotIn("parts", json.dumps(summary))
        self.assertNotIn("records", json.dumps(summary))
        self.assertIsNone(result["semantic_result"])

    def test_partition_membership_and_closed_scope_are_distinct(self):
        hidden = self.root / "parts/.hidden.csv"
        hidden.write_bytes(b"not selected")
        self.assertEqual(self.verify()["outcome"], "PASS")
        self.value["closed_scopes"] = ["parts"]
        self.assertEqual(self.verify()["reason_codes"], ["undeclared-members"])
        self.value["closed_scopes"] = []
        (self.root / "parts/b.csv").write_bytes(self.content)
        self.assertEqual(self.verify()["reason_codes"], ["logical-member-mismatch"])

    def test_changed_missing_sources_and_limits(self):
        self.member.write_bytes(self.content.replace(b"10", b"11"))
        self.assertEqual(self.verify()["reason_codes"], ["digest-mismatch", "logical-member-mismatch"])
        self.member.write_bytes(self.content + b"2,20\n")
        self.assertEqual(self.verify()["reason_codes"], ["logical-member-mismatch", "size-mismatch"])
        with self.assertRaisesRegex(ParisonError, "byte limit"):
            self.verify(max_input_bytes=1)
        with self.assertRaisesRegex(ParisonError, "byte limit"):
            self.verify(max_input_bytes=len(self.content))
        self.member.unlink()
        result = self.verify()
        self.assertEqual(result["reason_codes"], ["logical-member-mismatch", "missing-resource"])
        self.assertIsNone(result["files"][0]["observed_sha256"])
        (self.root / "parts").rmdir()
        self.assertEqual(self.verify()["outcome"], "FAIL")
        self.value["closed_scopes"] = ["parts"]
        self.assertEqual(self.verify()["reason_codes"], ["logical-member-mismatch", "missing-resource"])

    def test_symlinks_aliases_and_nested_partition_objects_are_errors(self):
        nested = self.root / "parts/nested"
        nested.mkdir()
        with self.assertRaises(ParisonError):
            self.verify()
        nested.rmdir()
        alias = self.root / "alias.csv"
        os.link(self.member, alias)
        extra = copy.deepcopy(self.value["files"][0])
        extra["path"] = "alias.csv"
        self.value["files"].append(extra)
        with self.assertRaisesRegex(ParisonError, "aliases"):
            self.verify()
        self.value["files"].pop()
        self.member.unlink()
        try:
            self.member.symlink_to(alias)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaises(ParisonError):
            self.verify()

    def test_membership_changes_during_verification_abort(self):
        from parison import manifesting

        original = manifesting._identity

        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            (self.root / "parts/b.csv").write_bytes(self.content)
            return result

        with (
            patch.object(manifesting, "_identity", side_effect=changed),
            self.assertRaisesRegex(ParisonError, "changed"),
        ):
            self.verify()

    def test_shared_workbook_inventory_is_hashed_once_for_distinct_selections(self):
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.active.append(["id", "value"])
        workbook.active.append(["1", 10])
        workbook.active.append(["2", 20])
        path = self.root / "shared.xlsx"
        workbook.save(path)
        workbook.close()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.value["files"] = [{"path": "shared.xlsx", "bytes": path.stat().st_size, "sha256": digest}]
        self.value["bindings"] = [
            {
                "id": name,
                "role": side,
                "source_kind": "file",
                "source": f"xlsx:shared.xlsx#Sheet!{selection}",
                "members": ["shared.xlsx"],
                "source_sha256": digest,
                "policy_sha256": "c" * 64,
            }
            for name, selection in (("first", "A1:B2"), ("second", "A1:B3"))
            for side in ("baseline", "candidate")
        ]
        result = self.verify()
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(len(result["bindings"]), 4)
