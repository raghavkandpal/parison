import hashlib
import json
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from concurrent.futures import Future
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, assemble_suite, explain_recipe, export_evidence, inspect_bundle, list_suite, load_schema, load_suite, report_ci, run_suite, verify_bundle


RECIPE = {
    "recipe_version": 1,
    "comparison_mode": "keyed",
    "keys": ["id"],
    "scope": {"snapshot": "suite-test", "cutoff": "2026-10-09T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
    "identity": {"null_keys": "reject", "duplicates": "reject"},
    "nulls_equal": True,
    "columns": {"id": {"type": "string"}, "value": {"type": "integer"}},
    "output": {"sensitivity": "summary"},
}


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "recipe.json").write_text(json.dumps(RECIPE), encoding="utf-8")
        (self.root / "baseline.csv").write_text("id,value\na,1\n", encoding="utf-8")
        (self.root / "candidate.csv").write_text("id,value\na,1\n", encoding="utf-8")
        (self.root / "different.csv").write_text("id,value\na,2\n", encoding="utf-8")
        (self.root / "invalid.csv").write_text("id,value\na,not-an-integer\n", encoding="utf-8")
        self.plan = self.root / "suite.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_plan(self, cases):
        self.plan.write_text(json.dumps({"suite_version": 1, "cases": cases}), encoding="utf-8")

    def write_plan_v2(self, cases, defaults=None):
        plan = {"suite_version": 2, "cases": cases}
        if defaults is not None:
            plan["defaults"] = defaults
        self.plan.write_text(json.dumps(plan), encoding="utf-8")

    def case(self, identifier="orders"):
        return {"id": identifier, "recipe": "recipe.json", "baseline": "baseline.csv", "candidate": "candidate.csv"}

    def test_schema_and_loader_resolve_references(self):
        schema = load_schema("suite")
        Draft202012Validator.check_schema(schema)
        self.write_plan([self.case()])
        Draft202012Validator(schema).validate(json.loads(self.plan.read_text(encoding="utf-8")))
        loaded = load_suite(self.plan)
        self.assertEqual(loaded["cases"][0]["recipe"], str(self.root / "recipe.json"))
        self.assertEqual(loaded["cases"][0]["baseline"], str(self.root / "baseline.csv"))

    def test_policy_lock_and_cli_validation(self):
        case = self.case()
        case["expected_policy_sha256"] = explain_recipe(self.root / "recipe.json")["policy_sha256"]
        self.write_plan([case])
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["validate-suite", str(self.plan)]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"cases": 1, "status": "valid"})
        self.assertIn("Validated comparison suite", stderr.getvalue())

    def test_suite_v2_listing_selection_limits_and_fingerprint(self):
        first = self.case("orders") | {"tags": ["critical", "finance"], "description": "Order totals", "limits": {"max_rows": 7}}
        second = self.case("users") | {"tags": ["critical"]}
        self.write_plan_v2([first, second], {"limits": {"max_input_bytes": 99}})
        schema = load_schema("suite-v2")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(json.loads(self.plan.read_text(encoding="utf-8")))
        listed = list_suite(self.plan, tags=["critical", "finance"])
        self.assertEqual([case["id"] for case in listed["cases"]], ["orders"])
        self.assertEqual(listed["cases"][0]["limits"]["max_rows"], 7)
        self.assertEqual(listed["cases"][0]["limits"]["max_input_bytes"], 99)
        self.assertRegex(listed["suite_policy_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual([case["id"] for case in list_suite(self.plan, shard_index=1, shard_count=2)["cases"]], ["users"])
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["list-suite", str(self.plan), "--tag", "critical", "--json"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["selected_cases"], 2)

    def test_suite_v2_rejects_unportable_and_ambiguous_metadata(self):
        self.write_plan_v2([self.case() | {"tags": ["z", "a"]}])
        with self.assertRaisesRegex(ParisonError, "sorted unique"):
            load_suite(self.plan)
        unportable = self.case()
        unportable["recipe"] = str(self.root / "recipe.json")
        self.write_plan_v2([unportable])
        with self.assertRaisesRegex(ParisonError, "portable plan-relative"):
            load_suite(self.plan)
        self.write_plan_v2([self.case()])
        with self.assertRaisesRegex(ParisonError, "contains no cases"):
            list_suite(self.plan, tags=["missing"])
        with self.assertRaisesRegex(ParisonError, "unknown suite case"):
            list_suite(self.plan, case_ids=["orders", "missing"])

    def test_suite_v2_run_selection_and_shard_are_explicit_and_verifiable(self):
        self.write_plan_v2([
            self.case("first") | {"tags": ["critical"]},
            self.case("second") | {"tags": ["slow"]},
            self.case("third") | {"tags": ["critical"]},
        ])
        shard = self.root / "shard"
        result = run_suite(self.plan, shard, shard_index=0, shard_count=2)
        self.assertEqual(result["kind"], "suite-shard")
        self.assertTrue(result["execution_complete"])
        self.assertFalse(result["scope_complete"])
        self.assertEqual([case["id"] for case in result["cases"]], ["first", "third"])
        self.assertEqual(verify_bundle(shard)["kind"], "suite-shard")
        self.assertEqual(inspect_bundle(shard)["selection"]["shard_count"], 2)
        Draft202012Validator(load_schema("suite-result-v2")).validate(result)
        Draft202012Validator(load_schema("suite-manifest-v2")).validate(json.loads((shard / "manifest.json").read_text(encoding="utf-8")))

        selected = self.root / "selected"
        selected_result = run_suite(self.plan, selected, tags=["slow"])
        self.assertEqual(selected_result["kind"], "suite")
        self.assertFalse(selected_result["scope_complete"])
        self.assertEqual([case["id"] for case in selected_result["cases"]], ["second"])

    def test_suite_v2_case_limits_reach_child_result(self):
        self.write_plan_v2([self.case() | {"limits": {"max_rows": 1}}])
        output = self.root / "limited-v2"
        run_suite(self.plan, output)
        child = json.loads((output / "cases" / "orders" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(child["resource_limits"]["max_rows_per_input"], 1)

    def test_concurrent_suite_matches_sequential_semantics_and_plan_order(self):
        passing = self.case("first")
        failing = self.case("second") | {"candidate": "different.csv"}
        self.write_plan_v2([passing, failing, self.case("third")])
        sequential = run_suite(self.plan, self.root / "sequential")
        concurrent = run_suite(self.plan, self.root / "concurrent", jobs=2)
        self.assertEqual(concurrent["outcome"], sequential["outcome"])
        self.assertEqual(concurrent["outcome_counts"], sequential["outcome_counts"])
        self.assertEqual([case["id"] for case in concurrent["cases"]], ["first", "second", "third"])
        self.assertEqual([case["outcome"] for case in concurrent["cases"]], ["PASS", "FAIL", "PASS"])
        self.assertEqual(verify_bundle(self.root / "concurrent")["kind"], "suite")

    def test_concurrent_suite_validates_job_bound_and_cli(self):
        self.write_plan_v2([self.case("first"), self.case("second")])
        with self.assertRaisesRegex(ParisonError, "jobs must be between 1 and 16"):
            run_suite(self.plan, self.root / "invalid", jobs=0)
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            self.assertEqual(main(["run-suite", "--plan", str(self.plan), "--output", str(self.root / "cli-concurrent"), "--jobs", "2"]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["cases"], 2)

    def test_concurrent_worker_failure_is_explicit_and_does_not_cancel_other_cases(self):
        self.write_plan_v2([self.case("broken"), self.case("passing")])

        class InjectedExecutor:
            def __init__(self, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def submit(self, function, case, *args):
                future = Future()
                if case["id"] == "broken":
                    future.set_exception(RuntimeError("source-value-must-not-leak"))
                else:
                    future.set_result(function(case, *args))
                return future

        with patch("parison.core.ProcessPoolExecutor", InjectedExecutor):
            result = run_suite(self.plan, self.root / "worker-failure", jobs=2)
        self.assertEqual(result["outcome"], "ERROR")
        self.assertEqual([case["outcome"] for case in result["cases"]], ["ERROR", "PASS"])
        child = json.loads((self.root / "worker-failure" / "cases" / "broken" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(child["problems"], ["suite worker failed unexpectedly"])
        self.assertNotIn("source-value-must-not-leak", json.dumps(child))
        self.assertEqual(verify_bundle(self.root / "worker-failure")["outcome"], "ERROR")

    def test_assemble_suite_proves_exact_coverage_and_plan_order(self):
        self.write_plan_v2([self.case("first"), self.case("second"), self.case("third")])
        shard_0, shard_1 = self.root / "shard-0", self.root / "shard-1"
        run_suite(self.plan, shard_0, shard_index=0, shard_count=2)
        run_suite(self.plan, shard_1, shard_index=1, shard_count=2)
        output = self.root / "assembled"
        result = assemble_suite(self.plan, [shard_1, shard_0], output)
        self.assertEqual([case["id"] for case in result["cases"]], ["first", "second", "third"])
        self.assertTrue(result["scope_complete"])
        self.assertEqual(verify_bundle(output)["kind"], "suite")
        stdout, stderr = StringIO(), StringIO()
        cli_output = self.root / "assembled-cli"
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["assemble-suite", "--plan", str(self.plan), "--input", str(shard_0), "--input", str(shard_1), "--output", str(cli_output)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["cases"], 3)

    def test_assemble_suite_rejects_gaps_duplicates_and_tampering(self):
        self.write_plan_v2([self.case("first"), self.case("second")])
        shard_0, shard_1 = self.root / "shard-0", self.root / "shard-1"
        run_suite(self.plan, shard_0, shard_index=0, shard_count=2)
        run_suite(self.plan, shard_1, shard_index=1, shard_count=2)
        with self.assertRaisesRegex(ParisonError, "exact coverage"):
            assemble_suite(self.plan, [shard_0], self.root / "gap")
        with self.assertRaisesRegex(ParisonError, "duplicate suite shard index"):
            assemble_suite(self.plan, [shard_0, shard_0], self.root / "duplicate")
        child_result = shard_1 / "cases" / "second" / "result.json"
        child_result.write_text(child_result.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "failed integrity"):
            assemble_suite(self.plan, [shard_0, shard_1], self.root / "tampered")

    def test_resume_reuses_only_verified_current_children(self):
        self.write_plan_v2([self.case("first"), self.case("second")])
        workspace = self.root / "workspace"
        run_suite(self.plan, self.root / "initial", workspace=workspace)
        with patch("parison.core.compare", side_effect=AssertionError("comparison should be reused")):
            resumed = run_suite(self.plan, self.root / "resumed", workspace=workspace, resume=True)
        self.assertEqual(resumed["outcome"], "PASS")
        self.assertEqual(verify_bundle(self.root / "resumed")["kind"], "suite")

        (self.root / "candidate.csv").write_text("id,value\na,2\n", encoding="utf-8")
        calls = 0
        from parison.core import compare as real_compare
        def counted_compare(*args, **kwargs):
            nonlocal calls
            calls += 1
            return real_compare(*args, **kwargs)
        with patch("parison.core.compare", side_effect=counted_compare):
            changed = run_suite(self.plan, self.root / "changed", workspace=workspace, resume=True)
        self.assertEqual(calls, 2)
        self.assertEqual(changed["outcome"], "FAIL")

    def test_concurrent_resume_reuses_verified_children(self):
        self.write_plan_v2([self.case("first"), self.case("second"), self.case("third")])
        workspace = self.root / "concurrent-workspace"
        run_suite(self.plan, self.root / "concurrent-initial", workspace=workspace, jobs=2)
        manifests = {
            case: (workspace / "cases" / case / "manifest.json").stat().st_mtime_ns
            for case in ("first", "second", "third")
        }
        result = run_suite(self.plan, self.root / "concurrent-resumed", workspace=workspace, resume=True, jobs=3)
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(
            manifests,
            {case: (workspace / "cases" / case / "manifest.json").stat().st_mtime_ns for case in manifests},
        )
        self.assertEqual(verify_bundle(self.root / "concurrent-resumed")["kind"], "suite")

    def test_resume_rejects_implicit_or_unsafe_workspace(self):
        self.write_plan_v2([self.case()])
        with self.assertRaisesRegex(ParisonError, "requires --workspace"):
            run_suite(self.plan, self.root / "output", resume=True)
        workspace = self.root / "workspace"
        workspace.mkdir()
        with self.assertRaisesRegex(ParisonError, "already exists"):
            run_suite(self.plan, self.root / "other", workspace=workspace)
        empty_workspace = self.root / "empty-workspace"
        empty_workspace.mkdir()
        with self.assertRaisesRegex(ParisonError, "incomplete or unsafe"):
            run_suite(self.plan, self.root / "third", workspace=empty_workspace, resume=True)

    def test_ci_reports_are_bounded_safe_and_outcome_explicit(self):
        passing = self.case("passing")
        failing = self.case("failing")
        failing["candidate"] = "different.csv"
        self.write_plan_v2([passing, failing])
        bundle = self.root / "bundle"
        run_suite(self.plan, bundle)
        markdown = self.root / "summary.md"
        metadata = report_ci(bundle, markdown, "markdown")
        self.assertLessEqual(metadata["bytes"], 1_000_000)
        text = markdown.read_text(encoding="utf-8")
        self.assertIn("**FAIL**", text)
        self.assertIn("`failing`", text)
        self.assertNotIn("a,2", text)
        with self.assertRaisesRegex(ParisonError, "already exists"):
            report_ci(bundle, markdown, "markdown")

        junit = self.root / "junit.xml"
        report_ci(bundle, junit, "junit")
        root = ET.parse(junit).getroot()
        self.assertEqual(root.attrib["failures"], "1")
        outcomes = {node.attrib["name"]: node.find("./properties/property").attrib["value"] for node in root.findall("testcase")}
        self.assertEqual(outcomes, {"passing": "PASS", "failing": "FAIL"})
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            self.assertEqual(main(["report-ci", str(bundle), "--format", "markdown", "--output", str(self.root / "cli.md")]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["format"], "markdown")

    def test_rejects_duplicates_unknown_fields_and_policy_drift(self):
        self.write_plan([self.case(), self.case()])
        with self.assertRaisesRegex(ParisonError, "duplicate suite case id"):
            load_suite(self.plan)
        invalid = self.case()
        invalid["command"] = "anything"
        self.write_plan([invalid])
        with self.assertRaisesRegex(ParisonError, "invalid fields"):
            load_suite(self.plan)
        locked = self.case()
        locked["expected_policy_sha256"] = "0" * 64
        self.write_plan([locked])
        with self.assertRaisesRegex(ParisonError, "does not match expected"):
            load_suite(self.plan)

    def test_rejects_unsafe_ids_and_missing_inputs(self):
        self.write_plan([self.case("../escape")])
        with self.assertRaisesRegex(ParisonError, "invalid id"):
            load_suite(self.plan)
        missing = self.case()
        missing["candidate"] = "missing.csv"
        self.write_plan([missing])
        with self.assertRaisesRegex(ParisonError, "candidate is not a regular input"):
            load_suite(self.plan)

    def test_run_suite_publishes_ordered_children_and_reduces_outcome(self):
        passing = self.case("passing")
        failing = self.case("failing")
        failing["candidate"] = "different.csv"
        self.write_plan([passing, failing])
        output = self.root / "run"
        result = run_suite(self.plan, output)
        self.assertEqual(result["outcome"], "FAIL")
        self.assertTrue(result["complete"])
        self.assertEqual(result["outcome_counts"]["PASS"], 1)
        self.assertEqual(result["outcome_counts"]["FAIL"], 1)
        self.assertEqual([case["id"] for case in result["cases"]], ["passing", "failing"])
        self.assertTrue((output / "cases" / "passing" / "manifest.json").is_file())
        self.assertTrue((output / "cases" / "failing" / "manifest.json").is_file())
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        Draft202012Validator(load_schema("suite-result")).validate(result)
        Draft202012Validator(load_schema("suite-manifest")).validate(manifest)
        self.assertEqual(manifest["kind"], "suite")
        self.assertEqual(set(manifest["cases"]), {"passing", "failing"})
        self.assertEqual(verify_bundle(output)["kind"], "suite")
        inspection = inspect_bundle(output)
        self.assertEqual(inspection["outcome_counts"]["FAIL"], 1)
        self.assertNotIn("discrepancy_sample", json.dumps(inspection))
        with self.assertRaisesRegex(ParisonError, "requires a child run bundle"):
            export_evidence(output, self.root / "suite-evidence.jsonl")
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as verify_stderr:
            self.assertEqual(main(["verify", str(output)]), 0)
        self.assertIn("suite", verify_stderr.getvalue())
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(main(["run-suite", "--plan", str(self.plan), "--output", str(self.root / "cli-run")]), 1)
        self.assertEqual(json.loads(stdout.getvalue())["cases"], 2)
        self.assertIn("Parison suite FAIL", stderr.getvalue())
        with self.assertRaisesRegex(ParisonError, "output already exists"):
            run_suite(self.plan, output)
        child_result = output / "cases" / "passing" / "result.json"
        child_result.write_text(child_result.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "failed integrity"):
            verify_bundle(output)

    def test_run_suite_continues_after_case_error(self):
        broken = self.case("broken")
        broken["candidate"] = "invalid.csv"
        self.write_plan([broken, self.case("passing")])
        result = run_suite(self.plan, self.root / "error-run")
        self.assertEqual(result["outcome"], "ERROR")
        self.assertEqual(result["completed_cases"], 2)
        self.assertEqual([case["outcome"] for case in result["cases"]], ["ERROR", "PASS"])

    def test_interruption_stops_after_publishing_interrupted_child(self):
        self.write_plan([self.case("first"), self.case("second")])
        output = self.root / "interrupted"
        with patch("parison.core.compare", side_effect=KeyboardInterrupt):
            result = run_suite(self.plan, output)
        self.assertEqual(result["outcome"], "INTERRUPTED")
        self.assertEqual(result["completed_cases"], 1)
        self.assertEqual(result["total_cases"], 2)
        self.assertFalse(result["complete"])
        self.assertEqual(verify_bundle(output)["outcome"], "INTERRUPTED")

    def test_rejects_self_consistent_parent_summary_tampering(self):
        self.write_plan([self.case()])
        output = self.root / "tampered"
        run_suite(self.plan, output)
        result_path = output / "suite-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["outcome_counts"]["PASS"] = 0
        result["outcome_counts"]["FAIL"] = 1
        result_path.write_text(json.dumps(result), encoding="utf-8")
        manifest_path = output / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"]["suite-result.json"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ParisonError, "invalid counts"):
            verify_bundle(output)

    def test_parent_publication_failure_cleans_staging(self):
        self.write_plan([self.case()])
        output = self.root / "publication"
        real_replace = os.replace

        def fail_parent(source, destination):
            if Path(destination) == output:
                raise OSError("injected parent publication failure")
            return real_replace(source, destination)

        with patch("parison.core.os.replace", side_effect=fail_parent), self.assertRaisesRegex(ParisonError, "cannot publish suite"):
            run_suite(self.plan, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob(".publication-*")), [])


if __name__ == "__main__":
    unittest.main()
