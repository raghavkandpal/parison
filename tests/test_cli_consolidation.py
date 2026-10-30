"""The new task paths preserve shipped command results and errors."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from parison import cli, partition_discovery, postgres_ingress, postgres_pair, postgres_rehearsal
from parison.core import ParisonError
from parison.decision_dossier import main as dossier_main


def _invoke(command, argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = command(argv)
        except SystemExit as exc:
            code = exc.code
    return code, stdout.getvalue(), stderr.getvalue()


class CliConsolidation(unittest.TestCase):
    def test_old_and_new_task_paths_match(self):
        cases = (
            (
                postgres_ingress.main,
                ["--plan", "p", "--output", "o"],
                ["postgres", "table"],
                "parison.postgres_ingress.export_postgres",
            ),
            (
                postgres_pair.main,
                ["--plan", "p", "--output", "o"],
                ["postgres", "pair"],
                "parison.postgres_pair.export_postgres_pair",
            ),
            (
                partition_discovery.main,
                ["discover", "--plan", "p", "--recipe", "r", "--baseline", "b", "--candidate", "c", "--output", "o"],
                ["partitions"],
                "parison.partition_discovery.discover",
            ),
            (partition_discovery.main, ["verify", "d"], ["partitions"], "parison.partition_discovery.verify"),
            (
                partition_discovery.main,
                [
                    "investigate",
                    "--plan",
                    "p",
                    "--discovery",
                    "d",
                    "--recipe",
                    "r",
                    "--baseline",
                    "b",
                    "--candidate",
                    "c",
                    "--output",
                    "o",
                ],
                ["partitions"],
                "parison.partition_investigation.investigate",
            ),
            (
                partition_discovery.main,
                ["verify-investigation", "d", "--discovery", "x"],
                ["partitions"],
                "parison.partition_investigation.verify_investigation",
            ),
            (
                postgres_rehearsal.main,
                [
                    "run",
                    "--plan",
                    "p",
                    "--output",
                    "o",
                    "--baseline",
                    "b",
                    "--candidate",
                    "c",
                    "--orders-recipe",
                    "r",
                    "--lines-recipe",
                    "l",
                    "--reconciliation",
                    "x",
                ],
                ["rehearsal"],
                "parison.postgres_rehearsal.run",
            ),
            (
                postgres_rehearsal.main,
                [
                    "verify",
                    "d",
                    "--baseline",
                    "b",
                    "--candidate",
                    "c",
                    "--orders-recipe",
                    "r",
                    "--lines-recipe",
                    "l",
                    "--reconciliation",
                    "x",
                ],
                ["rehearsal"],
                "parison.postgres_rehearsal.verify",
            ),
        )
        for old_main, args, prefix, target in cases:
            with self.subTest(command=prefix + args[:1]):
                for outcome in ("PASS", "FAIL", "INCONCLUSIVE"):
                    with patch(target, return_value={"outcome": outcome, "complete": outcome != "INCONCLUSIVE"}):
                        self.assertEqual(_invoke(old_main, args), _invoke(cli.main, prefix + args))
                with patch(target, side_effect=ParisonError("invalid evidence")):
                    self.assertEqual(_invoke(old_main, args), _invoke(cli.main, prefix + args))

    def test_help_and_private_unknown_command(self):
        for args, expected in (
            (["postgres", "--help"], "table"),
            (["postgres", "table", "--help"], "--plan"),
            (["postgres", "pair", "--help"], "--output"),
            (["partitions", "--help"], "investigate"),
            (["rehearsal", "--help"], "verify"),
            (["dossier", "--help"], "create"),
        ):
            with self.subTest(args=args):
                code, stdout, stderr = _invoke(cli.main, args)
                self.assertEqual((code, stderr), (0, ""))
                self.assertIn(expected, stdout)
        self.assertEqual(
            _invoke(cli.main, ["postgres", "private-value"]), (2, "", "parison postgres: invalid command\n")
        )

    def test_existing_dossier_route(self):
        with patch("parison.decision_dossier.verify", return_value={"outcome": "PASS"}):
            self.assertEqual(_invoke(dossier_main, ["verify", "d"]), _invoke(cli.main, ["dossier", "verify", "d"]))


if __name__ == "__main__":
    unittest.main()
