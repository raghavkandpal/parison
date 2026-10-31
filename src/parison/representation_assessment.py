"""Explicit offline native-representation assessment, proposals and replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .core import ParisonError
from .evolution import normalize_evolution
from .representation import NOT_ASSESSED, _text
from .source_collection import _directory, _members, _stamp, _stat_stamp, _verified_collection
from .source_receipt import _identifier, _integer, _object, _read_json, _sha

SCOPE = "native-column-representation-v1"
KIND = "representation-assessment"
PLAN_LIMIT = 2 * 1024 * 1024
RESULT_LIMIT = 8 * 1024 * 1024
META_LIMIT = 256 * 1024
REASONS = (
    "table_membership_changed",
    "field_membership_changed",
    "key_changed",
    "declaration_mismatch",
    "unsupported_representation",
    "type_changed",
    "numeric_changed",
    "character_length_changed",
    "datetime_precision_changed",
    "nullability_changed",
    "nullability_unknown",
    "collation_changed",
    "collation_version_mismatch",
    "collation_unknown",
    "materialization_changed",
    "upstream_materialization_required",
    "metadata_unavailable",
)
_RANK = {"ACCEPT": 0, "INCONCLUSIVE": 1, "DENY": 2}
_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}")
_RULES = ("integer", "numeric", "text_length", "datetime_precision", "nullability")
_ERROR = "invalid or incomplete representation evidence"


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _id(value):
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ParisonError(_ERROR)
    return value


def _read_plan(path):
    path = Path(path)
    check_output_parent(path.parent)
    if path.is_symlink():
        raise ParisonError(_ERROR)
    flags = os.O_RDONLY | (os.O_NOFOLLOW | os.O_NONBLOCK if os.name == "posix" else 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > PLAN_LIMIT:
            raise ParisonError(_ERROR)
        data = handle.read(PLAN_LIMIT + 1)
        if len(data) > PLAN_LIMIT or _stat_stamp(before) != _stamp(handle):
            raise ParisonError(_ERROR)
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )


def _parents(baseline, candidate):
    return {"baseline": _verified_collection(baseline), "candidate": _verified_collection(candidate)}


def _inputs(parents):
    return {side: parent["manifest_sha256"] for side, parent in parents.items()}


def _columns(parent, table_id):
    record = parent["representation"]
    if record is None:
        return None
    return {c["name"]: c for c in record["tables"][table_id]["columns"]}


def validate_plan(value, parents):
    plan = _object(value, "assessment_plan_version baseline_manifest_sha256 candidate_manifest_sha256 tables rules")
    _integer(plan["assessment_plan_version"], 1, 1)
    for side, digest in _inputs(parents).items():
        if _sha(plan[f"{side}_manifest_sha256"]) != digest:
            raise ParisonError(_ERROR)
    rules = _object(plan["rules"], " ".join(_RULES))
    for name, rule in rules.items():
        if type(rule) is not str or rule not in {"exact", "relax" if name == "nullability" else "widen"}:
            raise ParisonError(_ERROR)
    tables = plan["tables"]
    if not isinstance(tables, dict) or not 1 <= len(tables) <= 32:
        raise ParisonError(_ERROR)
    seen = {"baseline": set(), "candidate": set()}
    paired = 0
    for table_id, entry in tables.items():
        _id(table_id)
        _object(entry, "baseline_id candidate_id evolution")
        active = []
        for side, parent in parents.items():
            source_id = entry[f"{side}_id"]
            if source_id is not None:
                _id(source_id)
                if source_id in seen[side] or source_id not in parent["receipt"]["table_manifests"]:
                    raise ParisonError(_ERROR)
                seen[side].add(source_id)
                active.append(side)
        if not active:
            raise ParisonError(_ERROR)
        if len(active) != 2:
            if entry["evolution"] is not None:
                raise ParisonError(_ERROR)
            continue
        paired += 1
        declaration = entry["evolution"]
        # Bound lists before the shared lineage normalizer traverses them.
        if (
            not isinstance(declaration, dict)
            or not isinstance(declaration.get("changes"), list)
            or not 1 <= len(declaration["changes"]) <= 200
        ):
            raise ParisonError(_ERROR)
        counts = {"baseline": 0, "candidate": 0}
        names = {"baseline": set(), "candidate": set()}
        for change in declaration["changes"]:
            _object(change, "change baseline candidate")
            for side in parents:
                fields = change[side]
                if not isinstance(fields, list):
                    raise ParisonError(_ERROR)
                counts[side] += len(fields)
                if counts[side] > 100:
                    raise ParisonError(_ERROR)
                for field in fields:
                    if not isinstance(field, dict):
                        raise ParisonError(_ERROR)
                    _id(field.get("id"))
                    names[side].add(_identifier(field.get("name")))
                    if isinstance(field.get("default"), str):
                        _text(field["default"])
        if normalize_evolution(declaration) != declaration:
            raise ParisonError(_ERROR)
        for side, parent in parents.items():
            columns = _columns(parent, entry[f"{side}_id"])
            if columns is not None and names[side] != set(columns):
                raise ParisonError(_ERROR)
    if paired > 16 or any(seen[side] != set(parent["receipt"]["table_manifests"]) for side, parent in parents.items()):
        raise ParisonError(_ERROR)
    if len(_canonical(plan)) + 1 > PLAN_LIMIT:
        raise ParisonError(_ERROR)
    return plan


def _add(findings, table, field, reason, compatibility):
    key = table, field, reason
    previous = findings.get(key)
    if previous is None or _RANK[compatibility] > _RANK[previous["compatibility"]]:
        findings[key] = {"table_id": table, "field_id": field, "reason": reason, "compatibility": compatibility}
    if len(findings) > 20000:
        raise ParisonError(_ERROR)


def _text_widen(baseline, candidate):
    if baseline["type"]["name"] not in {"varchar", "text"} or candidate["type"]["name"] not in {"varchar", "text"}:
        return False
    if baseline["type"]["name"] == "text" and candidate["type"]["name"] != "text":
        return False
    b, c = baseline["characters"], candidate["characters"]
    return c["state"] == "unbounded" or (b["state"] == c["state"] == "known" and c["max_length"] >= b["max_length"])


def _integer_widen(baseline, candidate):
    ranks = {"int2": 0, "int4": 1, "int8": 2}
    b, c = baseline["type"]["name"], candidate["type"]["name"]
    return b in ranks and c in ranks and ranks[c] >= ranks[b]


def _collation_observation(fact, emit):
    if fact["state"] == "unknown":
        emit("collation_unknown", "INCONCLUSIVE")
    elif fact["state"] == "resolved":
        recorded, actual = fact["recorded_version"], fact["actual_version"]
        if recorded["state"] == actual["state"] == "known":
            if recorded["value"] != actual["value"]:
                emit("collation_version_mismatch", "DENY")
        elif not (
            recorded["state"] == actual["state"] == "not-versioned"
            and fact["provider"] == "libc"
            and fact["collate"] in {"C", "POSIX"}
            and fact["ctype"] in {"C", "POSIX"}
        ):
            emit("collation_unknown", "INCONCLUSIVE")


def _collation_findings(baseline, candidate, emit):
    b, c = baseline["collation"], candidate["collation"]
    for fact in (b, c):
        _collation_observation(fact, emit)
    if "unknown" in (b["state"], c["state"]):
        emit("collation_unknown", "INCONCLUSIVE")
        return
    if b["state"] != c["state"]:
        emit("collation_changed", "DENY")
        return
    if b["state"] == "not-applicable":
        return
    definitions = ("provider", "encoding", "deterministic", "collate", "ctype", "locale", "rules")
    if any(b[k] != c[k] for k in definitions):
        emit("collation_changed", "DENY")
    versions = [fact[key] for fact in (b, c) for key in ("recorded_version", "actual_version")]
    if any(
        b[key]["state"] == c[key]["state"] == "known" and b[key]["value"] != c[key]["value"]
        for key in ("recorded_version", "actual_version")
    ):
        emit("collation_changed", "DENY")
    all_known = all(v["state"] == "known" for v in versions)
    c_posix = all(v["state"] == "not-versioned" for v in versions) and all(
        f["provider"] == "libc" and f["collate"] in {"C", "POSIX"} and f["ctype"] in {"C", "POSIX"} for f in (b, c)
    )
    if not all_known and not c_posix:
        emit("collation_unknown", "INCONCLUSIVE")


def _field_findings(baseline, candidate, rules, emit):
    supported = baseline["type"]["supported"] and candidate["type"]["supported"]
    if not supported:
        emit("unsupported_representation", "INCONCLUSIVE")
    if baseline["selected"] != candidate["selected"]:
        emit("field_membership_changed", "DENY")
    btype, ctype = baseline["type"], candidate["type"]
    if (btype["schema"], btype["name"]) != (ctype["schema"], ctype["name"]):
        allowed = supported and (
            (rules["integer"] == "widen" and _integer_widen(baseline, candidate))
            or (rules["text_length"] == "widen" and _text_widen(baseline, candidate))
        )
        emit("type_changed", "ACCEPT" if allowed else "DENY")
    b, c = baseline["numeric"], candidate["numeric"]
    if any(b[k] != c[k] for k in ("state", "precision", "radix", "scale")):
        allowed = rules["integer"] == "widen" and _integer_widen(baseline, candidate)
        if btype["name"] == ctype["name"] == "numeric" and rules["numeric"] == "widen":
            allowed = c["state"] == "unbounded" or (
                b["state"] == c["state"] == "known"
                and c["scale"] >= b["scale"]
                and c["precision"] - c["scale"] >= b["precision"] - b["scale"]
            )
        emit("numeric_changed", ("ACCEPT" if allowed else "DENY") if supported else "INCONCLUSIVE")
    if baseline["characters"] != candidate["characters"]:
        allowed = rules["text_length"] == "widen" and _text_widen(baseline, candidate)
        emit("character_length_changed", ("ACCEPT" if allowed else "DENY") if supported else "INCONCLUSIVE")
    if baseline["datetime"] != candidate["datetime"]:
        b, c = baseline["datetime"], candidate["datetime"]
        allowed = (
            rules["datetime_precision"] == "widen"
            and btype["name"] == ctype["name"]
            and b["state"] == c["state"] == "known"
            and b["timezone"] == c["timezone"]
            and b["precision"] is not None
            and c["precision"] is not None
            and c["precision"] >= b["precision"]
        )
        emit("datetime_precision_changed", ("ACCEPT" if allowed else "DENY") if supported else "INCONCLUSIVE")
    b, c = baseline["nullability"]["guarantee"], candidate["nullability"]["guarantee"]
    if "unknown" in (b, c):
        emit("nullability_unknown", "INCONCLUSIVE")
    elif b != c:
        emit(
            "nullability_changed",
            "ACCEPT" if b == "non-null" and c == "nullable" and rules["nullability"] == "relax" else "DENY",
        )
    _collation_findings(baseline, candidate, emit)
    if baseline["materialization"] != candidate["materialization"]:
        emit("materialization_changed", "INCONCLUSIVE")


def _declared_field(column, declaration, emit):
    guarantee = column["nullability"]["guarantee"]
    if guarantee == "unknown":
        emit("nullability_unknown", "INCONCLUSIVE")
    elif guarantee != declaration["nullability"]:
        emit("declaration_mismatch", "DENY")
    _collation_observation(column["collation"], emit)


def evaluate(plan, parents):
    validate_plan(plan, parents)
    findings = {}
    fields_count = tables_count = 0
    for table_id, entry in sorted(plan["tables"].items()):
        if entry["baseline_id"] is None or entry["candidate_id"] is None:
            _add(findings, table_id, None, "table_membership_changed", "DENY")
            continue
        tables_count += 1
        columns = {side: _columns(parent, entry[f"{side}_id"]) for side, parent in parents.items()}
        if any(v is None for v in columns.values()):
            _add(findings, table_id, None, "metadata_unavailable", "INCONCLUSIVE")
            continue
        changes = entry["evolution"]["changes"]
        declarations = {side: {f["name"]: f for change in changes for f in change[side]} for side in parents}
        fields_count += len({f["id"] for side in declarations.values() for f in side.values()})
        keys = {
            side: [
                declarations[side][name]["id"]
                for name in parent["representation"]["tables"][entry[f"{side}_id"]]["primary_key"]
            ]
            for side, parent in parents.items()
        }
        if keys["baseline"] != keys["candidate"]:
            _add(findings, table_id, None, "key_changed", "DENY")
        for change in changes:
            for side in parents:
                for declaration in change[side]:
                    column = columns[side][declaration["name"]]

                    def emit(reason, status, field=declaration["id"], table=table_id):
                        return _add(findings, table, field, reason, status)

                    _declared_field(column, declaration, emit)
                    if not column["type"]["supported"]:
                        emit("unsupported_representation", "INCONCLUSIVE")
            if change["change"] in {"unchanged", "renamed"}:
                baseline, candidate = (change[side][0] for side in parents)

                def emit(reason, status, field=baseline["id"], table=table_id):
                    return _add(findings, table, field, reason, status)

                _field_findings(
                    columns["baseline"][baseline["name"]], columns["candidate"][candidate["name"]], plan["rules"], emit
                )
            elif change["change"] in {"split", "merged"}:
                for declaration in change["baseline"] + change["candidate"]:
                    _add(findings, table_id, declaration["id"], "upstream_materialization_required", "DENY")
            else:
                side = "candidate" if change["change"] == "added" else "baseline"
                declaration = change[side][0]
                column = columns[side][declaration["name"]]
                required = (
                    declaration["presence"] == "required" or column["selected"] or declaration["id"] in keys[side]
                )
                _add(
                    findings, table_id, declaration["id"], "field_membership_changed", "DENY" if required else "ACCEPT"
                )
    values = sorted(
        findings.values(), key=lambda f: (f["table_id"], f["field_id"] is not None, f["field_id"] or "", f["reason"])
    )
    compatibility = max((f["compatibility"] for f in values), key=_RANK.get, default="ACCEPT")
    complete = all(p["representation"] is not None for p in parents.values())
    result = {
        "representation_assessment_version": 1,
        "kind": KIND,
        "scope": SCOPE,
        "plan_sha256": _digest(_canonical(plan)),
        "inputs": _inputs(parents),
        "complete": complete,
        "compatibility": compatibility,
        "findings": values,
        "not_assessed": list(NOT_ASSESSED),
    }
    result_data = _canonical(result) + b"\n"
    if len(result_data) > RESULT_LIMIT:
        raise ParisonError(_ERROR)
    summary = {
        "representation_summary_version": 1,
        "kind": KIND,
        "scope": SCOPE,
        "complete": complete,
        "compatibility": compatibility,
        "tables": tables_count,
        "fields": fields_count,
        "reason_counts": {reason: sum(f["reason"] == reason for f in values) for reason in REASONS},
        "assessment_sha256": _digest(result_data),
        "not_assessed": list(NOT_ASSESSED),
    }
    return result, summary


def _proposal(parents):
    if any(p["representation"] is None for p in parents.values()):
        raise ParisonError(_ERROR)
    tables = {side: p["representation"]["tables"] for side, p in parents.items()}
    common = sorted(set(tables["baseline"]) & set(tables["candidate"]))
    suggestions = []
    for i, table_id in enumerate(common, 1):
        names = {side: {c["name"] for c in record[table_id]["columns"]} for side, record in tables.items()}
        shared = sorted(names["baseline"] & names["candidate"])
        suggestions.append(
            {
                "id": f"table_{i}",
                "baseline_id": table_id,
                "candidate_id": table_id,
                "fields": [
                    {"id": f"field_{j}", "baseline_name": name, "candidate_name": name, "reason": "exact-name-only"}
                    for j, name in enumerate(shared, 1)
                ],
                "unresolved_baseline": sorted(names["baseline"] - names["candidate"]),
                "unresolved_candidate": sorted(names["candidate"] - names["baseline"]),
            }
        )
    return {
        "representation_proposal_version": 1,
        "status": "unapproved",
        "inputs": _inputs(parents),
        "tables": suggestions,
        "unresolved_tables": {side: sorted(set(record) - set(common)) for side, record in tables.items()},
    }


def _target(output, baseline, candidate):
    target = Path(output)
    check_output_parent(target.parent)
    absolute = Path(os.path.abspath(target))
    if (
        any(
            absolute == root or absolute.is_relative_to(root)
            for root in (Path(os.path.abspath(baseline)), Path(os.path.abspath(candidate)))
        )
        or target.exists()
        or target.is_symlink()
    ):
        raise ParisonError(_ERROR)
    for ancestor in (target.parent, *target.parent.parents):
        if ancestor.exists() and any(
            Path(source).exists() and ancestor.samefile(source) for source in (baseline, candidate)
        ):
            raise ParisonError(_ERROR)
    return target


def _write(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def propose(baseline, candidate, output):
    target = _target(output, baseline, candidate)
    parents = _parents(baseline, candidate)
    proposal = _proposal(parents)
    data = _canonical(proposal) + b"\n"
    if len(data) > PLAN_LIMIT:
        raise ParisonError(_ERROR)
    stage = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}-", dir=target.parent)
        stage = Path(name)
        with os.fdopen(descriptor, "w+b") as handle:
            handle.write(data)
            handle.flush()
            before = _stamp(handle)
            handle.seek(0)
            if (
                handle.read(PLAN_LIMIT + 1) != data
                or _stamp(handle) != before
                or stage.is_symlink()
                or _stat_stamp(stage.stat()) != before
            ):
                raise ParisonError(_ERROR)
        check_output_parent(target.parent)
        rename_no_replace(stage, target)
        stage = None
    finally:
        if stage is not None:
            stage.unlink()
    tables = proposal["tables"]
    return {
        "proposal_version": 1,
        "status": "unapproved",
        "table_suggestions": len(tables),
        "field_suggestions": sum(len(t["fields"]) for t in tables),
        "unresolved_tables": sum(len(v) for v in proposal["unresolved_tables"].values()),
        "unresolved_fields": sum(len(t[k]) for t in tables for k in ("unresolved_baseline", "unresolved_candidate")),
        "proposal_sha256": _digest(data),
    }


def _artifact(plan, parents):
    result, summary = evaluate(plan, parents)
    files = {
        "effective-plan.json": _canonical(plan) + b"\n",
        "assessment.json": _canonical(result) + b"\n",
        "summary.json": _canonical(summary) + b"\n",
    }
    files["manifest.json"] = (
        _canonical(
            {
                "representation_assessment_manifest_version": 1,
                "kind": KIND,
                "files": {name: _digest(data) for name, data in files.items()},
            }
        )
        + b"\n"
    )
    return files, summary


def assess(plan_path, baseline, candidate, output):
    target = _target(output, baseline, candidate)
    parents = _parents(baseline, candidate)
    plan = validate_plan(_read_plan(plan_path), parents)
    files, summary = _artifact(plan, parents)
    stage = None
    try:
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        for name, data in files.items():
            _write(stage / name, data)
        if _verify_artifact(stage, parents) != summary:
            raise ParisonError(_ERROR)
        check_output_parent(target.parent)
        rename_no_replace(stage, target)
        stage = None
    finally:
        if stage is not None:
            shutil.rmtree(stage)
    return summary


def _verify_artifact(directory, parents):
    root = Path(directory)
    check_output_parent(root.parent)
    names = {"effective-plan.json", "assessment.json", "summary.json", "manifest.json"}
    limits = {
        name: PLAN_LIMIT if name == "effective-plan.json" else RESULT_LIMIT if name == "assessment.json" else META_LIMIT
        for name in names
    }
    with ExitStack() as stack:
        fd = _directory(stack, root)
        if _members(root, fd) != names:
            raise ParisonError(_ERROR)
        directory_stamp = _stat_stamp(os.fstat(fd)) if fd is not None else None
        handles, values, data = {}, {}, {}
        for name in sorted(names):
            if fd is not None:
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                handle = stack.enter_context(os.fdopen(descriptor, "rb"))
            else:
                path = root / name
                if path.is_symlink() or not path.is_file():
                    raise ParisonError(_ERROR)
                handle = stack.enter_context(path.open("rb"))
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limits[name]:
                raise ParisonError(_ERROR)
            handles[name] = handle
        stamps = {name: _stamp(handle) for name, handle in handles.items()}
        for name, handle in handles.items():
            values[name], data[name] = _read_json(handle, limits[name])
        expected, summary = _artifact(validate_plan(values["effective-plan.json"], parents), parents)
        if data != expected or any(_stamp(handle) != stamps[name] for name, handle in handles.items()):
            raise ParisonError(_ERROR)
        if (
            (fd is None and root.is_symlink())
            or _members(root, fd) != names
            or (fd is not None and _stat_stamp(os.fstat(fd)) != directory_stamp)
        ):
            raise ParisonError(_ERROR)
        return summary


def verify(directory, baseline, candidate):
    return _verify_artifact(directory, _parents(baseline, candidate))


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParisonError(_ERROR)


def parser():
    root = _SafeParser(prog="parison representation", description="Assess native PostgreSQL representation evidence")
    commands = root.add_subparsers(dest="command", required=True, parser_class=_SafeParser)
    propose_parser = commands.add_parser(
        "propose",
        help="suggest exact unapproved field matches",
        usage="%(prog)s [-h] --baseline BASELINE\n                                      --candidate CANDIDATE --output OUTPUT",
    )
    for name in ("baseline", "candidate", "output"):
        propose_parser.add_argument("--" + name, required=True)
    assess_parser = commands.add_parser(
        "assess",
        help="assess explicitly declared native representation rules",
        usage="%(prog)s [-h] --plan PLAN --baseline BASELINE\n                                     --candidate CANDIDATE --output OUTPUT",
    )
    for name in ("plan", "baseline", "candidate", "output"):
        assess_parser.add_argument("--" + name, required=True)
    verify_parser = commands.add_parser(
        "verify",
        help="replay an assessment against both verified parents",
        usage="%(prog)s [-h] --baseline BASELINE\n                                     --candidate CANDIDATE\n                                     directory",
    )
    verify_parser.add_argument("directory")
    for name in ("baseline", "candidate"):
        verify_parser.add_argument("--" + name, required=True)
    return root


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    action = argv[0] if argv and argv[0] in {"propose", "assess", "verify"} else None
    prefix = "parison representation" + (f" {action}" if action else "")
    try:
        args = vars(parser().parse_args(argv))
        action = args.pop("command")
        if action == "assess":
            args["plan_path"] = args.pop("plan")
        summary = {"propose": propose, "assess": assess, "verify": verify}[action](**args)
        print(_canonical(summary).decode("utf-8"))
        return 0 if action == "propose" else {"ACCEPT": 0, "DENY": 1, "INCONCLUSIVE": 3}[summary["compatibility"]]
    except KeyboardInterrupt:
        print(f"{prefix}: interrupted", file=sys.stderr)
        return 130
    except (ParisonError, OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        print(f"{prefix}: {_ERROR}", file=sys.stderr)
        return 2
