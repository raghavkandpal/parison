"""Contract tests for the optional one-table PostgreSQL reader."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from parison.analysis import _canonical
from parison.core import ParisonError
from parison.source_receipt import source_summary, validate_postgres_plan, verify_postgres_export


class PostgresIngress(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "bundle"
        self.root.mkdir()
        self.plan = {
            "plan_version": 1,
            "source_id": "source-a",
            "schema": "public",
            "table": "orders",
            "columns": ["id", "note"],
            "primary_key": ["id"],
            "limits": {
                "max_rows": 10,
                "max_output_bytes": 1000,
                "statement_timeout_ms": 1000,
                "wall_timeout_ms": 2000,
            },
        }

    def _bundle(self):
        data = b"id,note\r\n1,hello\r\n"
        (self.root / "data.csv").write_bytes(data)
        receipt = {
            "postgres_source_receipt_version": 1,
            "kind": "postgresql-table-export",
            "plan_sha256": hashlib.sha256(_canonical(self.plan)).hexdigest(),
            "source": {
                "source_id": "source-a",
                "database": "database-a",
                "schema": "public",
                "table": "orders",
                "columns": ["id", "note"],
                "primary_key": ["id"],
                "types": ["int4", "text"],
                "server_version_num": 180006,
                "role": "reader",
                "role_is_owner": False,
                "role_bypassrls": False,
                "role_superuser": False,
            },
            "transaction": {
                "isolation": "repeatable read",
                "read_only": True,
                "row_security": "off",
                "snapshot": "1:2:",
                "client_encoding": "UTF8",
                "date_style": "ISO, YMD",
                "time_zone": "UTC",
            },
            "selection": {
                "sql": 'SELECT "id", "note" FROM "public"."orders" ORDER BY "id"',
                "format": "csv-utf8-v1",
                "null_marker": "\\N",
                "null_marker_collision": False,
            },
            "limits": self.plan["limits"],
            "observed": {
                "server_rows": 1,
                "local_rows": 1,
                "output_bytes": len(data),
                "output_sha256": hashlib.sha256(data).hexdigest(),
                "elapsed_ms": 10,
                "complete": True,
            },
        }
        receipt_bytes = _canonical(receipt) + b"\n"
        (self.root / "receipt.json").write_bytes(receipt_bytes)
        summary = source_summary(receipt, receipt_bytes)
        summary_bytes = _canonical(summary) + b"\n"
        (self.root / "summary.json").write_bytes(summary_bytes)
        manifest = {
            "postgres_source_manifest_version": 1,
            "kind": "postgresql-table-export",
            "complete": True,
            "files": {
                "data.csv": hashlib.sha256(data).hexdigest(),
                "receipt.json": hashlib.sha256(receipt_bytes).hexdigest(),
                "summary.json": hashlib.sha256(summary_bytes).hexdigest(),
            },
        }
        (self.root / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
        return summary

    def test_offline_verified_summary(self):
        expected = self._bundle()
        self.assertEqual(verify_postgres_export(self.root), expected)
        self.assertEqual(
            set(expected),
            {
                "postgres_source_summary_version",
                "kind",
                "complete",
                "coverage_claim",
                "rows",
                "bytes",
                "output_sha256",
                "receipt_sha256",
            },
        )
        self.assertEqual(
            hashlib.sha256((self.root / "receipt.json").read_bytes()).hexdigest(),
            "ee5db838074ac91b10eede44859362b78fb6bdef4dd9acd7ab5735fcf200f520",
        )

    def test_tampered_data_fails(self):
        self._bundle()
        (self.root / "data.csv").write_bytes(b"id,note\r\n1,other\r\n")
        with self.assertRaises(ParisonError):
            verify_postgres_export(self.root)

    def test_symlink_fails(self):
        self._bundle()
        path = self.root / "data.csv"
        path.unlink()
        path.symlink_to("/etc/passwd")
        with self.assertRaises(ParisonError):
            verify_postgres_export(self.root)

    def test_plan_is_closed(self):
        self.assertEqual(validate_postgres_plan(self.plan), self.plan)
        with self.assertRaises(ParisonError):
            validate_postgres_plan({**self.plan, "dsn": "secret"})

    def test_forged_receipt_cannot_claim_truth(self):
        self._bundle()
        receipt_path = self.root / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["transaction"]["read_only"] = False
        receipt_path.write_bytes(_canonical(receipt) + b"\n")
        with self.assertRaises(ParisonError):
            verify_postgres_export(self.root)
