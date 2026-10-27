from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from parison import __version__
from parison._safe_fs import check_output_parent as _check_output_parent
from parison._safe_fs import rename_no_replace as _rename_no_replace
from parison.core import (
    ParisonError,
    _classify,
    _decoded_sizes,
    _iter_input_rows,
    _multiset_encoding,
    _normalize,
    _parse_input,
    _parse_row,
    _source_bytes,
    _source_digest,
    _source_name,
    _verify_manifest_files,
    compare,
    explain_recipe,
    load_recipe,
)
from parison.core import (
    _digest as file_digest,
)

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
        normalized_coordination.update(
            {
                "watermark_kind": coordination["watermark_kind"],
                "idle_partition_policy": coordination["idle_partition_policy"],
            }
        )

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
        _exact(item, {"id", "policy_sha256", "columns"}, where)
        dataset_id = _identifier(item["id"], f"{where}.id")
        if dataset_id in dataset_columns:
            raise ParisonError(f"duplicate dataset id {dataset_id!r}")
        columns = _columns(item["columns"], f"{where}.columns")
        dataset_columns[dataset_id] = {column["name"]: column["type"] for column in columns}
        datasets.append(
            {
                "id": dataset_id,
                "policy_sha256": _digest(item["policy_sha256"], f"{where}.policy_sha256"),
                "columns": columns,
            }
        )

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
            "conservation": {
                "id",
                "kind",
                "parent_dataset",
                "parent_identity",
                "parent_group_columns",
                "child_dataset",
                "child_group_columns",
                "parent_measure",
                "child_measure",
                "operator",
                "nulls",
                "comparison",
                "tolerance",
            },
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
                if dataset_columns[dataset_id].get(column) not in {"integer", "decimal"}:
                    raise ParisonError(f"{where}.{field} must name a numeric column")
            if (
                dataset_columns[check["parent_dataset"]][check["parent_measure"]]
                != dataset_columns[check["child_dataset"]][check["child_measure"]]
            ):
                raise ParisonError(f"{where} parent and child measure types must match")
            if (
                check["operator"] != "sum"
                or not isinstance(check["nulls"], str)
                or check["nulls"] not in {"forbid", "zero"}
                or not isinstance(check["comparison"], str)
                or check["comparison"] not in {"exact", "tolerance"}
            ):
                raise ParisonError(f"{where} has unsupported conservation semantics")
            tolerance = check["tolerance"]
            if check["comparison"] == "exact":
                if tolerance is not None:
                    raise ParisonError(f"{where}.tolerance must be null for exact comparison")
            else:
                _exact(tolerance, {"formula", "absolute", "relative"}, f"{where}.tolerance")
                if tolerance["formula"] != "symmetric-v1" or any(
                    type(tolerance[key]) not in {int, float} or not math.isfinite(tolerance[key]) or tolerance[key] < 0
                    for key in ("absolute", "relative")
                ):
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
    return {
        "reconciliation_version": 1,
        "alignment_sha256": _digest(value["alignment_sha256"], "alignment_sha256"),
        "datasets": datasets,
        "checks": checks,
    }


def canonical_reconciliation_bytes(value: Any) -> bytes:
    return _canonical(normalize_reconciliation(value))


def load_reconciliation(path: str | Path) -> dict[str, Any]:
    return normalize_reconciliation(_load(path, "reconciliation declaration"))


def explain_reconciliation(path: str | Path) -> dict[str, Any]:
    normalized = load_reconciliation(path)
    return {**normalized, "reconciliation_sha256": hashlib.sha256(_canonical(normalized)).hexdigest()}


