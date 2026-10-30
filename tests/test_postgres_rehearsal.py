"""Pinned end-to-end offline migration rehearsal and hostile evidence corpus."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from parison.analysis import _canonical
from parison.core import ParisonError, compare, explain_recipe
from parison.postgres_rehearsal import _identity, main, run, verify
from parison.reconciliation import normalize_reconciliation
from parison.source_pair import pair_summary, verify_postgres_pair
from parison.source_receipt import selection_sql, source_summary

FIXTURES = Path(__file__).parent / "fixtures"


def write(path, value):
    path.write_bytes(_canonical(value) + b"\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair(root, major, orders="1,10.00\n2,20.00\n", lines="1,1,10.00\n2,2,20.00\n"):
    """Synthetic adapter evidence, never a substitute for the live gate."""
    root.mkdir()
    limits = {
        "max_rows": 300000,
        "max_output_bytes": 1 << 30,
        "statement_timeout_ms": 300000,
        "wall_timeout_ms": 600000,
    }
    tables = {"orders": ["id", "amount"], "order_lines": ["id", "order_id", "amount"]}
    plan = {"pair_plan_version": 1, "source_id": f"pg{major}", "tables": {}, "limits": limits}
    manifests, rows, size = {}, {}, 0
    for slot, body in (("orders", orders), ("order_lines", lines)):
        child = root / "tables" / slot
        child.mkdir(parents=True)
        columns = tables[slot]
        data = (",".join(columns) + "\n" + body).encode()
        (child / "data.csv").write_bytes(data)
        rows[slot] = len(body.splitlines())
        size += len(data)
        receipt = json.loads((FIXTURES / "postgres_ingress" / "receipt.json").read_text())
        source = receipt["source"]
        source.update(
            source_id=f"pg{major}",
            server_version_num=major * 10000,
            table=slot,
            columns=columns,
            types=["int4"] * (len(columns) - 1) + ["numeric"],
        )
        plan["tables"][slot] = {"schema": "public", "table": slot, "columns": columns, "primary_key": ["id"]}
        receipt["plan_sha256"] = _identity(
            {"plan_version": 1, "source_id": plan["source_id"], **plan["tables"][slot], "limits": limits}
        )
        receipt["limits"] = limits
        receipt["selection"]["sql"] = selection_sql("public", slot, columns, ["id"])
        receipt["observed"].update(
            local_rows=rows[slot],
            server_rows=rows[slot],
            output_bytes=len(data),
            output_sha256=hashlib.sha256(data).hexdigest(),
        )
        files = {"data.csv": hashlib.sha256(data).hexdigest(), "receipt.json": write(child / "receipt.json", receipt)}
        files["summary.json"] = write(
            child / "summary.json", source_summary(receipt, (child / "receipt.json").read_bytes())
        )
        manifest = json.loads((FIXTURES / "postgres_ingress" / "manifest.json").read_text())
        manifest["files"] = files
        manifests[slot] = write(child / "manifest.json", manifest)
    receipt = {
        "postgres_pair_receipt_version": 1,
        "kind": "postgresql-two-table-export",
        "pair_plan_sha256": _identity(plan),
        "source": {name: source[name] for name in ("source_id", "database", "role", "server_version_num")},
        "transaction": {"isolation": "repeatable read", "read_only": True, "row_security": "off", "snapshot": "1:2:"},
        "table_manifests": manifests,
        "limits": limits,
        "observed": {"rows": sum(rows.values()), "bytes": size, "elapsed_ms": 10, "complete": True},
    }
    files = {"receipt.json": write(root / "receipt.json", receipt)}
    files["summary.json"] = write(root / "summary.json", pair_summary(receipt, (root / "receipt.json").read_bytes()))
    digest = write(
        root / "manifest.json",
        {
            "postgres_pair_manifest_version": 1,
            "kind": receipt["kind"],
            "complete": True,
            "files": {**files, **manifests},
        },
    )
    verify_postgres_pair(root)
    return {
        "manifest_sha256": digest,
        "pair_plan_sha256": _identity(plan),
        "snapshot": "1:2:",
        "expected_rows": rows,
        "types": {slot: ["int4"] * (len(columns) - 1) + ["numeric"] for slot, columns in tables.items()},
    }


def setup(root):
    recipes = {}
    for slot in ("orders", "order_lines"):
        recipe = json.loads((FIXTURES / "partition_discovery" / "recipe.json").read_text())
        recipe["null_tokens"] = {"baseline": [r"\N"], "candidate": [r"\N"]}
        if slot == "order_lines":
            recipe["columns"] = {
                "id": recipe["columns"]["id"],
                "order_id": {"type": "integer", "comparison": "exact"},
                "amount": recipe["columns"]["amount"],
            }
        # Recipe column order is acquisition order, unlike canonical object ordering.
        path = root / f"{slot}.json"
        path.write_text(json.dumps(recipe))
        recipes[slot] = path
    policies = {slot: explain_recipe(path)["policy_sha256"] for slot, path in recipes.items()}
    checks = [
        {"id": slot, "kind": "identity", "dataset": slot, "columns": ["id"], "nulls": "forbid"} for slot in recipes
    ]
    checks += [
        {
            "id": "reference",
            "kind": "reference",
            "child_dataset": "order_lines",
            "child_columns": ["order_id"],
            "parent_identity": "orders",
            "nulls": "forbid",
        },
        {
            "id": "total",
            "kind": "conservation",
            "parent_dataset": "orders",
            "parent_identity": "orders",
            "parent_group_columns": ["id"],
            "child_dataset": "order_lines",
            "child_group_columns": ["order_id"],
            "parent_measure": "amount",
            "child_measure": "amount",
            "operator": "sum",
            "nulls": "forbid",
            "comparison": "exact",
            "tolerance": None,
        },
    ]
    datasets = [
        {
            "id": slot,
            "policy_sha256": policies[slot],
            "columns": [
                {"name": name, "type": spec["type"]} for name, spec in json.loads(path.read_text())["columns"].items()
            ],
        }
        for slot, path in recipes.items()
    ]
    normalized = normalize_reconciliation(
        {"reconciliation_version": 1, "alignment_sha256": "0" * 64, "datasets": datasets, "checks": checks}
    )
    declaration = {
        "postgres_rehearsal_relationships_version": 1,
        "datasets": normalized["datasets"],
        "checks": normalized["checks"],
    }
    write(root / "relationships.json", declaration)
    (root / "claim.txt").write_text("Synthetic stopped-write fixture claim; unauthenticated.\n")
    partitions = json.loads((FIXTURES / "partition_discovery" / "plan.json").read_text())
    return {
        "rehearsal_plan_version": 1,
        "pairs": {side: pair(root / side, major) for side, major in (("baseline", 16), ("candidate", 18))},
        "coordination": {
            "mode": "source-owned",
            "claim_sha256": hashlib.sha256((root / "claim.txt").read_bytes()).hexdigest(),
        },
        "policies": policies,
        "partitions": {slot: copy.deepcopy(partitions) for slot in recipes},
        "reconciliation_sha256": _identity(declaration),
        "limits": {
            "max_input_bytes": 10000,
            "max_rows": 100,
            "max_keys": 100,
            "max_groups": 100,
            "max_temp_bytes": 1000000,
        },
    }


class PostgresRehearsal(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plan = setup(self.root)
        self.args = {
            "baseline": self.root / "baseline",
            "candidate": self.root / "candidate",
            "orders_recipe": self.root / "orders.json",
            "lines_recipe": self.root / "order_lines.json",
            "reconciliation": self.root / "relationships.json",
            "claim": self.root / "claim.txt",
        }

    def run_case(self):
        write(self.root / "plan.json", self.plan)
        return run(self.root / "plan.json", output=self.root / "result", **self.args)

    def replace_pair(self, side, **kwargs):
        shutil.rmtree(self.root / side)
        self.plan["pairs"][side] = pair(self.root / side, 16 if side == "baseline" else 18, **kwargs)

    def test_golden_bytes_and_replay(self):
        result = self.run_case()
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(verify(self.root / "result", **self.args), result)
        expected = FIXTURES / "postgres_rehearsal" / "expected"
        for file in expected.rglob("*.json"):
            self.assertEqual(file.read_bytes(), (self.root / "result" / file.relative_to(expected)).read_bytes())
        self.assertEqual(len(list(expected.rglob("*.json"))), 12)
        for slot in ("orders", "order_lines"):
            exact = compare(
                self.args["orders_recipe" if slot == "orders" else "lines_recipe"],
                self.root / "baseline" / "tables" / slot / "data.csv",
                self.root / "candidate" / "tables" / slot / "data.csv",
            )
            self.assertEqual(exact["outcome"], result["parity"][slot])

    def test_unestablished_and_matching_omissions(self):
        self.plan["coordination"] = {"mode": "unestablished", "claim_sha256": None}
        self.args["claim"] = None
        for side in ("baseline", "candidate"):
            self.replace_pair(side, orders="1,10.00\n", lines="1,1,10.00\n")
            self.plan["pairs"][side]["expected_rows"] = {"orders": 2, "order_lines": 2}
        result = self.run_case()
        self.assertEqual(result["outcome"], "INCONCLUSIVE")
        self.assertEqual(result["parity"], {"orders": "PASS", "order_lines": "PASS"})
        self.assertEqual(result["coverage"], "INCONCLUSIVE")

    def test_orphans_offsetting_partial_and_swap(self):
        for mutation in (
            {"lines": "1,3,10.00\n2,2,20.00\n"},
            {"lines": "1,1,11.00\n2,2,19.00\n"},
            {"lines": "1,1,10.00\n"},
            {"orders": "1,20.00\n2,10.00\n"},
        ):
            with self.subTest(mutation=mutation):
                self.replace_pair("candidate", **mutation)
                summary = self.run_case()
                self.assertEqual(summary["outcome"], "FAIL")
                receipt = json.loads((self.root / "result" / "receipt.json").read_text())
                for slot in ("orders", "order_lines"):
                    exact = compare(
                        self.args["orders_recipe" if slot == "orders" else "lines_recipe"],
                        self.root / "baseline" / "tables" / slot / "data.csv",
                        self.root / "candidate" / "tables" / slot / "data.csv",
                    )
                    self.assertEqual(exact["outcome"], summary["parity"][slot])
                    self.assertEqual(exact["counts"], receipt["parity"][slot]["counts"])
                    self.assertEqual(exact["discrepancy_count"], receipt["parity"][slot]["discrepancy_count"])
                shutil.rmtree(self.root / "result")

    def test_duplicate_conversion_and_null_fail_closed(self):
        for lines in ("1,1,10.00\n1,2,20.00\n", "1,1,not-numeric\n", "1,\\N,10.00\n", "1,,10.00\n"):
            with self.subTest(lines=lines):
                self.replace_pair("candidate", lines=lines)
                try:
                    result = self.run_case()
                except (ParisonError, ValueError):
                    self.assertFalse((self.root / "result").exists())
                else:
                    self.assertEqual(result["outcome"], "FAIL")
                    shutil.rmtree(self.root / "result")

    def test_reviewed_bindings_reject_substitution(self):
        original = copy.deepcopy(self.plan)
        for field, value in (
            ("snapshot", "stale"),
            ("pair_plan_sha256", "0" * 64),
            ("manifest_sha256", "0" * 64),
            ("types", {"orders": ["text", "numeric"], "order_lines": ["int4", "int4", "numeric"]}),
        ):
            self.plan = copy.deepcopy(original)
            self.plan["pairs"]["baseline"][field] = value
            with self.assertRaises(ParisonError):
                self.run_case()
        self.plan = original
        self.args["claim"].write_text("wrong claim")
        with self.assertRaises(ParisonError):
            self.run_case()

    def test_no_overwrite_tamper_source_removal(self):
        self.run_case()
        with self.assertRaises(ParisonError):
            self.run_case()
        receipt = self.root / "result" / "receipt.json"
        value = json.loads(receipt.read_text())
        value["coverage"] = "INCONCLUSIVE"
        digest = write(receipt, value)
        manifest_path = self.root / "result" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["receipt.json"] = digest
        write(manifest_path, manifest)
        with self.assertRaises(ParisonError):
            verify(self.root / "result", **self.args)
        shutil.rmtree(self.root / "baseline")
        with self.assertRaises(ParisonError):
            verify(self.root / "result", **self.args)

    def test_interruption_limits_and_safe_cli(self):
        with patch("parison.postgres_rehearsal.check_conservation", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_case()
        self.assertFalse(list(self.root.glob(".result-*")))
        self.plan["limits"]["max_rows"] = 1
        with self.assertRaises(ParisonError):
            self.run_case()
        output, error = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = main(
                [
                    "run",
                    "--plan",
                    str(self.root / "plan.json"),
                    "--output",
                    str(self.root / "result"),
                    *[item for key, value in self.args.items() for item in ("--" + key.replace("_", "-"), str(value))],
                ]
            )
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(error.getvalue(), "parison-rehearsal: invalid or incomplete rehearsal evidence\n")

    def test_installed_schemas_and_unknown_members(self):
        from jsonschema import Draft202012Validator

        from parison.core import load_schema
        from parison.postgres_rehearsal import validate_plan

        self.run_case()
        for name in ("plan", "receipt", "summary", "manifest"):
            value = json.loads((self.root / "result" / f"{name}.json").read_text())
            schema = load_schema(f"postgres-rehearsal-{name}")
            Draft202012Validator(schema).validate(value)
            value["unexpected"] = True
            self.assertFalse(Draft202012Validator(schema).is_valid(value))
        Draft202012Validator(load_schema("postgres-rehearsal-relationships")).validate(
            json.loads(self.args["reconciliation"].read_text())
        )
        for value in (None, [], {}, {**self.plan, "rehearsal_plan_version": True}, {**self.plan, "extra": 1}):
            with self.assertRaises(ParisonError):
                validate_plan(value)

    def test_missing_coordination_alone_and_exit_three(self):
        self.plan["coordination"] = {"mode": "unestablished", "claim_sha256": None}
        self.args["claim"] = None
        result = self.run_case()
        self.assertEqual(result["outcome"], "INCONCLUSIVE")
        self.assertEqual(result["coverage"], "PASS")
        with redirect_stdout(StringIO()):
            status = main(
                [
                    "verify",
                    str(self.root / "result"),
                    *[
                        item
                        for key, value in self.args.items()
                        if value is not None
                        for item in ("--" + key.replace("_", "-"), str(value))
                    ],
                ]
            )
        self.assertEqual(status, 3)

    def test_wrong_version_policy_and_mandatory_checks(self):
        self.replace_pair("baseline")
        original = self.plan["policies"]["orders"]
        self.plan["policies"]["orders"] = "0" * 64
        with self.assertRaises(ParisonError):
            self.run_case()
        self.plan["policies"]["orders"] = original
        relation = json.loads(self.args["reconciliation"].read_text())
        relation["checks"] = [c for c in relation["checks"] if c["kind"] != "conservation"]
        write(self.args["reconciliation"], relation)
        self.plan["reconciliation_sha256"] = _identity(relation)
        with self.assertRaises(ParisonError):
            self.run_case()

    def test_symlink_and_missing_partition(self):
        self.run_case()
        child = self.root / "result" / "discovery" / "orders" / "receipt.json"
        child.unlink()
        with self.assertRaises(ParisonError):
            verify(self.root / "result", **self.args)
        shutil.rmtree(self.root / "result")
        try:
            (self.root / "result").symlink_to(self.root / "baseline", target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ParisonError):
            self.run_case()

    def test_mutation_during_run(self):
        from parison.postgres_rehearsal import check_conservation

        def mutate(*args, **kwargs):
            result = check_conservation(*args, **kwargs)
            (self.root / "candidate" / "tables" / "orders" / "data.csv").write_text("changed")
            return result

        with patch("parison.postgres_rehearsal.check_conservation", side_effect=mutate):
            with self.assertRaises(ParisonError):
                self.run_case()
        self.assertFalse((self.root / "result").exists())

    def test_selective_investigation_handoff(self):
        from parison.partition_investigation import investigate, verify_investigation

        self.replace_pair("candidate", lines="1,1,11.00\n2,2,20.00\n")
        self.run_case()
        discovery = self.root / "result" / "discovery" / "order_lines"
        plan = {
            "investigation_plan_version": 1,
            "discovery_manifest_sha256": hashlib.sha256((discovery / "manifest.json").read_bytes()).hexdigest(),
            "partition_indices": [0],
            "limits": {
                "max_cases_total": 10,
                "max_cases_per_partition": 10,
                "max_staged_bytes": 10000,
                "max_output_bytes": 10000,
            },
        }
        write(self.root / "investigation.json", plan)
        baseline = self.root / "baseline" / "tables" / "order_lines" / "data.csv"
        candidate = self.root / "candidate" / "tables" / "order_lines" / "data.csv"
        investigate(
            self.root / "investigation.json",
            discovery,
            self.args["lines_recipe"],
            baseline,
            candidate,
            self.root / "investigation",
        )
        result = verify_investigation(
            self.root / "investigation", discovery, self.args["lines_recipe"], baseline, candidate
        )
        self.assertEqual(result["verification"], "exact-source-backed")

    def test_discovery_substitution_cannot_publish_pass(self):
        from parison.postgres_rehearsal import discover

        self.replace_pair("candidate", orders="1,11.00\n2,20.00\n", lines="1,1,11.00\n2,2,20.00\n")

        def substitute(plan, recipe, baseline, candidate, output):
            original = candidate.read_bytes()
            candidate.write_bytes(baseline.read_bytes())
            try:
                return discover(plan, recipe, baseline, candidate, output)
            finally:
                candidate.write_bytes(original)

        with patch("parison.postgres_rehearsal.discover", side_effect=substitute):
            with self.assertRaises(ParisonError):
                self.run_case()
        self.assertFalse((self.root / "result").exists())
        self.assertFalse(list(self.root.glob(".result-*")))

    def test_argument_errors_never_echo_values(self):
        output, error = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = main(["run", "--secret", "RAW-CREDENTIAL-MARKER"])
        self.assertEqual(status, 2)
        self.assertNotIn("RAW-CREDENTIAL", output.getvalue() + error.getvalue())

    def test_major_version_rejected(self):
        shutil.rmtree(self.root / "baseline")
        self.plan["pairs"]["baseline"] = pair(self.root / "baseline", 18)
        with self.assertRaises(ParisonError):
            self.run_case()
