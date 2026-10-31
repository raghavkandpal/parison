"""Versioned local exact partition discovery and integrity verification."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent, rename_no_replace
from .analysis import _canonical, _strict_object
from .comparison import _multiset_encoding, compare
from .core import ParisonError, _checked_policy_sha256, _parse_row, load_recipe
from .inputs import _iter_input_rows
from .policies import load_recipe_text
from .source_collection import _directory, _members, _stamp, _stat_stamp
from .source_receipt import _read_json as _canonical_json

_LIMIT_CAPS = {
    "max_input_bytes": 1_000_000_000,
    "max_rows_per_input": 5_000_000,
    "max_rows_per_partition_side": 1_000_000,
    "max_staged_bytes": 2_000_000_000,
    "max_partition_bytes": 1_000_000_000,
}
_COUNT_NAMES = (
    "baseline",
    "candidate",
    "common_keys",
    "baseline_only",
    "candidate_only",
    "matched_exact",
    "matched_within_tolerance",
    "matched_with_required_difference",
)
_CLASS_NAMES = ("exact", "within_tolerance", "different")


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _bounded_bytes(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ParisonError("partition evidence file is missing, unsafe or too large")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(descriptor, "rb") as handle:
            before = _stamp(handle)
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ParisonError("partition evidence file is not regular")
            data = handle.read(limit + 1)
            if _stamp(handle) != before:
                raise ParisonError("partition evidence file changed during reading")
        if len(data) > limit:
            raise ParisonError("partition evidence file is missing, unsafe or too large")
        return data
    except OSError as exc:
        raise ParisonError("cannot read partition evidence file") from exc


def _parse_json(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeError, ValueError) as exc:
        raise ParisonError("invalid partition JSON") from exc


def _read_json(path: Path, *, limit: int = 256 * 1024) -> Any:
    return _parse_json(_bounded_bytes(path, limit))


_HASH_ERROR = "invalid or incomplete hash partition evidence"


class _HashInterrupted(KeyboardInterrupt):
    pass


def _hash_context(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"implementation", "python_version", "unicode_version"}
        or value["implementation"] != "CPython"
    ):
        raise ParisonError(_HASH_ERROR)
    for name, pattern in (
        ("python_version", r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,3}"),
        ("unicode_version", r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}"),
    ):
        if not isinstance(value[name], str) or re.fullmatch(pattern, value[name]) is None:
            raise ParisonError(_HASH_ERROR)


def _execution_context():
    context = {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "unicode_version": unicodedata.unidata_version,
    }
    _hash_context(context)
    if tuple(map(int, context["python_version"].split(".")[:2])) not in {(3, 11), (3, 12), (3, 13), (3, 14)}:
        raise ParisonError(_HASH_ERROR)
    return context


def _hash_key(parsed, recipe, limit):
    """Bound the entire typed frame before constructing the composite buffer."""
    names = recipe["keys"]
    size = len(b"parison-key-v1\0") + 2 + 9 * len(names)
    if size > limit:
        raise ParisonError(_HASH_ERROR)
    for name in names:
        value = parsed[name]
        if value is None:
            continue
        kind = recipe["columns"][name]["type"]
        if (kind == "integer" and type(value) is not int) or (kind == "string" and type(value) is not str):
            raise ParisonError(_HASH_ERROR)
        if kind not in {"integer", "string"}:
            raise ParisonError(_HASH_ERROR)
        text = str(value) if kind == "integer" else value
        if len(text) > limit - size:
            raise ParisonError(_HASH_ERROR)
        size += len(text.encode("utf-8", errors="strict"))
        if size > limit:
            raise ParisonError(_HASH_ERROR)
    return (
        b"parison-key-v1\0"
        + len(names).to_bytes(2, "big")
        + _multiset_encoding(tuple(parsed[name] for name in names), names, recipe)
    )


def _hash_bucket(encoded, buckets):
    """Routing-only seam: collisions must still use the exact comparator."""
    return int.from_bytes(hashlib.sha256(encoded).digest(), "big") % buckets


def _hash_plan(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"partition_plan_version", "routing", "limits"}
        or type(value["partition_plan_version"]) is not int
        or value["partition_plan_version"] != 2
    ):
        raise ParisonError(_HASH_ERROR)
    routing = value["routing"]
    if (
        not isinstance(routing, dict)
        or set(routing) != {"kind", "hash", "encoding", "buckets"}
        or routing["kind"] != "hash-v1"
        or routing["hash"] != "sha256"
        or routing["encoding"] != "typed-key-v1"
        or type(routing["buckets"]) is not int
        or not 2 <= routing["buckets"] <= 128
    ):
        raise ParisonError(_HASH_ERROR)
    limits = value["limits"]
    caps = {**_LIMIT_CAPS, "max_key_bytes": 65536}
    if (
        not isinstance(limits, dict)
        or set(limits) != set(caps)
        or any(type(limits[name]) is not int or not 0 < limits[name] <= cap for name, cap in caps.items())
    ):
        raise ParisonError(_HASH_ERROR)
    return value


def validate_plan(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("partition_plan_version") == 2:
        return _hash_plan(value)
    if not isinstance(value, dict) or set(value) != {"partition_plan_version", "ranges", "limits"}:
        raise ParisonError("invalid partition plan fields")
    if type(value["partition_plan_version"]) is not int or value["partition_plan_version"] != 1:
        raise ParisonError("unsupported partition plan version")
    ranges = value["ranges"]
    if not isinstance(ranges, list) or not 2 <= len(ranges) <= 128:
        raise ParisonError("partition plan requires 2-128 ranges")
    previous: int | None = None
    for index, item in enumerate(ranges):
        if not isinstance(item, dict) or set(item) != {"upper"}:
            raise ParisonError("invalid partition range")
        upper = item["upper"]
        if index == len(ranges) - 1:
            if upper is not None:
                raise ParisonError("last partition range must have open upper bound")
        elif type(upper) is not int or (previous is not None and upper <= previous):
            raise ParisonError("partition upper bounds must be increasing integers")
        else:
            previous = upper
    limits = value["limits"]
    if not isinstance(limits, dict) or set(limits) != set(_LIMIT_CAPS):
        raise ParisonError("invalid partition limits")
    for name, cap in _LIMIT_CAPS.items():
        limit = limits[name]
        if type(limit) is not int or not 0 < limit <= cap:
            raise ParisonError(f"invalid partition limit: {name}")
    return value


def _recipe(path: Path) -> tuple[dict[str, Any], str]:
    recipe = load_recipe(path)
    if (
        recipe["comparison_mode"] != "keyed"
        or len(recipe["keys"]) != 1
        or recipe["columns"][recipe["keys"][0]]["type"] != "integer"
        or recipe["output"]["sensitivity"] != "summary"
        or recipe.get("column_mappings")
        or recipe.get("field_projection")
        or recipe.get("input_projection")
        or recipe.get("excluded_columns")
    ):
        raise ParisonError("partition discovery requires a simple summary keyed integer recipe")
    return recipe, _checked_policy_sha256(recipe, None)


def _source(path: str | Path, limit: int) -> tuple[Path, dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() != ".csv" or source.is_symlink() or not source.is_file():
        raise ParisonError("partition input must be a regular non-symlink CSV file")
    size = source.stat().st_size
    if size > limit:
        raise ParisonError("partition input exceeds source byte limit")
    return source, {"sha256": _digest(source), "bytes": size}


def _csv_bytes(values: list[Any], delimiter: str) -> bytes:
    stream = io.StringIO(newline="")
    csv.writer(stream, delimiter=delimiter).writerow(values)
    return stream.getvalue().encode("utf-8")


def _route(
    plan: dict[str, Any],
    recipe: dict[str, Any],
    sources: dict[str, Path],
    workspace: Path,
    selected: set[int] | None = None,
    staged_byte_limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], int]:
    uppers = [item["upper"] for item in plan["ranges"][:-1]]
    columns = list(recipe["columns"])
    key_name = recipe["keys"][0]
    limits = plan["limits"]
    active = set(range(len(plan["ranges"]))) if selected is None else selected
    if not active or any(type(index) is not int or index < 0 or index >= len(plan["ranges"]) for index in active):
        raise ParisonError("invalid selected partition ranges")
    stage_cap = min(limits["max_staged_bytes"], staged_byte_limit or limits["max_staged_bytes"])
    records = [{"upper": item["upper"], "baseline": {}, "candidate": {}} for item in plan["ranges"]]
    handles: dict[tuple[str, int], Any] = {}
    staged = 0
    rows = {"baseline": 0, "candidate": 0}
    try:
        for side in ("baseline", "candidate"):
            delimiter = recipe["delimiters"][side]
            for index in sorted(active):
                handle = (workspace / f"{side}-{index}.csv").open("wb")
                handles[(side, index)] = handle
                header = _csv_bytes(columns, delimiter)
                handle.write(header)
                records[index][side] = {"rows": 0, "bytes": len(header)}
                staged += len(header)
                if len(header) > limits["max_partition_bytes"] or staged > stage_cap:
                    raise ParisonError("partition staging exceeds byte limit")
            for raw in _iter_input_rows(sources[side], recipe, limits["max_rows_per_input"], side):
                rows[side] += 1
                parsed = _parse_row(raw, recipe, side)
                key = parsed[key_name]
                if key is None:
                    raise ParisonError("null integer key cannot be routed")
                index = bisect.bisect_right(uppers, key)
                if index not in active:
                    continue
                record = records[index][side]
                null_token = recipe["null_tokens"][side][0] if recipe["null_tokens"][side] else None
                line = _csv_bytes([null_token if raw.get(name) is None else raw[name] for name in columns], delimiter)
                record["rows"] += 1
                record["bytes"] += len(line)
                staged += len(line)
                if record["rows"] > limits["max_rows_per_partition_side"]:
                    raise ParisonError("partition row limit exceeded")
                if record["bytes"] > limits["max_partition_bytes"] or staged > stage_cap:
                    raise ParisonError("partition byte limit exceeded")
                handles[(side, index)].write(line)
    finally:
        for handle in handles.values():
            handle.close()
    for side in ("baseline", "candidate"):
        if selected is None and sum(record[side]["rows"] for record in records) != rows[side]:
            raise ParisonError("partition routing count mismatch")
        for index in sorted(active):
            record = records[index]
            record[side]["sha256"] = _digest(workspace / f"{side}-{index}.csv")
    return records, rows, staged


def _compare_ranges(
    plan: dict[str, Any],
    recipe: dict[str, Any],
    records: list[dict[str, Any]],
    rows: dict[str, int],
    workspace: Path,
) -> tuple[dict[str, int], dict[str, dict[str, int]], int, str, bool]:
    derived = {**recipe, "scope": {**recipe["scope"], "expected_empty": True}}
    derived_path = workspace / "derived-recipe.json"
    if plan["partition_plan_version"] == 2:
        if _bounded_bytes(derived_path, 262144) != _canonical(derived):
            raise ParisonError(_HASH_ERROR)
    else:
        derived_path.write_bytes(_canonical(derived))
    totals = {name: 0 for name in _COUNT_NAMES}
    field_counts = {
        name: {classification: 0 for classification in _CLASS_NAMES}
        for name in recipe["columns"]
        if name not in recipe["keys"]
    }
    problems = False
    for index, record in enumerate(records):
        result = compare(
            derived_path,
            workspace / f"baseline-{index}.csv",
            workspace / f"candidate-{index}.csv",
            sample_limit=0,
            max_rows=plan["limits"]["max_rows_per_partition_side"],
            max_input_bytes=plan["limits"]["max_staged_bytes"],
        )
        record["counts"] = result["counts"]
        record["field_counts"] = result["field_counts"]
        record["outcome"] = result["outcome"]
        record["complete"] = result["complete"]
        problems |= not result["complete"]
        for name in _COUNT_NAMES:
            totals[name] += result["counts"][name]
        for name in field_counts:
            for classification in _CLASS_NAMES:
                field_counts[name][classification] += result["field_counts"][name][classification]
    if totals["baseline"] != rows["baseline"] or totals["candidate"] != rows["candidate"]:
        raise ParisonError("partition comparison count mismatch")
    if problems:
        for name in ("matched_exact", "matched_within_tolerance", "matched_with_required_difference"):
            totals[name] = 0
        field_counts = {name: {classification: 0 for classification in _CLASS_NAMES} for name in field_counts}
    empty = not rows["baseline"] or not rows["candidate"]
    complete = not problems and (not empty or recipe["scope"]["expected_empty"])
    outcome = (
        "INCONCLUSIVE"
        if not complete
        else "FAIL"
        if totals["baseline_only"] or totals["candidate_only"] or totals["matched_with_required_difference"]
        else "PASS"
    )
    differences = (
        totals["baseline_only"]
        + totals["candidate_only"]
        + sum(field_counts[name]["different"] + field_counts[name]["within_tolerance"] for name in field_counts)
    )
    return totals, field_counts, differences, outcome, complete


def _pinned_hash_input(stack, path, limit):
    path = Path(path)
    check_output_parent(path.parent)
    if path.is_symlink():
        raise ParisonError(_HASH_ERROR)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    handle = stack.enter_context(os.fdopen(descriptor, "rb"))
    info = os.fstat(handle.fileno())
    before = _stat_stamp(info)
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ParisonError(_HASH_ERROR)

    def unchanged():
        check_output_parent(path.parent)
        if path.is_symlink() or _stat_stamp(path.stat()) != before or _stamp(handle) != before:
            raise ParisonError(_HASH_ERROR)

    unchanged()
    return handle, unchanged


def _stage_guard(workspace, expected, stamps):
    """Bind private file bytes, names and directory identity across semantic reads."""
    check_output_parent(workspace)
    directory = _stat_stamp(workspace.stat())
    parent = _stat_stamp(workspace.parent.stat())

    def unchanged():
        check_output_parent(workspace)
        if (
            _stat_stamp(workspace.stat()) != directory
            or _stat_stamp(workspace.parent.stat()) != parent
            or {p.name for p in workspace.iterdir()} != set(expected)
        ):
            raise ParisonError(_HASH_ERROR)
        for name, digest in expected.items():
            path = workspace / name
            if path.is_symlink() or _stat_stamp(path.stat()) != stamps[name] or _digest(path) != digest:
                raise ParisonError(_HASH_ERROR)

    unchanged()
    return unchanged


def _run_hash(plan, recipe_path, baseline, candidate, workspace, stack):
    context = _execution_context()
    workspace_fd = _directory(stack, workspace)
    workspace_identity = workspace.stat().st_dev, workspace.stat().st_ino
    parent_stamp = _stat_stamp(workspace.parent.stat())

    def workspace_check():
        check_output_parent(workspace)
        if (workspace.stat().st_dev, workspace.stat().st_ino) != workspace_identity or _stat_stamp(
            workspace.parent.stat()
        ) != parent_stamp:
            raise ParisonError(_HASH_ERROR)

    recipe_handle, recipe_check = _pinned_hash_input(stack, recipe_path, 262144)
    recipe_bytes = recipe_handle.read(262145)
    recipe_check()
    if len(recipe_bytes) > 262144:
        raise ParisonError(_HASH_ERROR)
    _parse_json(recipe_bytes)
    recipe = load_recipe_text(recipe_bytes.decode("utf-8"))
    if (
        recipe["comparison_mode"] != "keyed"
        or not 1 <= len(recipe["keys"]) <= 16
        or len(recipe["columns"]) > 100
        or any(recipe["columns"][name]["type"] not in {"integer", "string"} for name in recipe["keys"])
        or recipe["output"]["sensitivity"] != "summary"
        or any(
            recipe.get(name) for name in ("column_mappings", "field_projection", "input_projection", "excluded_columns")
        )
    ):
        raise ParisonError(_HASH_ERROR)
    derived = _canonical({**recipe, "scope": {**recipe["scope"], "expected_empty": True}})
    if len(derived) > 262144:
        raise ParisonError(_HASH_ERROR)
    limits, expected, checks, identities, sources = plan["limits"], {}, [recipe_check], {}, {}
    file_stamps = {}
    staged = 0

    def write(handle, data):
        nonlocal staged
        if len(data) > limits["max_staged_bytes"] - staged:
            raise ParisonError(_HASH_ERROR)
        handle.write(data)
        staged += len(data)

    def create(name):
        workspace_check()
        descriptor = os.open(
            name if workspace_fd is not None else workspace / name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=workspace_fd,
        )
        return os.fdopen(descriptor, "wb")

    with create("derived-recipe.json") as handle:
        write(handle, derived)
    expected["derived-recipe.json"] = hashlib.sha256(derived).hexdigest()
    file_stamps["derived-recipe.json"] = _stat_stamp((workspace / "derived-recipe.json").stat())
    for side, original in (("baseline", baseline), ("candidate", candidate)):
        if Path(original).suffix.lower() != ".csv":
            raise ParisonError(_HASH_ERROR)
        source, check = _pinned_hash_input(stack, original, limits["max_input_bytes"])
        checks.append(check)
        name, size, digest = f"snapshot-{side}.csv", 0, hashlib.sha256()
        with create(name) as handle:
            while block := source.read(1024 * 1024):
                size += len(block)
                if size > limits["max_input_bytes"]:
                    raise ParisonError(_HASH_ERROR)
                write(handle, block)
                digest.update(block)
        check()
        identities[side] = {"sha256": digest.hexdigest(), "bytes": size}
        expected[name], sources[side] = digest.hexdigest(), workspace / name
        file_stamps[name] = _stat_stamp(sources[side].stat())

    def snapshots_check():
        workspace_check()
        for side, path in sources.items():
            if (
                path.is_symlink()
                or _stat_stamp(path.stat()) != file_stamps[path.name]
                or _digest(path) != identities[side]["sha256"]
            ):
                raise ParisonError(_HASH_ERROR)

    count = plan["routing"]["buckets"]
    columns = sorted(recipe["columns"])
    records = [{"bucket": index, "baseline": {}, "candidate": {}} for index in range(count)]
    rows = {"baseline": 0, "candidate": 0}
    for side in ("baseline", "candidate"):
        snapshots_check()
        with ExitStack() as writers:
            handles, digests = [], []
            header = _csv_bytes(columns, recipe["delimiters"][side])
            for index in range(count):
                if len(header) > limits["max_partition_bytes"]:
                    raise ParisonError(_HASH_ERROR)
                handles.append(writers.enter_context(create(f"{side}-{index}.csv")))
                write(handles[-1], header)
                digests.append(hashlib.sha256(header))
                records[index][side] = {"rows": 0, "bytes": len(header)}
            # Directory entries remain fixed while this side is parsed and written.
            directory = _stat_stamp(workspace.stat())
            for raw in _iter_input_rows(sources[side], recipe, limits["max_rows_per_input"], side):
                rows[side] += 1
                parsed = _parse_row(raw, recipe, side)
                index = _hash_bucket(_hash_key(parsed, recipe, limits["max_key_bytes"]), count)
                record = records[index][side]
                null_token = recipe["null_tokens"][side][0] if recipe["null_tokens"][side] else None
                line = _csv_bytes(
                    [null_token if raw.get(name) is None else raw[name] for name in columns], recipe["delimiters"][side]
                )
                if (
                    record["rows"] >= limits["max_rows_per_partition_side"]
                    or len(line) > limits["max_partition_bytes"] - record["bytes"]
                ):
                    raise ParisonError(_HASH_ERROR)
                write(handles[index], line)
                digests[index].update(line)
                record["rows"] += 1
                record["bytes"] += len(line)
            if _stat_stamp(workspace.stat()) != directory:
                raise ParisonError(_HASH_ERROR)
        for index in range(count):
            digest = digests[index].hexdigest()
            records[index][side]["sha256"] = digest
            expected[f"{side}-{index}.csv"] = digest
            file_stamps[f"{side}-{index}.csv"] = _stat_stamp((workspace / f"{side}-{index}.csv").stat())
        snapshots_check()
    staged_check = _stage_guard(workspace, expected, file_stamps)
    counts, fields, differences, outcome, complete = _compare_ranges(plan, recipe, records, rows, workspace)
    staged_check()
    workspace_check()

    def source_check():
        for check in checks:
            check()

    source_check()
    return {
        "partition_receipt_version": 2,
        "policy_sha256": _checked_policy_sha256(recipe, None),
        "plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
        "routing": plan["routing"],
        "normalization_runtime": context,
        "derived_recipe_bytes": len(derived),
        "inputs": identities,
        "route_rows": rows,
        "staged_bytes": staged,
        "partitions": records,
        "counts": counts,
        "field_counts": fields,
        "discrepancy_count": differences,
        "outcome": outcome,
        "complete": complete,
    }, source_check


def _run(
    plan: dict[str, Any], recipe_path: Path, baseline: str | Path, candidate: str | Path, workspace: Path
) -> dict[str, Any]:
    recipe, policy_sha256 = _recipe(recipe_path)
    sources = {}
    identities = {}
    for side, path in (("baseline", baseline), ("candidate", candidate)):
        sources[side], identities[side] = _source(path, plan["limits"]["max_input_bytes"])
    records, rows, staged = _route(plan, recipe, sources, workspace)
    if any(_digest(sources[side]) != identities[side]["sha256"] for side in sources):
        raise ParisonError("partition input changed during routing")
    counts, field_counts, discrepancy_count, outcome, complete = _compare_ranges(plan, recipe, records, rows, workspace)
    if any(
        _digest(workspace / f"{side}-{index}.csv") != record[side]["sha256"]
        for index, record in enumerate(records)
        for side in ("baseline", "candidate")
    ):
        raise ParisonError("partition staging changed during comparison")
    if any(_digest(sources[side]) != identities[side]["sha256"] for side in sources):
        raise ParisonError("partition input changed during comparison")
    return {
        "partition_receipt_version": 1,
        "policy_sha256": policy_sha256,
        "plan_sha256": hashlib.sha256(_canonical(plan)).hexdigest(),
        "inputs": identities,
        "route_rows": rows,
        "staged_bytes": staged,
        "partitions": records,
        "counts": counts,
        "field_counts": field_counts,
        "discrepancy_count": discrepancy_count,
        "outcome": outcome,
        "complete": complete,
    }


def _summary(receipt: dict[str, Any]) -> dict[str, Any]:
    result = {
        name: receipt[name]
        for name in (
            "partition_receipt_version",
            "policy_sha256",
            "plan_sha256",
            "inputs",
            "route_rows",
            "staged_bytes",
            "counts",
            "discrepancy_count",
            "outcome",
            "complete",
        )
    }

    if receipt["partition_receipt_version"] == 2:
        result.update(routing=receipt["routing"], normalization_runtime=receipt["normalization_runtime"])
    return result


def _digest_text(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _counts(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(_COUNT_NAMES)
        and all(type(count) is int and count >= 0 for count in value.values())
    )


def _field_counts(value: Any) -> bool:
    return isinstance(value, dict) and all(
        isinstance(fields, dict)
        and set(fields) == set(_CLASS_NAMES)
        and all(type(count) is int and count >= 0 for count in fields.values())
        for fields in value.values()
    )


def _consistent_counts(counts: dict[str, int], fields: dict[str, dict[str, int]], complete: bool) -> bool:
    if (
        counts["common_keys"] + counts["baseline_only"] > counts["baseline"]
        or counts["common_keys"] + counts["candidate_only"] > counts["candidate"]
    ):
        return False
    matched = sum(
        counts[name] for name in ("matched_exact", "matched_within_tolerance", "matched_with_required_difference")
    )
    if matched != (counts["common_keys"] if complete else 0):
        return False
    return all(
        sum(classifications.values()) == (counts["common_keys"] if complete else 0)
        for classifications in fields.values()
    )


def _validate_receipt(plan: dict[str, Any], receipt: Any) -> None:
    version = plan["partition_plan_version"]
    is_hash = version == 2
    extras = {"routing", "normalization_runtime", "derived_recipe_bytes"} if is_hash else set()
    if (
        not isinstance(receipt, dict)
        or set(receipt)
        != {
            "partition_receipt_version",
            "policy_sha256",
            "plan_sha256",
            "inputs",
            "route_rows",
            "staged_bytes",
            "partitions",
            "counts",
            "field_counts",
            "discrepancy_count",
            "outcome",
            "complete",
        }
        | extras
        or type(receipt["partition_receipt_version"]) is not int
        or receipt["partition_receipt_version"] != version
        or not _digest_text(receipt["policy_sha256"])
        or receipt["plan_sha256"] != hashlib.sha256(_canonical(plan)).hexdigest()
        or not _counts(receipt["counts"])
        or not _field_counts(receipt["field_counts"])
        or type(receipt["discrepancy_count"]) is not int
        or receipt["discrepancy_count"] < 0
        or type(receipt["staged_bytes"]) is not int
        or receipt["staged_bytes"] < 0
        or type(receipt["complete"]) is not bool
        or receipt["outcome"] not in {"PASS", "FAIL", "INCONCLUSIVE"}
    ):
        raise ParisonError("invalid partition receipt")
    if is_hash:
        _hash_plan({"partition_plan_version": 2, "routing": receipt["routing"], "limits": plan["limits"]})
        _hash_context(receipt["normalization_runtime"])
        if (
            receipt["routing"] != plan["routing"]
            or type(receipt["derived_recipe_bytes"]) is not int
            or not 1 <= receipt["derived_recipe_bytes"] <= 262144
            or len(receipt["field_counts"]) > 100
        ):
            raise ParisonError(_HASH_ERROR)
    if (
        not isinstance(receipt["inputs"], dict)
        or set(receipt["inputs"]) != {"baseline", "candidate"}
        or not isinstance(receipt["route_rows"], dict)
        or set(receipt["route_rows"]) != {"baseline", "candidate"}
    ):
        raise ParisonError("invalid partition source identities")
    for side in ("baseline", "candidate"):
        identity = receipt["inputs"][side]
        if (
            not isinstance(identity, dict)
            or set(identity) != {"sha256", "bytes"}
            or not _digest_text(identity["sha256"])
            or type(identity["bytes"]) is not int
            or not 0 <= identity["bytes"] <= plan["limits"]["max_input_bytes"]
            or type(receipt["route_rows"][side]) is not int
            or not 0 <= receipt["route_rows"][side] <= plan["limits"]["max_rows_per_input"]
        ):
            raise ParisonError("invalid partition source identity")
    partitions = receipt["partitions"]
    count = plan["routing"]["buckets"] if is_hash else len(plan["ranges"])
    if not isinstance(partitions, list) or len(partitions) != count:
        raise ParisonError("partition record count mismatch")
    totals = {name: 0 for name in _COUNT_NAMES}
    field_totals = {name: {classification: 0 for classification in _CLASS_NAMES} for name in receipt["field_counts"]}
    staged = sum(v["bytes"] for v in receipt["inputs"].values()) + receipt["derived_recipe_bytes"] if is_hash else 0
    incomplete = False
    for index, record in enumerate(partitions):
        label = "bucket" if is_hash else "upper"
        expected_label = index if is_hash else plan["ranges"][index]["upper"]
        if (
            not isinstance(record, dict)
            or set(record)
            != {
                label,
                "baseline",
                "candidate",
                "counts",
                "field_counts",
                "outcome",
                "complete",
            }
            or type(record[label]) is not type(expected_label)
            or record[label] != expected_label
            or not _counts(record["counts"])
            or not _field_counts(record["field_counts"])
            or set(record["field_counts"]) != set(field_totals)
            or type(record["complete"]) is not bool
            or record["outcome"] not in {"PASS", "FAIL", "INCONCLUSIVE"}
        ):
            raise ParisonError("invalid partition record")
        incomplete |= not record["complete"]
        if not _consistent_counts(record["counts"], record["field_counts"], record["complete"]):
            raise ParisonError("partition record arithmetic mismatch")
        if (
            is_hash
            and record["complete"]
            and any(
                record["counts"]["common_keys"] + record["counts"][f"{side}_only"] != record["counts"][side]
                for side in ("baseline", "candidate")
            )
        ):
            raise ParisonError(_HASH_ERROR)
        expected_outcome = (
            "INCONCLUSIVE"
            if not record["complete"]
            else "FAIL"
            if record["counts"]["baseline_only"]
            or record["counts"]["candidate_only"]
            or record["counts"]["matched_with_required_difference"]
            else "PASS"
        )
        if record["outcome"] != expected_outcome:
            raise ParisonError("partition record outcome mismatch")
        for side in ("baseline", "candidate"):
            item = record[side]
            if (
                not isinstance(item, dict)
                or set(item) != {"rows", "bytes", "sha256"}
                or type(item["rows"]) is not int
                or not 0 <= item["rows"] <= plan["limits"]["max_rows_per_partition_side"]
                or type(item["bytes"]) is not int
                or not 0 < item["bytes"] <= plan["limits"]["max_partition_bytes"]
                or not _digest_text(item["sha256"])
                or item["rows"] != record["counts"][side]
            ):
                raise ParisonError("invalid partition side record")
            staged += item["bytes"]
        for name in totals:
            totals[name] += record["counts"][name]
        for name in field_totals:
            for classification in _CLASS_NAMES:
                field_totals[name][classification] += record["field_counts"][name][classification]
    if incomplete:
        for name in ("matched_exact", "matched_within_tolerance", "matched_with_required_difference"):
            totals[name] = 0
        field_totals = {name: {classification: 0 for classification in _CLASS_NAMES} for name in field_totals}
    if (
        staged != receipt["staged_bytes"]
        or staged > plan["limits"]["max_staged_bytes"]
        or totals != receipt["counts"]
        or field_totals != receipt["field_counts"]
        or any(receipt["route_rows"][side] != totals[side] for side in ("baseline", "candidate"))
        or (incomplete and receipt["complete"])
        or (receipt["outcome"] == "INCONCLUSIVE") != (not receipt["complete"])
    ):
        raise ParisonError("partition receipt arithmetic mismatch")
    if (
        is_hash
        and not incomplete
        and all(totals[side] > 0 for side in ("baseline", "candidate"))
        and not receipt["complete"]
    ):
        raise ParisonError(_HASH_ERROR)
    if not _consistent_counts(totals, field_totals, not incomplete):
        raise ParisonError("partition receipt arithmetic mismatch")
    differences = (
        totals["baseline_only"]
        + totals["candidate_only"]
        + sum(fields["different"] + fields["within_tolerance"] for fields in field_totals.values())
    )
    if receipt["discrepancy_count"] != differences or (
        receipt["complete"]
        and receipt["outcome"]
        != (
            "FAIL"
            if (totals["baseline_only"] or totals["candidate_only"] or totals["matched_with_required_difference"])
            else "PASS"
        )
    ):
        raise ParisonError("partition receipt outcome mismatch")


def discover(
    plan_path: str | Path, recipe_path: str | Path, baseline: str | Path, candidate: str | Path, output: str | Path
) -> dict[str, Any]:
    plan = validate_plan(_read_json(Path(plan_path)))
    if plan["partition_plan_version"] == 2:
        return _discover_hash(plan, recipe_path, baseline, candidate, output)
    target = Path(output)
    check_output_parent(target.parent)
    if target.exists() or target.is_symlink():
        raise ParisonError("partition output already exists")
    stage: Path | None = None
    try:
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        os.chmod(stage, 0o700)
        workspace = stage / "temporary"
        workspace.mkdir(mode=0o700)
        receipt = _run(plan, Path(recipe_path), baseline, candidate, workspace)
        shutil.rmtree(workspace)
        values = {"plan.json": plan, "receipt.json": receipt, "summary.json": _summary(receipt)}
        for name, value in values.items():
            (stage / name).write_bytes(_canonical(value) + b"\n")
        manifest = {"partition_manifest_version": 1, "files": {name: _digest(stage / name) for name in values}}
        (stage / "manifest.json").write_bytes(_canonical(manifest) + b"\n")
        rename_no_replace(stage, target)
        return values["summary.json"]
    except BaseException:
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)
        raise


def _cleanup_hash_stage(stage, identity, fd):
    """Remove owned contents through their pinned directory, never a replacement."""
    if fd is not None:
        for entry in os.scandir(fd):
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.name, dir_fd=fd)
            else:
                os.unlink(entry.name, dir_fd=fd)
        if not stage.is_symlink() and (stage.stat().st_dev, stage.stat().st_ino) == identity:
            stage.rmdir()
        return
    # Platforms without directory descriptors: locate only the owned identity.
    for path in stage.parent.iterdir():
        if not path.is_symlink() and path.is_dir() and (path.stat().st_dev, path.stat().st_ino) == identity:
            shutil.rmtree(path)
            return


def _discover_hash(plan, recipe, baseline, candidate, output):
    stage = None
    stage_stack = ExitStack()
    stage_fd = None
    identity = None
    try:
        _execution_context()
        target = Path(output)
        check_output_parent(target.parent)
        if target.exists() or target.is_symlink():
            raise ParisonError(_HASH_ERROR)
        stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
        identity = stage.stat().st_dev, stage.stat().st_ino
        stage_fd = _directory(stage_stack, stage)
        os.chmod(stage, 0o700)

        def stage_check():
            check_output_parent(stage)
            if stage.is_symlink() or (stage.stat().st_dev, stage.stat().st_ino) != identity:
                raise ParisonError(_HASH_ERROR)

        def metadata(name, data):
            stage_check()
            descriptor = os.open(
                name if stage_fd is not None else stage / name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=stage_fd,
            )
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                file_identity = _stamp(handle)[:2]
            stage_check()
            info = os.stat(name if stage_fd is not None else stage / name, dir_fd=stage_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or _stat_stamp(info)[:2] != file_identity:
                raise ParisonError(_HASH_ERROR)
            return _stat_stamp(info)

        workspace = stage / "temporary"
        stage_check()
        if stage_fd is not None:
            os.mkdir("temporary", mode=0o700, dir_fd=stage_fd)
        else:
            workspace.mkdir(mode=0o700)
        stage_check()
        with ExitStack() as stack:
            receipt, source_check = _run_hash(plan, recipe, baseline, candidate, workspace, stack)
            stage_check()
            if stage_fd is not None:
                shutil.rmtree("temporary", dir_fd=stage_fd)
            else:
                shutil.rmtree(workspace)
            stage_check()
            values = {"plan.json": plan, "receipt.json": receipt, "summary.json": _summary(receipt)}
            digests, stamps = {}, {}
            for name, value in values.items():
                data = _canonical(value) + b"\n"
                if len(data) > (8 * 1024 * 1024 if name == "receipt.json" else 262144):
                    raise ParisonError(_HASH_ERROR)
                stamps[name] = metadata(name, data)
                digests[name] = hashlib.sha256(data).hexdigest()
            manifest = _canonical({"partition_manifest_version": 2, "files": digests}) + b"\n"
            stamps["manifest.json"] = metadata("manifest.json", manifest)
            metadata_check = _stage_guard(
                stage, {**digests, "manifest.json": hashlib.sha256(manifest).hexdigest()}, stamps
            )
            _verified_hash_evidence(stage, None, None, None)
            source_check()
            metadata_check()
            stage_check()
            rename_no_replace(stage, target)
            stage = None
        return values["summary.json"]
    except KeyboardInterrupt:
        raise _HashInterrupted from None
    except (ParisonError, OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ParisonError(_HASH_ERROR) from None
    finally:
        try:
            if stage is not None and identity is not None:
                _cleanup_hash_stage(stage, identity, stage_fd)
        except OSError:
            pass
        finally:
            stage_stack.close()


def _verified_hash_evidence(root, recipe, baseline, candidate):
    """Pinned v2 integrity verification and optional complete exact replay."""
    try:
        check_output_parent(root.parent)
        names = {"plan.json", "receipt.json", "summary.json", "manifest.json"}
        with ExitStack() as stack:
            fd = _directory(stack, root)
            if _members(root, fd) != names:
                raise ParisonError(_HASH_ERROR)
            directory_stamp = _stat_stamp(os.fstat(fd) if fd is not None else root.stat())
            handles = {}
            for name in sorted(names):
                if fd is not None:
                    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                    handle = stack.enter_context(os.fdopen(descriptor, "rb"))
                else:
                    path = root / name
                    if path.is_symlink() or not path.is_file():
                        raise ParisonError(_HASH_ERROR)
                    handle = stack.enter_context(path.open("rb"))
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > (
                    8 * 1024 * 1024 if name == "receipt.json" else 262144
                ):
                    raise ParisonError(_HASH_ERROR)
                handles[name] = handle
            stamps = {name: _stamp(handle) for name, handle in handles.items()}
            values, data = {}, {}
            for name, handle in handles.items():
                values[name], data[name] = _canonical_json(
                    handle, 8 * 1024 * 1024 if name == "receipt.json" else 262144
                )
            manifest = values["manifest.json"]
            if (
                set(manifest) != {"partition_manifest_version", "files"}
                or type(manifest["partition_manifest_version"]) is not int
                or manifest["partition_manifest_version"] != 2
                or manifest["files"]
                != {
                    name: hashlib.sha256(data[name]).hexdigest()
                    for name in ("plan.json", "receipt.json", "summary.json")
                }
            ):
                raise ParisonError(_HASH_ERROR)
            plan = _hash_plan(values["plan.json"])
            receipt, summary = values["receipt.json"], values["summary.json"]
            _validate_receipt(plan, receipt)
            if data["summary.json"] != _canonical(_summary(receipt)) + b"\n":
                raise ParisonError(_HASH_ERROR)
            if any(value is not None for value in (recipe, baseline, candidate)):
                if (
                    any(value is None for value in (recipe, baseline, candidate))
                    or _execution_context() != receipt["normalization_runtime"]
                ):
                    raise ParisonError(_HASH_ERROR)
                with tempfile.TemporaryDirectory(prefix="parison-hash-replay-") as temporary:
                    workspace = Path(temporary) / "temporary"
                    workspace.mkdir(mode=0o700)
                    with ExitStack() as sources:
                        replay, source_check = _run_hash(plan, recipe, baseline, candidate, workspace, sources)
                        if replay != receipt:
                            raise ParisonError(_HASH_ERROR)
                        source_check()
            if (
                any(_stamp(handle) != stamps[name] for name, handle in handles.items())
                or _members(root, fd) != names
                or root.is_symlink()
                or _stat_stamp(root.stat()) != directory_stamp
                or (fd is not None and _stat_stamp(os.fstat(fd)) != directory_stamp)
                or (fd is not None and (root.is_symlink() or _stat_stamp(root.stat()) != directory_stamp))
            ):
                raise ParisonError(_HASH_ERROR)
            if fd is None and any(
                (root / name).is_symlink() or _stat_stamp((root / name).stat()) != stamps[name] for name in names
            ):
                raise ParisonError(_HASH_ERROR)
            return plan, receipt, summary, hashlib.sha256(data["manifest.json"]).hexdigest()
    except KeyboardInterrupt:
        raise _HashInterrupted from None
    except (ParisonError, OSError, UnicodeError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ParisonError(_HASH_ERROR) from None


def _verified_evidence(
    directory: str | Path,
    recipe: str | Path | None = None,
    baseline: str | Path | None = None,
    candidate: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    root = Path(directory)
    if (
        root.is_symlink()
        or not root.is_dir()
        or {p.name for p in root.iterdir()} != {"plan.json", "receipt.json", "summary.json", "manifest.json"}
    ):
        raise ParisonError("invalid partition evidence directory")
    manifest_bytes = _bounded_bytes(root / "manifest.json", 256 * 1024)
    manifest = _parse_json(manifest_bytes)
    # Version sniff only: v2 captures and validates its own pinned bytes afresh.
    if (
        isinstance(manifest, dict)
        and type(manifest.get("partition_manifest_version")) is int
        and manifest["partition_manifest_version"] == 2
    ):
        return _verified_hash_evidence(root, recipe, baseline, candidate)
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"partition_manifest_version", "files"}
        or type(manifest["partition_manifest_version"]) is not int
        or manifest["partition_manifest_version"] != 1
        or not isinstance(manifest["files"], dict)
        or set(manifest["files"]) != {"plan.json", "receipt.json", "summary.json"}
    ):
        raise ParisonError("invalid partition manifest")
    captured: dict[str, Any] = {}
    for name, digest in manifest["files"].items():
        path = root / name
        if not _digest_text(digest):
            raise ParisonError("partition evidence file is unsafe")
        data = _bounded_bytes(path, 8 * 1024 * 1024 if name == "receipt.json" else 256 * 1024)
        if digest != hashlib.sha256(data).hexdigest():
            raise ParisonError("partition evidence digest mismatch")
        captured[name] = _parse_json(data)
    plan = validate_plan(captured["plan.json"])
    if plan["partition_plan_version"] != 1:
        raise ParisonError("partition evidence version mismatch")
    receipt = captured["receipt.json"]
    summary = captured["summary.json"]
    _validate_receipt(plan, receipt)
    if summary != _summary(receipt):
        raise ParisonError("inconsistent partition receipt")

    def unchanged() -> bool:
        return manifest_bytes == _bounded_bytes(root / "manifest.json", 256 * 1024) and all(
            hashlib.sha256(
                _bounded_bytes(root / name, 8 * 1024 * 1024 if name == "receipt.json" else 256 * 1024)
            ).hexdigest()
            == digest
            for name, digest in manifest["files"].items()
        )

    if recipe is None and baseline is None and candidate is None:
        if not unchanged():
            raise ParisonError("partition evidence changed during verification")
        return plan, receipt, summary, hashlib.sha256(manifest_bytes).hexdigest()
    if recipe is None or baseline is None or candidate is None:
        raise ParisonError("source-backed verification requires recipe and both inputs")
    with tempfile.TemporaryDirectory(prefix="parison-partition-verify-") as temp:
        rerun = _run(plan, Path(recipe), baseline, candidate, Path(temp))
    if rerun != receipt:
        raise ParisonError("partition source-backed verification mismatch")
    if not unchanged():
        raise ParisonError("partition evidence changed during verification")
    return plan, receipt, summary, hashlib.sha256(manifest_bytes).hexdigest()


def verify(
    directory: str | Path,
    recipe: str | Path | None = None,
    baseline: str | Path | None = None,
    candidate: str | Path | None = None,
) -> dict[str, Any]:
    _, _, summary, _ = _verified_evidence(directory, recipe, baseline, candidate)
    mode = "integrity-only" if recipe is None and baseline is None and candidate is None else "exact-source-backed"
    return {**summary, "verification": mode}


def parser(
    prog: str = "parison-partitions", parser_class: type[argparse.ArgumentParser] = argparse.ArgumentParser
) -> argparse.ArgumentParser:
    parser = parser_class(prog=prog)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=parser_class)
    create = sub.add_parser("discover")
    for name in ("plan", "recipe", "baseline", "candidate", "output"):
        create.add_argument(f"--{name}", required=True)
    check = sub.add_parser("verify")
    check.add_argument("directory")
    for name in ("recipe", "baseline", "candidate"):
        check.add_argument(f"--{name}")
    investigation = sub.add_parser("investigate")
    for name in ("plan", "discovery", "recipe", "baseline", "candidate", "output"):
        investigation.add_argument(f"--{name}", required=True)
    investigation_check = sub.add_parser("verify-investigation")
    investigation_check.add_argument("directory")
    investigation_check.add_argument("--discovery", required=True)
    for name in ("recipe", "baseline", "candidate"):
        investigation_check.add_argument(f"--{name}")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    prog: str = "parison-partitions",
    parser_class: type[argparse.ArgumentParser] = argparse.ArgumentParser,
) -> int:
    args = parser(prog, parser_class).parse_args(argv)
    try:
        if args.command == "discover":
            result = discover(args.plan, args.recipe, args.baseline, args.candidate, args.output)
        elif args.command == "verify":
            result = verify(args.directory, args.recipe, args.baseline, args.candidate)
        else:
            from .partition_investigation import investigate, verify_investigation

            result = (
                investigate(args.plan, args.discovery, args.recipe, args.baseline, args.candidate, args.output)
                if args.command == "investigate"
                else verify_investigation(args.directory, args.discovery, args.recipe, args.baseline, args.candidate)
            )
        print(json.dumps(result, sort_keys=True))
        if args.command != "discover":
            return 0
        return 0 if result["outcome"] == "PASS" else 1 if result["outcome"] == "FAIL" else 2
    except _HashInterrupted:
        print("parison-partitions: hash evidence verification interrupted", file=sys.stderr)
        return 130
    except (ParisonError, OSError, ValueError) as exc:
        print(f"parison-partitions: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
