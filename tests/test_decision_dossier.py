"""Portable dossier replay, canonical bytes and hostile input checks."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.analysis import _canonical
from parison.core import ParisonError, load_schema
from parison.decision_dossier import create, main, validate_plan, verify
from parison.workbench import workbench_projection

FIXTURES = Path(__file__).parent / "fixtures" / "postgres_rehearsal"
EXPECTED = Path(__file__).parent / "fixtures" / "decision_dossier" / "expected"


def save(path, value):
    path.write_bytes(_canonical(value) + b"\n")


class Dossier(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ("baseline", "candidate", "rehearsal"):
            shutil.copytree(FIXTURES / ("expected" if name == "rehearsal" else name), self.root / name)
        for name in ("orders.json", "order_lines.json", "relationships.json", "claim.txt"):
            shutil.copyfile(FIXTURES / name, self.root / name)
        self.plan = {
            "dossier_plan_version": 1,
            "rehearsal_manifest_sha256": hashlib.sha256(
                (self.root / "rehearsal" / "manifest.json").read_bytes()
            ).hexdigest(),
            "investigations": {"orders": None, "order_lines": None},
            "exceptions": [{"id": "review-1", "reference_sha256": "a" * 64, "disposition": "open"}],
            "signoffs": [{"role": "migration-owner", "reference_sha256": "b" * 64}],
        }
        self.args = {
            "plan_path": self.root / "plan.json",
            "rehearsal": self.root / "rehearsal",
            "baseline": self.root / "baseline",
            "candidate": self.root / "candidate",
            "orders_recipe": self.root / "orders.json",
            "lines_recipe": self.root / "order_lines.json",
            "relationships": self.root / "relationships.json",
            "claim": self.root / "claim.txt",
            "output": self.root / "dossier",
        }

    def publish(self):
        save(self.root / "plan.json", self.plan)
        return create(**self.args)

    def test_portable_golden_and_workbench(self):
        summary = self.publish()
        self.assertEqual(summary["outcome"], "PASS")
        self.assertEqual(summary["authorization"], "external-required")
        for name in ("baseline", "candidate", "rehearsal"):
            shutil.rmtree(self.root / name)
        for name in ("orders.json", "order_lines.json", "relationships.json", "claim.txt"):
            (self.root / name).unlink()
        self.assertEqual(verify(self.root / "dossier"), summary)
        self.assertEqual(workbench_projection(self.root / "dossier"), summary)
        for file in EXPECTED.rglob("*"):
            if file.is_file():
                self.assertEqual(file.read_bytes(), (self.root / "dossier" / file.relative_to(EXPECTED)).read_bytes())
        self.assertEqual(len([p for p in EXPECTED.rglob("*") if p.is_file()]), 42)

    def test_open_reference_never_changes_outcome(self):
        self.plan["exceptions"].append({"id": "review-2", "reference_sha256": "c" * 64, "disposition": "accepted"})
        self.plan["signoffs"].append({"role": "security", "reference_sha256": "d" * 64})
        result = self.publish()
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["open_exception_count"], 1)
        self.assertEqual(result["signoff_count"], 2)
        self.assertEqual(result["authorization"], "external-required")

    def test_tamper_and_digest_valid_forgery(self):
        self.publish()
        receipt_path = self.root / "dossier" / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["outcome"] = "FAIL"
        save(receipt_path, receipt)
        summary_path = self.root / "dossier" / "summary.json"
        summary = json.loads(summary_path.read_text())
        summary["outcome"] = "FAIL"
        save(summary_path, summary)
        manifest_path = self.root / "dossier" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for name in ("receipt.json", "summary.json"):
            manifest["files"][name] = hashlib.sha256((self.root / "dossier" / name).read_bytes()).hexdigest()
        save(manifest_path, manifest)
        with self.assertRaises(ParisonError):
            verify(self.root / "dossier")

    def test_missing_member_symlink_and_collision(self):
        self.publish()
        with self.assertRaises(ParisonError):
            self.publish()
        member = self.root / "dossier" / "members" / "orders-recipe.json"
        member.unlink()
        with self.assertRaises(ParisonError):
            verify(self.root / "dossier")
        member.symlink_to(self.root / "orders.json")
        with self.assertRaises(ParisonError):
            verify(self.root / "dossier")

    def test_invalid_plan_and_schemas(self):
        self.publish()
        for name in ("plan", "receipt", "summary", "manifest"):
            schema = load_schema(f"dossier-{name}")
            value = json.loads((self.root / "dossier" / f"{name}.json").read_text())
            Draft202012Validator(schema).validate(value)
            value["extra"] = True
            self.assertFalse(Draft202012Validator(schema).is_valid(value))
        for plan in (
            None,
            {},
            {**self.plan, "dossier_plan_version": True},
            {**self.plan, "signoffs": self.plan["signoffs"] * 17},
            {**self.plan, "exceptions": self.plan["exceptions"] * 2},
        ):
            with self.assertRaises(ParisonError):
                validate_plan(plan)

    def test_interruption_cleans_stage_and_cli_is_safe(self):
        with patch("parison.decision_dossier._replay", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.publish()
        self.assertFalse((self.root / "dossier").exists())
        self.assertFalse(list(self.root.glob(".dossier-*")))
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(["create", "--secret", "RAW-CREDENTIAL-MARKER"])
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn("RAW-CREDENTIAL", stderr.getvalue())

    def test_unestablished_coordination_stays_inconclusive(self):
        from parison.postgres_rehearsal import run as rehearse

        plan = json.loads((self.root / "rehearsal" / "plan.json").read_text())
        plan["coordination"] = {"mode": "unestablished", "claim_sha256": None}
        shutil.rmtree(self.root / "rehearsal")
        (self.root / "claim.txt").unlink()
        save(self.root / "rehearsal-plan.json", plan)
        rehearse(
            self.root / "rehearsal-plan.json",
            self.root / "baseline",
            self.root / "candidate",
            self.root / "orders.json",
            self.root / "order_lines.json",
            self.root / "relationships.json",
            self.root / "rehearsal",
        )
        self.plan["rehearsal_manifest_sha256"] = hashlib.sha256(
            (self.root / "rehearsal" / "manifest.json").read_bytes()
        ).hexdigest()
        self.args["claim"] = None
        result = self.publish()
        self.assertEqual(result["outcome"], "INCONCLUSIVE")
        self.assertEqual(result["authorization"], "external-required")

    def test_failed_rehearsal_and_selected_investigation(self):
        from parison.partition_investigation import investigate
        from parison.postgres_rehearsal import run as rehearse
        from tests.test_postgres_rehearsal import pair

        shutil.rmtree(self.root / "candidate")
        candidate = pair(self.root / "candidate", 18, lines="1,1,11.00\n2,2,20.00\n")
        rehearsal_plan = json.loads((self.root / "rehearsal" / "plan.json").read_text())
        rehearsal_plan["pairs"]["candidate"] = candidate
        shutil.rmtree(self.root / "rehearsal")
        save(self.root / "rehearsal-plan.json", rehearsal_plan)
        result = rehearse(
            self.root / "rehearsal-plan.json",
            self.root / "baseline",
            self.root / "candidate",
            self.root / "orders.json",
            self.root / "order_lines.json",
            self.root / "relationships.json",
            self.root / "rehearsal",
            self.root / "claim.txt",
        )
        self.assertEqual(result["outcome"], "FAIL")
        self.plan["rehearsal_manifest_sha256"] = hashlib.sha256(
            (self.root / "rehearsal" / "manifest.json").read_bytes()
        ).hexdigest()
        discovery = self.root / "rehearsal" / "discovery" / "order_lines"
        investigation_plan = {
            "investigation_plan_version": 1,
            "discovery_manifest_sha256": hashlib.sha256((discovery / "manifest.json").read_bytes()).hexdigest(),
            "partition_indices": [0],
            "limits": {
                "max_cases_total": 10,
                "max_cases_per_partition": 10,
                "max_staged_bytes": 10000,
                "max_output_bytes": 10000,
            },
        }
        save(self.root / "investigation-plan.json", investigation_plan)
        investigation = self.root / "investigation"
        investigate(
            self.root / "investigation-plan.json",
            discovery,
            self.root / "order_lines.json",
            self.root / "baseline" / "tables" / "order_lines" / "data.csv",
            self.root / "candidate" / "tables" / "order_lines" / "data.csv",
            investigation,
        )
        self.plan["investigations"]["order_lines"] = hashlib.sha256(
            (investigation / "manifest.json").read_bytes()
        ).hexdigest()
        self.args["lines_investigation"] = investigation
        summary = self.publish()
        self.assertEqual(summary["outcome"], "FAIL")
        shutil.rmtree(self.root / "baseline")
        shutil.rmtree(self.root / "candidate")
        shutil.rmtree(self.root / "rehearsal")
        shutil.rmtree(investigation)
        self.assertEqual(verify(self.root / "dossier"), summary)
        item = self.root / "dossier" / "members" / "investigations" / "order_lines" / "cases.json"
        item.write_bytes(item.read_bytes().replace(b"11.00", b"12.00"))
        with self.assertRaises(ParisonError):
            verify(self.root / "dossier")

    def test_duplicate_json_and_nonfinite_rejected(self):
        self.publish()
        plan = self.root / "dossier" / "plan.json"
        plan.write_text('{"dossier_plan_version":1,"dossier_plan_version":1}\n')
        with self.assertRaises(ParisonError):
            verify(self.root / "dossier")
        plan.write_text('{"dossier_plan_version":NaN}\n')
        with self.assertRaises(ParisonError):
            verify(self.root / "dossier")

    def test_cli_and_workbench_share_exact_summary(self):
        from parison.cli import main as parison_main

        summary = self.publish()
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = parison_main(["dossier", "verify", str(self.root / "dossier")])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), summary)
        self.assertEqual(workbench_projection(self.root / "dossier"), summary)

    def test_workbench_results_route_returns_cli_summary(self):
        import http.client
        import threading

        from parison.workbench_host import create_workbench_server
        from tests.test_workbench_host import WorkbenchHostTests

        summary = self.publish()
        server, _ = create_workbench_server(self.root, "test-capability")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(*server.server_address)
        try:
            response = WorkbenchHostTests()._post(connection, server, "/api/evidence", {"bundle": "dossier"})
            self.assertEqual(response.status, 200)
            payload = response.read()
            self.assertEqual(json.loads(payload), summary)
            for private in (b"review-1", b"migration-owner", b"order_lines", b"claim.txt"):
                self.assertNotIn(private, payload)
        finally:
            connection.close()
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_output_inside_source_rejected_before_staging(self):
        self.args["output"] = self.root / "baseline" / "nested" / "dossier"
        save(self.root / "plan.json", self.plan)
        with self.assertRaises(ParisonError):
            create(**self.args)
        self.assertFalse((self.root / "baseline" / "nested").exists())

    def test_empty_directory_bomb_is_bounded(self):
        from parison.decision_dossier import _tree

        bomb = self.root / "bomb"
        bomb.mkdir()
        for number in range(257):
            (bomb / str(number)).mkdir()
        with self.assertRaises(ParisonError):
            _tree(bomb)

    def test_symlinked_recipe_parent_rejected(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        self.args["orders_recipe"] = alias / "orders.json"
        with self.assertRaises(ParisonError):
            self.publish()
        self.assertFalse((self.root / "dossier").exists())

    def test_manifest_schema_rejects_traversal(self):
        schema = load_schema("dossier-manifest")
        malicious = {"dossier_manifest_version": 1, "files": {"members/../../etc": "0" * 64}}
        self.assertFalse(Draft202012Validator(schema).is_valid(malicious))

    @unittest.skipUnless(hasattr(__import__("os"), "mkfifo"), "FIFO unavailable")
    def test_fifo_member_fails_without_blocking(self):
        import os

        from parison.decision_dossier import _tree

        fifo = self.root / "fifo-root"
        fifo.mkdir()
        os.mkfifo(fifo / "untrusted")
        with self.assertRaises(ParisonError):
            _tree(fifo)
