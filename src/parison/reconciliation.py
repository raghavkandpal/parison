from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from parison.core import ParisonError


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_TYPES = {"string", "integer", "decimal", "float", "boolean", "date", "timestamp"}


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ParisonError(f"duplicate JSON member: {key}")
        value[key] = item
    return value


def _load(path: str | Path, kind: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_object)
    except ParisonError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read {kind}: {exc}") from exc


def _exact(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ParisonError(f"{where} must contain exactly {', '.join(sorted(keys))}")
    return value


def _identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ParisonError(f"{where} must be a stable identifier")
    return value


def _digest(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ParisonError(f"{where} must be a lowercase SHA-256 digest")
    return value


def _timestamp(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise ParisonError(f"{where} must be an RFC 3339 UTC timestamp with at most microsecond precision")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ParisonError(f"{where} is not a valid timestamp") from exc
    return parsed.strftime("%Y-%m-%dT%H:%M:%S.") + f"{parsed.microsecond:06d}Z"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalize_time_alignment(value: Any) -> dict[str, Any]:
    _exact(value, {"alignment_version", "event_window", "coordination", "datasets"}, "time alignment")
    if type(value["alignment_version"]) is not int or value["alignment_version"] != 1:
        raise ParisonError("alignment_version must be 1")
    window = _exact(value["event_window"], {"start", "end", "bounds"}, "event_window")
    start = _timestamp(window["start"], "event_window.start")
    end = _timestamp(window["end"], "event_window.end")
    if datetime.fromisoformat(start[:-1] + "+00:00") >= datetime.fromisoformat(end[:-1] + "+00:00"):
        raise ParisonError("event_window.start must be before event_window.end")
    if window["bounds"] != "start-inclusive-end-exclusive":
        raise ParisonError("event_window.bounds must be 'start-inclusive-end-exclusive'")

    coordination = value["coordination"]
    if not isinstance(coordination, dict):
        raise ParisonError("coordination must be an object")
    mode = coordination.get("mode")
    if not isinstance(mode, str):
        raise ParisonError("coordination.mode is unsupported")
    common = {"mode", "claim_id", "receipt_sha256"}
    expected = common | ({"watermark_kind", "idle_partition_policy"} if mode == "watermark" else set())
    _exact(coordination, expected, "coordination")
    if mode not in {"source-snapshot", "watermark", "declared-cutoff"}:
        raise ParisonError("coordination.mode is unsupported")
    normalized_coordination = {
        "mode": mode,
        "claim_id": _identifier(coordination["claim_id"], "coordination.claim_id"),
        "receipt_sha256": _digest(coordination["receipt_sha256"], "coordination.receipt_sha256"),
    }
    if mode == "watermark":
        if coordination["watermark_kind"] not in {"closed-world", "heuristic"}:
            raise ParisonError("coordination.watermark_kind must be 'closed-world' or 'heuristic'")
        if coordination["idle_partition_policy"] not in {"not-applicable", "documented"}:
            raise ParisonError("coordination.idle_partition_policy must be 'not-applicable' or 'documented'")
        normalized_coordination.update({
            "watermark_kind": coordination["watermark_kind"],
            "idle_partition_policy": coordination["idle_partition_policy"],
        })

    if not isinstance(value["datasets"], list) or not value["datasets"]:
        raise ParisonError("datasets must be a nonempty array")
    datasets, seen, domains = [], set(), {}
    mode_fields = {
        "source-snapshot": {"id", "event_time_column", "snapshot_token", "token_domain"},
        "watermark": {"id", "event_time_column", "watermark", "allowed_lateness_seconds"},
        "declared-cutoff": {"id", "event_time_column"},
    }
    for index, item in enumerate(value["datasets"]):
        where = f"datasets[{index}]"
        _exact(item, mode_fields[mode], where)
        dataset_id = _identifier(item["id"], f"{where}.id")
        if dataset_id in seen:
            raise ParisonError(f"duplicate dataset id {dataset_id!r}")
        seen.add(dataset_id)
        event_time_column = _identifier(item["event_time_column"], f"{where}.event_time_column")
        normalized = {"id": dataset_id, "event_time_column": event_time_column}
        if mode == "source-snapshot":
            token = item["snapshot_token"]
            if not isinstance(token, str) or not token:
                raise ParisonError(f"{where}.snapshot_token must be a nonempty opaque string")
            domain = _identifier(item["token_domain"], f"{where}.token_domain")
            if domain in domains and domains[domain] != token:
                raise ParisonError(f"snapshot token domain {domain!r} has unequal tokens")
            domains[domain] = token
            normalized.update({"snapshot_token": token, "token_domain": domain})
        elif mode == "watermark":
            normalized["watermark"] = _timestamp(item["watermark"], f"{where}.watermark")
            lateness = item["allowed_lateness_seconds"]
            if type(lateness) is not int or lateness < 0:
                raise ParisonError(f"{where}.allowed_lateness_seconds must be a nonnegative integer")
            normalized["allowed_lateness_seconds"] = lateness
        datasets.append(normalized)
    datasets.sort(key=lambda item: item["id"])
    return {
        "alignment_version": 1,
        "event_window": {"start": start, "end": end, "bounds": "start-inclusive-end-exclusive"},
        "coordination": normalized_coordination,
        "datasets": datasets,
    }


def canonical_time_alignment_bytes(value: Any) -> bytes:
    return _canonical(normalize_time_alignment(value))


def load_time_alignment(path: str | Path) -> dict[str, Any]:
    return normalize_time_alignment(_load(path, "time alignment declaration"))


def explain_time_alignment(path: str | Path) -> dict[str, Any]:
    normalized = load_time_alignment(path)
    return {**normalized, "alignment_sha256": hashlib.sha256(_canonical(normalized)).hexdigest()}


def _columns(value: Any, where: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ParisonError(f"{where} must be a nonempty column array")
    result, names = [], set()
    for index, item in enumerate(value):
        _exact(item, {"name", "type"}, f"{where}[{index}]")
        name = _identifier(item["name"], f"{where}[{index}].name")
        if name in names:
            raise ParisonError(f"{where} repeats column {name!r}")
        if not isinstance(item["type"], str) or item["type"] not in _TYPES:
            raise ParisonError(f"{where}[{index}].type is unsupported")
        names.add(name)
        result.append({"name": name, "type": item["type"]})
    return result


def normalize_reconciliation(value: Any) -> dict[str, Any]:
    _exact(value, {"reconciliation_version", "alignment_sha256", "datasets", "checks"}, "reconciliation")
    if type(value["reconciliation_version"]) is not int or value["reconciliation_version"] != 1:
        raise ParisonError("reconciliation_version must be 1")
    if not isinstance(value["datasets"], list) or not value["datasets"]:
        raise ParisonError("datasets must be a nonempty array")
    datasets, dataset_columns = [], {}
    for index, item in enumerate(value["datasets"]):
        where = f"datasets[{index}]"
        _exact(item, {"id", "recipe_sha256", "columns"}, where)
        dataset_id = _identifier(item["id"], f"{where}.id")
        if dataset_id in dataset_columns:
            raise ParisonError(f"duplicate dataset id {dataset_id!r}")
        columns = _columns(item["columns"], f"{where}.columns")
        dataset_columns[dataset_id] = {column["name"]: column["type"] for column in columns}
        datasets.append({"id": dataset_id, "recipe_sha256": _digest(item["recipe_sha256"], f"{where}.recipe_sha256"), "columns": columns})

    if not isinstance(value["checks"], list) or not value["checks"]:
        raise ParisonError("checks must be a nonempty array")
    checks, check_ids, identities, dependency_edges = [], set(), {}, []
    for index, item in enumerate(value["checks"]):
        where = f"checks[{index}]"
        if not isinstance(item, dict):
            raise ParisonError(f"{where} must be an object")
        kind = item.get("kind")
        fields = {
            "identity": {"id", "kind", "dataset", "columns", "nulls"},
            "reference": {"id", "kind", "child_dataset", "child_columns", "parent_identity", "nulls"},
            "conservation": {"id", "kind", "parent_dataset", "parent_identity", "parent_group_columns", "child_dataset", "child_group_columns", "parent_measure", "child_measure", "operator", "nulls", "comparison", "tolerance"},
        }
        if not isinstance(kind, str) or kind not in fields:
            raise ParisonError(f"{where}.kind is unsupported")
        _exact(item, fields[kind], where)
        check_id = _identifier(item["id"], f"{where}.id")
        if check_id in check_ids:
            raise ParisonError(f"duplicate check id {check_id!r}")
        check_ids.add(check_id)
        checks.append(dict(item))
        if kind == "identity":
            identities[check_id] = item

    def typed(dataset: Any, columns: Any, where: str) -> tuple[str, ...]:
        dataset_id = _identifier(dataset, f"{where}.dataset")
        if dataset_id not in dataset_columns:
            raise ParisonError(f"{where} names undeclared dataset {dataset_id!r}")
        if not isinstance(columns, list) or not columns:
            raise ParisonError(f"{where}.columns must be a nonempty array")
        if len(set(columns)) != len(columns):
            raise ParisonError(f"{where}.columns must not repeat columns")
        types = []
        for column in columns:
            _identifier(column, f"{where}.columns[]")
            if column not in dataset_columns[dataset_id]:
                raise ParisonError(f"{where} names undeclared column {column!r}")
            types.append(dataset_columns[dataset_id][column])
        return tuple(types)

    for check in checks:
        kind, check_id = check["kind"], check["id"]
        where = f"check {check_id!r}"
        if kind == "identity":
            typed(check["dataset"], check["columns"], where)
            if check["nulls"] not in {"forbid", "equal"}:
                raise ParisonError(f"{where}.nulls is unsupported")
        elif kind == "reference":
            child_types = typed(check["child_dataset"], check["child_columns"], where)
            parent_identity = _identifier(check["parent_identity"], f"{where}.parent_identity")
            parent = identities.get(parent_identity)
            if parent is None:
                raise ParisonError(f"{where} names undeclared parent identity")
            parent_types = typed(parent["dataset"], parent["columns"], f"identity {parent['id']!r}")
            if child_types != parent_types:
                raise ParisonError(f"{where} child and parent key types must match")
            if check["nulls"] not in {"forbid", "all-null-exempt", "match-null"}:
                raise ParisonError(f"{where}.nulls is unsupported")
            dependency_edges.append((check["child_dataset"], parent["dataset"]))
        else:
            parent_identity = _identifier(check["parent_identity"], f"{where}.parent_identity")
            parent = identities.get(parent_identity)
            if parent is None or parent["dataset"] != check["parent_dataset"]:
                raise ParisonError(f"{where} must name an identity on its parent dataset")
            parent_types = typed(check["parent_dataset"], check["parent_group_columns"], where)
            child_types = typed(check["child_dataset"], check["child_group_columns"], where)
            if parent_types != child_types:
                raise ParisonError(f"{where} parent and child group types must match")
            if tuple(check["parent_group_columns"]) != tuple(parent["columns"]):
                raise ParisonError(f"{where} parent group columns must equal its identity columns")
            for field in ("parent_measure", "child_measure"):
                dataset_id = check["parent_dataset"] if field == "parent_measure" else check["child_dataset"]
                column = _identifier(check[field], f"{where}.{field}")
                if dataset_columns[dataset_id].get(column) not in {"integer", "decimal", "float"}:
                    raise ParisonError(f"{where}.{field} must name a numeric column")
            if check["operator"] != "sum" or not isinstance(check["nulls"], str) or check["nulls"] not in {"forbid", "zero"} or not isinstance(check["comparison"], str) or check["comparison"] not in {"exact", "tolerance"}:
                raise ParisonError(f"{where} has unsupported conservation semantics")
            tolerance = check["tolerance"]
            if check["comparison"] == "exact":
                if tolerance is not None:
                    raise ParisonError(f"{where}.tolerance must be null for exact comparison")
            else:
                _exact(tolerance, {"formula", "absolute", "relative"}, f"{where}.tolerance")
                if tolerance["formula"] != "symmetric-v1" or any(type(tolerance[key]) not in {int, float} or not math.isfinite(tolerance[key]) or tolerance[key] < 0 for key in ("absolute", "relative")):
                    raise ParisonError(f"{where}.tolerance must be a nonnegative symmetric-v1 tolerance")
            dependency_edges.append((check["child_dataset"], check["parent_dataset"]))

    graph = {dataset["id"]: set() for dataset in datasets}
    for child, parent in dependency_edges:
        graph[child].add(parent)
    visiting, visited = set(), set()
    def visit(node: str) -> None:
        if node in visiting:
            raise ParisonError("dataset relationship graph must be acyclic")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)
    for node in sorted(graph):
        visit(node)

    datasets.sort(key=lambda item: item["id"])
    order = {"identity": 0, "reference": 1, "conservation": 2}
    checks.sort(key=lambda item: (order[item["kind"]], item["id"]))
    return {"reconciliation_version": 1, "alignment_sha256": _digest(value["alignment_sha256"], "alignment_sha256"), "datasets": datasets, "checks": checks}


def canonical_reconciliation_bytes(value: Any) -> bytes:
    return _canonical(normalize_reconciliation(value))


def load_reconciliation(path: str | Path) -> dict[str, Any]:
    return normalize_reconciliation(_load(path, "reconciliation declaration"))


def explain_reconciliation(path: str | Path) -> dict[str, Any]:
    normalized = load_reconciliation(path)
    return {**normalized, "reconciliation_sha256": hashlib.sha256(_canonical(normalized)).hexdigest()}
