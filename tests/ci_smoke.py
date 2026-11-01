"""Installed-wheel smoke suites, invoked explicitly rather than by unit discovery."""

import importlib.metadata
import io
import json
import subprocess
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import parison
from parison.cli import main
from parison.core import _SCHEMAS, load_schema
from parison.partition_discovery import main as partitions_main
from parison.workbench_host import create_workbench_server


def invoke(arguments):
    call = partitions_main if arguments[0] == "parison-partitions" else main
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            return call(arguments[1:])
        except SystemExit as exit:
            return exit.code


class InstalledSmoke(unittest.TestCase):
    def test_installed_wheel_and_entry_points(self):
        self.assertNotEqual(Path(parison.__file__).resolve().parent.parent, Path(__file__).resolve().parents[1] / "src")
        entries = importlib.metadata.distribution("parison").entry_points
        expected = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())["project"][
            "scripts"
        ]
        self.assertEqual({entry.name: entry.value for entry in entries if entry.group == "console_scripts"}, expected)
        for entry in entries:
            if entry.group == "console_scripts":
                with self.subTest(entry=entry.name):
                    completed = subprocess.run([entry.name, "--help"], capture_output=True, text=True, timeout=30)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(invoke(["parison", "--version"]), 0)

    def test_canonical_subcommand_help(self):
        for args in (
            ("postgres",),
            ("postgres", "table"),
            ("postgres", "pair"),
            ("postgres", "collection"),
            ("partitions",),
            ("rehearsal",),
            ("dossier",),
        ):
            with self.subTest(command=args):
                self.assertEqual(invoke(["parison", *args, "--help"]), 0)

    def test_every_registered_schema_from_installed_wheel(self):
        for name in _SCHEMAS:
            with self.subTest(schema=name), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["schema", name]), 0)
                self.assertEqual(json.loads(output.getvalue()), load_schema(name))

    def test_quickstart(self):
        with tempfile.TemporaryDirectory() as scratch:
            project = str(Path(scratch) / "project")
            for args in (
                ["init", project],
                [
                    "compare",
                    "--recipe",
                    project + "/recipe.json",
                    "--baseline",
                    project + "/baseline.csv",
                    "--candidate",
                    project + "/candidate.csv",
                    "--output",
                    project + "/run",
                ],
                ["verify", project + "/run"],
            ):
                self.assertEqual(invoke(["parison", *args]), 0)


class NativeWorkflows(unittest.TestCase):
    def test_historical_installed_workflows(self):
        with tempfile.TemporaryDirectory() as scratch:
            for arguments in COMMANDS:
                args = [value.replace("{scratch}", scratch) for value in arguments]
                with self.subTest(command=arguments[:2]):
                    self.assertEqual(invoke(args), 0)

    def test_loopback_host(self):
        server, url = create_workbench_server(".")
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            self.assertTrue(url.startswith("http://127.0.0.1:"))
        finally:
            server.server_close()


