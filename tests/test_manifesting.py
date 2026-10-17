import copy
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, load_schema
from parison.manifesting import (
    canonical_dataset_manifest_bytes,
    canonical_reproducibility_diagnostic_bytes,
    capture_reproducibility_diagnostic,
    create_dataset_manifest,
    diff_reproducibility_diagnostics,
    explain_dataset_manifest,
    normalize_dataset_manifest,
    verify_dataset_manifest,
)

ROOT = Path(__file__).parents[1]


class DatasetManifest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "baseline").mkdir()
        (self.root / "candidate").mkdir()
        (self.root / "baseline/orders.csv").write_text("id,value\n1,10\n", encoding="utf-8")
        (self.root / "candidate/orders.jsonl").write_text('{"id":"1","value":10}\n', encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.policy_path = ROOT / "examples/1.3/reconciliation.json"
        self.policy_sha256 = json.loads(
            (ROOT / "examples/1.4/payout-dataset-manifest.json").read_text(encoding="utf-8")
        )["policy"]["sha256"]
        self.resources = [
            ("orders", "candidate", "jsonl", "candidate/orders.jsonl"),
            ("orders", "baseline", "csv", "baseline/orders.csv"),
        ]

    def tearDown(self):
        self.temporary.cleanup()

    def create(self):
        return create_dataset_manifest(
            self.root,
            "orders-backfill",
            "reconciliation",
            self.policy_sha256,
            self.resources,
            self.manifest,
            self.policy_path,
        )

    def test_installed_schemas_are_valid(self):
        for name in ("dataset-manifest", "reproducibility-diagnostic"):
            Draft202012Validator.check_schema(load_schema(name))

    def test_canonical_byte_fixtures_are_pinned(self):
        manifest = {
            "manifest_version": 1,
            "collection_id": "fixture",
            "policy": {"kind": "suite", "sha256": "a" * 64},
            "closed_scopes": [],
            "resources": [
                {
                    "id": "orders",
                    "role": "baseline",
                    "format": "csv",
                    "path": "baseline/orders.csv",
                    "bytes": 4,
                    "sha256": "b" * 64,
                }
            ],
        }
        diagnostic = {
            "diagnostic_version": 1,
            "manifest_sha256": "c" * 64,
            "runtime": {
                "parison_version": "1.4.0",
                "python_implementation": "cpython",
                "python_version": "3.14.0",
                "os_family": "linux",
                "architecture": "x86_64",
                "sqlite_version": "3.50.4",
                "parquet_reader": None,
            },
            "observations": [],
        }
        self.assertEqual(
            canonical_dataset_manifest_bytes(manifest),
            (ROOT / "tests/fixtures/dataset-manifest-v1.canonical.json").read_bytes().removesuffix(b"\n"),
        )
        self.assertEqual(
            canonical_reproducibility_diagnostic_bytes(diagnostic),
            (ROOT / "tests/fixtures/reproducibility-diagnostic-v1.canonical.json").read_bytes().removesuffix(b"\n"),
        )

    def test_creation_is_canonical_atomic_and_verifiable(self):
        created = self.create()
        Draft202012Validator(load_schema("dataset-manifest")).validate(
            {key: created[key] for key in ("manifest_version", "collection_id", "policy", "closed_scopes", "resources")}
        )
        self.assertEqual([item["role"] for item in created["resources"]], ["baseline", "candidate"])
        explained = explain_dataset_manifest(self.manifest)
        self.assertEqual(created, explained)
        self.assertEqual(verify_dataset_manifest(self.manifest, self.root, self.policy_path)["outcome"], "PASS")
        with self.assertRaisesRegex(ParisonError, "already exists"):
            self.create()
        reordered = json.loads(self.manifest.read_text(encoding="utf-8"))
        reordered["resources"].reverse()
        authored = {
            key: created[key] for key in ("manifest_version", "collection_id", "policy", "closed_scopes", "resources")
        }
        self.assertEqual(canonical_dataset_manifest_bytes(reordered), canonical_dataset_manifest_bytes(authored))

    def test_verification_reports_missing_size_and_digest_without_path_leakage(self):
        self.create()
        candidate = self.root / "candidate/orders.jsonl"
        candidate.write_text('{"id":"1","value":11}\n', encoding="utf-8")
        result = verify_dataset_manifest(self.manifest, self.root, self.policy_path, summary=True)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["reason_codes"], ["resource-digest-mismatch"])
        self.assertNotIn("orders", json.dumps(result))
        candidate.write_text("larger\n", encoding="utf-8")
        self.assertEqual(
            verify_dataset_manifest(self.manifest, self.root, self.policy_path)["reason_codes"],
            ["resource-size-mismatch"],
        )
        candidate.unlink()
        self.assertEqual(
            verify_dataset_manifest(self.manifest, self.root, self.policy_path)["reason_codes"], ["resource-missing"]
        )

    def test_reviewed_closed_scope_detects_every_undeclared_file(self):
        create_dataset_manifest(
            self.root,
            "closed",
            "reconciliation",
            self.policy_sha256,
            [("orders", "baseline", "csv", "baseline/orders.csv")],
            self.manifest,
            self.policy_path,
            ["baseline"],
        )
        (self.root / "baseline/extra.csv").write_text("id,value\n2,20\n", encoding="utf-8")
        result = verify_dataset_manifest(self.manifest, self.root, self.policy_path, summary=True)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["counts"]["undeclared"], 1)
        self.assertEqual(result["reason_codes"], ["resource-undeclared"])
        self.assertNotIn("extra.csv", json.dumps(result))
        with self.assertRaisesRegex(ParisonError, "undeclared resources"):
            create_dataset_manifest(
                self.root,
                "closed",
                "reconciliation",
                self.policy_sha256,
                [("orders", "baseline", "csv", "baseline/orders.csv")],
                self.root / "other.json",
                self.policy_path,
                ["baseline"],
            )

    def test_paths_symlinks_aliases_and_sqlite_sidecars_fail_closed(self):
        value = {
            "manifest_version": 1,
            "collection_id": "x",
            "policy": {"kind": "suite", "sha256": "a" * 64},
            "closed_scopes": [],
            "resources": [],
        }
        for path in ("../x.csv", "/x.csv", "a\\b.csv", "C:/x.csv", "a/./b.csv"):
            invalid = copy.deepcopy(value)
            invalid["resources"] = [
                {"id": "x", "role": "baseline", "format": "csv", "path": path, "bytes": 0, "sha256": "b" * 64}
            ]
            with self.subTest(path=path), self.assertRaises(ParisonError):
                normalize_dataset_manifest(invalid)
        linked = self.root / "linked.csv"
        linked.symlink_to(self.root / "baseline/orders.csv")
        with self.assertRaises(ParisonError):
            create_dataset_manifest(
                self.root,
                "x",
                "reconciliation",
                self.policy_sha256,
                [("x", "baseline", "csv", "linked.csv")],
                self.root / "linked.json",
                self.policy_path,
            )
        alias = self.root / "alias.csv"
        os.link(self.root / "baseline/orders.csv", alias)
        with self.assertRaisesRegex(ParisonError, "hard-link"):
            create_dataset_manifest(
                self.root,
                "x",
                "reconciliation",
                self.policy_sha256,
                [("x", "baseline", "csv", "baseline/orders.csv"), ("y", "supporting", "csv", "alias.csv")],
                self.root / "alias.json",
                self.policy_path,
            )
        database = self.root / "data.sqlite"
        database.write_bytes(b"fixture")
        Path(str(database) + "-wal").write_bytes(b"wal")
        with self.assertRaisesRegex(ParisonError, "journal"):
            create_dataset_manifest(
                self.root,
                "x",
                "reconciliation",
                self.policy_sha256,
                [("db", "baseline", "sqlite", "data.sqlite")],
                self.root / "sqlite.json",
                self.policy_path,
            )
        for suffix in ("-wal", "-journal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
        database.unlink()
        connection = sqlite3.connect(database)
        connection.execute("create table rows (id integer primary key, value text)")
        connection.execute("insert into rows values (1, 'stable')")
        connection.commit()
        connection.close()
        created = create_dataset_manifest(
            self.root,
            "sqlite",
            "reconciliation",
            self.policy_sha256,
            [("db", "baseline", "sqlite", "data.sqlite")],
            self.root / "quiescent.json",
            self.policy_path,
        )
        self.assertEqual(created["resources"][0]["format"], "sqlite")

    @unittest.skipUnless(
        os.open in os.supports_dir_fd and getattr(os, "O_NOFOLLOW", 0), "descriptor-relative traversal is POSIX-only"
    )
    def test_parent_replacement_cannot_redirect_an_opened_resource(self):
        original = self.root / "baseline/orders.csv"
        expected = __import__("hashlib").sha256(original.read_bytes()).hexdigest()
        replacement = self.root / "replacement"
        replacement.mkdir()
        (replacement / "orders.csv").write_text("id,value\n1,999\n", encoding="utf-8")
        real_open, replaced = os.open, False

        def racing_open(path, flags, *args, **kwargs):
            nonlocal replaced
            if path == "orders.csv" and kwargs.get("dir_fd") is not None and not replaced:
                (self.root / "baseline").rename(self.root / "baseline-original")
                (self.root / "baseline").symlink_to(replacement, target_is_directory=True)
                replaced = True
            return real_open(path, flags, *args, **kwargs)

        with patch("parison.manifesting.os.open", side_effect=racing_open):
            created = create_dataset_manifest(
                self.root,
                "race",
                "reconciliation",
                self.policy_sha256,
                [("orders", "baseline", "csv", "baseline/orders.csv")],
                self.manifest,
                self.policy_path,
            )
        self.assertEqual(created["resources"][0]["sha256"], expected)

    def test_descriptor_mutation_is_a_controlled_error(self):
        root_stat = self.root.stat()
        before = (self.root / "baseline/orders.csv").stat()
        after = SimpleNamespace(
            st_dev=before.st_dev,
            st_ino=before.st_ino,
            st_size=before.st_size,
            st_mtime_ns=before.st_mtime_ns + 1,
            st_mode=before.st_mode,
        )
        with patch("parison.manifesting.os.fstat", side_effect=[root_stat, before, after]):
            with self.assertRaisesRegex(ParisonError, "resource-changed-during-read"):
                create_dataset_manifest(
                    self.root,
                    "mutation",
                    "reconciliation",
                    self.policy_sha256,
                    [("orders", "baseline", "csv", "baseline/orders.csv")],
                    self.manifest,
                    self.policy_path,
                )

    def test_diagnostics_are_separate_deterministic_and_informational(self):
        created = self.create()
        left, right = self.root / "left.json", self.root / "right.json"
        first = capture_reproducibility_diagnostic(self.manifest, left)
        second = capture_reproducibility_diagnostic(self.manifest, right)
        Draft202012Validator(load_schema("reproducibility-diagnostic")).validate(
            {key: first[key] for key in ("diagnostic_version", "manifest_sha256", "runtime", "observations")}
        )
        self.assertEqual(first, second)
        value = json.loads(right.read_text(encoding="utf-8"))
        value["runtime"]["python_version"] = "9.9.9"
        right.write_text(json.dumps(value), encoding="utf-8")
        result = diff_reproducibility_diagnostics(left, right)
        self.assertEqual(result["outcome"], "INFORMATIONAL")
        self.assertEqual(
            next(item for item in result["fields"] if item["field"] == "python_version")["status"], "different"
        )
        value["manifest_sha256"] = "f" * 64
        right.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "different manifests"):
            diff_reproducibility_diagnostics(left, right)
        self.assertEqual(created["manifest_sha256"], first["manifest_sha256"])
        value["manifest_sha256"] = first["manifest_sha256"]
        value["observations"] = ["unknown-observation"]
        right.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "observations"):
            diff_reproducibility_diagnostics(left, right)

    def test_cli_end_to_end(self):
        arguments = [
            "create-dataset-manifest",
            "--root",
            str(self.root),
            "--collection-id",
            "orders",
            "--policy-kind",
            "reconciliation",
            "--policy-sha256",
            self.policy_sha256,
            "--policy-file",
            str(self.policy_path),
        ]
        for resource in self.resources:
            arguments.extend(["--resource", *resource])
        arguments.extend(["--output", str(self.manifest)])
        with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
            self.assertEqual(main(arguments), 0)
            self.assertIn("manifest_sha256", json.loads(stdout.getvalue()))
        with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
            self.assertEqual(
                main(
                    [
                        "verify-dataset-manifest",
                        "--manifest",
                        str(self.manifest),
                        "--root",
                        str(self.root),
                        "--policy-file",
                        str(self.policy_path),
                        "--summary",
                    ]
                ),
                0,
            )
            self.assertEqual(json.loads(stdout.getvalue())["outcome"], "PASS")


if __name__ == "__main__":
    unittest.main()
