from __future__ import annotations

import re
import shlex
import unittest
from pathlib import Path

from parison.cli import parser
from scripts.generate_command_reference import render

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_command_reference_matches_parser(self):
        self.assertEqual((ROOT / "docs" / "command-reference.md").read_text(encoding="utf-8"), render())

    def test_current_guide_local_links_exist(self):
        guide = ROOT / "docs" / "user-guide.md"
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", guide.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                path = (guide.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(path.exists(), f"missing link target: {target}")

    def test_current_guide_commands_match_parser(self):
        guide = (ROOT / "docs" / "user-guide.md").read_text(encoding="utf-8")
        commands = []
        for block in re.findall(r"```sh\n(.*?)```", guide, re.DOTALL):
            logical_lines = block.replace("\\\n", " ").splitlines()
            commands.extend(line for line in logical_lines if line.startswith("parison "))
        self.assertGreaterEqual(len(commands), 30)
        for command in commands:
            with self.subTest(command=command):
                arguments = shlex.split(command.split(" > ", 1)[0])[1:]
                try:
                    parser().parse_args(arguments)
                except SystemExit as error:
                    self.assertEqual(error.code, 0)


if __name__ == "__main__":
    unittest.main()
