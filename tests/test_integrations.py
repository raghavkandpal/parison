import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1] / "examples" / "integrations"


class IntegrationReferences(unittest.TestCase):
    def test_python_examples_compile_and_keep_parison_external(self):
        for name in ("airflow_dag.py", "dagster_assets.py"):
            with self.subTest(name=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                ast.parse(source, filename=name)
                self.assertIn("parison", source)
                self.assertIn("compare", source)
                self.assertIn("verify", source)
                self.assertNotIn("shell=True", source)
        airflow = (ROOT / "airflow_dag.py").read_text(encoding="utf-8")
        self.assertIn('pendulum.datetime(2026, 1, 1, tz="UTC")', airflow)
        dagster = (ROOT / "dagster_assets.py").read_text(encoding="utf-8")
        self.assertIn('deps=["baseline_output", "candidate_output"]', dagster)

    def test_dbt_example_preserves_build_extract_compare_verify_order(self):
        source = (ROOT / "dbt-parison-gate.sh").read_text(encoding="utf-8")
        self.assertLess(source.index("dbt build"), source.index("EXPORT_PARITY_INPUTS"))
        self.assertLess(source.index("EXPORT_PARITY_INPUTS"), source.index("parison compare"))
        self.assertLess(source.index("parison compare"), source.index("parison verify"))
        self.assertLess(source.index("comparison_code=$?"), source.index("parison verify"))
        self.assertLess(source.index("parison verify"), source.index('exit "$comparison_code"'))
        for variable in ("PARISON_RECIPE", "PARISON_BASELINE", "PARISON_CANDIDATE", "PARISON_OUTPUT"):
            self.assertIn(f'"${{{variable}', source)

    def test_orchestrators_verify_before_restoring_nonzero_comparison(self):
        airflow = (ROOT / "airflow_dag.py").read_text(encoding="utf-8")
        self.assertLess(airflow.index("code=$?"), airflow.index("parison verify"))
        self.assertLess(airflow.index("parison verify"), airflow.index('exit "$code"'))
        dagster = (ROOT / "dagster_assets.py").read_text(encoding="utf-8")
        self.assertLess(dagster.index("check=False"), dagster.index('"parison", "verify"'))
        self.assertLess(dagster.index('"parison", "verify"'), dagster.index("comparison.returncode"))

    def test_readme_states_snapshot_and_credential_boundaries(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("same logical snapshot", readme)
        self.assertIn("no warehouse, orchestrator or cloud credentials", readme)


if __name__ == "__main__":
    unittest.main()
