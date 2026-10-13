import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from parison.cli import main


class ProjectInit(unittest.TestCase):
    def test_init_creates_runnable_minimal_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "migration-check"
            stdout, stderr = StringIO(), StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(["init", str(project)]), 0)

            self.assertEqual(json.loads(stdout.getvalue()), {
                "directory": str(project),
                "files": ["README.md", "baseline.csv", "candidate.csv", "recipe.json"],
            })
            self.assertIn("Next: cd", stderr.getvalue())
            self.assertEqual(
                sorted(path.name for path in project.iterdir()),
                ["README.md", "baseline.csv", "candidate.csv", "recipe.json"],
            )
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(["validate-recipe", str(project / "recipe.json")]), 0)
                self.assertEqual(main([
                    "compare", "--recipe", str(project / "recipe.json"),
                    "--baseline", str(project / "baseline.csv"),
                    "--candidate", str(project / "candidate.csv"),
                    "--output", str(project / "run"),
                ]), 0)
                self.assertEqual(main(["verify", str(project / "run")]), 0)

    def test_init_accepts_existing_empty_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "empty"
            project.mkdir()
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(["init", str(project)]), 0)
            self.assertTrue((project / "recipe.json").is_file())

    def test_init_refuses_nonempty_directory_without_changing_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "existing"
            project.mkdir()
            marker = project / "keep.txt"
            marker.write_text("keep me\n", encoding="utf-8")
            stderr = StringIO()
            with redirect_stdout(StringIO()), redirect_stderr(stderr):
                self.assertEqual(main(["init", str(project)]), 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep me\n")
            self.assertEqual(sorted(path.name for path in project.iterdir()), ["keep.txt"])
            self.assertIn("not empty", stderr.getvalue())

    def test_init_refuses_file_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "existing"
            destination.write_text("keep me\n", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(["init", str(destination)]), 2)
            self.assertEqual(destination.read_text(encoding="utf-8"), "keep me\n")

    def test_init_refuses_directory_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            link = root / "linked-project"
            try:
                os.symlink(target, link, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            stderr = StringIO()
            with redirect_stdout(StringIO()), redirect_stderr(stderr):
                self.assertEqual(main(["init", str(link)]), 2)
            self.assertEqual(list(target.iterdir()), [])
            self.assertIn("must not be a symlink", stderr.getvalue())

    def test_complete_migration_evidence_workflow(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "migration-check"
            catalog = root / "catalog.sqlite"
            suite = root / "suite"
            statement = root / "statement.json"
            cutover = root / "cutover.md"

            def run(arguments):
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    self.assertEqual(main(arguments), 0, arguments)

            run(["init", str(project)])
            run(["validate-inputs", "--records", "--recipe", str(project / "recipe.json"), "--baseline", str(project / "baseline.csv"), "--candidate", str(project / "candidate.csv")])
            for name in ("rehearsal-1", "rehearsal-2"):
                output = project / name
                run(["compare", "--recipe", str(project / "recipe.json"), "--baseline", str(project / "baseline.csv"), "--candidate", str(project / "candidate.csv"), "--output", str(output)])
                run(["catalog", "add", "--database", str(catalog), str(output)])

            stdout = StringIO()
            with redirect_stdout(stdout), redirect_stderr(StringIO()):
                self.assertEqual(main(["explain", str(project / "recipe.json")]), 0)
            policy = json.loads(stdout.getvalue())["policy_sha256"]
            run(["catalog", "history", "--database", str(catalog), "--policy-sha256", policy])
            run(["catalog", "diff", "--database", str(catalog), str(project / "rehearsal-1"), str(project / "rehearsal-2")])

            run(["run-suite", "--plan", str(repository / "examples" / "0.15" / "payout-suite.json"), "--output", str(suite)])
            run(["verify", str(suite)])
            run(["statement", str(suite), "--output", str(statement)])
            run(["verify-statement", str(suite), str(statement)])
            run(["report-cutover", str(suite), "--output", str(cutover)])
            self.assertTrue(cutover.is_file())


if __name__ == "__main__":
    unittest.main()
