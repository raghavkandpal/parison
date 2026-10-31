"""Explicit representation decisions, verified-parent replay and safe publication."""

import copy
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from parison import cli
from parison import representation_assessment as assessment
from parison.analysis import _canonical
from parison.core import ParisonError
from parison.representation import _normal_facts
from parison.source_collection import collection_summary

ROOT = Path(__file__).parent / "fixtures" / "postgres_representation"


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_bytes(_canonical(value) + b"\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RepresentationAssessment(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.baseline, self.candidate = (self.root / side for side in ("baseline", "candidate"))
        for side, target in (("baseline", self.baseline), ("candidate", self.candidate)):
            shutil.copytree(ROOT / side, target)
        self.output = self.root / "assessment"
        self.plan_path = self.root / "plan.json"
        write(self.plan_path, read(ROOT / "assessment" / "effective-plan.json"))

    def parents(self):
        return assessment._parents(self.baseline, self.candidate)

    def plan(self, parents=None):
        plan = read(self.plan_path)
        parents = parents or self.parents()
        for side, digest_value in assessment._inputs(parents).items():
            plan[f"{side}_manifest_sha256"] = digest_value
        return plan

    def rehash(self, root):
        receipt = read(root / "receipt.json")
        for child in (root / "tables").iterdir():
            source = read(child / "receipt.json")
            source["observed"]["output_bytes"] = (child / "data.csv").stat().st_size
            source["observed"]["output_sha256"] = digest(child / "data.csv")
            write(child / "receipt.json", source)
            summary = read(child / "summary.json")
            summary.update(
                receipt_sha256=digest(child / "receipt.json"),
                bytes=source["observed"]["output_bytes"],
                output_sha256=source["observed"]["output_sha256"],
            )
            write(child / "summary.json", summary)
            manifest = read(child / "manifest.json")
            manifest["files"] = {name: digest(child / name) for name in manifest["files"]}
            write(child / "manifest.json", manifest)
            receipt["table_manifests"][child.name] = digest(child / "manifest.json")
        receipt["observed"]["bytes"] = sum((c / "data.csv").stat().st_size for c in (root / "tables").iterdir())
        metadata = read(root / "representation.json")
        metadata["table_manifests"] = receipt["table_manifests"]
        write(root / "representation.json", metadata)
        receipt["representation_sha256"] = digest(root / "representation.json")
        receipt["observed"]["representation_bytes"] = (root / "representation.json").stat().st_size
        write(root / "receipt.json", receipt)
        write(root / "summary.json", collection_summary(receipt, (root / "receipt.json").read_bytes()))
        manifest = read(root / "manifest.json")
        manifest.update(
            table_manifests=receipt["table_manifests"], files={name: digest(root / name) for name in manifest["files"]}
        )
        write(root / "manifest.json", manifest)

    def test_frozen_artifact_proposal_and_replay_bytes(self):
        result = assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        self.assertEqual(result, read(ROOT / "assessment" / "summary.json"))
        for path in self.output.iterdir():
            self.assertEqual(path.read_bytes(), (ROOT / "assessment" / path.name).read_bytes())
        self.assertEqual(assessment.verify(self.output, self.baseline, self.candidate), result)
        proposal = self.root / "proposal.json"
        self.assertEqual(
            assessment.propose(self.baseline, self.candidate, proposal), read(ROOT / "proposal-summary.json")
        )
        self.assertEqual(proposal.read_bytes(), (ROOT / "proposal.json").read_bytes())
        self.assertNotIn("rules", read(proposal))
        self.assertEqual(read(proposal)["status"], "unapproved")

    def test_compatibility_does_not_compare_rows(self):
        data = self.candidate / "tables" / "orders" / "data.csv"
        data.write_bytes(data.read_bytes().replace(b"hello", b"other"))
        self.rehash(self.candidate)
        write(self.plan_path, self.plan())
        result = assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        self.assertEqual(result["compatibility"], "ACCEPT")
        self.assertNotIn("PASS", json.dumps(result))
        self.assertNotEqual(data.read_bytes(), (self.baseline / "tables" / "orders" / "data.csv").read_bytes())

    def test_replay_rejects_rehashed_forgery_and_changed_parents(self):
        assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        result = read(self.output / "assessment.json")
        result["compatibility"] = "DENY"
        write(self.output / "assessment.json", result)
        manifest = read(self.output / "manifest.json")
        manifest["files"]["assessment.json"] = digest(self.output / "assessment.json")
        write(self.output / "manifest.json", manifest)
        with self.assertRaises(ParisonError):
            assessment.verify(self.output, self.baseline, self.candidate)
        shutil.rmtree(self.output)
        assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        data = self.candidate / "tables" / "orders" / "data.csv"
        data.write_bytes(data.read_bytes().replace(b"hello", b"other"))
        self.rehash(self.candidate)
        with self.assertRaises(ParisonError):
            assessment.verify(self.output, self.baseline, self.candidate)

    def test_invalid_plans_and_semantic_negative_obligations(self):
        parents = self.parents()
        original = self.plan(parents)
        for path, replacement in (
            (["assessment_plan_version"], True),
            (["assessment_plan_version"], 1.0),
            (["rules", "integer"], "coerce"),
            (["baseline_manifest_sha256"], "0" * 64),
            (["tables", "orders", "candidate_id"], "order_lines"),
            (["tables", "orders", "evolution", "changes"], original["tables"]["orders"]["evolution"]["changes"][:1]),
        ):
            with self.subTest(path=path):
                value = copy.deepcopy(original)
                target = value
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = replacement
                with self.assertRaises(ParisonError):
                    assessment.validate_plan(value, parents)
        for case in read(ROOT / "semantic-negative.json"):
            with self.subTest(case=case["case"]):
                if case["schema"] == "representation-assessment-plan-v1":
                    with self.assertRaises(ParisonError):
                        assessment.validate_plan(case["value"], parents)
                elif case["schema"] == "representation-proposal-v1":
                    self.assertNotEqual(assessment._proposal(parents), case["value"])
                    # Proposals are not executable plans, including this invalid one.
                    with self.assertRaises(ParisonError):
                        assessment.validate_plan(case["value"], parents)
                else:
                    write(self.candidate / "representation.json", case["value"])
                    self.rehash(self.candidate)
                    with self.assertRaises(ParisonError):
                        self.parents()

    def test_cli_help_errors_and_safe_stdout(self):
        for action in (None, "propose", "assess", "verify"):
            argv = ["representation", *([action] if action else []), "--help"]
            out = io.StringIO()
            with redirect_stdout(out), self.assertRaises(SystemExit) as raised:
                cli.main(argv)
            self.assertEqual(raised.exception.code, 0)
            self.assertEqual(out.getvalue(), (ROOT / f"{action or 'representation'}-help.txt").read_text())
        for case in read(ROOT / "cli-errors.json"):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(cli.main(["representation", *case["argv"]]), 2)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(err.getvalue(), case["stderr"])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(
                cli.main(
                    [
                        "representation",
                        "assess",
                        "--plan",
                        str(self.plan_path),
                        "--baseline",
                        str(self.baseline),
                        "--candidate",
                        str(self.candidate),
                        "--output",
                        str(self.output),
                    ]
                ),
                0,
            )
        self.assertEqual(out.getvalue().encode(), _canonical(read(ROOT / "assessment" / "summary.json")) + b"\n")
        self.assertEqual(err.getvalue(), "")
        for value in ("public", "orders", "note", "hello", str(self.root)):
            self.assertNotIn(value, out.getvalue())

    def test_cli_denial_unknown_replay_and_proposal_statuses(self):
        proposal = self.root / "proposal.json"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(
                cli.main(
                    [
                        "representation",
                        "propose",
                        "--baseline",
                        str(self.baseline),
                        "--candidate",
                        str(self.candidate),
                        "--output",
                        str(proposal),
                    ]
                ),
                0,
            )
        self.assertEqual(out.getvalue().encode(), _canonical(read(ROOT / "proposal-summary.json")) + b"\n")
        original = read(self.candidate / "representation.json")
        for validated, status, code in ((True, "DENY", 1), (False, "INCONCLUSIVE", 3)):
            with self.subTest(status=status):
                metadata = copy.deepcopy(original)
                metadata["tables"]["orders"]["columns"][1]["nullability"] = {
                    "declared_not_null": True,
                    "information_schema_nullable": "NO",
                    "constraints": [{"name": "note_nn", "validated": validated, "enforced": True}],
                    "guarantee": "non-null" if validated else "unknown",
                }
                write(self.candidate / "representation.json", metadata)
                self.rehash(self.candidate)
                write(self.plan_path, self.plan())
                output = self.root / status
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        cli.main(
                            [
                                "representation",
                                "assess",
                                "--plan",
                                str(self.plan_path),
                                "--baseline",
                                str(self.baseline),
                                "--candidate",
                                str(self.candidate),
                                "--output",
                                str(output),
                            ]
                        ),
                        code,
                    )
                self.assertEqual(json.loads(out.getvalue())["compatibility"], status)
                out = io.StringIO()
                with redirect_stdout(out):
                    self.assertEqual(
                        cli.main(
                            [
                                "representation",
                                "verify",
                                str(output),
                                "--baseline",
                                str(self.baseline),
                                "--candidate",
                                str(self.candidate),
                            ]
                        ),
                        code,
                    )
                self.assertEqual(json.loads(out.getvalue())["compatibility"], status)

    def test_legacy_parents_unavailable_without_inventing_inventory(self):
        shutil.rmtree(self.baseline)
        shutil.copytree(ROOT.parent / "postgres_collection" / "only-expected", self.baseline)
        parents = self.parents()
        result, summary = assessment.evaluate(self.plan(parents), parents)
        self.assertFalse(summary["complete"])
        self.assertEqual((summary["compatibility"], summary["fields"], summary["tables"]), ("INCONCLUSIVE", 0, 2))
        self.assertEqual([f["reason"] for f in result["findings"]], ["metadata_unavailable"] * 2)
        with self.assertRaises(ParisonError):
            assessment.propose(self.baseline, self.candidate, self.root / "proposal.json")
        plan = self.plan(parents)
        plan["tables"] = {
            f"{side}_{tid}": {
                "baseline_id": tid if side == "baseline" else None,
                "candidate_id": tid if side == "candidate" else None,
                "evolution": None,
            }
            for side, parent in parents.items()
            for tid in parent["receipt"]["table_manifests"]
        }
        _, summary = assessment.evaluate(plan, parents)
        self.assertEqual(
            (summary["compatibility"], summary["fields"], summary["tables"], summary["complete"]), ("DENY", 0, 0, False)
        )

    def test_unknown_nullability_and_deny_precedence(self):
        metadata = read(self.candidate / "representation.json")
        note = metadata["tables"]["orders"]["columns"][1]
        note["nullability"] = {
            "declared_not_null": True,
            "information_schema_nullable": "NO",
            "constraints": [{"name": "note_nn", "validated": False, "enforced": True}],
            "guarantee": "unknown",
        }
        write(self.candidate / "representation.json", metadata)
        self.rehash(self.candidate)
        parents = self.parents()
        plan = self.plan(parents)
        _, summary = assessment.evaluate(plan, parents)
        self.assertEqual(summary["compatibility"], "INCONCLUSIVE")
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["reason_counts"]["nullability_unknown"], 1)
        plan["tables"]["order_lines"] = {"baseline_id": "order_lines", "candidate_id": None, "evolution": None}
        plan["tables"]["new_lines"] = {"baseline_id": None, "candidate_id": "order_lines", "evolution": None}
        _, summary = assessment.evaluate(plan, parents)
        self.assertEqual(summary["compatibility"], "DENY")
        self.assertEqual(summary["reason_counts"]["nullability_unknown"], 1)

    def test_one_sided_optional_fields_preserve_unknown_guarantees(self):
        original = read(self.candidate / "representation.json")
        for kind in ("nullability", "collation"):
            with self.subTest(kind=kind):
                metadata = copy.deepcopy(original)
                extra = copy.deepcopy(metadata["tables"]["orders"]["columns"][1])
                extra.update(name="extra", ordinal=3, selected=False)
                if kind == "nullability":
                    extra["nullability"] = {
                        "declared_not_null": True,
                        "information_schema_nullable": "NO",
                        "constraints": [{"name": "extra_nn", "validated": False, "enforced": True}],
                        "guarantee": "unknown",
                    }
                else:
                    extra["collation"] = {
                        "state": "unknown",
                        "origin": "unknown",
                        **{
                            key: None
                            for key in (
                                "schema",
                                "name",
                                "provider",
                                "encoding",
                                "deterministic",
                                "collate",
                                "ctype",
                                "locale",
                                "rules",
                            )
                        },
                        "recorded_version": {"state": "unknown", "value": None},
                        "actual_version": {"state": "unknown", "value": None},
                    }
                metadata["tables"]["orders"]["columns"].append(extra)
                write(self.candidate / "representation.json", metadata)
                self.rehash(self.candidate)
                parents = self.parents()
                plan = self.plan(parents)
                plan["tables"]["orders"]["evolution"]["changes"].append(
                    {
                        "change": "added",
                        "baseline": [],
                        "candidate": [
                            {
                                "id": "extra",
                                "name": "extra",
                                "presence": "optional",
                                "nullability": "non-null" if kind == "nullability" else "nullable",
                            }
                        ],
                    }
                )
                _, summary = assessment.evaluate(plan, parents)
                self.assertEqual(summary["compatibility"], "INCONCLUSIVE")
                self.assertEqual(summary["reason_counts"][f"{kind}_unknown"], 1)
                # Reversing the declaration preserves unknowns for optional removal.
                reverse = copy.deepcopy(plan)
                reverse["baseline_manifest_sha256"], reverse["candidate_manifest_sha256"] = (
                    reverse["candidate_manifest_sha256"],
                    reverse["baseline_manifest_sha256"],
                )
                declaration = reverse["tables"]["orders"]["evolution"]["changes"][-1]
                declaration.update(change="removed", baseline=declaration["candidate"], candidate=[])
                _, summary = assessment.evaluate(
                    reverse, {"baseline": parents["candidate"], "candidate": parents["baseline"]}
                )
                self.assertEqual(summary["compatibility"], "INCONCLUSIVE")
                self.assertEqual(summary["reason_counts"][f"{kind}_unknown"], 1)

    def test_publication_failure_interrupt_no_overwrite_and_input_exclusion(self):
        for method in ("assess", "propose"):
            target = self.output if method == "assess" else self.root / "proposal.json"

            def call(method=method, target=target):
                return (
                    assessment.assess(self.plan_path, self.baseline, self.candidate, target)
                    if method == "assess"
                    else assessment.propose(self.baseline, self.candidate, target)
                )

            for failure in (OSError("private failure"), KeyboardInterrupt()):
                with (
                    self.subTest(method=method, failure=type(failure).__name__),
                    patch.object(assessment, "rename_no_replace", side_effect=failure),
                ):
                    with self.assertRaises(type(failure)):
                        call()
                    self.assertFalse(target.exists())
                    self.assertFalse(list(self.root.glob(f".{target.name}-*")))
            call()
            before = target.read_bytes() if target.is_file() else (target / "manifest.json").read_bytes()
            with self.assertRaises(ParisonError):
                call()
            self.assertEqual(
                target.read_bytes() if target.is_file() else (target / "manifest.json").read_bytes(), before
            )
        with self.assertRaises(ParisonError):
            assessment.propose(self.baseline, self.candidate, self.baseline / "private.json")
        with self.assertRaises(ParisonError):
            assessment.assess(self.plan_path, self.baseline, self.candidate, self.candidate / "assessment")

    @unittest.skipUnless(os.name == "posix", "POSIX symlink and pinned reader checks")
    def test_artifact_symlinks_mutation_and_safe_interrupt(self):
        assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        member = self.output / "assessment.json"
        outside = self.root / "outside.json"
        member.rename(outside)
        member.symlink_to(outside)
        with self.assertRaises(OSError):
            assessment.verify(self.output, self.baseline, self.candidate)
        member.unlink()
        outside.rename(member)
        original = assessment._artifact

        def mutate(*args):
            answer = original(*args)
            with member.open("ab") as handle:
                handle.write(b" ")
            return answer

        with patch.object(assessment, "_artifact", side_effect=mutate):
            with self.assertRaises(ParisonError):
                assessment.verify(self.output, self.baseline, self.candidate)
        out, err = io.StringIO(), io.StringIO()
        with (
            patch.object(assessment, "verify", side_effect=KeyboardInterrupt),
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            self.assertEqual(
                cli.main(
                    [
                        "representation",
                        "verify",
                        str(self.output),
                        "--baseline",
                        str(self.baseline),
                        "--candidate",
                        str(self.candidate),
                    ]
                ),
                130,
            )
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "parison representation verify: interrupted\n")

    def test_plan_and_artifact_size_limits_and_findings_bound(self):
        self.plan_path.write_bytes(b" " * (assessment.PLAN_LIMIT + 1))
        with self.assertRaises(ParisonError):
            assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        self.assertFalse(self.output.exists())
        write(self.plan_path, read(ROOT / "assessment" / "effective-plan.json"))
        assessment.assess(self.plan_path, self.baseline, self.candidate, self.output)
        (self.output / "summary.json").write_bytes(b" " * (assessment.META_LIMIT + 1))
        with self.assertRaises(ParisonError):
            assessment.verify(self.output, self.baseline, self.candidate)
        findings = {}
        for i in range(20000):
            assessment._add(findings, "table", f"f{i}", "type_changed", "ACCEPT")
        with self.assertRaises(ParisonError):
            assessment._add(findings, "table", "overflow", "type_changed", "ACCEPT")