COMMANDS = (
    ["parison", "verify-postgres-export", "tests/fixtures/postgres_ingress"],
    ["parison", "verify-postgres-pair", "tests/fixtures/postgres_pair"],
    [
        "parison-partitions",
        "discover",
        "--plan",
        "tests/fixtures/partition_discovery/plan.json",
        "--recipe",
        "tests/fixtures/partition_discovery/recipe.json",
        "--baseline",
        "tests/fixtures/partition_discovery/baseline.csv",
        "--candidate",
        "tests/fixtures/partition_discovery/candidate.csv",
        "--output",
        "{scratch}/parison-partition-smoke",
    ],
    [
        "parison-partitions",
        "verify",
        "{scratch}/parison-partition-smoke",
        "--recipe",
        "tests/fixtures/partition_discovery/recipe.json",
        "--baseline",
        "tests/fixtures/partition_discovery/baseline.csv",
        "--candidate",
        "tests/fixtures/partition_discovery/candidate.csv",
    ],
    [
        "parison",
        "partitions",
        "verify",
        "{scratch}/parison-partition-smoke",
        "--recipe",
        "tests/fixtures/partition_discovery/recipe.json",
        "--baseline",
        "tests/fixtures/partition_discovery/baseline.csv",
        "--candidate",
        "tests/fixtures/partition_discovery/candidate.csv",
    ],
    [
        "parison-partitions",
        "discover",
        "--plan",
        "tests/fixtures/partition_discovery/plan.json",
        "--recipe",
        "tests/fixtures/partition_investigation/recipe.json",
        "--baseline",
        "tests/fixtures/partition_discovery/baseline.csv",
        "--candidate",
        "tests/fixtures/partition_investigation/candidate.csv",
        "--output",
        "{scratch}/parison-investigation-discovery",
    ],
    [
        "parison-partitions",
        "investigate",
        "--plan",
        "tests/fixtures/partition_investigation/plan.json",
        "--discovery",
        "{scratch}/parison-investigation-discovery",
        "--recipe",
        "tests/fixtures/partition_investigation/recipe.json",
        "--baseline",
        "tests/fixtures/partition_discovery/baseline.csv",
        "--candidate",
        "tests/fixtures/partition_investigation/candidate.csv",
        "--output",
        "{scratch}/parison-investigation-smoke",
    ],
    [
        "parison-partitions",
        "verify-investigation",
        "{scratch}/parison-investigation-smoke",
        "--discovery",
        "{scratch}/parison-investigation-discovery",
        "--recipe",
        "tests/fixtures/partition_investigation/recipe.json",
        "--baseline",
        "tests/fixtures/partition_discovery/baseline.csv",
        "--candidate",
        "tests/fixtures/partition_investigation/candidate.csv",
    ],
    [
        "parison",
        "verify-dataset-manifest",
        "--manifest",
        "examples/1.4/payout-dataset-manifest.json",
        "--root",
        ".",
        "--policy-file",
        "examples/1.3/reconciliation.json",
        "--summary",
    ],
    [
        "parison",
        "reconcile",
        "--alignment",
        "examples/1.3/alignment.json",
        "--reconciliation",
        "examples/1.3/reconciliation.json",
        "--receipt",
        "examples/1.3/extraction-receipt.json",
        "--dataset",
        "payments",
        "examples/1.3/payments.recipe.json",
        "examples/1.3/payments-baseline.csv",
        "examples/1.3/payments-candidate.jsonl",
        "--dataset",
        "payouts",
        "examples/1.3/payouts.recipe.json",
        "examples/1.3/payouts-baseline.csv",
        "examples/1.3/payouts-candidate.jsonl",
        "--engine",
        "sqlite",
        "--output",
        "{scratch}/parison-1.3-reconciliation",
        "--summary",
    ],
    ["parison", "verify", "{scratch}/parison-1.3-reconciliation"],
    ["parison", "inspect", "{scratch}/parison-1.3-reconciliation"],
    [
        "parison",
        "compare",
        "--recipe",
        "examples/0.8/multiset.recipe.json",
        "--baseline",
        "examples/0.8/baseline.csv",
        "--candidate",
        "examples/0.8/candidate.jsonl",
        "--output",
        "{scratch}/parison-multiset-smoke",
    ],
    ["parison", "inspect", "{scratch}/parison-multiset-smoke"],
    ["parison", "statement", "{scratch}/parison-multiset-smoke", "--output", "{scratch}/parison-statement.json"],
    ["parison", "verify-statement", "{scratch}/parison-multiset-smoke", "{scratch}/parison-statement.json"],
    ["parison", "report-cutover", "{scratch}/parison-multiset-smoke", "--output", "{scratch}/parison-cutover.md"],
    ["parison", "run-suite", "--plan", "examples/0.10/mixed-suite.json", "--output", "{scratch}/parison-suite-smoke"],
    ["parison", "verify", "{scratch}/parison-suite-smoke"],
    ["parison", "init", "{scratch}/parison-quickstart"],
    [
        "parison",
        "compare",
        "--recipe",
        "{scratch}/parison-quickstart/recipe.json",
        "--baseline",
        "{scratch}/parison-quickstart/baseline.csv",
        "--candidate",
        "{scratch}/parison-quickstart/candidate.csv",
        "--output",
        "{scratch}/parison-quickstart/run",
    ],
    ["parison", "verify", "{scratch}/parison-quickstart/run"],
)
