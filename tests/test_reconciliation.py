import copy
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, explain_recipe, load_schema
from parison.reconciliation import canonical_reconciliation_bytes, canonical_time_alignment_bytes, check_conservation, check_identity_references, explain_reconciliation, explain_time_alignment, normalize_reconciliation, normalize_time_alignment, preflight_alignment, run_reconciliation, summarize_reconciliation_result


ROOT = Path(__file__).parents[1]


def alignment(mode="source-snapshot"):
    value = {
        "alignment_version": 1,
        "event_window": {"start": "2026-09-01T00:00:00Z", "end": "2026-10-01T00:00:00Z", "bounds": "start-inclusive-end-exclusive"},
        "coordination": {"mode": mode, "claim_id": "september-close-4", "receipt_sha256": "a" * 64},
        "datasets": [
            {"id": "payments", "event_time_column": "occurred_at", "snapshot_token": "snapshot-42", "token_domain": "ledger"},
            {"id": "payouts", "event_time_column": "occurred_at", "snapshot_token": "snapshot-42", "token_domain": "ledger"},
        ],
    }
    if mode == "watermark":
        value["coordination"].update({"watermark_kind": "closed-world", "idle_partition_policy": "documented"})
        for dataset in value["datasets"]:
            dataset.pop("snapshot_token")
            dataset.pop("token_domain")
            dataset.update({"watermark": "2026-10-01T00:00:00Z", "allowed_lateness_seconds": 3600})
    elif mode == "declared-cutoff":
        for dataset in value["datasets"]:
            dataset.pop("snapshot_token")
            dataset.pop("token_domain")
    return value


def reconciliation():
    return {
        "reconciliation_version": 1,
        "alignment_sha256": "b" * 64,
        "datasets": [
            {"id": "payments", "policy_sha256": "c" * 64, "columns": [{"name": "payout_id", "type": "string"}, {"name": "amount", "type": "decimal"}]},
            {"id": "payouts", "policy_sha256": "d" * 64, "columns": [{"name": "payout_id", "type": "string"}, {"name": "amount", "type": "decimal"}]},
        ],
        "checks": [
            {"id": "payout-id", "kind": "identity", "dataset": "payouts", "columns": ["payout_id"], "nulls": "forbid"},
            {"id": "payment-payout", "kind": "reference", "child_dataset": "payments", "child_columns": ["payout_id"], "parent_identity": "payout-id", "nulls": "forbid"},
            {"id": "payout-total", "kind": "conservation", "parent_dataset": "payouts", "parent_identity": "payout-id", "parent_group_columns": ["payout_id"], "child_dataset": "payments", "child_group_columns": ["payout_id"], "parent_measure": "amount", "child_measure": "amount", "operator": "sum", "nulls": "forbid", "comparison": "exact", "tolerance": None},
        ],
    }


