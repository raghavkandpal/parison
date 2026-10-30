"""Acquisition orchestration and fail-closed publication without a server."""

import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from parison import cli
from parison import postgres_collection as collection
from parison.core import ParisonError
from parison.source_collection import verify_postgres_collection

FIXTURE = Path(__file__).parent / "fixtures/postgres_collection"


class DriverError(Exception):
    pass


class Connection:
    def __init__(self):
        self.statements = []
        self.fail_commit = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self

    def execute(self, statement, *args):
        self.statements.append(statement)
        if statement == "COMMIT" and self.fail_commit:
            raise DriverError("private server error")

    def cancel(self):
        pass


class CollectionAcquisition(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = json.loads((FIXTURE / "plan.json").read_text())
        self.plan_path = self.root / "plan.json"
        self.plan_path.write_text(json.dumps(self.plan))
        self.output = self.root / "output"
        self.conn = Connection()
        self.actual_qualify = collection._qualify_table
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            patch.dict(sys.modules, {"psycopg": SimpleNamespace(connect=lambda *a, **k: self.conn, Error=DriverError)})
        )
        self.stack.enter_context(patch.object(collection, "_qualify_table", side_effect=self.qualify))
        self.stack.enter_context(patch.object(collection, "_acquire_table", side_effect=self.acquire))

    def qualify(self, cursor, plan):
        source = json.loads((FIXTURE / "expected/tables/orders/receipt.json").read_text())["source"]
        source.update({name: plan[name] for name in ("schema", "table", "columns", "primary_key")})
        return source, "1:2:"

    def acquire(self, cursor, plan, stage, started, rows, size):
        if rows < 1 or size < 18:
            raise ParisonError("budget")
        shutil.copyfile(FIXTURE / "expected/tables/orders/data.csv", stage / "data.csv")
        source, snapshot = self.qualify(cursor, plan)
        import hashlib

        from parison.source_receipt import selection_sql

        return {
            "source": source,
            "snapshot": snapshot,
            "selection": selection_sql(plan["schema"], plan["table"], plan["columns"], plan["primary_key"], only=True),
            "server_rows": 1,
            "local_rows": 1,
            "size": 18,
            "digest": hashlib.sha256((stage / "data.csv").read_bytes()).hexdigest(),
        }

    def test_snapshot_order_and_atomic_complete_output(self):
        summary = collection.export_postgres_collection(self.plan_path, self.output)
        self.assertEqual(summary, verify_postgres_collection(self.output))
        self.assertEqual(summary["rows"], 2)
        locks = [s for s in self.conn.statements if s.startswith("LOCK TABLE")]
        self.assertEqual(
            locks,
            [
                'LOCK TABLE "public"."order_lines" IN ACCESS SHARE MODE',
                'LOCK TABLE "public"."orders" IN ACCESS SHARE MODE',
            ],
        )
        self.assertIn("COMMIT", self.conn.statements)
        with self.assertRaises(ParisonError):
            collection.export_postgres_collection(self.plan_path, self.output)

    def test_every_table_qualified_before_any_copy(self):
        def late_failure(cursor, plan):
            if plan["table"] == "orders":
                raise ParisonError("private late source")
            return self.qualify(cursor, plan)

        with (
            patch.object(collection, "_qualify_table", side_effect=late_failure),
            patch.object(collection, "_acquire_table") as copy,
        ):
            with self.assertRaises(ParisonError):
                collection.export_postgres_collection(self.plan_path, self.output)
            copy.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".output-*")))

    def test_commit_verification_and_rename_failure_cleanup(self):
        for failure in ("commit", "verify", "rename"):
            with self.subTest(failure=failure), ExitStack() as stack:
                self.conn.fail_commit = failure == "commit"
                if failure == "verify":
                    stack.enter_context(
                        patch.object(collection, "verify_postgres_collection", side_effect=ParisonError("private"))
                    )
                if failure == "rename":
                    stack.enter_context(
                        patch.object(collection, "rename_no_replace", side_effect=FileExistsError("private"))
                    )
                with self.assertRaises(ParisonError):
                    collection.export_postgres_collection(self.plan_path, self.output)
                self.assertFalse(self.output.exists())
                self.assertFalse(list(self.root.glob(".output-*")))
        self.conn.fail_commit = False

    def test_late_interrupt_and_shared_budget_cleanup(self):
        real = self.acquire

        def interrupted(cursor, plan, stage, *args):
            if plan["table"] == "orders":
                (stage / "data.csv").write_bytes(b"private partial")
                raise KeyboardInterrupt
            return real(cursor, plan, stage, *args)

        with patch.object(collection, "_acquire_table", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                collection.export_postgres_collection(self.plan_path, self.output)
        self.assertFalse(list(self.root.glob(".output-*")))
        for limits in ({"max_rows": 1}, {"max_output_bytes": 35}):
            plan = copy.deepcopy(self.plan)
            plan["limits"].update(limits)
            self.plan_path.write_text(json.dumps(plan))
            with self.assertRaises(ParisonError):
                collection.export_postgres_collection(self.plan_path, self.output)
            self.assertFalse(list(self.root.glob(".output-*")))

    def test_deadline_includes_post_commit_verification(self):
        now = [0.0]

        def verify(path):
            now[0] = 100.0
            return verify_postgres_collection(path)

        with (
            patch.object(collection.time, "monotonic", side_effect=lambda: now[0]),
            patch.object(collection, "verify_postgres_collection", side_effect=verify),
        ):
            with self.assertRaises(ParisonError):
                collection.export_postgres_collection(self.plan_path, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".output-*")))

    def test_plan_and_cli_errors_are_value_free(self):
        self.plan_path.write_text('{"a":1,"a":2}')
        with self.assertRaises(ParisonError):
            collection.export_postgres_collection(self.plan_path, self.output)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(
                cli.main(["postgres", "collection", "--plan", "private-path", "--output", str(self.output)]), 2
            )
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "parison postgres collection: invalid or incomplete collection evidence\n")
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as raised:
            cli.main(["postgres", "collection", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(out.getvalue(), (FIXTURE / "acquire-help.txt").read_text())

    def test_unqualified_versions_fail_before_catalog_probe(self):
        from unittest.mock import Mock

        source, snapshot = self.qualify(None, next(iter(self.plan["tables"].values())))
        cursor = Mock()
        for version in (160016, 170010, 180005, 190000):
            with (
                self.subTest(version=version),
                patch.object(
                    collection, "_metadata", return_value=({**source, "server_version_num": version}, snapshot)
                ),
            ):
                with self.assertRaises(ParisonError):
                    self.actual_qualify(cursor, {})
        cursor.execute.assert_not_called()

    def test_connection_failure_and_snapshot_substitution(self):
        with patch("psycopg.connect", side_effect=DriverError("private")):
            with self.assertRaises(ParisonError):
                collection.export_postgres_collection(self.plan_path, self.output)
        self.assertFalse(list(self.root.glob(".output-*")))

        def replaced(*args):
            item = self.acquire(*args)
            return {**item, "snapshot": "substituted"}

        with patch.object(collection, "_acquire_table", side_effect=replaced):
            with self.assertRaises(ParisonError):
                collection.export_postgres_collection(self.plan_path, self.output)
        self.assertFalse(list(self.root.glob(".output-*")))

    def test_publication_race_preserves_other_destination(self):
        real = collection.rename_no_replace

        def raced(stage, target):
            target.mkdir()
            (target / "owned-by-other").write_text("keep")
            real(stage, target)

        with patch.object(collection, "rename_no_replace", side_effect=raced):
            with self.assertRaises(ParisonError):
                collection.export_postgres_collection(self.plan_path, self.output)
        self.assertEqual((self.output / "owned-by-other").read_text(), "keep")
        self.assertFalse(list(self.root.glob(".output-*")))
