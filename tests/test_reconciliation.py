import copy
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

from parison.cli import main
from parison.core import ParisonError, explain_recipe, inspect_bundle, load_schema, verify_bundle
from parison.evidence import evidence_statement, export_statement, report_cutover, verify_statement
from parison.manifesting import (
    capture_reconciliation_input_bindings,
    create_dataset_manifest_v2,
    publish_dataset_evidence_bundle_v2,
)
from parison.reconciliation import (
    _publish_reconciliation_bundle,
    canonical_reconciliation_bytes,
    canonical_time_alignment_bytes,
    check_conservation,
    check_identity_references,
    explain_reconciliation,
    explain_time_alignment,
    file_digest,
    inspect_reconciliation_bundle,
    normalize_reconciliation,
    normalize_time_alignment,
    preflight_alignment,
    publish_reconciliation_bundle,
    run_reconciliation,
    run_reconciliation_with_bindings,
    summarize_reconciliation_result,
    verify_reconciliation_bundle,
)

ROOT = Path(__file__).parents[1]


def alignment(mode="source-snapshot"):
    value = {
        "alignment_version": 1,
        "event_window": {
            "start": "2026-09-01T00:00:00Z",
            "end": "2026-10-01T00:00:00Z",
            "bounds": "start-inclusive-end-exclusive",
        },
        "coordination": {"mode": mode, "claim_id": "september-close-4", "receipt_sha256": "a" * 64},
        "datasets": [
            {
                "id": "payments",
                "event_time_column": "occurred_at",
                "snapshot_token": "snapshot-42",
                "token_domain": "ledger",
            },
            {
                "id": "payouts",
                "event_time_column": "occurred_at",
                "snapshot_token": "snapshot-42",
                "token_domain": "ledger",
            },
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
            {
                "id": "payments",
                "policy_sha256": "c" * 64,
                "columns": [{"name": "payout_id", "type": "string"}, {"name": "amount", "type": "decimal"}],
            },
            {
                "id": "payouts",
                "policy_sha256": "d" * 64,
                "columns": [{"name": "payout_id", "type": "string"}, {"name": "amount", "type": "decimal"}],
            },
        ],
        "checks": [
            {"id": "payout-id", "kind": "identity", "dataset": "payouts", "columns": ["payout_id"], "nulls": "forbid"},
            {
                "id": "payment-payout",
                "kind": "reference",
                "child_dataset": "payments",
                "child_columns": ["payout_id"],
                "parent_identity": "payout-id",
                "nulls": "forbid",
            },
            {
                "id": "payout-total",
                "kind": "conservation",
                "parent_dataset": "payouts",
                "parent_identity": "payout-id",
                "parent_group_columns": ["payout_id"],
                "child_dataset": "payments",
                "child_group_columns": ["payout_id"],
                "parent_measure": "amount",
                "child_measure": "amount",
                "operator": "sum",
                "nulls": "forbid",
                "comparison": "exact",
                "tolerance": None,
            },
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
            "recipe_version": 1,
            "comparison_mode": "keyed",
            "keys": ["payout_id"],
            "scope": {
                "snapshot": "fixture",
                "cutoff": "2026-10-01T00:00:00Z",
                "filters": [],
                "completeness": "full",
                "expected_empty": False,
            },
            "identity": {"null_keys": "reject", "duplicates": "reject"},
            "nulls_equal": True,
            "null_tokens": {"baseline": [], "candidate": []},
            "columns": {
                "payout_id": {"type": "string", "comparison": "exact"},
                "occurred_at": {"type": "timestamp", "comparison": "exact", "timezone": "require-aware"},
                "amount": {"type": "decimal", "comparison": "exact", "scale": 2},
            },
            "column_mappings": {},
            "excluded_columns": {},
            "delimiters": {"baseline": ",", "candidate": ","},
            "input_projection": "semantic-scalar-v1",
            "output": {"sensitivity": "summary"},
        }
        recipe_path = directory / "recipe.json"
        recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
        policy_sha256 = explain_recipe(recipe_path)["policy_sha256"]
        reconciliation_value = {
            "reconciliation_version": 1,
            "alignment_sha256": explain_time_alignment(alignment_path)["alignment_sha256"],
            "datasets": [
                {
                    "id": dataset_id,
                    "policy_sha256": policy_sha256,
                    "columns": [
                        {"name": "payout_id", "type": "string"},
                        {"name": "occurred_at", "type": "timestamp"},
                        {"name": "amount", "type": "decimal"},
                    ],
                }
                for dataset_id in ("payments", "payouts")
            ],
            "checks": [
                {
                    "id": "payout-id",
                    "kind": "identity",
                    "dataset": "payouts",
                    "columns": ["payout_id"],
                    "nulls": "forbid",
                }
            ],
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

    def test_fresh_reconciliation_input_capture_binds_sources_and_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = explain_reconciliation(files[1])
            captured = capture_reconciliation_input_bindings(declaration, files[3])
            self.assertEqual(
                captured["policy"], {"kind": "reconciliation", "sha256": declaration["reconciliation_sha256"]}
            )
            self.assertEqual(len(captured["bindings"]), 4)
            self.assertEqual(captured["bindings"][0]["selection"], {"kind": "file"})
            Draft202012Validator(
                json.loads((ROOT / "src/parison/schemas/input-bindings-v1.schema.json").read_text())
            ).validate(captured)
            files[3]["payments"]["baseline"].write_text("changed", encoding="utf-8")
            self.assertNotEqual(captured, capture_reconciliation_input_bindings(declaration, files[3]))

    def test_versioned_reconciliation_bundle_verifies_input_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            bundle = root / "bound-run"
            run_reconciliation_with_bindings(bundle, *files)
            manifest = verify_bundle(bundle)
            self.assertEqual(manifest["schema_version"], 2)
            statement = evidence_statement(bundle)
            self.assertEqual(statement["predicateType"], "https://parison.dev/attestations/evidence/v2")
            self.assertEqual(statement["predicate"]["policy"]["kind"], "reconciliation")
            Draft202012Validator(load_schema("statement-v2")).validate(statement)
            handoff = root / "reconciliation-statement.json"
            export_statement(bundle, handoff)
            self.assertEqual(verify_statement(bundle, handoff)["status"], "valid")
            self.assertNotIn(str(root), handoff.read_text())
            forged = json.loads(handoff.read_text())
            forged["predicate"]["coordinationOutcome"] = "FAIL"
            changed = root / "changed-statement.json"
            changed.write_text(json.dumps(forged), encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "does not match"):
                verify_statement(bundle, changed)
            report = root / "reconciliation-report.md"
            report_cutover(bundle, report)
            self.assertIn("Coordination outcome", report.read_text())
            Draft202012Validator(load_schema("reconciliation-manifest-v2")).validate(manifest)
            self.assertNotIn(str(root), (bundle / "input-bindings.json").read_text())
            command = [
                "reconcile",
                "--alignment",
                str(files[0]),
                "--reconciliation",
                str(files[1]),
                "--receipt",
                str(files[2]),
                "--output",
                str(root / "cli-run"),
                "--input-bindings",
            ]
            for identifier, sources in files[3].items():
                command.extend(
                    [
                        "--dataset",
                        identifier,
                        str(sources["recipe"]),
                        str(sources["baseline"]),
                        str(sources["candidate"]),
                    ]
                )
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(command), 0)
            self.assertEqual(verify_bundle(root / "cli-run")["schema_version"], 2)
            record = json.loads((bundle / "input-bindings.json").read_text())
            original_record = (bundle / "input-bindings.json").read_text()
            record["bindings"][0]["policy_sha256"] = "0" * 64
            member = bundle / "input-bindings.json"
            member.write_text(json.dumps(record), encoding="utf-8")
            manifest_path = bundle / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files"]["input-bindings.json"] = file_digest(member)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ParisonError):
                verify_bundle(bundle)
            member.write_text(original_record.replace('"binding_version":1', '"binding_version":1,"binding_version":1'))
            manifest["files"]["input-bindings.json"] = file_digest(member)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "duplicate JSON key"):
                verify_bundle(bundle)

    def test_same_file_selector_change_cannot_publish_old_reconciliation_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            old_result = run_reconciliation(*files)
            document = root / "selected.json"
            document.write_text('{"left":[],"right":[]}', encoding="utf-8")
            files[3]["payments"]["baseline"] = f"json:{document}#/left"
            old_result["datasets"][0]["baseline_sha256"] = file_digest(document)

            def change_selector(*_args, **_kwargs):
                files[3]["payments"]["baseline"] = f"json:{document}#/right"
                return old_result

            output = root / "substituted"
            with patch("parison.reconciliation.run_reconciliation", side_effect=change_selector):
                with self.assertRaisesRegex(ParisonError, "changed during execution"):
                    run_reconciliation_with_bindings(output, *files)
            self.assertFalse(output.exists())

    def test_versioned_publication_rejects_invalid_staging_and_cleans_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            result = run_reconciliation(*files)
            record = capture_reconciliation_input_bindings(explain_reconciliation(files[1]), files[3])
            result["outcome"] = "FAIL"
            output = root / "invalid-bound-run"
            with self.assertRaisesRegex(ParisonError, "metadata is inconsistent"):
                _publish_reconciliation_bundle(output, result, files[0], files[1], record, files[3])
            self.assertFalse(output.exists())
            self.assertFalse(list(root.glob(".invalid-bound-run-*")))

    def test_reconciliation_dataset_v2_publication_binds_receipt_and_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            semantic = root / "semantic-run"
            run_reconciliation_with_bindings(semantic, *files)
            policy = explain_reconciliation(files[1])
            physical = [
                files[2],
                *(files[3][identifier][role] for identifier in files[3] for role in ("baseline", "candidate")),
            ]
            inventory = [
                {"path": path.name, "bytes": path.stat().st_size, "sha256": file_digest(path)} for path in physical
            ]
            bindings = [
                {
                    "id": dataset["id"],
                    "role": role,
                    "source_kind": "file",
                    "source": files[3][dataset["id"]][role].name,
                    "members": [files[3][dataset["id"]][role].name],
                    "source_sha256": file_digest(files[3][dataset["id"]][role]),
                    "policy_sha256": dataset["policy_sha256"],
                }
                for dataset in policy["datasets"]
                for role in ("baseline", "candidate")
            ]
            draft = root / "draft.json"
            draft.write_text(
                json.dumps(
                    {
                        "manifest_version": 2,
                        "collection_id": "reconciled",
                        "policy": {"kind": "reconciliation", "sha256": policy["reconciliation_sha256"]},
                        "closed_scopes": [],
                        "files": inventory,
                        "bindings": bindings,
                    }
                ),
                encoding="utf-8",
            )
            manifest = root / "dataset-manifest.json"
            create_dataset_manifest_v2(root, draft, manifest, files[1])
            output = root / "dataset-evidence"
            publish_dataset_evidence_bundle_v2(output, manifest, root, files[1], semantic)
            self.assertEqual(verify_bundle(output)["schema_version"], 2)
            self.assertEqual(inspect_bundle(output)["binding_count"], 4)
            statement = evidence_statement(output)
            self.assertEqual(statement["predicate"]["bundleKind"], "dataset-evidence")
            self.assertEqual(statement["predicate"]["policy"]["kind"], "reconciliation")
            Draft202012Validator(load_schema("statement-v2")).validate(statement)
            handoff = root / "dataset-statement.json"
            export_statement(output, handoff)
            self.assertEqual(verify_statement(output, handoff)["status"], "valid")
            self.assertNotIn(str(root), handoff.read_text())

    def test_typed_statement_wire_fixture(self):
        payload = (ROOT / "tests/fixtures/statement-reconciliation-v2.canonical.json").read_bytes()
        value = json.loads(payload)
        self.assertEqual(
            payload, (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
        Draft202012Validator(load_schema("statement-v2")).validate(value)

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
        self.assertEqual(
            canonical_time_alignment_bytes(alignment()),
            (ROOT / "tests/fixtures/time-alignment-v1.canonical.json").read_bytes().removesuffix(b"\n"),
        )

    def test_alignment_rejects_ambiguous_time_and_coordination(self):
        cases = []
        invalid = alignment()
        invalid["event_window"]["start"] = "2026-09-01T00:00:00+00:00"
        cases.append(invalid)
        invalid = alignment()
        invalid["event_window"]["end"] = invalid["event_window"]["start"]
        cases.append(invalid)
        invalid = alignment()
        invalid["datasets"][1]["snapshot_token"] = "different"
        cases.append(invalid)
        invalid = alignment("watermark")
        invalid["datasets"][0]["allowed_lateness_seconds"] = -1
        cases.append(invalid)
        invalid = alignment()
        invalid["datasets"][1]["id"] = invalid["datasets"][0]["id"]
        cases.append(invalid)
        invalid = alignment()
        invalid["coordination"]["mode"] = []
        cases.append(invalid)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ParisonError):
                normalize_time_alignment(value)

    def test_reconciliation_is_canonical_and_semantically_closed(self):
        value = reconciliation()
        normalized = normalize_reconciliation(value)
        self.assertEqual([item["kind"] for item in normalized["checks"]], ["identity", "reference", "conservation"])
        reordered = copy.deepcopy(value)
        reordered["datasets"].reverse()
        reordered["checks"].reverse()
        self.assertEqual(canonical_reconciliation_bytes(value), canonical_reconciliation_bytes(reordered))
        self.assertEqual(
            canonical_reconciliation_bytes(value),
            (ROOT / "tests/fixtures/reconciliation-v1.canonical.json").read_bytes().removesuffix(b"\n"),
        )

    def test_reconciliation_rejects_cross_reference_errors(self):
        cases = []
        invalid = reconciliation()
        invalid["datasets"][1]["id"] = "payments"
        cases.append(invalid)
        invalid = reconciliation()
        invalid["checks"][1]["parent_identity"] = "missing"
        cases.append(invalid)
        invalid = reconciliation()
        invalid["datasets"][0]["columns"][0]["type"] = "integer"
        cases.append(invalid)
        invalid = reconciliation()
        invalid["checks"][2]["parent_group_columns"] = ["amount"]
        cases.append(invalid)
        invalid = reconciliation()
        invalid["checks"][1]["parent_identity"] = []
        cases.append(invalid)
        invalid = reconciliation()
        invalid["checks"].append(
            {"id": "cycle-id", "kind": "identity", "dataset": "payments", "columns": ["payout_id"], "nulls": "forbid"}
        )
        invalid["checks"].append(
            {
                "id": "cycle",
                "kind": "reference",
                "child_dataset": "payouts",
                "child_columns": ["payout_id"],
                "parent_identity": "cycle-id",
                "nulls": "forbid",
            }
        )
        cases.append(invalid)
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
            arguments = [
                "preflight-alignment",
                "--alignment",
                str(files[0]),
                "--reconciliation",
                str(files[1]),
                "--receipt",
                str(files[2]),
            ]
            for dataset_id, runtime in files[3].items():
                arguments.extend(
                    [
                        "--dataset",
                        dataset_id,
                        str(runtime["recipe"]),
                        str(runtime["baseline"]),
                        str(runtime["candidate"]),
                    ]
                )
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

    def test_alignment_preflight_rejects_malformed_event_time(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), timestamp="not-a-timestamp")
            with self.assertRaises(ParisonError):
                preflight_alignment(*files)

    def test_identity_reference_memory_sqlite_equivalence(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append(
                {
                    "id": "payment-payout",
                    "kind": "reference",
                    "child_dataset": "payments",
                    "child_columns": ["payout_id"],
                    "parent_identity": "payout-id",
                    "nulls": "forbid",
                }
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            memory = check_identity_references(files[1], files[3], engine="memory")
            sqlite = check_identity_references(files[1], files[3], engine="sqlite", temp_directory=Path(temporary))
            self.assertEqual(memory["outcome"], "PASS")
            self.assertEqual(memory, sqlite)
            validator = Draft202012Validator(load_schema("relationship-result"))
            validator.validate(memory)
            validator.validate(sqlite)
            arguments = ["check-identity-references", "--reconciliation", str(files[1])]
            for dataset_id, runtime in files[3].items():
                arguments.extend(
                    [
                        "--dataset",
                        dataset_id,
                        str(runtime["recipe"]),
                        str(runtime["baseline"]),
                        str(runtime["candidate"]),
                    ]
                )
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue())["sides"], memory["sides"])

    def test_identity_reference_reports_duplicates_orphans_and_null_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append(
                {
                    "id": "payment-payout",
                    "kind": "reference",
                    "child_dataset": "payments",
                    "child_columns": ["payout_id"],
                    "parent_identity": "payout-id",
                    "nulls": "forbid",
                }
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            files[3]["payouts"]["candidate"].write_text(
                "payout_id,occurred_at,amount\np-1,2026-09-01T00:00:00Z,1.00\np-1,2026-09-02T00:00:00Z,1.00\n",
                encoding="utf-8",
            )
            files[3]["payments"]["baseline"].write_text(
                "payout_id,occurred_at,amount\nmissing,2026-09-01T00:00:00Z,1.00\n", encoding="utf-8"
            )
            result = check_identity_references(files[1], files[3])
            self.assertEqual(result["outcome"], "FAIL")
            baseline_reference = next(item for item in result["sides"]["baseline"] if item["kind"] == "reference")
            candidate_identity = next(item for item in result["sides"]["candidate"] if item["kind"] == "identity")
            self.assertEqual(baseline_reference["counts"]["orphan_rows"], 1)
            self.assertEqual(candidate_identity["counts"]["duplicate_keys"], 1)

    def test_reference_null_policies_are_explicit(self):
        for nulls, parent_null, expected_exempt in (("all-null-exempt", False, 1), ("match-null", True, 0)):
            with self.subTest(nulls=nulls), tempfile.TemporaryDirectory() as temporary:
                files = self._preflight_files(Path(temporary))
                declaration = json.loads(files[1].read_text(encoding="utf-8"))
                declaration["checks"][0]["nulls"] = "equal" if parent_null else "forbid"
                declaration["checks"].append(
                    {
                        "id": "payment-payout",
                        "kind": "reference",
                        "child_dataset": "payments",
                        "child_columns": ["payout_id"],
                        "parent_identity": "payout-id",
                        "nulls": nulls,
                    }
                )
                files[1].write_text(json.dumps(declaration), encoding="utf-8")
                for side in ("baseline", "candidate"):
                    child = Path(temporary) / f"payments-{side}.jsonl"
                    child.write_text(
                        '{"payout_id":null,"occurred_at":"2026-09-01T00:00:00Z","amount":"1.00"}\n', encoding="utf-8"
                    )
                    files[3]["payments"][side] = child
                    if parent_null:
                        parent = Path(temporary) / f"payouts-{side}.jsonl"
                        parent.write_text(
                            '{"payout_id":null,"occurred_at":"2026-09-01T00:00:00Z","amount":"1.00"}\n',
                            encoding="utf-8",
                        )
                        files[3]["payouts"][side] = parent
                result = check_identity_references(files[1], files[3])
                self.assertEqual(result["outcome"], "PASS")
                reference = next(item for item in result["sides"]["baseline"] if item["kind"] == "reference")
                self.assertEqual(reference["counts"]["exempt_rows"], expected_exempt)

    def test_conservation_memory_sqlite_equivalence_and_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append(
                {
                    "id": "payout-total",
                    "kind": "conservation",
                    "parent_dataset": "payouts",
                    "parent_identity": "payout-id",
                    "parent_group_columns": ["payout_id"],
                    "child_dataset": "payments",
                    "child_group_columns": ["payout_id"],
                    "parent_measure": "amount",
                    "child_measure": "amount",
                    "operator": "sum",
                    "nulls": "forbid",
                    "comparison": "exact",
                    "tolerance": None,
                }
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            memory = check_conservation(files[1], files[3])
            sqlite = check_conservation(files[1], files[3], engine="sqlite", temp_directory=Path(temporary))
            self.assertEqual(memory["outcome"], "PASS")
            self.assertEqual(memory, sqlite)
            validator = Draft202012Validator(load_schema("conservation-result"))
            validator.validate(memory)
            validator.validate(sqlite)
            arguments = ["check-conservation", "--reconciliation", str(files[1])]
            for dataset_id, runtime in files[3].items():
                arguments.extend(
                    [
                        "--dataset",
                        dataset_id,
                        str(runtime["recipe"]),
                        str(runtime["baseline"]),
                        str(runtime["candidate"]),
                    ]
                )
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue())["sides"], memory["sides"])
            files[3]["payments"]["candidate"].write_text(
                "payout_id,occurred_at,amount\np-1,2026-09-01T00:00:00Z,2.00\n", encoding="utf-8"
            )
            failed = check_conservation(files[1], files[3])
            self.assertEqual(failed["outcome"], "FAIL")
            self.assertEqual(failed["sides"]["candidate"][0]["counts"]["different_groups"], 1)

    def test_conservation_tolerance_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append(
                {
                    "id": "payout-total",
                    "kind": "conservation",
                    "parent_dataset": "payouts",
                    "parent_identity": "payout-id",
                    "parent_group_columns": ["payout_id"],
                    "child_dataset": "payments",
                    "child_group_columns": ["payout_id"],
                    "parent_measure": "amount",
                    "child_measure": "amount",
                    "operator": "sum",
                    "nulls": "forbid",
                    "comparison": "tolerance",
                    "tolerance": {"formula": "symmetric-v1", "absolute": 0.01, "relative": 0},
                }
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            files[3]["payments"]["candidate"].write_text(
                "payout_id,occurred_at,amount\np-1,2026-09-01T00:00:00Z,1.01\n", encoding="utf-8"
            )
            result = check_conservation(files[1], files[3])
            self.assertEqual(result["outcome"], "PASS")
            self.assertEqual(result["sides"]["candidate"][0]["counts"]["within_tolerance_groups"], 1)

    def test_conservation_zero_nulls_negative_values_and_signed_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append(
                {
                    "id": "payout-total",
                    "kind": "conservation",
                    "parent_dataset": "payouts",
                    "parent_identity": "payout-id",
                    "parent_group_columns": ["payout_id"],
                    "child_dataset": "payments",
                    "child_group_columns": ["payout_id"],
                    "parent_measure": "amount",
                    "child_measure": "amount",
                    "operator": "sum",
                    "nulls": "zero",
                    "comparison": "exact",
                    "tolerance": None,
                }
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            for side in ("baseline", "candidate"):
                parent = Path(temporary) / f"payouts-{side}.jsonl"
                child = Path(temporary) / f"payments-{side}.jsonl"
                parent.write_text(
                    '{"payout_id":"p-1","occurred_at":"2026-09-01T00:00:00Z","amount":"-0.00"}\n', encoding="utf-8"
                )
                child.write_text(
                    '{"payout_id":"p-1","occurred_at":"2026-09-01T00:00:00Z","amount":null}\n', encoding="utf-8"
                )
                files[3]["payouts"][side], files[3]["payments"][side] = parent, child
            result = check_conservation(files[1], files[3])
            self.assertEqual(result["outcome"], "PASS")
            self.assertEqual(result["sides"]["baseline"][0]["counts"]["exact_groups"], 1)

    def test_composed_reconciliation_and_summary_safety(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].extend(
                [
                    {
                        "id": "payment-payout",
                        "kind": "reference",
                        "child_dataset": "payments",
                        "child_columns": ["payout_id"],
                        "parent_identity": "payout-id",
                        "nulls": "forbid",
                    },
                    {
                        "id": "payout-total",
                        "kind": "conservation",
                        "parent_dataset": "payouts",
                        "parent_identity": "payout-id",
                        "parent_group_columns": ["payout_id"],
                        "child_dataset": "payments",
                        "child_group_columns": ["payout_id"],
                        "parent_measure": "amount",
                        "child_measure": "amount",
                        "operator": "sum",
                        "nulls": "forbid",
                        "comparison": "exact",
                        "tolerance": None,
                    },
                ]
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            result = run_reconciliation(*files)
            self.assertEqual(result["outcome"], "PASS")
            Draft202012Validator(load_schema("reconciliation-result")).validate(result)
            summary = summarize_reconciliation_result(result)
            rendered = json.dumps(summary)
            for sensitive in ("payments", "payouts", "payout_id", "occurred_at", temporary):
                self.assertNotIn(sensitive, rendered)
            self.assertEqual(summary["dataset_outcome_counts"], {"PASS": 2, "FAIL": 0, "INCONCLUSIVE": 0})
            arguments = [
                "reconcile",
                "--alignment",
                str(files[0]),
                "--reconciliation",
                str(files[1]),
                "--receipt",
                str(files[2]),
                "--summary",
            ]
            for dataset_id, runtime in files[3].items():
                arguments.extend(
                    [
                        "--dataset",
                        dataset_id,
                        str(runtime["recipe"]),
                        str(runtime["baseline"]),
                        str(runtime["candidate"]),
                    ]
                )
            with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
                self.assertEqual(json.loads(stdout.getvalue()), summary)
            sqlite = run_reconciliation(*files, engine="sqlite", temp_directory=Path(temporary))
            self.assertEqual(result, sqlite)

    def test_composed_reconciliation_reduces_fail_before_inconclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), mode="declared-cutoff")
            self.assertEqual(run_reconciliation(*files)["outcome"], "INCONCLUSIVE")
            files[3]["payments"]["candidate"].write_text(
                "payout_id,occurred_at,amount\nother,2026-09-01T00:00:00Z,1.00\n", encoding="utf-8"
            )
            self.assertEqual(run_reconciliation(*files)["outcome"], "FAIL")

    def test_relational_migration_can_pass_parity_but_fail_relationships(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"].append(
                {
                    "id": "payment-payout",
                    "kind": "reference",
                    "child_dataset": "payments",
                    "child_columns": ["payout_id"],
                    "parent_identity": "payout-id",
                    "nulls": "forbid",
                }
            )
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            for side in ("baseline", "candidate"):
                files[3]["payments"][side].write_text(
                    "payout_id,occurred_at,amount\nmissing,2026-09-01T00:00:00Z,1.00\n", encoding="utf-8"
                )
            result = run_reconciliation(*files)
            self.assertEqual([item["outcome"] for item in result["datasets"]], ["PASS", "PASS"])
            self.assertEqual(result["outcome"], "FAIL")
            self.assertTrue(
                all(
                    item["counts"]["orphan_rows"] == 1
                    for item in result["relationships"]["baseline"] + result["relationships"]["candidate"]
                    if item["kind"] == "reference"
                )
            )

    def test_partitioned_backfill_can_pass_data_but_remain_inconclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary), mode="declared-cutoff")
            for runtime in files[3].values():
                for side in ("baseline", "candidate"):
                    source = runtime[side]
                    partitioned = source.parent / f"{source.stem}-partitions"
                    partitioned.mkdir()
                    (partitioned / "02.csv").write_text("payout_id,occurred_at,amount\n", encoding="utf-8")
                    (partitioned / "01.csv").write_bytes(source.read_bytes())
                    runtime[side] = partitioned
            result = run_reconciliation(*files)
            self.assertEqual([item["outcome"] for item in result["datasets"]], ["PASS", "PASS"])
            self.assertEqual(result["outcome"], "INCONCLUSIVE")
            self.assertEqual(result["alignment"]["reason_codes"], ["coordination-not-machine-established"])

    def test_alignment_preflight_qualifies_pre_epoch_offsets_null_and_missing_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            files = self._preflight_files(Path(temporary))
            declaration = json.loads(files[0].read_text(encoding="utf-8"))
            declaration["event_window"].update(start="1969-12-31T00:00:00Z", end="1970-01-02T00:00:00Z")
            files[0].write_text(json.dumps(declaration), encoding="utf-8")
            reconciliation_value = json.loads(files[1].read_text(encoding="utf-8"))
            reconciliation_value["alignment_sha256"] = explain_time_alignment(files[0])["alignment_sha256"]
            files[1].write_text(json.dumps(reconciliation_value), encoding="utf-8")
            for runtime in files[3].values():
                for side in ("baseline", "candidate"):
                    runtime[side].write_text(
                        "payout_id,occurred_at,amount\np-1,1970-01-01T01:00:00+01:00,1.00\n", encoding="utf-8"
                    )
            self.assertEqual(preflight_alignment(*files)["outcome"], "PASS")
            candidate = Path(temporary) / "payments-candidate.jsonl"
            candidate.write_text('{"payout_id":"p-1","occurred_at":null,"amount":"1.00"}\n', encoding="utf-8")
            files[3]["payments"]["candidate"] = candidate
            self.assertEqual(preflight_alignment(*files)["outcome"], "FAIL")
            files[2].unlink()
            with self.assertRaisesRegex(ParisonError, "receipt"):
                preflight_alignment(*files)

    def test_reconciliation_bundle_is_atomic_verified_and_summary_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            result = run_reconciliation(*files)
            bundle = root / "bundle"
            publish_reconciliation_bundle(bundle, result, files[0], files[1])
            self.assertEqual(verify_reconciliation_bundle(bundle)["outcome"], "PASS")
            self.assertEqual(verify_bundle(bundle)["kind"], "reconciliation")
            inspected = inspect_reconciliation_bundle(bundle)
            self.assertEqual(inspect_bundle(bundle), inspected)
            self.assertEqual(inspected["kind"], "reconciliation")
            self.assertNotIn("payout", json.dumps(inspected))
            with self.assertRaisesRegex(ParisonError, "already exists"):
                publish_reconciliation_bundle(bundle, result, files[0], files[1])
            (bundle / "summary.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ParisonError, "integrity check"):
                verify_reconciliation_bundle(bundle)

    def test_reconciliation_bundle_verification_binds_receipt_and_dataset_policies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            bundle = root / "bundle"
            publish_reconciliation_bundle(bundle, run_reconciliation(*files), files[0], files[1])

            def rewrite(name, mutate):
                path = bundle / name
                value = json.loads(path.read_text(encoding="utf-8"))
                mutate(value)
                path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                manifest_path = bundle / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["files"][name] = file_digest(path)
                manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            rewrite("reconciliation-result.json", lambda value: value.update(receipt_sha256="f" * 64))
            rewrite("summary.json", lambda value: value.update(receipt_sha256="f" * 64))
            with self.assertRaisesRegex(ParisonError, "metadata is inconsistent"):
                verify_reconciliation_bundle(bundle)

            shutil.rmtree(bundle)
            publish_reconciliation_bundle(bundle, run_reconciliation(*files), files[0], files[1])
            rewrite("reconciliation-result.json", lambda value: value["datasets"][0].update(policy_sha256="f" * 64))
            with self.assertRaisesRegex(ParisonError, "metadata is inconsistent"):
                verify_reconciliation_bundle(bundle)

    def test_hardened_verifier_accepts_produced_alignment_outcomes(self):
        for mode, timestamp, expected in (
            ("source-snapshot", "2026-09-01T00:00:00Z", "PASS"),
            ("declared-cutoff", "2026-09-01T00:00:00Z", "INCONCLUSIVE"),
            ("watermark", "2026-09-01T00:00:00Z", "PASS"),
            ("source-snapshot", "2026-10-01T00:00:00Z", "FAIL"),
            ("declared-cutoff", "2026-10-01T00:00:00Z", "FAIL"),
        ):
            with self.subTest(mode=mode, timestamp=timestamp), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                files = self._preflight_files(root, mode=mode, timestamp=timestamp)
                result = run_reconciliation(*files)
                self.assertEqual(result["outcome"], expected)
                publish_reconciliation_bundle(root / "bundle", result, files[0], files[1])
                self.assertEqual(verify_reconciliation_bundle(root / "bundle")["outcome"], expected)

    def test_verifier_rejects_inconsistent_counts_with_valid_file_digests(self):
        mutations = json.loads(
            (ROOT / "tests/fixtures/2.2/reconciliation-count-mutations.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            declaration = json.loads(files[1].read_text(encoding="utf-8"))
            declaration["checks"] = reconciliation()["checks"]
            files[1].write_text(json.dumps(declaration), encoding="utf-8")
            original = run_reconciliation(*files)
            for mutation in mutations:
                with self.subTest(mutation=mutation["id"]):
                    result = copy.deepcopy(original)
                    item = next(
                        item for item in result["relationships"]["baseline"] if item["kind"] == mutation["kind"]
                    )
                    item["counts"].update(mutation["changes"])
                    for key in mutation["remove"]:
                        del item["counts"][key]
                    bundle = root / mutation["id"]
                    publish_reconciliation_bundle(bundle, result, files[0], files[1])
                    with self.assertRaises(ParisonError):
                        verify_reconciliation_bundle(bundle)
            for label in ("conservation", "alignment", "child-placement"):
                with self.subTest(component=label):
                    result = copy.deepcopy(original)
                    if label == "conservation":
                        result[label]["baseline"][0]["counts"]["groups"] += 1
                    elif label == "child-placement":
                        result["conservation"]["baseline"][0]["counts"]["parent_without_children_groups"] = 1
                    else:
                        result[label]["datasets"][0]["sides"]["baseline"]["rows"] += 1
                    bundle = root / label
                    publish_reconciliation_bundle(bundle, result, files[0], files[1])
                    with self.assertRaises(ParisonError):
                        verify_reconciliation_bundle(bundle)
            valid = root / "valid"
            publish_reconciliation_bundle(valid, original, files[0], files[1])
            self.assertEqual(verify_reconciliation_bundle(valid)["outcome"], "PASS")

    def test_hardened_verifier_accepts_conservation_producer_edges(self):
        for case in ("empty", "parent-without-children", "null-zero", "tolerant"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                files = self._preflight_files(root)
                declaration = json.loads(files[1].read_text(encoding="utf-8"))
                check = copy.deepcopy(reconciliation()["checks"][-1])
                if case == "null-zero":
                    check["nulls"] = "zero"
                if case == "tolerant":
                    check["comparison"] = "tolerance"
                    check["tolerance"] = {"formula": "symmetric-v1", "absolute": 1.0, "relative": 0}
                declaration["checks"].append(check)
                files[1].write_text(json.dumps(declaration), encoding="utf-8")
                for dataset in ("payouts", "payments"):
                    for side in ("baseline", "candidate"):
                        path = root / f"{dataset}-{side}.jsonl"
                        rows = []
                        if case != "empty" and not (case == "parent-without-children" and dataset == "payments"):
                            amount = None if case == "null-zero" and dataset == "payments" else "0.00"
                            if case == "tolerant" and dataset == "payments":
                                amount = "0.50"
                            rows.append({"payout_id": "p-1", "occurred_at": "2026-09-01T00:00:00Z", "amount": amount})
                        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
                        if not rows:
                            path = root / f"{dataset}-{side}.csv"
                            path.write_text("payout_id,occurred_at,amount\n", encoding="utf-8")
                        files[3][dataset][side] = path
                result = run_reconciliation(*files)
                counts = result["conservation"]["baseline"][0]["counts"]
                if case == "empty":
                    self.assertEqual(counts["groups"], 0)
                elif case == "parent-without-children":
                    self.assertEqual(counts["parent_without_children_groups"], 1)
                elif case == "null-zero":
                    self.assertEqual(counts["exact_groups"], 1)
                    self.assertEqual(counts["null_measure_rows"], 0)
                if case == "tolerant":
                    self.assertEqual(counts["within_tolerance_groups"], 1)
                self.assertEqual(
                    result["outcome"], "INCONCLUSIVE" if case in {"empty", "parent-without-children"} else "PASS"
                )
                publish_reconciliation_bundle(root / "bundle", result, files[0], files[1])
                self.assertEqual(verify_reconciliation_bundle(root / "bundle")["outcome"], result["outcome"])

    def test_verifier_controls_malformed_collections(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            original = run_reconciliation(*files)
            for label in ("datasets-null", "component-null", "outcome-array"):
                with self.subTest(shape=label):
                    bundle = root / label
                    publish_reconciliation_bundle(bundle, original, files[0], files[1])
                    result = copy.deepcopy(original)
                    if label == "datasets-null":
                        result["datasets"] = None
                    elif label == "component-null":
                        result["relationships"]["baseline"].append(None)
                    else:
                        result["relationships"]["baseline"][0]["outcome"] = []
                    path = bundle / "reconciliation-result.json"
                    path.write_text(json.dumps(result), encoding="utf-8")
                    manifest_path = bundle / "manifest.json"
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest["files"][path.name] = file_digest(path)
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaises(ParisonError):
                        verify_reconciliation_bundle(bundle)

    def test_reconcile_cli_publishes_and_verifies_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            bundle = root / "bundle"
            arguments = [
                "reconcile",
                "--alignment",
                str(files[0]),
                "--reconciliation",
                str(files[1]),
                "--receipt",
                str(files[2]),
                "--output",
                str(bundle),
            ]
            for dataset_id, runtime in files[3].items():
                arguments.extend(
                    [
                        "--dataset",
                        dataset_id,
                        str(runtime["recipe"]),
                        str(runtime["baseline"]),
                        str(runtime["candidate"]),
                    ]
                )
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(main(arguments), 0)
            for command in ("verify-reconciliation", "inspect-reconciliation"):
                with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()):
                    self.assertEqual(main([command, str(bundle)]), 0)
                    self.assertEqual(json.loads(stdout.getvalue())["outcome"], "PASS")

    def test_sqlite_and_publication_cleanup_on_interruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            with (
                patch("parison.reconciliation._iter_input_rows", side_effect=KeyboardInterrupt),
                self.assertRaises(KeyboardInterrupt),
            ):
                check_identity_references(files[1], files[3], engine="sqlite", temp_directory=root)
            self.assertEqual(list(root.glob("parison-reconciliation-*")), [])
            result = run_reconciliation(*files)
            with (
                patch("parison.reconciliation._rename_no_replace", side_effect=KeyboardInterrupt),
                self.assertRaises(KeyboardInterrupt),
            ):
                publish_reconciliation_bundle(root / "interrupted", result, files[0], files[1])
            self.assertFalse((root / "interrupted").exists())
            self.assertEqual(list(root.glob(".interrupted-*")), [])

    def test_publication_does_not_replace_concurrently_created_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            result = run_reconciliation(*files)
            target = root / "raced"
            from parison.reconciliation import _rename_no_replace

            def race(source, destination):
                destination.mkdir()
                return _rename_no_replace(source, destination)

            with (
                patch("parison.reconciliation._rename_no_replace", side_effect=race),
                self.assertRaisesRegex(ParisonError, "cannot publish"),
            ):
                publish_reconciliation_bundle(target, result, files[0], files[1])
            self.assertEqual(list(target.iterdir()), [])
            self.assertEqual(list(root.glob(".raced-*")), [])

    def test_publication_exposes_only_the_complete_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = self._preflight_files(root)
            result = run_reconciliation(*files)
            target = root / "bundle"
            from parison.reconciliation import _rename_no_replace

            def observe(source, destination):
                self.assertFalse(destination.exists())
                self.assertEqual(
                    {path.name for path in source.iterdir()},
                    {
                        "effective-alignment.json",
                        "effective-reconciliation.json",
                        "manifest.json",
                        "reconciliation-result.json",
                        "summary.json",
                    },
                )
                return _rename_no_replace(source, destination)

            with patch("parison.reconciliation._rename_no_replace", side_effect=observe):
                publish_reconciliation_bundle(target, result, files[0], files[1])
            self.assertEqual(verify_reconciliation_bundle(target)["outcome"], "PASS")


if __name__ == "__main__":
    unittest.main()