class ReconciliationContracts(unittest.TestCase):
    def _preflight_files(self, directory, mode="source-snapshot", timestamp="2026-09-01T00:00:00Z"):
        receipt = directory / "receipt.json"
        receipt.write_text('{"source":"fixture"}\n', encoding="utf-8")
        value = alignment(mode)
        import hashlib
        value["coordination"]["receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
        alignment_path = directory / "alignment.json"
        alignment_path.write_text(json.dumps(value), encoding="utf-8")
        recipe = {
            "recipe_version": 1, "comparison_mode": "keyed", "keys": ["payout_id"],
            "scope": {"snapshot": "fixture", "cutoff": "2026-10-01T00:00:00Z", "filters": [], "completeness": "full", "expected_empty": False},
            "identity": {"null_keys": "reject", "duplicates": "reject"}, "nulls_equal": True,
            "null_tokens": {"baseline": [], "candidate": []},
            "columns": {"payout_id": {"type": "string", "comparison": "exact"}, "occurred_at": {"type": "timestamp", "comparison": "exact", "timezone": "require-aware"}, "amount": {"type": "decimal", "comparison": "exact", "scale": 2}},
            "column_mappings": {}, "excluded_columns": {}, "delimiters": {"baseline": ",", "candidate": ","},
            "input_projection": "semantic-scalar-v1", "output": {"sensitivity": "summary"},
        }
        recipe_path = directory / "recipe.json"
        recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
        policy_sha256 = explain_recipe(recipe_path)["policy_sha256"]
        reconciliation_value = {
            "reconciliation_version": 1,
            "alignment_sha256": explain_time_alignment(alignment_path)["alignment_sha256"],
            "datasets": [{"id": dataset_id, "policy_sha256": policy_sha256, "columns": [{"name": "payout_id", "type": "string"}, {"name": "occurred_at", "type": "timestamp"}, {"name": "amount", "type": "decimal"}]} for dataset_id in ("payments", "payouts")],
            "checks": [{"id": "payout-id", "kind": "identity", "dataset": "payouts", "columns": ["payout_id"], "nulls": "forbid"}],
        }
        reconciliation_path = directory / "reconciliation.json"
        reconciliation_path.write_text(json.dumps(reconciliation_value), encoding="utf-8")
        sources = {}
        for dataset_id in ("payments", "payouts"):
            sides = {}
            for side in ("baseline", "candidate"):
                path = directory / f"{dataset_id}-{side}.csv"
                path.write_text(f"payout_id,occurred_at,amount\np-1,{timestamp},1.00\n", encoding="utf-8")
                sides[side] = path
            sources[dataset_id] = {"recipe": recipe_path, **sides}
        return alignment_path, reconciliation_path, receipt, sources

    def test_installed_schemas_accept_contracts_and_reject_unknown_fields(self):
        for name, value in (("time-alignment", alignment()), ("reconciliation", reconciliation())):
            schema = load_schema(name)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(value)
            invalid = copy.deepcopy(value)
            invalid["future"] = True
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(invalid)))

    def test_alignment_modes_are_closed_and_canonical(self):
        for mode in ("source-snapshot", "watermark", "declared-cutoff"):
            normalized = normalize_time_alignment(alignment(mode))
            self.assertEqual(normalized["coordination"]["mode"], mode)
        reordered = alignment()
        reordered["datasets"].reverse()
        self.assertEqual(canonical_time_alignment_bytes(alignment()), canonical_time_alignment_bytes(reordered))
        self.assertEqual(canonical_time_alignment_bytes(alignment()), (ROOT / "tests/fixtures/time-alignment-v1.canonical.json").read_bytes().removesuffix(b"\n"))

    def test_alignment_rejects_ambiguous_time_and_coordination(self):
        cases = []
        invalid = alignment(); invalid["event_window"]["start"] = "2026-09-01T00:00:00+00:00"; cases.append(invalid)
        invalid = alignment(); invalid["event_window"]["end"] = invalid["event_window"]["start"]; cases.append(invalid)
        invalid = alignment(); invalid["datasets"][1]["snapshot_token"] = "different"; cases.append(invalid)
        invalid = alignment("watermark"); invalid["datasets"][0]["allowed_lateness_seconds"] = -1; cases.append(invalid)
        invalid = alignment(); invalid["datasets"][1]["id"] = invalid["datasets"][0]["id"]; cases.append(invalid)
        invalid = alignment(); invalid["coordination"]["mode"] = []; cases.append(invalid)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ParisonError):
                normalize_time_alignment(value)

    def test_reconciliation_is_canonical_and_semantically_closed(self):
        value = reconciliation()
        normalized = normalize_reconciliation(value)
        self.assertEqual([item["kind"] for item in normalized["checks"]], ["identity", "reference", "conservation"])
        reordered = copy.deepcopy(value)
        reordered["datasets"].reverse(); reordered["checks"].reverse()
        self.assertEqual(canonical_reconciliation_bytes(value), canonical_reconciliation_bytes(reordered))
        self.assertEqual(canonical_reconciliation_bytes(value), (ROOT / "tests/fixtures/reconciliation-v1.canonical.json").read_bytes().removesuffix(b"\n"))

    def test_reconciliation_rejects_cross_reference_errors(self):
        cases = []
        invalid = reconciliation(); invalid["datasets"][1]["id"] = "payments"; cases.append(invalid)
        invalid = reconciliation(); invalid["checks"][1]["parent_identity"] = "missing"; cases.append(invalid)
        invalid = reconciliation(); invalid["datasets"][0]["columns"][0]["type"] = "integer"; cases.append(invalid)
        invalid = reconciliation(); invalid["checks"][2]["parent_group_columns"] = ["amount"]; cases.append(invalid)
        invalid = reconciliation(); invalid["checks"][1]["parent_identity"] = []; cases.append(invalid)
        invalid = reconciliation(); invalid["checks"].append({"id": "cycle-id", "kind": "identity", "dataset": "payments", "columns": ["payout_id"], "nulls": "forbid"}); invalid["checks"].append({"id": "cycle", "kind": "reference", "child_dataset": "payouts", "child_columns": ["payout_id"], "parent_identity": "cycle-id", "nulls": "forbid"}); cases.append(invalid)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ParisonError):
                normalize_reconciliation(value)

    def test_cli_validates_and_explains_both_contracts(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            alignment_path, reconciliation_path = directory / "alignment.json", directory / "reconciliation.json"
            alignment_path.write_text(json.dumps(alignment()), encoding="utf-8")
            reconciliation_path.write_text(json.dumps(reconciliation()), encoding="utf-8")
            for command, path, digest in (
                ("time-alignment", alignment_path, "alignment_sha256"),
                ("reconciliation", reconciliation_path, "reconciliation_sha256"),
            ):
                with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                    self.assertEqual(main([f"validate-{command}", str(path)]), 0)
                    self.assertEqual(stdout.getvalue(), "valid\n")
                with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                    self.assertEqual(main([f"explain-{command}", str(path)]), 0)
                    self.assertRegex(json.loads(stdout.getvalue())[digest], "^[0-9a-f]{64}$")

    def test_alignment_preflight_pass_fail_and_inconclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            result = preflight_alignment(*files)
            self.assertEqual((result["outcome"], result["alignment_status"]), ("PASS", "PASS"))
            self.assertEqual(result["datasets"][0]["sides"]["baseline"]["in_window"], 1)
            Draft202012Validator(load_schema("alignment-preflight")).validate(result)
            arguments = ["preflight-alignment", "--alignment", str(files[0]), "--reconciliation", str(files[1]), "--receipt", str(files[2])]
            for dataset_id, runtime in files[3].items():
                arguments.extend(["--dataset", dataset_id, str(runtime["recipe"]), str(runtime["baseline"]), str(runtime["candidate"])])
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue())["outcome"], "PASS")
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), timestamp="2026-10-01T00:00:00Z")
            result = preflight_alignment(*files)
            self.assertEqual(result["outcome"], "FAIL")
            self.assertEqual(result["reason_codes"], ["event-time-scope-failed"])
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), mode="declared-cutoff")
            result = preflight_alignment(*files)
            self.assertEqual(result["outcome"], "INCONCLUSIVE")
            self.assertEqual(result["reason_codes"], ["coordination-not-machine-established"])

    def test_alignment_preflight_watermark_and_receipt_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), mode="watermark")
            self.assertEqual(preflight_alignment(*files)["outcome"], "PASS")
            value = json.loads(files[0].read_text(encoding="utf-8"))
            value["datasets"][0]["watermark"] = "2026-09-30T23:59:59.999999Z"
            files[0].write_text(json.dumps(value), encoding="utf-8")
            reconciliation_value = json.loads(files[1].read_text(encoding="utf-8"))
            reconciliation_value["alignment_sha256"] = explain_time_alignment(files[0])["alignment_sha256"]
            files[1].write_text(json.dumps(reconciliation_value), encoding="utf-8")
            self.assertEqual(preflight_alignment(*files)["outcome"], "FAIL")
            files[2].write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "receipt SHA-256"):
                preflight_alignment(*files)

    def test_identity_reference_memory_sqlite_equivalence(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append({"id": "payment-payout", "kind": "reference", "child_dataset": "payments", "child_columns": ["payout_id"], "parent_identity": "payout-id", "nulls": "forbid"})
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            memory = check_identity_references(files[1], files[3], engine="memory")
            sqlite = check_identity_references(files[1], files[3], engine="sqlite", temp_directory=Path(temporary))
            self.assertEqual(memory["outcome"], "PASS")
            self.assertEqual(memory["sides"], sqlite["sides"])
            self.assertGreater(sqlite["temporary_bytes"], 0)
            validator = Draft202012Validator(load_schema("relationship-result"))
            validator.validate(memory); validator.validate(sqlite)
            arguments = ["check-identity-references", "--reconciliation", str(files[1])]
            for dataset_id, runtime in files[3].items():
                arguments.extend(["--dataset", dataset_id, str(runtime["recipe"]), str(runtime["baseline"]), str(runtime["candidate"])])
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue())["sides"], memory["sides"])

    def test_identity_reference_reports_duplicates_orphans_and_null_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append({"id": "payment-payout", "kind": "reference", "child_dataset": "payments", "child_columns": ["payout_id"], "parent_identity": "payout-id", "nulls": "forbid"})
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            files[3]["payouts"]["candidate"].write_text("payout_id,occurred_at,amount\np-1,2026-09-01T00:00:00Z,1.00\np-1,2026-09-02T00:00:00Z,1.00\n", encoding="utf-8")
            files[3]["payments"]["baseline"].write_text("payout_id,occurred_at,amount\nmissing,2026-09-01T00:00:00Z,1.00\n", encoding="utf-8")
            result = check_identity_references(files[1], files[3])
            self.assertEqual(result["outcome"], "FAIL")
            baseline_reference = next(item for item in result["sides"]["baseline"] if item["kind"] == "reference")
            candidate_identity = next(item for item in result["sides"]["candidate"] if item["kind"] == "identity")
            self.assertEqual(baseline_reference["counts"]["orphan_rows"], 1)
            self.assertEqual(candidate_identity["counts"]["duplicate_keys"], 1)

    def test_conservation_memory_sqlite_equivalence_and_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append({"id": "payout-total", "kind": "conservation", "parent_dataset": "payouts", "parent_identity": "payout-id", "parent_group_columns": ["payout_id"], "child_dataset": "payments", "child_group_columns": ["payout_id"], "parent_measure": "amount", "child_measure": "amount", "operator": "sum", "nulls": "forbid", "comparison": "exact", "tolerance": None})
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            memory = check_conservation(files[1], files[3])
            sqlite = check_conservation(files[1], files[3], engine="sqlite", temp_directory=Path(temporary))
            self.assertEqual(memory["outcome"], "PASS")
            self.assertEqual(memory["sides"], sqlite["sides"])
            validator = Draft202012Validator(load_schema("conservation-result"))
            validator.validate(memory); validator.validate(sqlite)
            arguments = ["check-conservation", "--reconciliation", str(files[1])]
            for dataset_id, runtime in files[3].items():
                arguments.extend(["--dataset", dataset_id, str(runtime["recipe"]), str(runtime["baseline"]), str(runtime["candidate"])])
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue())["sides"], memory["sides"])
            files[3]["payments"]["candidate"].write_text("payout_id,occurred_at,amount\np-1,2026-09-01T00:00:00Z,2.00\n", encoding="utf-8")
            failed = check_conservation(files[1], files[3])
            self.assertEqual(failed["outcome"], "FAIL")
            self.assertEqual(failed["sides"]["candidate"][0]["counts"]["different_groups"], 1)

    def test_conservation_tolerance_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append({"id": "payout-total", "kind": "conservation", "parent_dataset": "payouts", "parent_identity": "payout-id", "parent_group_columns": ["payout_id"], "child_dataset": "payments", "child_group_columns": ["payout_id"], "parent_measure": "amount", "child_measure": "amount", "operator": "sum", "nulls": "forbid", "comparison": "tolerance", "tolerance": {"formula": "symmetric-v1", "absolute": 0.01, "relative": 0}})
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            files[3]["payments"]["candidate"].write_text("payout_id,occurred_at,amount\np-1,2026-09-01T00:00:00Z,1.01\n", encoding="utf-8")
            result = check_conservation(files[1], files[3])
            self.assertEqual(result["outcome"], "PASS")
            self.assertEqual(result["sides"]["candidate"][0]["counts"]["within_tolerance_groups"], 1)

    def test_composed_reconciliation_and_summary_safety(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].extend([
                {"id": "payment-payout", "kind": "reference", "child_dataset": "payments", "child_columns": ["payout_id"], "parent_identity": "payout-id", "nulls": "forbid"},
                {"id": "payout-total", "kind": "conservation", "parent_dataset": "payouts", "parent_identity": "payout-id", "parent_group_columns": ["payout_id"], "child_dataset": "payments", "child_group_columns": ["payout_id"], "parent_measure": "amount", "child_measure": "amount", "operator": "sum", "nulls": "forbid", "comparison": "exact", "tolerance": None},
            ])
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            result = run_reconciliation(*files)
            self.assertEqual(result["outcome"], "PASS")
            Draft202012Validator(load_schema("reconciliation-result")).validate(result)
            summary = summarize_reconciliation_result(result)
            rendered = json.dumps(summary)
            for sensitive in ("payments", "payouts", "payout_id", "occurred_at", temporary):
                self.assertNotIn(sensitive, rendered)
            self.assertEqual(summary["dataset_outcome_counts"], {"PASS": 2, "FAIL": 0, "INCONCLUSIVE": 0})
            arguments = ["reconcile", "--alignment", str(files[0]), "--reconciliation", str(files[1]), "--receipt", str(files[2]), "--summary"]
            for dataset_id, runtime in files[3].items():
                arguments.extend(["--dataset", dataset_id, str(runtime["recipe"]), str(runtime["baseline"]), str(runtime["candidate"])])
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue()), summary)

    def test_composed_reconciliation_reduces_fail_before_inconclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), mode="declared-cutoff")
            self.assertEqual(run_reconciliation(*files)["outcome"], "INCONCLUSIVE")
            files[3]["payments"]["candidate"].write_text("payout_id,occurred_at,amount\nother,2026-09-01T00:00:00Z,1.00\n", encoding="utf-8")
            self.assertEqual(run_reconciliation(*files)["outcome"], "FAIL")


if __name__ == "__main__":
    unittest.main()