class RepresentationRules(unittest.TestCase):
    def setUp(self):
        self.parents = assessment._parents(ROOT / "baseline", ROOT / "candidate")
        self.plan = read(ROOT / "assessment" / "effective-plan.json")

    def column(self, kind="text", **facts):
        template = copy.deepcopy(self.parents["candidate"]["representation"]["tables"]["orders"]["columns"][1])
        template["type"].update(name=kind, schema="pg_catalog", supported=True, typmod=facts.get("typmod", -1))
        _supported, numeric, characters, datetime = _normal_facts(template["type"])
        template.update(numeric=numeric, characters=characters, datetime=datetime)
        if kind not in {"text", "varchar"}:
            template["collation"] = copy.deepcopy(
                self.parents["candidate"]["representation"]["tables"]["orders"]["columns"][0]["collation"]
            )
        return template

    def compare(self, baseline, candidate, rules):
        findings = []
        assessment._field_findings(baseline, candidate, rules, lambda reason, status: findings.append((reason, status)))
        return max((s for _, s in findings), key=assessment._RANK.get, default="ACCEPT"), findings

    def test_frozen_rule_cases_execute_real_comparator_or_evaluator(self):
        cases = read(ROOT / "rule-cases.json")
        self.assertEqual(len(cases), 31)
        for case in cases:
            with self.subTest(case=case["case"]):
                dimension = case["dimension"]
                rules = {k: "exact" for k in assessment._RULES}
                if dimension in rules:
                    rules[dimension] = case["rule"]
                b, c = self.column(), self.column()
                if dimension == "integer":
                    b, c = self.column(case["baseline"]), self.column(case["candidate"])
                elif dimension == "numeric":

                    def numeric(value):
                        typmod = (
                            -1
                            if value["precision"] is None
                            else 4 + (value["precision"] << 16) + (value["scale"] & 2047)
                        )
                        return self.column("numeric", typmod=typmod)

                    b, c = numeric(case["baseline"]), numeric(case["candidate"])
                elif dimension == "text_length":

                    def text(value):
                        return self.column(value["type"], typmod=-1 if value["length"] is None else value["length"] + 4)

                    b, c = text(case["baseline"]), text(case["candidate"])
                elif dimension == "datetime_precision":

                    def timestamp(value):
                        return self.column(
                            "timestamp" if value["timezone"] == "naive" else "timestamptz", typmod=value["precision"]
                        )

                    b, c = timestamp(case["baseline"]), timestamp(case["candidate"])
                elif dimension == "nullability":
                    b["nullability"]["guarantee"], c["nullability"]["guarantee"] = case["baseline"], case["candidate"]
                elif dimension == "collation":
                    for column, value in ((b, case["baseline"]), (c, case["candidate"])):
                        if value == "unknown":
                            column["collation"]["state"] = "unknown"
                        else:
                            for key, source in (("recorded_version", "recorded"), ("actual_version", "actual")):
                                column["collation"][key] = {"state": "known", "value": value[source]}
                elif dimension == "unsupported_representation":
                    b["type"]["supported"] = c["type"]["supported"] = False
                elif dimension == "materialization":
                    b["materialization"]["generated"], c["materialization"]["generated"] = (
                        case["baseline"],
                        case["candidate"],
                    )
                else:
                    parents, plan = copy.deepcopy(self.parents), copy.deepcopy(self.plan)
                    if dimension == "metadata":
                        parents["baseline"]["representation"] = None
                    elif dimension == "table_membership":
                        parents["baseline"]["representation"] = None
                        plan["tables"]["orders"] = {"baseline_id": "orders", "candidate_id": None, "evolution": None}
                        plan["tables"]["new_orders"] = {
                            "baseline_id": None,
                            "candidate_id": "orders",
                            "evolution": None,
                        }
                    elif dimension == "key":
                        for parent in parents.values():
                            parent["representation"]["tables"]["orders"]["primary_key"] = ["id", "note"]
                        parents["candidate"]["representation"]["tables"]["orders"]["primary_key"].reverse()
                    elif dimension == "evolution":
                        old = plan["tables"]["orders"]["evolution"]["changes"][0]
                        left = copy.deepcopy(old["baseline"][0])
                        right = copy.deepcopy(old["candidate"][0])
                        right["id"] = "id_new"
                        note = copy.deepcopy(plan["tables"]["orders"]["evolution"]["changes"][1]["candidate"][0])
                        note["id"] = "note_new"
                        plan["tables"]["orders"]["evolution"]["changes"] = [
                            {
                                "change": "removed",
                                "baseline": plan["tables"]["orders"]["evolution"]["changes"][1]["baseline"],
                                "candidate": [],
                            },
                            {"change": "split", "baseline": [left], "candidate": [right, note]},
                        ]
                    elif dimension == "field_membership":
                        extra = self.column("int4")
                        extra.update(name="extra", selected=case["candidate"]["selected"])
                        parents["candidate"]["representation"]["tables"]["orders"]["columns"].append(extra)
                        plan["tables"]["orders"]["evolution"]["changes"].append(
                            {
                                "change": "added",
                                "baseline": [],
                                "candidate": [
                                    {
                                        "id": "extra",
                                        "name": "extra",
                                        "presence": case["candidate"]["presence"],
                                        "nullability": "nullable",
                                    }
                                ],
                            }
                        )
                    _, summary = assessment.evaluate(plan, parents)
                    self.assertEqual(summary["compatibility"], case["expected"])
                    continue
                actual, findings = self.compare(b, c, rules)
                self.assertEqual(actual, case["expected"])
                if b != c and actual == "ACCEPT":
                    self.assertTrue(findings, "allowed changes must remain findings")

    def test_returned_not_assessed_lists_cannot_mutate_future_results(self):
        result, summary = assessment.evaluate(self.plan, self.parents)
        result["not_assessed"].append("unexpected")
        summary["not_assessed"].clear()
        result, summary = assessment.evaluate(self.plan, self.parents)
        expected = read(ROOT / "assessment" / "summary.json")["not_assessed"]
        self.assertEqual(result["not_assessed"], expected)
        self.assertEqual(summary["not_assessed"], expected)

    def test_fully_known_provider_drift_is_denied_without_unknown_label(self):
        b, c = self.column(), self.column()
        for column, value in ((b, "153"), (c, "154")):
            column["collation"].update(provider="icu", collate=None, ctype=None, locale="en-US")
            for key in ("recorded_version", "actual_version"):
                column["collation"][key] = {"state": "known", "value": value}
        status, findings = self.compare(b, c, self.plan["rules"])
        self.assertEqual(status, "DENY")
        self.assertIn(("collation_changed", "DENY"), findings)
        self.assertNotIn(("collation_unknown", "INCONCLUSIVE"), findings)

    def test_provider_versions_compare_corresponding_observation_meanings(self):
        b, c = self.column(), self.column()
        for column in (b, c):
            column["collation"].update(provider="icu", collate=None, ctype=None, locale="en-US")
            column["collation"]["recorded_version"] = {"state": "known", "value": "153"}
            column["collation"]["actual_version"] = {"state": "known", "value": "154"}
        status, findings = self.compare(b, c, self.plan["rules"])
        self.assertEqual(status, "DENY")
        self.assertIn(("collation_version_mismatch", "DENY"), findings)
        self.assertNotIn(("collation_changed", "DENY"), findings)
        self.assertNotIn(("collation_unknown", "INCONCLUSIVE"), findings)
        b["collation"]["actual_version"] = {"state": "unknown", "value": None}
        c["collation"]["recorded_version"] = {"state": "unknown", "value": None}
        status, findings = self.compare(b, c, self.plan["rules"])
        self.assertEqual(status, "INCONCLUSIVE")
        self.assertNotIn(("collation_changed", "DENY"), findings)
        self.assertNotIn(("collation_version_mismatch", "DENY"), findings)

    def test_selection_membership_and_collation_names(self):
        b, c = self.column(), self.column()
        c["collation"].update(origin="explicit", schema="private", name="other")
        self.assertEqual(self.compare(b, c, self.plan["rules"])[0], "ACCEPT")
        c["selected"] = not b["selected"]
        status, findings = self.compare(b, c, self.plan["rules"])
        self.assertEqual(status, "DENY")
        self.assertIn(("field_membership_changed", "DENY"), findings)

    def test_disjoint_union_bound_and_unpaired_legacy_completeness(self):
        parents = copy.deepcopy(self.parents)
        for side in parents:
            parents[side]["representation"] = None
            parents[side]["receipt"]["table_manifests"] = {f"t{i}": "0" * 64 for i in range(16)}
        plan = copy.deepcopy(self.plan)
        plan["tables"] = {
            f"{side}_{i}": {
                "baseline_id": f"t{i}" if side == "b" else None,
                "candidate_id": f"t{i}" if side == "c" else None,
                "evolution": None,
            }
            for side in ("b", "c")
            for i in range(16)
        }
        result, summary = assessment.evaluate(plan, parents)
        self.assertEqual(len(result["findings"]), 32)
        self.assertEqual(
            (summary["compatibility"], summary["complete"], summary["tables"], summary["fields"]), ("DENY", False, 0, 0)
        )
        plan["tables"]["extra"] = copy.deepcopy(plan["tables"]["b_0"])
        with self.assertRaises(ParisonError):
            assessment.evaluate(plan, parents)


if __name__ == "__main__":
    unittest.main()
