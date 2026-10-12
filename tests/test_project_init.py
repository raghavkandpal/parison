import json
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


if __name__ == "__main__":
    unittest.main()