def preflight_alignment(
    alignment_path: str | Path,
    reconciliation_path: str | Path,
    receipt_path: str | Path,
    inputs: dict[str, dict[str, str | Path]],
    max_input_bytes: int = 1_000_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
) -> dict[str, Any]:
    """Scan event-time scope and evaluate source-owned coordination claims."""
    if max_input_bytes <= 0 or max_rows <= 0:
        raise ParisonError("input byte and row limits must be positive")
    alignment = explain_time_alignment(alignment_path)
    reconciliation = explain_reconciliation(reconciliation_path)
    if reconciliation["alignment_sha256"] != alignment["alignment_sha256"]:
        raise ParisonError("reconciliation alignment_sha256 does not match the time alignment declaration")
    aligned = {item["id"]: item for item in alignment["datasets"]}
    reconciled = {item["id"]: item for item in reconciliation["datasets"]}
    if set(aligned) != set(reconciled) or set(inputs) != set(aligned):
        raise ParisonError("alignment, reconciliation and runtime input dataset ids must match exactly")
    for dataset_id, runtime in inputs.items():
        _identifier(dataset_id, "runtime dataset id")
        _exact(runtime, {"recipe", "baseline", "candidate"}, f"runtime dataset {dataset_id!r}")

    receipt = Path(receipt_path)
    if receipt.is_symlink() or not receipt.is_file():
        raise ParisonError("coordination receipt must be a regular non-symlink file")
    receipt_sha256 = file_digest(receipt)
    if receipt_sha256 != alignment["coordination"]["receipt_sha256"]:
        raise ParisonError("coordination receipt SHA-256 does not match the declaration")

    sources = tuple(inputs[dataset_id][side] for dataset_id in sorted(inputs) for side in ("baseline", "candidate"))
    if sum(_source_bytes(source) for source in sources) > max_input_bytes:
        raise ParisonError(f"combined input size exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes(sources, max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in sources}
    start = datetime.fromisoformat(alignment["event_window"]["start"][:-1] + "+00:00")
    end = datetime.fromisoformat(alignment["event_window"]["end"][:-1] + "+00:00")
    results = []
    for dataset_id in sorted(inputs):
        runtime, declaration, contract = inputs[dataset_id], aligned[dataset_id], reconciled[dataset_id]
        recipe = load_recipe(runtime["recipe"])
        policy = explain_recipe(runtime["recipe"])
        if policy["policy_sha256"] != contract["policy_sha256"]:
            raise ParisonError(f"dataset {dataset_id!r} policy SHA-256 does not match reconciliation")
        event_column = declaration["event_time_column"]
        if event_column not in recipe["columns"] or recipe["columns"][event_column]["type"] != "timestamp":
            raise ParisonError(f"dataset {dataset_id!r} event_time_column must name a configured timestamp")
        declared_columns = {column["name"]: column["type"] for column in contract["columns"]}
        actual_columns = {name: configured["type"] for name, configured in recipe["columns"].items()}
        if declared_columns != actual_columns:
            raise ParisonError(f"dataset {dataset_id!r} semantic columns do not match its effective recipe")
        sides = {}
        for side in ("baseline", "candidate"):
            counts = {
                "rows": 0,
                "in_window": 0,
                "before_window": 0,
                "at_or_after_end": 0,
                "null_event_time": 0,
                "invalid_event_time": 0,
            }
            for raw in _iter_input_rows(runtime[side], recipe, max_rows, side, decoded_sizes):
                counts["rows"] += 1
                raw_value = raw.get(_source_name(recipe, event_column, side))
                if raw_value is None:
                    counts["null_event_time"] += 1
                    continue
                timestamp = _normalize(
                    _parse_input(raw_value, recipe["columns"][event_column], event_column, recipe),
                    recipe["columns"][event_column],
                )
                if timestamp is None:
                    counts["null_event_time"] += 1
                    continue
                if timestamp < start:
                    counts["before_window"] += 1
                elif timestamp >= end:
                    counts["at_or_after_end"] += 1
                else:
                    counts["in_window"] += 1
            sides[side] = counts
        results.append({"id": dataset_id, "sides": sides})
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while alignment was being checked")

    data_failure = any(
        counts[field]
        for dataset in results
        for counts in dataset["sides"].values()
        for field in ("before_window", "at_or_after_end", "null_event_time", "invalid_event_time")
    )
    coordination = alignment["coordination"]
    reasons = []
    coordination_status = "PASS"
    if coordination["mode"] == "watermark":
        insufficient = [
            item["id"]
            for item in alignment["datasets"]
            if datetime.fromisoformat(item["watermark"][:-1] + "+00:00") < end
        ]
        if insufficient:
            coordination_status, reasons = "FAIL", ["watermark-before-window-end"]
        elif coordination["watermark_kind"] == "heuristic":
            coordination_status, reasons = "INCONCLUSIVE", ["heuristic-watermark"]
    elif coordination["mode"] == "declared-cutoff":
        coordination_status, reasons = "INCONCLUSIVE", ["coordination-not-machine-established"]
    outcome = (
        "FAIL"
        if data_failure or coordination_status == "FAIL"
        else "INCONCLUSIVE"
        if coordination_status == "INCONCLUSIVE"
        else "PASS"
    )
    if data_failure:
        reasons.append("event-time-scope-failed")
    return {
        "alignment_preflight_version": 1,
        "outcome": outcome,
        "alignment_status": "FAIL" if data_failure else coordination_status,
        "reason_codes": sorted(set(reasons)),
        "alignment_sha256": alignment["alignment_sha256"],
        "reconciliation_sha256": reconciliation["reconciliation_sha256"],
        "receipt_sha256": receipt_sha256,
        "coordination_mode": coordination["mode"],
        "event_window": alignment["event_window"],
        "datasets": results,
        "resource_limits": {
            "max_input_bytes": max_input_bytes,
            "max_decoded_bytes": max_decoded_bytes,
            "max_rows_per_input": max_rows,
        },
    }


def check_identity_references(
    reconciliation_path: str | Path,
    inputs: dict[str, dict[str, str | Path]],
    engine: str = "memory",
    max_input_bytes: int = 1_000_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
    max_keys: int = 100_000,
    max_temp_bytes: int = 5_000_000_000,
    temp_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate reconciliation-v1 identity and reference checks on both sides."""
    if engine not in {"memory", "sqlite"}:
        raise ParisonError("engine must be memory or sqlite")
    if any(limit <= 0 for limit in (max_input_bytes, max_decoded_bytes, max_rows, max_keys, max_temp_bytes)):
        raise ParisonError("resource limits must be positive")
    if engine == "memory" and temp_directory is not None:
        raise ParisonError("temp_directory requires engine='sqlite'")
    if temp_directory is not None and (Path(temp_directory).is_symlink() or not Path(temp_directory).is_dir()):
        raise ParisonError("temp directory must be an existing non-symlink directory")
    reconciliation = explain_reconciliation(reconciliation_path)
    contracts = {item["id"]: item for item in reconciliation["datasets"]}
    if set(inputs) != set(contracts):
        raise ParisonError("reconciliation and runtime input dataset ids must match exactly")
    sources = tuple(inputs[dataset_id][side] for dataset_id in sorted(inputs) for side in ("baseline", "candidate"))
    if sum(_source_bytes(source) for source in sources) > max_input_bytes:
        raise ParisonError(f"combined input size exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes(sources, max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in sources}
    recipes = {}
    for dataset_id, runtime in inputs.items():
        _exact(runtime, {"recipe", "baseline", "candidate"}, f"runtime dataset {dataset_id!r}")
        recipe = load_recipe(runtime["recipe"])
        policy = explain_recipe(runtime["recipe"])
        if policy["policy_sha256"] != contracts[dataset_id]["policy_sha256"]:
            raise ParisonError(f"dataset {dataset_id!r} policy SHA-256 does not match reconciliation")
        declared = {column["name"]: column["type"] for column in contracts[dataset_id]["columns"]}
        actual = {name: configured["type"] for name, configured in recipe["columns"].items()}
        if declared != actual:
            raise ParisonError(f"dataset {dataset_id!r} semantic columns do not match its effective recipe")
        recipes[dataset_id] = recipe

    identities = {check["id"]: check for check in reconciliation["checks"] if check["kind"] == "identity"}
    references = [check for check in reconciliation["checks"] if check["kind"] == "reference"]
    memory_keys: dict[tuple[str, str], Counter[bytes]] = {}
    results = {side: [] for side in ("baseline", "candidate")}

    def encoded(row: dict[str, Any], dataset_id: str, columns: list[str]) -> tuple[bytes, tuple[Any, ...]]:
        values = tuple(row[column] for column in columns)
        return _multiset_encoding(values, columns, recipes[dataset_id]), values

    def rows(dataset_id: str, side: str):
        recipe = recipes[dataset_id]
        for raw in _iter_input_rows(inputs[dataset_id][side], recipe, max_rows, side, decoded_sizes):
            yield _parse_row(raw, recipe, side)

    parent = Path(temp_directory) if temp_directory is not None else None
    workspace = (
        tempfile.TemporaryDirectory(prefix="parison-reconciliation-", dir=parent) if engine == "sqlite" else None
    )
    connection = None
    try:
        if workspace is not None:
            database = Path(workspace.name) / "relationships.sqlite"
            connection = sqlite3.connect(database)
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            page_limit = max_temp_bytes // page_size
            if page_limit < 4:
                raise ParisonError(f"temporary storage limit {max_temp_bytes} bytes is too small")
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute(f"PRAGMA max_page_count={page_limit}")
            connection.execute(
                "CREATE TABLE identities (side TEXT NOT NULL, check_id TEXT NOT NULL, key BLOB NOT NULL, occurrences INTEGER NOT NULL, PRIMARY KEY(side, check_id, key)) WITHOUT ROWID"
            )

        for side in ("baseline", "candidate"):
            for check_id, check in identities.items():
                counts, null_rows, total = Counter(), 0, 0
                for row in rows(check["dataset"], side):
                    key, values = encoded(row, check["dataset"], check["columns"])
                    total += 1
                    null_rows += any(value is None for value in values)
                    if connection is None:
                        counts[key] += 1
                        if len(counts) > max_keys:
                            raise ParisonError(f"identity {check_id!r} exceeds distinct key limit {max_keys}")
                    else:
                        connection.execute(
                            "INSERT INTO identities VALUES (?, ?, ?, 1) ON CONFLICT(side, check_id, key) DO UPDATE SET occurrences = occurrences + 1",
                            (side, check_id, key),
                        )
                if connection is not None:
                    connection.commit()
                    distinct, duplicates = connection.execute(
                        "SELECT COUNT(*), COALESCE(SUM(occurrences > 1), 0) FROM identities WHERE side=? AND check_id=?",
                        (side, check_id),
                    ).fetchone()
                    if distinct > max_keys:
                        raise ParisonError(f"identity {check_id!r} exceeds distinct key limit {max_keys}")
                else:
                    distinct, duplicates = len(counts), sum(value > 1 for value in counts.values())
                    memory_keys[(side, check_id)] = counts
                failed = duplicates > 0 or (check["nulls"] == "forbid" and null_rows > 0)
                results[side].append(
                    {
                        "id": check_id,
                        "kind": "identity",
                        "outcome": "FAIL" if failed else "PASS",
                        "counts": {
                            "rows": total,
                            "distinct_keys": distinct,
                            "null_key_rows": null_rows,
                            "duplicate_keys": duplicates,
                        },
                    }
                )

            for check in references:
                parent_check = identities[check["parent_identity"]]
                counts = {
                    "child_rows": 0,
                    "exempt_rows": 0,
                    "matched_rows": 0,
                    "orphan_rows": 0,
                    "ambiguous_parent_rows": 0,
                    "null_failure_rows": 0,
                }
                for row in rows(check["child_dataset"], side):
                    counts["child_rows"] += 1
                    key, values = encoded(row, check["child_dataset"], check["child_columns"])
                    all_null, any_null = all(value is None for value in values), any(value is None for value in values)
                    if check["nulls"] == "all-null-exempt" and all_null:
                        counts["exempt_rows"] += 1
                        continue
                    if check["nulls"] in {"forbid", "all-null-exempt"} and any_null:
                        counts["null_failure_rows"] += 1
                        continue
                    if connection is None:
                        occurrences = memory_keys[(side, parent_check["id"])].get(key, 0)
                    else:
                        found = connection.execute(
                            "SELECT occurrences FROM identities WHERE side=? AND check_id=? AND key=?",
                            (side, parent_check["id"], key),
                        ).fetchone()
                        occurrences = found[0] if found else 0
                    if occurrences == 1:
                        counts["matched_rows"] += 1
                    elif occurrences == 0:
                        counts["orphan_rows"] += 1
                    else:
                        counts["ambiguous_parent_rows"] += 1
                failed = any(counts[field] for field in ("orphan_rows", "ambiguous_parent_rows", "null_failure_rows"))
                results[side].append(
                    {"id": check["id"], "kind": "reference", "outcome": "FAIL" if failed else "PASS", "counts": counts}
                )
        if connection is not None:
            connection.commit()
    except sqlite3.Error as exc:
        if "full" in str(exc).lower():
            raise ParisonError(f"temporary storage exceeds limit {max_temp_bytes} bytes") from exc
        raise ParisonError(f"relationship spill database failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
        if workspace is not None:
            workspace.cleanup()

    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while relationships were being checked")
    outcome = "FAIL" if any(check["outcome"] == "FAIL" for side in results.values() for check in side) else "PASS"
    output = {
        "relationship_result_version": 1,
        "outcome": outcome,
        "reconciliation_sha256": reconciliation["reconciliation_sha256"],
        "sides": results,
        "resource_limits": {
            "max_input_bytes": max_input_bytes,
            "max_decoded_bytes": max_decoded_bytes,
            "max_rows_per_input": max_rows,
            "max_keys_per_identity": max_keys,
        },
    }
    return output


def check_conservation(
    reconciliation_path: str | Path,
    inputs: dict[str, dict[str, str | Path]],
    engine: str = "memory",
    max_input_bytes: int = 1_000_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
    max_groups: int = 100_000,
    max_temp_bytes: int = 5_000_000_000,
    temp_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate reconciliation-v1 grouped-sum conservation on both sides."""
    if engine not in {"memory", "sqlite"}:
        raise ParisonError("engine must be memory or sqlite")
    if any(limit <= 0 for limit in (max_input_bytes, max_decoded_bytes, max_rows, max_groups, max_temp_bytes)):
        raise ParisonError("resource limits must be positive")
    if engine == "memory" and temp_directory is not None:
        raise ParisonError("temp_directory requires engine='sqlite'")
    if temp_directory is not None and (Path(temp_directory).is_symlink() or not Path(temp_directory).is_dir()):
        raise ParisonError("temp directory must be an existing non-symlink directory")
    reconciliation = explain_reconciliation(reconciliation_path)
    contracts = {item["id"]: item for item in reconciliation["datasets"]}
    if set(inputs) != set(contracts):
        raise ParisonError("reconciliation and runtime input dataset ids must match exactly")
    sources = tuple(inputs[dataset_id][side] for dataset_id in sorted(inputs) for side in ("baseline", "candidate"))
    if sum(_source_bytes(source) for source in sources) > max_input_bytes:
        raise ParisonError(f"combined input size exceeds limit {max_input_bytes} bytes")
    decoded_sizes = _decoded_sizes(sources, max_decoded_bytes)
    before = {str(source): _source_digest(source) for source in sources}
    recipes = {}
    for dataset_id, runtime in inputs.items():
        _exact(runtime, {"recipe", "baseline", "candidate"}, f"runtime dataset {dataset_id!r}")
        recipe = load_recipe(runtime["recipe"])
        if explain_recipe(runtime["recipe"])["policy_sha256"] != contracts[dataset_id]["policy_sha256"]:
            raise ParisonError(f"dataset {dataset_id!r} policy SHA-256 does not match reconciliation")
        declared = {column["name"]: column["type"] for column in contracts[dataset_id]["columns"]}
        if declared != {name: configured["type"] for name, configured in recipe["columns"].items()}:
            raise ParisonError(f"dataset {dataset_id!r} semantic columns do not match its effective recipe")
        recipes[dataset_id] = recipe

    checks = [check for check in reconciliation["checks"] if check["kind"] == "conservation"]
    if not checks:
        raise ParisonError("reconciliation declares no conservation checks")
    results = {side: [] for side in ("baseline", "candidate")}

    def rows(dataset_id: str, side: str):
        recipe = recipes[dataset_id]
        for raw in _iter_input_rows(inputs[dataset_id][side], recipe, max_rows, side, decoded_sizes):
            yield _parse_row(raw, recipe, side)

    def key(row: dict[str, Any], dataset_id: str, columns: list[str]) -> bytes:
        return _multiset_encoding(tuple(row[column] for column in columns), columns, recipes[dataset_id])

    parent = Path(temp_directory) if temp_directory is not None else None
    workspace = tempfile.TemporaryDirectory(prefix="parison-conservation-", dir=parent) if engine == "sqlite" else None
    connection = None
    try:
        if workspace is not None:
            database = Path(workspace.name) / "conservation.sqlite"
            connection = sqlite3.connect(database)
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            page_limit = max_temp_bytes // page_size
            if page_limit < 4:
                raise ParisonError(f"temporary storage limit {max_temp_bytes} bytes is too small")
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute(f"PRAGMA max_page_count={page_limit}")
            connection.execute(
                "CREATE TABLE groups (side TEXT NOT NULL, check_id TEXT NOT NULL, key BLOB NOT NULL, parent_count INTEGER NOT NULL DEFAULT 0, parent_value TEXT, child_count INTEGER NOT NULL DEFAULT 0, child_sum TEXT NOT NULL DEFAULT '0', PRIMARY KEY(side, check_id, key)) WITHOUT ROWID"
            )

        for side in ("baseline", "candidate"):
            for check in checks:
                groups: dict[bytes, dict[str, Any]] = {}
                counts = {
                    "parent_rows": 0,
                    "child_rows": 0,
                    "groups": 0,
                    "compared_groups": 0,
                    "exact_groups": 0,
                    "within_tolerance_groups": 0,
                    "different_groups": 0,
                    "child_only_groups": 0,
                    "parent_without_children_groups": 0,
                    "duplicate_parent_groups": 0,
                    "null_measure_rows": 0,
                }
                for role in ("parent", "child"):
                    dataset_id = check[f"{role}_dataset"]
                    columns = check[f"{role}_group_columns"]
                    measure = check[f"{role}_measure"]
                    for row in rows(dataset_id, side):
                        counts[f"{role}_rows"] += 1
                        encoded_key, value = key(row, dataset_id, columns), row[measure]
                        if value is None:
                            if check["nulls"] == "forbid":
                                counts["null_measure_rows"] += 1
                            value = 0
                        if connection is None:
                            state = groups.setdefault(
                                encoded_key, {"parent_count": 0, "parent_value": None, "child_count": 0, "child_sum": 0}
                            )
                            if len(groups) > max_groups:
                                raise ParisonError(f"conservation {check['id']!r} exceeds group limit {max_groups}")
                            if role == "parent":
                                state["parent_count"] += 1
                                state["parent_value"] = value
                            else:
                                state["child_count"] += 1
                                state["child_sum"] += value
                        else:
                            connection.execute(
                                "INSERT OR IGNORE INTO groups (side, check_id, key) VALUES (?, ?, ?)",
                                (side, check["id"], encoded_key),
                            )
                            if role == "parent":
                                connection.execute(
                                    "UPDATE groups SET parent_count=parent_count+1, parent_value=? WHERE side=? AND check_id=? AND key=?",
                                    (str(value), side, check["id"], encoded_key),
                                )
                            else:
                                found = connection.execute(
                                    "SELECT child_sum FROM groups WHERE side=? AND check_id=? AND key=?",
                                    (side, check["id"], encoded_key),
                                ).fetchone()
                                total = Decimal(found[0]) + Decimal(str(value))
                                connection.execute(
                                    "UPDATE groups SET child_count=child_count+1, child_sum=? WHERE side=? AND check_id=? AND key=?",
                                    (str(total), side, check["id"], encoded_key),
                                )
                if connection is not None:
                    connection.commit()
                    size = connection.execute(
                        "SELECT COUNT(*) FROM groups WHERE side=? AND check_id=?", (side, check["id"])
                    ).fetchone()[0]
                    if size > max_groups:
                        raise ParisonError(f"conservation {check['id']!r} exceeds group limit {max_groups}")
                    records = connection.execute(
                        "SELECT parent_count, parent_value, child_count, child_sum FROM groups WHERE side=? AND check_id=? ORDER BY key",
                        (side, check["id"]),
                    )
                else:
                    records = (
                        (state["parent_count"], state["parent_value"], state["child_count"], state["child_sum"])
                        for _, state in sorted(groups.items())
                    )
                policy = {
                    "comparison": "exact" if check["comparison"] == "exact" else "numeric",
                    "tolerance": check["tolerance"],
                }
                for parent_count, parent_value, child_count, child_sum in records:
                    counts["groups"] += 1
                    if not parent_count:
                        counts["child_only_groups"] += 1
                        continue
                    if parent_count > 1:
                        counts["duplicate_parent_groups"] += 1
                        continue
                    if not child_count:
                        counts["parent_without_children_groups"] += 1
                    counts["compared_groups"] += 1
                    parent_numeric = Decimal(parent_value) if connection is not None else parent_value
                    child_numeric = Decimal(child_sum) if connection is not None else child_sum
                    classification, _, _ = _classify(parent_numeric, child_numeric, policy, True)
                    counts[f"{classification}_groups"] += 1
                failed = any(
                    counts[field]
                    for field in (
                        "different_groups",
                        "child_only_groups",
                        "duplicate_parent_groups",
                        "null_measure_rows",
                    )
                )
                results[side].append(
                    {
                        "id": check["id"],
                        "kind": "conservation",
                        "outcome": "FAIL" if failed else "PASS",
                        "counts": counts,
                    }
                )
        if connection is not None:
            connection.commit()
    except sqlite3.Error as exc:
        if "full" in str(exc).lower():
            raise ParisonError(f"temporary storage exceeds limit {max_temp_bytes} bytes") from exc
        raise ParisonError(f"conservation spill database failed: {exc}") from exc
    finally:
        if connection is not None:
            connection.close()
        if workspace is not None:
            workspace.cleanup()
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while conservation was being checked")
    outcome = "FAIL" if any(check["outcome"] == "FAIL" for side in results.values() for check in side) else "PASS"
    return {
        "conservation_result_version": 1,
        "outcome": outcome,
        "reconciliation_sha256": reconciliation["reconciliation_sha256"],
        "sides": results,
        "resource_limits": {
            "max_input_bytes": max_input_bytes,
            "max_decoded_bytes": max_decoded_bytes,
            "max_rows_per_input": max_rows,
            "max_groups_per_check": max_groups,
        },
    }


def run_reconciliation(
    alignment_path: str | Path,
    reconciliation_path: str | Path,
    receipt_path: str | Path,
    inputs: dict[str, dict[str, str | Path]],
    engine: str = "memory",
    max_input_bytes: int = 1_000_000_000,
    max_decoded_bytes: int = 1_000_000_000,
    max_rows: int = 5_000_000,
    max_keys: int = 100_000,
    max_groups: int = 100_000,
    max_distinct_rows: int = 100_000,
    max_temp_bytes: int = 5_000_000_000,
    temp_directory: str | Path | None = None,
    cancelled=None,
    progress=None,
) -> dict[str, Any]:
    """Compose alignment, existing parity and all declared relationship predicates."""

    def checkpoint(phase: str) -> None:
        if progress is not None:
            progress(phase)
        if cancelled is not None and cancelled():
            raise ParisonError("workbench reconciliation cancelled")

    checkpoint("preflight")
    sources = tuple(inputs[dataset_id][side] for dataset_id in sorted(inputs) for side in ("baseline", "candidate"))
    before = {str(source): _source_digest(source) for source in sources}
    alignment = preflight_alignment(
        alignment_path,
        reconciliation_path,
        receipt_path,
        inputs,
        max_input_bytes,
        max_decoded_bytes,
        max_rows,
    )
    checkpoint("parity")
    declaration = explain_reconciliation(reconciliation_path)
    parity = []
    for dataset in declaration["datasets"]:
        checkpoint("parity")
        dataset_id = dataset["id"]
        recipe = load_recipe(inputs[dataset_id]["recipe"])
        mode = recipe["comparison_mode"]
        result = compare(
            inputs[dataset_id]["recipe"],
            inputs[dataset_id]["baseline"],
            inputs[dataset_id]["candidate"],
            sample_limit=0,
            max_input_bytes=max_input_bytes,
            max_rows=max_rows,
            expected_policy_sha256=dataset["policy_sha256"],
            max_decoded_bytes=max_decoded_bytes,
            max_groups=max_groups,
            max_distinct_rows=max_distinct_rows,
            engine="memory" if mode == "aggregate" else engine,
            max_temp_bytes=max_temp_bytes,
            temp_directory=None if engine == "memory" or mode == "aggregate" else temp_directory,
        )
        parity.append(
            {
                "id": dataset_id,
                "outcome": result["outcome"],
                "complete": result["complete"],
                "schema_version": result["schema_version"],
                "contract": result["runtime"]["contract"],
                "policy_sha256": result["policy_sha256"],
                "baseline_sha256": result["inputs"].get("baseline", {}).get("sha256"),
                "candidate_sha256": result["inputs"].get("candidate", {}).get("sha256"),
                "discrepancy_count": result["discrepancy_count"],
            }
        )
    checkpoint("relationships")
    relationships = check_identity_references(
        reconciliation_path,
        inputs,
        engine,
        max_input_bytes,
        max_decoded_bytes,
        max_rows,
        max_keys,
        max_temp_bytes,
        temp_directory,
    )
    checkpoint("conservation")
    if any(check["kind"] == "conservation" for check in declaration["checks"]):
        conservation = check_conservation(
            reconciliation_path,
            inputs,
            engine,
            max_input_bytes,
            max_decoded_bytes,
            max_rows,
            max_groups,
            max_temp_bytes,
            temp_directory,
        )
    else:
        conservation = {"outcome": "PASS", "sides": {"baseline": [], "candidate": []}}
    checkpoint("verifying")
    if any(_source_digest(source) != digest for source, digest in before.items()):
        raise ParisonError("an input changed while reconciliation was running")
    component_outcomes = [
        alignment["outcome"],
        relationships["outcome"],
        conservation["outcome"],
        *(item["outcome"] for item in parity),
    ]
    outcome = (
        "FAIL" if "FAIL" in component_outcomes else "INCONCLUSIVE" if "INCONCLUSIVE" in component_outcomes else "PASS"
    )
    return {
        "reconciliation_result_version": 1,
        "outcome": outcome,
        "complete": True,
        "alignment_sha256": alignment["alignment_sha256"],
        "reconciliation_sha256": declaration["reconciliation_sha256"],
        "receipt_sha256": alignment["receipt_sha256"],
        "alignment": {
            "outcome": alignment["outcome"],
            "status": alignment["alignment_status"],
            "reason_codes": alignment["reason_codes"],
            "datasets": alignment["datasets"],
        },
        "datasets": parity,
        "relationships": relationships["sides"],
        "conservation": conservation["sides"],
        "runtime": {"contract": "reconciliation-v1", "parison_version": __version__},
        "resource_limits": {
            "max_input_bytes": max_input_bytes,
            "max_decoded_bytes": max_decoded_bytes,
            "max_rows_per_input": max_rows,
            "max_keys_per_identity": max_keys,
            "max_groups_per_check": max_groups,
            "max_distinct_rows_per_input": max_distinct_rows,
        },
    }


def run_reconciliation_with_bindings(
    output: str | Path,
    alignment_path: str | Path,
    reconciliation_path: str | Path,
    receipt_path: str | Path,
    inputs: dict[str, dict[str, str | Path]],
    before_publish=None,
    **limits: Any,
) -> dict[str, Any]:
    """Run and publish a reconciliation with a fresh semantic input record."""
    from .manifesting import capture_reconciliation_input_bindings

    declaration = explain_reconciliation(reconciliation_path)
    before = capture_reconciliation_input_bindings(declaration, inputs)
    result = run_reconciliation(alignment_path, reconciliation_path, receipt_path, inputs, **limits)
    if capture_reconciliation_input_bindings(declaration, inputs) != before:
        raise ParisonError("reconciliation inputs changed during execution")
    _verify_reconciliation_input_bindings(before, result, declaration)
    if before_publish is not None:
        before_publish()
    _publish_reconciliation_bundle(
        output, result, alignment_path, reconciliation_path, before, inputs, before_publish=before_publish
    )
    return result


def _verify_reconciliation_input_bindings(
    record: Any, result: dict[str, Any], declaration: dict[str, Any]
) -> dict[str, Any]:
    from .manifesting import normalize_input_bindings

    record = normalize_input_bindings(record)
    if record["policy"] != {"kind": "reconciliation", "sha256": declaration["reconciliation_sha256"]}:
        raise ParisonError("reconciliation input binding policy does not match declaration")
    observed = {(item["id"], item["role"]): item for item in record["bindings"]}
    datasets = {item["id"]: item for item in declaration["datasets"]}
    parity = {item["id"]: item for item in result["datasets"]}
    if set(parity) != set(datasets) or set(observed) != {
        (identifier, role) for identifier in datasets for role in ("baseline", "candidate")
    }:
        raise ParisonError("reconciliation input bindings do not match datasets")
    for identifier, dataset in datasets.items():
        for role in ("baseline", "candidate"):
            binding = observed[(identifier, role)]
            if (
                binding["policy_sha256"] != dataset["policy_sha256"]
                or binding["source_sha256"] != parity[identifier][f"{role}_sha256"]
            ):
                raise ParisonError("reconciliation input binding does not match parity execution")
    return record


def summarize_reconciliation_result(result: dict[str, Any]) -> dict[str, Any]:
    component_counts = {label: 0 for label in ("PASS", "FAIL", "INCONCLUSIVE")}
    for item in result["datasets"]:
        component_counts[item["outcome"]] += 1
    relationship_counts = {
        kind: {label: 0 for label in ("PASS", "FAIL")} for kind in ("identity", "reference", "conservation")
    }
    for field in ("relationships", "conservation"):
        for side in ("baseline", "candidate"):
            for item in result[field][side]:
                relationship_counts[item["kind"]][item["outcome"]] += 1
    return {
        "reconciliation_result_version": result["reconciliation_result_version"],
        "outcome": result["outcome"],
        "complete": result["complete"],
        "alignment_sha256": result["alignment_sha256"],
        "reconciliation_sha256": result["reconciliation_sha256"],
        "receipt_sha256": result["receipt_sha256"],
        "alignment": {
            "outcome": result["alignment"]["outcome"],
            "status": result["alignment"]["status"],
            "reason_codes": result["alignment"]["reason_codes"],
        },
        "dataset_outcome_counts": component_counts,
        "relationship_outcome_counts": relationship_counts,
    }


def publish_reconciliation_bundle(
    output: str | Path,
    result: dict[str, Any],
    alignment_path: str | Path,
    reconciliation_path: str | Path,
) -> None:
    """Publish the released schema-1 reconciliation result."""
    _publish_reconciliation_bundle(output, result, alignment_path, reconciliation_path)


def _publish_reconciliation_bundle(
    output: str | Path,
    result: dict[str, Any],
    alignment_path: str | Path,
    reconciliation_path: str | Path,
    input_bindings: dict[str, Any] | None = None,
    input_sources: dict[str, dict[str, str | Path]] | None = None,
    *,
    before_publish=None,
) -> None:
    target = Path(output)
    if target.exists():
        raise ParisonError(f"output already exists: {target}")
    alignment, declaration = explain_time_alignment(alignment_path), explain_reconciliation(reconciliation_path)
    if (
        result.get("alignment_sha256") != alignment["alignment_sha256"]
        or result.get("reconciliation_sha256") != declaration["reconciliation_sha256"]
    ):
        raise ParisonError("result fingerprints do not match declarations")
    if input_bindings is not None:
        from .manifesting import capture_reconciliation_input_bindings

        if input_sources is None or capture_reconciliation_input_bindings(declaration, input_sources) != input_bindings:
            raise ParisonError("reconciliation input bindings changed before publication")
        input_bindings = _verify_reconciliation_input_bindings(input_bindings, result, declaration)
    stage = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _check_output_parent(target.parent)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        payloads = {
            "reconciliation-result.json": result,
            "summary.json": summarize_reconciliation_result(result),
            "effective-alignment.json": {key: value for key, value in alignment.items() if key != "alignment_sha256"},
            "effective-reconciliation.json": {
                key: value for key, value in declaration.items() if key != "reconciliation_sha256"
            },
        }
        for name, value in payloads.items():
            (stage / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if input_bindings is not None:
            from .manifesting import canonical_input_bindings_bytes

            (stage / "input-bindings.json").write_bytes(canonical_input_bindings_bytes(input_bindings))
            payloads["input-bindings.json"] = input_bindings
        files = {name: file_digest(stage / name) for name in sorted(payloads)}
        manifest = {
            "schema_version": 2 if input_bindings is not None else 1,
            "kind": "reconciliation",
            "complete": result["complete"],
            "outcome": result["outcome"],
            "sensitivity": "raw",
            "runtime": result["runtime"],
            "files": files,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if (
            input_bindings is not None
            and capture_reconciliation_input_bindings(declaration, input_sources) != input_bindings
        ):
            raise ParisonError("reconciliation input bindings changed during publication")
        if input_bindings is not None:
            verify_reconciliation_bundle(stage)
        if before_publish is not None:
            before_publish()
        _rename_no_replace(stage, target)
        stage = None
    except ParisonError:
        raise
    except OSError as exc:
        raise ParisonError(f"cannot publish reconciliation bundle: {exc}") from exc
    finally:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


def _verified_counts(value: Any, fields: str) -> dict[str, int]:
    if (
        not isinstance(value, dict)
        or set(value) != set(fields.split())
        or any(type(count) is not int or count < 0 for count in value.values())
    ):
        raise ParisonError("reconciliation result has invalid count shape")
    return value


def _verify_component_counts(item: dict[str, Any], check: dict[str, Any], rows: dict[str, int]) -> None:
    kind = check["kind"]
    if kind == "identity":
        c = _verified_counts(item["counts"], "rows distinct_keys null_key_rows duplicate_keys")
        valid = (
            c["rows"] == rows[check["dataset"]]
            and c["null_key_rows"] <= c["rows"]
            and c["duplicate_keys"] <= c["distinct_keys"] <= c["rows"]
            and c["distinct_keys"] + c["duplicate_keys"] <= c["rows"]
            and (c["rows"] == 0) == (c["distinct_keys"] == 0)
            and (c["duplicate_keys"] == 0) == (c["distinct_keys"] == c["rows"])
        )
        failed = c["duplicate_keys"] > 0 or (check["nulls"] == "forbid" and c["null_key_rows"] > 0)
    elif kind == "reference":
        c = _verified_counts(
            item["counts"], "child_rows exempt_rows matched_rows orphan_rows ambiguous_parent_rows null_failure_rows"
        )
        valid = (
            c["child_rows"] == rows[check["child_dataset"]]
            and c["child_rows"] == sum(value for name, value in c.items() if name != "child_rows")
            and (check["nulls"] == "all-null-exempt" or c["exempt_rows"] == 0)
            and (check["nulls"] != "match-null" or c["null_failure_rows"] == 0)
        )
        failed = any(c[name] for name in ("orphan_rows", "ambiguous_parent_rows", "null_failure_rows"))
    else:
        c = _verified_counts(
            item["counts"],
            "parent_rows child_rows groups compared_groups exact_groups within_tolerance_groups different_groups "
            "child_only_groups parent_without_children_groups duplicate_parent_groups null_measure_rows",
        )
        valid = (
            c["parent_rows"] == rows[check["parent_dataset"]]
            and c["child_rows"] == rows[check["child_dataset"]]
            and c["groups"] == c["compared_groups"] + c["child_only_groups"] + c["duplicate_parent_groups"]
            and c["compared_groups"] == c["exact_groups"] + c["within_tolerance_groups"] + c["different_groups"]
            and c["parent_without_children_groups"] <= c["compared_groups"]
            and c["parent_rows"] >= c["compared_groups"] + 2 * c["duplicate_parent_groups"]
            and c["child_rows"] >= c["child_only_groups"] + c["compared_groups"] - c["parent_without_children_groups"]
            and c["groups"] <= c["parent_rows"] + c["child_rows"]
            and (c["child_rows"] == 0 or c["groups"] > c["parent_without_children_groups"])
            and (c["duplicate_parent_groups"] > 0 or c["parent_rows"] == c["compared_groups"])
            and c["null_measure_rows"] <= c["parent_rows"] + c["child_rows"]
            and (check["nulls"] != "zero" or c["null_measure_rows"] == 0)
            and (check["comparison"] != "exact" or c["within_tolerance_groups"] == 0)
        )
        failed = any(
            c[name]
            for name in ("different_groups", "child_only_groups", "duplicate_parent_groups", "null_measure_rows")
        )
    if not valid or item["outcome"] != ("FAIL" if failed else "PASS"):
        raise ParisonError("reconciliation result counts or derived outcome are inconsistent")


def _verify_alignment_counts(value: Any, declaration: dict[str, Any]) -> dict[str, dict[str, int]]:
    _exact(value, {"outcome", "status", "reason_codes", "datasets"}, "alignment result")
    datasets = value["datasets"]
    if not isinstance(datasets, list) or len(datasets) != len(declaration["datasets"]):
        raise ParisonError("alignment result datasets do not match declaration")
    rows = {"baseline": {}, "candidate": {}}
    failed = False
    for observed, declared in zip(datasets, declaration["datasets"], strict=True):
        _exact(observed, {"id", "sides"}, "alignment dataset")
        if observed["id"] != declared["id"]:
            raise ParisonError("alignment result datasets do not match declaration")
        _exact(observed["sides"], {"baseline", "candidate"}, "alignment sides")
        for side in rows:
            c = _verified_counts(
                observed["sides"][side],
                "rows in_window before_window at_or_after_end null_event_time invalid_event_time",
            )
            if c["rows"] != sum(count for name, count in c.items() if name != "rows"):
                raise ParisonError("alignment result counts are inconsistent")
            failed |= c["rows"] != c["in_window"]
            rows[side][observed["id"]] = c["rows"]
    coordination = declaration["coordination"]
    status, reasons = "PASS", []
    if coordination["mode"] == "watermark":
        if any(item["watermark"] < declaration["event_window"]["end"] for item in declaration["datasets"]):
            status, reasons = "FAIL", ["watermark-before-window-end"]
        elif coordination["watermark_kind"] == "heuristic":
            status, reasons = "INCONCLUSIVE", ["heuristic-watermark"]
    elif coordination["mode"] == "declared-cutoff":
        status, reasons = "INCONCLUSIVE", ["coordination-not-machine-established"]
    if failed:
        status = "FAIL"
        reasons.append("event-time-scope-failed")
    if value["outcome"] != status or value["status"] != status or value["reason_codes"] != sorted(reasons):
        raise ParisonError("alignment result derived outcome is inconsistent")
    return rows


def verify_reconciliation_bundle(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    manifest_path = root / "manifest.json"
    if root.is_symlink() or not root.is_dir() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise ParisonError("reconciliation bundle is missing or unsafe")
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes, object_pairs_hook=_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read reconciliation manifest: {exc}") from exc
    expected = {"schema_version", "kind", "complete", "outcome", "sensitivity", "runtime", "files"}
    if (
        not isinstance(manifest, dict)
        or set(manifest) != expected
        or manifest.get("schema_version") not in (1, 2)
        or manifest.get("kind") != "reconciliation"
        or manifest.get("complete") is not True
    ):
        raise ParisonError("reconciliation manifest is incomplete or unsupported")
    if manifest.get("outcome") not in {"PASS", "FAIL", "INCONCLUSIVE"} or manifest.get("sensitivity") != "raw":
        raise ParisonError("reconciliation manifest has invalid metadata")
    members = {
        "reconciliation-result.json",
        "summary.json",
        "effective-alignment.json",
        "effective-reconciliation.json",
    }
    if manifest["schema_version"] == 2:
        members.add("input-bindings.json")
    _verify_manifest_files(root, manifest["files"], members)
    try:
        result = json.loads(
            (root / "reconciliation-result.json").read_text(encoding="utf-8"), object_pairs_hook=_object
        )
        summary = json.loads((root / "summary.json").read_text(encoding="utf-8"), object_pairs_hook=_object)
        alignment = json.loads(
            (root / "effective-alignment.json").read_text(encoding="utf-8"), object_pairs_hook=_object
        )
        declaration = json.loads(
            (root / "effective-reconciliation.json").read_text(encoding="utf-8"), object_pairs_hook=_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError(f"cannot read reconciliation bundle: {exc}") from exc
    normalized_alignment, normalized_declaration = (
        normalize_time_alignment(alignment),
        normalize_reconciliation(declaration),
    )
    alignment_sha256 = hashlib.sha256(_canonical(normalized_alignment)).hexdigest()
    reconciliation_sha256 = hashlib.sha256(_canonical(normalized_declaration)).hexdigest()
    required_result = {
        "reconciliation_result_version",
        "outcome",
        "complete",
        "alignment_sha256",
        "reconciliation_sha256",
        "receipt_sha256",
        "alignment",
        "datasets",
        "relationships",
        "conservation",
        "runtime",
        "resource_limits",
    }
    dataset_ids = [item["id"] for item in normalized_declaration["datasets"]]
    relationship_checks = [
        (item["id"], item["kind"])
        for item in normalized_declaration["checks"]
        if item["kind"] in {"identity", "reference"}
    ]
    conservation_checks = [
        (item["id"], item["kind"]) for item in normalized_declaration["checks"] if item["kind"] == "conservation"
    ]
    if (
        not isinstance(result, dict)
        or set(result) != required_result
        or result.get("reconciliation_result_version") != 1
        or result.get("complete") is not True
    ):
        raise ParisonError("reconciliation result is incomplete or unsupported")
    if (
        not isinstance(result.get("datasets"), list)
        or [item.get("id") for item in result.get("datasets", []) if isinstance(item, dict)] != dataset_ids
        or len(result.get("datasets", [])) != len(dataset_ids)
    ):
        raise ParisonError("reconciliation result datasets do not match declaration")
    rows = _verify_alignment_counts(result["alignment"], normalized_alignment)
    checks = {check["id"]: check for check in normalized_declaration["checks"]}
    component_outcomes = [result.get("alignment", {}).get("outcome")]
    for field, expected_checks in (("relationships", relationship_checks), ("conservation", conservation_checks)):
        sides = result.get(field)
        if not isinstance(sides, dict) or set(sides) != {"baseline", "candidate"}:
            raise ParisonError(f"reconciliation result has invalid {field}")
        for side in ("baseline", "candidate"):
            observed = sides[side]
            if (
                not isinstance(observed, list)
                or any(not isinstance(item, dict) for item in observed)
                or [(item.get("id"), item.get("kind")) for item in observed if isinstance(item, dict)]
                != expected_checks
            ):
                raise ParisonError(f"reconciliation result {field} do not match declaration")
            for item in observed:
                if (
                    set(item) != {"id", "kind", "outcome", "counts"}
                    or item["outcome"] not in ("PASS", "FAIL")
                    or not isinstance(item["counts"], dict)
                    or any(type(value) is not int or value < 0 for value in item["counts"].values())
                ):
                    raise ParisonError(f"reconciliation result has invalid {field} counts")
                _verify_component_counts(item, checks[item["id"]], rows[side])
                component_outcomes.append(item["outcome"])
        if field == "relationships":
            for side in sides:
                identities = {item["id"]: item["counts"] for item in sides[side] if item["kind"] == "identity"}
                for item in sides[side]:
                    if item["kind"] != "reference":
                        continue
                    parent = identities[checks[item["id"]]["parent_identity"]]
                    if (item["counts"]["matched_rows"] > 0 and parent["distinct_keys"] == parent["duplicate_keys"]) or (
                        item["counts"]["ambiguous_parent_rows"] > 0 and parent["duplicate_keys"] == 0
                    ):
                        raise ParisonError("reference counts conflict with parent identity")
    for item in result["datasets"]:
        if set(item) != {
            "id",
            "outcome",
            "complete",
            "schema_version",
            "contract",
            "policy_sha256",
            "baseline_sha256",
            "candidate_sha256",
            "discrepancy_count",
        } or item["outcome"] not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            raise ParisonError("reconciliation result has invalid dataset parity")
        component_outcomes.append(item["outcome"])
    declared_policies = [item["policy_sha256"] for item in normalized_declaration["datasets"]]
    expected_outcome = (
        "FAIL" if "FAIL" in component_outcomes else "INCONCLUSIVE" if "INCONCLUSIVE" in component_outcomes else "PASS"
    )
    if (
        result.get("alignment_sha256") != alignment_sha256
        or result.get("reconciliation_sha256") != reconciliation_sha256
        or normalized_declaration["alignment_sha256"] != alignment_sha256
        or result.get("receipt_sha256") != normalized_alignment["coordination"]["receipt_sha256"]
        or [item["policy_sha256"] for item in result["datasets"]] != declared_policies
        or summary != summarize_reconciliation_result(result)
        or manifest["outcome"] != result.get("outcome")
        or manifest["runtime"] != result.get("runtime")
        or result.get("outcome") != expected_outcome
    ):
        raise ParisonError("reconciliation bundle metadata is inconsistent")
    if manifest["schema_version"] == 2:
        from .manifesting import _read_json

        record = _read_json(root / "input-bindings.json", "reconciliation input bindings")
        _verify_reconciliation_input_bindings(
            record, result, declaration | {"reconciliation_sha256": reconciliation_sha256}
        )
    if manifest_path.read_bytes() != manifest_bytes:
        raise ParisonError("reconciliation bundle changed during verification")
    return manifest


def inspect_reconciliation_bundle(directory: str | Path) -> dict[str, Any]:
    manifest = verify_reconciliation_bundle(directory)
    summary = json.loads((Path(directory) / "summary.json").read_text(encoding="utf-8"))
    return {
        "kind": "reconciliation",
        **summary,
        "runtime": manifest["runtime"],
        "bundle_sha256": file_digest(Path(directory) / "manifest.json"),
        "manifest_files": sorted(manifest["files"]),
    }


def diagnose_reconciliation_bundle(directory: str | Path) -> dict[str, Any]:
    """Count fixed failure reasons from verified preserved evidence only."""
    root = Path(directory)
    manifest = verify_reconciliation_bundle(root)
    path = root / "reconciliation-result.json"
    manifest_path = root / "manifest.json"
    try:
        manifest_bytes = manifest_path.read_bytes()
        if path.is_symlink() or manifest_path.is_symlink():
            raise ParisonError("reconciliation changed during diagnosis")
        if json.loads(manifest_bytes, object_pairs_hook=_object) != manifest:
            raise ParisonError("reconciliation changed during diagnosis")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != manifest["files"][path.name]:
            raise ParisonError("reconciliation changed during diagnosis")
        result = json.loads(payload, object_pairs_hook=_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ParisonError("cannot read reconciliation diagnosis") from exc
    reasons = {
        "identity_duplicate_keys": 0,
        "identity_null_key_rows": 0,
        "reference_orphan_rows": 0,
        "reference_ambiguous_parent_rows": 0,
        "reference_null_failure_rows": 0,
        "conservation_different_groups": 0,
        "conservation_child_only_groups": 0,
        "conservation_duplicate_parent_groups": 0,
        "conservation_null_measure_rows": 0,
        "conservation_parent_without_children_groups": 0,
    }
    for side in ("baseline", "candidate"):
        for item in result["relationships"][side] + result["conservation"][side]:
            for name, count in item["counts"].items():
                key = f"{item['kind']}_{name}"
                if key in reasons:
                    reasons[key] += count
    try:
        if path.read_bytes() != payload or manifest_path.read_bytes() != manifest_bytes:
            raise ParisonError("reconciliation changed during diagnosis")
    except OSError as exc:
        raise ParisonError("reconciliation changed during diagnosis") from exc
    return {
        "kind": "reconciliation-diagnosis",
        "outcome": result["outcome"],
        "alignment_outcome": result["alignment"]["outcome"],
        "alignment_reason_codes": result["alignment"]["reason_codes"],
        "dataset_outcome_counts": summarize_reconciliation_result(result)["dataset_outcome_counts"],
        "reason_counts": reasons,
        "bundle_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
