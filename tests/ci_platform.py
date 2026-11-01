"""Full native qualification: discover partition cases without feature YAML edits."""

from pathlib import Path


def load_tests(loader, tests, pattern):
    tests.addTests(
        loader.loadTestsFromNames(
            f"tests.{path.stem}" for path in sorted(Path(__file__).parent.glob("test_partition_*.py"))
        )
    )
    tests.addTests(
        loader.loadTestsFromNames(
            ("tests.test_xlsx", "tests.ci_smoke.InstalledSmoke", "tests.ci_smoke.NativeWorkflows")
        )
    )
    return tests
