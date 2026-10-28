"""Bounded, summary-only analysis of complete verified suite rehearsals."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

from .analysis import _canonical, _groups, _is_sha, _read_verified_run, _strict_object, _transition
from .core import ParisonError
from .evidence import _verified_bundle

MAX_RUNS = 16
MAX_CASES = 100
MAX_GROUPS = 10_000


def _identity(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(value)).hexdigest()


def _input_transitions(runs: list[dict]) -> list[dict]:
    return [
        {
            "from_run": index,
            "to_run": index + 1,
            **{
                side + "_changed": before["inputs"][side] != after["inputs"][side] for side in ("baseline", "candidate")
            },
        }
        for index, (before, after) in enumerate(itertools.pairwise(runs))
    ]


def analyze_suite_series(directories) -> dict[str, Any]:
    """Keep caller order and case units, omitting names and policy fragments."""
    paths = [Path(path) for path in itertools.islice(directories, MAX_RUNS + 1)]
    if not 2 <= len(paths) <= MAX_RUNS:
        raise ParisonError("suite series requires 2-16 parents")
    parents, case_rows, identity, snapshots = [], [], None, []
    for path in paths:
        manifest, before = _verified_bundle(path)
        if manifest.get("kind") != "suite":
            raise ParisonError("suite series requires complete non-shard suite parents")
        try:
            payload = (path / "suite-result.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != manifest["files"]["suite-result.json"]:
                raise ParisonError("suite changed during series analysis")
            result = json.loads(payload, object_pairs_hook=_strict_object)
        except (OSError, ValueError) as exc:
            raise ParisonError("cannot read suite series parent") from exc
        cases = result["cases"]
        if result["complete"] is not True or not 1 <= len(cases) <= MAX_CASES:
            raise ParisonError("suite series requires complete parents with 1-100 cases")
        policy = result["suite_policy_sha256" if result["suite_version"] == 2 else "suite_sha256"]
        current = (
            result["suite_version"],
            policy,
            result.get("selection"),
            [(case["id"], case["policy_sha256"], case["contract"]) for case in cases],
        )
        if identity is not None and current != identity:
            raise ParisonError("suite series requires exact policy, selection and ordered cases")
        identity = current
        parent_sha = hashlib.sha256(before).hexdigest()
        if any(parent["bundle_sha256"] == parent_sha for parent in parents):
            raise ParisonError("suite series requires distinct parents")
        parents.append({"bundle_sha256": parent_sha, "outcome": result["outcome"]})
        row, group_count = [], 0
        for case in cases:
            child, recipe, digest = _read_verified_run(path / case["bundle"])
            if (
                child["complete"] is not True
                or digest != case["manifest_sha256"]
                or child["policy_sha256"] != case["policy_sha256"]
            ):
                raise ParisonError("suite series child changed or is incomplete")
            groups = _groups(child, recipe)
            group_count += len(groups)
            if group_count > MAX_GROUPS:
                raise ParisonError("suite series exceeds 10000 case groups")
            row.append(
                {
                    "case_ref": _identity("parison:suite-case:v1", [policy, case["id"]]),
                    "policy_sha256": child["policy_sha256"],
                    "comparison_mode": recipe["comparison_mode"],
                    "run": {
                        "bundle_sha256": digest,
                        "outcome": child["outcome"],
                        "inputs": {side: child["inputs"][side]["sha256"] for side in ("baseline", "candidate")},
                    },
                    "groups": {group["group_id"]: group for group in groups},
                }
            )
        case_rows.append(row)
        snapshots.append(before)
    combined = []
    for members in zip(*case_rows, strict=True):
        first = members[0]
        if any(member["comparison_mode"] != first["comparison_mode"] for member in members):
            raise ParisonError("suite series requires exact per-case comparison modes")
        sources = sorted(first["groups"])
        if any(sorted(member["groups"]) != sources for member in members):
            raise ParisonError("suite series requires identical per-case group identities")
        groups = []
        for source in sources:
            descriptor = first["groups"][source]["descriptor"]
            group_id = _identity("parison:suite-group:v1", [first["case_ref"], source])
            counts = [member["groups"][source]["count"] for member in members]
            groups.append(
                {
                    "group_id": group_id,
                    "source_group_id": source,
                    "kind": descriptor["kind"],
                    "classification": descriptor["classification"],
                    "counts": counts,
                    "transitions": [
                        _transition(group_id, i, a, b) for i, (a, b) in enumerate(itertools.pairwise(counts))
                    ],
                }
            )
        runs = [member["run"] for member in members]
        combined.append(
            {name: first[name] for name in ("case_ref", "policy_sha256", "comparison_mode")}
            | {"runs": runs, "groups": groups, "input_transitions": _input_transitions(runs)}
        )
    for path, before in zip(paths, snapshots, strict=True):
        if _verified_bundle(path)[1] != before:
            raise ParisonError("suite changed during series analysis")
    series = {
        "suite_series_version": 1,
        "kind": "suite-series",
        "sensitivity": "summary",
        "suite_version": identity[0],
        "suite_policy_sha256": identity[1],
        "selection_sha256": hashlib.sha256(_canonical(identity[2])).hexdigest(),
        "runs": parents,
        "cases": combined,
    }
    validate_suite_series(series)
    return series


def _object(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys.split()):
        raise ParisonError("suite series contains invalid fields")


def _list(value, minimum, maximum):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ParisonError("suite series exceeds supported cardinality")


def _sha(value):
    if not _is_sha(value):
        raise ParisonError("suite series contains invalid identity")


def _run(value, child=False):
    _object(value, "bundle_sha256 outcome inputs" if child else "bundle_sha256 outcome")
    _sha(value["bundle_sha256"])
    if not isinstance(value["outcome"], str) or value["outcome"] not in {"PASS", "FAIL"}:
        raise ParisonError("suite series requires complete PASS/FAIL evidence")
    if child:
        _object(value["inputs"], "baseline candidate")
        for digest in value["inputs"].values():
            _sha(digest)


def _validate_suite_series(value: Any) -> None:
    """Independently validate the closed summary and all derived transitions."""
    _object(
        value, "suite_series_version kind sensitivity suite_version suite_policy_sha256 selection_sha256 runs cases"
    )
    if (
        type(value["suite_series_version"]) is not int
        or value["suite_series_version"] != 1
        or value["kind"] != "suite-series"
        or value["sensitivity"] != "summary"
        or type(value["suite_version"]) is not int
        or value["suite_version"] not in (1, 2)
    ):
        raise ParisonError("unsupported suite series version")
    _sha(value["suite_policy_sha256"])
    _sha(value["selection_sha256"])
    runs, cases = value["runs"], value["cases"]
    _list(runs, 2, MAX_RUNS)
    _list(cases, 1, MAX_CASES)
    for run in runs:
        _run(run)
    if len({run["bundle_sha256"] for run in runs}) != len(runs):
        raise ParisonError("suite series requires distinct parents")
    seen, group_count = set(), 0
    for case in cases:
        _object(case, "case_ref policy_sha256 comparison_mode runs groups input_transitions")
        _sha(case["case_ref"])
        _sha(case["policy_sha256"])
        if case["case_ref"] in seen:
            raise ParisonError("suite series contains duplicate cases")
        seen.add(case["case_ref"])
        mode = case["comparison_mode"]
        if not isinstance(mode, str) or mode not in {"keyed", "aggregate", "multiset"}:
            raise ParisonError("unsupported suite series comparison mode")
        _list(case["runs"], len(runs), len(runs))
        for run in case["runs"]:
            _run(run, child=True)
        if _canonical(case["input_transitions"]) != _canonical(_input_transitions(case["runs"])):
            raise ParisonError("suite series input transitions do not reconcile")
        _list(case["groups"], 1, MAX_GROUPS)
        group_count += len(case["groups"])
        if group_count > MAX_GROUPS:
            raise ParisonError("suite series exceeds 10000 case groups")
        sources = []
        failures = [False] * len(runs)
        for group in case["groups"]:
            _object(group, "group_id source_group_id kind classification counts transitions")
            _sha(group["source_group_id"])
            expected_id = _identity("parison:suite-group:v1", [case["case_ref"], group["source_group_id"]])
            if group["group_id"] != expected_id:
                raise ParisonError("suite series group identity mismatch")
            kind, classification = group["kind"], group["classification"]
            allowed = (
                {("record", side) for side in ("baseline_only", "candidate_only")}
                | {("field", side) for side in ("within_tolerance", "different")}
                if mode == "keyed"
                else {("group", side) for side in ("baseline_only", "candidate_only")}
                | {("measure", side) for side in ("within_tolerance", "different")}
                if mode == "aggregate"
                else {("row", side) for side in ("baseline_surplus", "candidate_surplus")}
            )
            if (
                not isinstance(kind, str)
                or not isinstance(classification, str)
                or (kind, classification) not in allowed
            ):
                raise ParisonError("suite series contains unsupported group semantics")
            counts = group["counts"]
            _list(counts, len(runs), len(runs))
            if any(type(count) is not int or count < 0 for count in counts):
                raise ParisonError("suite series contains invalid counts")
            expected = [_transition(expected_id, i, a, b) for i, (a, b) in enumerate(itertools.pairwise(counts))]
            if _canonical(group["transitions"]) != _canonical(expected):
                raise ParisonError("suite series count transitions do not reconcile")
            if classification != "within_tolerance":
                failures = [failed or count > 0 for failed, count in zip(failures, counts, strict=True)]
            sources.append(group["source_group_id"])
        if sources != sorted(set(sources)):
            raise ParisonError("suite series groups must be unique and ordered")
        if [run["outcome"] for run in case["runs"]] != ["FAIL" if failed else "PASS" for failed in failures]:
            raise ParisonError("suite series case outcomes do not reconcile")
    for index, run in enumerate(runs):
        expected = "FAIL" if any(case["runs"][index]["outcome"] == "FAIL" for case in cases) else "PASS"
        if run["outcome"] != expected:
            raise ParisonError("suite series parent outcomes do not reconcile")


def validate_suite_series(value: Any) -> None:
    """Reject malformed wire values with a controlled verification failure."""
    try:
        _validate_suite_series(value)
    except (ValueError, TypeError, KeyError) as exc:
        raise ParisonError("suite series contains invalid values") from exc
