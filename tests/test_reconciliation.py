import copy
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, load_schema
from parison.reconciliation import canonical_reconciliation_bytes, canonical_time_alignment_bytes, explain_reconciliation, explain_time_alignment, normalize_reconciliation, normalize_time_alignment


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
            {"id": "payments", "recipe_sha256": "c" * 64, "columns": [{"name": "payout_id", "type": "string"}, {"name": "amount", "type": "decimal"}]},
            {"id": "payouts", "recipe_sha256": "d" * 64, "columns": [{"name": "payout_id", "type": "string"}, {"name": "amount", "type": "decimal"}]},
        ],
        "checks": [
            {"id": "payout-id", "kind": "identity", "dataset": "payouts", "columns": ["payout_id"], "nulls": "forbid"},
            {"id": "payment-payout", "kind": "reference", "child_dataset": "payments", "child_columns": ["payout_id"], "parent_identity": "payout-id", "nulls": "forbid"},
            {"id": "payout-total", "kind": "conservation", "parent_dataset": "payouts", "parent_identity": "payout-id", "parent_group_columns": ["payout_id"], "child_dataset": "payments", "child_group_columns": ["payout_id"], "parent_measure": "amount", "child_measure": "amount", "operator": "sum", "nulls": "forbid", "comparison": "exact", "tolerance": None},
        ],
    }


class ReconciliationContracts(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
