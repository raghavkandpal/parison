"""Canonical and hostile local tests for coordinated PostgreSQL evidence."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.analysis import _canonical
from parison.core import ParisonError, load_schema
from parison.source_pair import KIND, SLOTS, pair_summary, validate_postgres_pair_plan, verify_postgres_pair
from parison.source_receipt import selection_sql, source_summary

FIXTURES = Path(__file__).parent / "fixtures"


def _write_json(path: Path, value: dict) -> bytes:
    data = _canonical(value) + b"\n"
    path.write_bytes(data)
    return data


class PostgresPair(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "pair"
        self.root.mkdir()
        tables = self.root / "tables"
        tables.mkdir()
        for slot in SLOTS:
            shutil.copytree(FIXTURES / "postgres_ingress", tables / slot)
        self.plan = {
            "pair_plan_version": 1,
            "source_id": "source-a",
            "tables": {
                "orders": {"schema": "public", "table": "orders", "columns": ["id", "note"], "primary_key": ["id"]},
                "order_lines": {
                    "schema": "public",
                    "table": "order_lines",
                    "columns": ["id", "note"],
                    "primary_key": ["id"],
                },
            },
            "limits": {
                "max_rows": 10,
                "max_output_bytes": 1000,
                "statement_timeout_ms": 1000,
                "wall_timeout_ms": 2000,
            },
        }

    def _bundle(self):
        children = {}
        for slot in SLOTS:
            path = self.root / "tables" / slot
            receipt = json.loads((path / "receipt.json").read_text())
            table = self.plan["tables"][slot]
            receipt["source"]["table"] = table["table"]
            receipt["selection"]["sql"] = selection_sql(
                table["schema"], table["table"], table["columns"], table["primary_key"]
            )
            child_plan = {
                "plan_version": 1,
                "source_id": self.plan["source_id"],
                **table,
                "limits": self.plan["limits"],
            }
            receipt["plan_sha256"] = hashlib.sha256(_canonical(child_plan)).hexdigest()
            receipt_bytes = _write_json(path / "receipt.json", receipt)
            summary_bytes = _write_json(path / "summary.json", source_summary(receipt, receipt_bytes))
            manifest = json.loads((path / "manifest.json").read_text())
            manifest["files"]["receipt.json"] = hashlib.sha256(receipt_bytes).hexdigest()
            manifest["files"]["summary.json"] = hashlib.sha256(summary_bytes).hexdigest()
            manifest_bytes = _write_json(path / "manifest.json", manifest)
            children[slot] = (receipt, hashlib.sha256(manifest_bytes).hexdigest())
        first = children["orders"][0]
        pair_receipt = {
            "postgres_pair_receipt_version": 1,
            "kind": KIND,
            "pair_plan_sha256": hashlib.sha256(_canonical(self.plan)).hexdigest(),
            "source": {name: first["source"][name] for name in ("source_id", "database", "role", "server_version_num")},
            "transaction": {
                "isolation": "repeatable read",
                "read_only": True,
                "row_security": "off",
                "snapshot": first["transaction"]["snapshot"],
            },
            "table_manifests": {slot: children[slot][1] for slot in SLOTS},
            "limits": self.plan["limits"],
            "observed": {"rows": 2, "bytes": 36, "elapsed_ms": 10, "complete": True},
        }
        receipt_bytes = _write_json(self.root / "receipt.json", pair_receipt)
        summary = pair_summary(pair_receipt, receipt_bytes)
        summary_bytes = _write_json(self.root / "summary.json", summary)
        _write_json(
            self.root / "manifest.json",
            {
                "postgres_pair_manifest_version": 1,
                "kind": KIND,
                "complete": True,
                "files": {
                    "receipt.json": hashlib.sha256(receipt_bytes).hexdigest(),
                    "summary.json": hashlib.sha256(summary_bytes).hexdigest(),
                    **pair_receipt["table_manifests"],
                },
            },
        )
        return summary

    def test_canonical_pair(self):
        expected = self._bundle()
        self.assertEqual(verify_postgres_pair(self.root), expected)
        for name in ("receipt.json", "summary.json", "manifest.json"):
            self.assertEqual((self.root / name).read_bytes(), (FIXTURES / "postgres_pair" / name).read_bytes())
        self.assertEqual(_canonical(self.plan) + b"\n", (FIXTURES / "postgres_pair_plan.json").read_bytes())
        self.assertEqual(
            set(expected),
            {
                "postgres_pair_summary_version",
                "kind",
                "complete",
                "coverage_claim",
                "tables",
                "rows",
                "bytes",
                "receipt_sha256",
            },
        )

    def test_installed_pair_schemas(self):
        self._bundle()
        documents = {
            "postgres-pair-plan": self.plan,
            **{
                f"postgres-pair-{kind}": json.loads((self.root / f"{kind}.json").read_text())
                for kind in ("receipt", "summary", "manifest")
            },
        }
        for name, document in documents.items():
            with self.subTest(schema=name):
                schema = load_schema(name)
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(document)

    def test_missing_or_swapped_child_fails(self):
        self._bundle()
        shutil.rmtree(self.root / "tables" / "order_lines")
        with self.assertRaises(ParisonError):
            verify_postgres_pair(self.root)

    def test_child_substitution_fails(self):
        self._bundle()
        shutil.rmtree(self.root / "tables" / "order_lines")
        shutil.copytree(self.root / "tables" / "orders", self.root / "tables" / "order_lines")
        with self.assertRaises(ParisonError):
            verify_postgres_pair(self.root)

    def test_changed_snapshot_fails(self):
        self._bundle()
        path = self.root / "tables" / "order_lines" / "receipt.json"
        receipt = json.loads(path.read_text())
        receipt["transaction"]["snapshot"] = "later:4:"
        _write_json(path, receipt)
        with self.assertRaises(ParisonError):
            verify_postgres_pair(self.root)

    def test_bad_plan_fails(self):
        self.assertEqual(validate_postgres_pair_plan(self.plan), self.plan)
        duplicate = {**self.plan, "tables": {**self.plan["tables"], "order_lines": self.plan["tables"]["orders"]}}
        with self.assertRaises(ParisonError):
            validate_postgres_pair_plan(duplicate)
        with self.assertRaises(ParisonError):
            validate_postgres_pair_plan({**self.plan, "dsn": "secret"})

    def test_tampered_summary_fails(self):
        self._bundle()
        summary = json.loads((self.root / "summary.json").read_text())
        summary["source_id"] = "secret"
        _write_json(self.root / "summary.json", summary)
        with self.assertRaises(ParisonError):
            verify_postgres_pair(self.root)

    def test_symlinked_pair_file_fails(self):
        self._bundle()
        path = self.root / "receipt.json"
        path.unlink()
        path.symlink_to(FIXTURES / "postgres_pair" / "receipt.json")
        with self.assertRaises(ParisonError):
            verify_postgres_pair(self.root)

    def test_digest_valid_wrong_total_fails(self):
        self._bundle()
        receipt = json.loads((self.root / "receipt.json").read_text())
        receipt["observed"]["rows"] = 1
        receipt_bytes = _write_json(self.root / "receipt.json", receipt)
        summary_bytes = _write_json(self.root / "summary.json", pair_summary(receipt, receipt_bytes))
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["files"]["receipt.json"] = hashlib.sha256(receipt_bytes).hexdigest()
        manifest["files"]["summary.json"] = hashlib.sha256(summary_bytes).hexdigest()
        _write_json(self.root / "manifest.json", manifest)
        with self.assertRaises(ParisonError):
            verify_postgres_pair(self.root)


if __name__ == "__main__":
    unittest.main()
