"""Private session ownership and recorded metadata checks; no reuse or mutation."""

from __future__ import annotations

import hashlib
import os
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path

from . import partition_discovery as discovery
from ._safe_fs import check_output_parent
from .analysis import _canonical
from .core import ParisonError, _checked_policy_sha256
from .policies import load_recipe_text
from .source_receipt import _integer, _object

_ERROR = "invalid or busy partition session ownership"


def _bounded_members(path, fd, limit):
    names = set()
    with os.scandir(fd if fd is not None else path) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > limit:
                raise ParisonError(_ERROR)
    return names


def _acquire(handle):
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

        def unlock():
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        def unlock():
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    return unlock


@contextmanager
def _read_owner(directory):
    """Yield a directory capability and recheck callback under exclusive read ownership.

    Callers must validate pinned journal/cache bytes AFTER acquiring this context.
    It recognizes only the root and fixed lock; it grants no cache reuse authority.
    Namespace changes are rejected, so this is not a mutating-session context.
    """
    try:
        root = Path(directory)
        with ExitStack() as stack:
            check_output_parent(root)
            original = root.lstat()
            fd = discovery._hash_directory(stack, root)
            native = discovery._windows_directory_pin(stack, root) if os.name == "nt" else None

            def root_identity():
                check_output_parent(root)
                info = root.lstat()
                if (
                    not stat.S_ISDIR(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                    or (info.st_dev, info.st_ino) != (original.st_dev, original.st_ino)
                ):
                    raise ParisonError(_ERROR)

            root_identity()
            path = root / ".lock"
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400:
                raise ParisonError(_ERROR)
            descriptor = os.open(
                ".lock" if fd is not None else path,
                os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0),
                dir_fd=fd,
            )
            handle = stack.enter_context(os.fdopen(descriptor, "r+b"))
            info = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_size != 1
                or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
            ):
                raise ParisonError(_ERROR)
            stack.callback(_acquire(handle))
            root_identity()
            handle.seek(0)
            if handle.read(2) != b"\x00":
                raise ParisonError(_ERROR)
            lock_stamp = discovery._file_stamp(handle)

            def root_stamp():
                info = os.fstat(fd) if fd is not None else root.lstat()
                change = discovery._windows_change_time(native) if native is not None else info.st_ctime_ns
                return (*discovery._stat_stamp(info)[:-1], change)

            # Only post-lock state can be authoritative; another owner may have just exited.
            directory_stamp = root_stamp()
            namespace = _bounded_members(root, fd, 6)

            def unchanged():
                root_identity()
                if (
                    root_stamp() != directory_stamp
                    or _bounded_members(root, fd, 6) != namespace
                    or discovery._file_stamp(handle) != lock_stamp
                    or discovery._named_file_stamp(path) != lock_stamp
                ):
                    raise ParisonError(_ERROR)

            unchanged()
            yield fd, unchanged
            unchanged()
    except (ParisonError, OSError, UnicodeError, ValueError, TypeError, OverflowError):
        raise ParisonError(_ERROR) from None


_METADATA_ERROR = "invalid partition session metadata"
_SIDES = ("baseline", "candidate")


def _sha(value):
    if not discovery._digest_text(value):
        raise ParisonError(_METADATA_ERROR)
    return value


def _descriptor(value, limit, *, minimum=0, rows=None):

    _object(value, "sha256 bytes" if rows is None else "sha256 bytes rows")
    _sha(value["sha256"])
    _integer(value["bytes"], minimum, limit)
    if rows is not None:
        _integer(value["rows"], 0, rows)
    return value


def _journal(value, plan):
    """Validate recorded metadata only; no file integrity or current reuse admission."""

    try:
        discovery.validate_plan(plan)
        _object(
            value,
            "partition_session_version state identity max_session_bytes routing results published_manifest_sha256",
        )
        _integer(value["partition_session_version"], 1, 1)
        state = value["state"]
        if type(state) is not str or state not in {
            "initializing",
            "routed",
            "comparing",
            "ready",
            "published",
            "abandoning",
        }:
            raise ParisonError(_METADATA_ERROR)
        _integer(value["max_session_bytes"], 1, 2100000000)
        identity = _object(
            value["identity"],
            "plan_sha256 policy_sha256 derived_recipe_sha256 inputs columns normalization_runtime engine",
        )
        for name in ("plan_sha256", "policy_sha256", "derived_recipe_sha256"):
            _sha(identity[name])
        if identity["plan_sha256"] != hashlib.sha256(_canonical(plan)).hexdigest():
            raise ParisonError(_METADATA_ERROR)
        discovery._hash_context(identity["normalization_runtime"])
        engine = _object(identity["engine"], "contract parison_version package_sha256")
        version = engine["parison_version"]
        if (
            engine["contract"] != "partition-session-engine-v1"
            or type(version) is not str
            or not 1 <= len(version) <= 64
            or not version.isascii()
        ):
            raise ParisonError(_METADATA_ERROR)
        _sha(engine["package_sha256"])
        columns = identity["columns"]
        if (
            type(columns) is not list
            or not columns
            or any(type(name) is not str or not name for name in columns)
            or len(set(columns)) != len(columns)
        ):
            raise ParisonError(_METADATA_ERROR)
        is_hash = plan["partition_plan_version"] == 2
        if is_hash and (len(columns) > 100 or columns != sorted(columns)):
            raise ParisonError(_METADATA_ERROR)
        limits = plan["limits"]
        _object(identity["inputs"], "baseline candidate")
        for side in _SIDES:
            _descriptor(identity["inputs"][side], limits["max_input_bytes"])
        count = plan["routing"]["buckets"] if is_hash else len(plan["ranges"])
        results = value["results"]
        if type(results) is not list or len(results) != count:
            raise ParisonError(_METADATA_ERROR)
        for item in results:
            if item is not None:
                _descriptor(item, 1048576, minimum=1)
        manifest = value["published_manifest_sha256"]
        if manifest is not None:
            _sha(manifest)
            if any(item is None for item in results):
                raise ParisonError(_METADATA_ERROR)
        routing = value["routing"]
        if state == "initializing" and (
            routing is not None or any(item is not None for item in results) or manifest is not None
        ):
            raise ParisonError(_METADATA_ERROR)
        if state in {"routed", "comparing", "ready", "published"} and routing is None:
            raise ParisonError(_METADATA_ERROR)
        if state == "routed" and any(item is not None for item in results):
            raise ParisonError(_METADATA_ERROR)
        if state in {"ready", "published"}:
            if manifest is None or any(item is None for item in results):
                raise ParisonError(_METADATA_ERROR)
        elif state != "abandoning" and manifest is not None:
            raise ParisonError(_METADATA_ERROR)
        if routing is None:
            if any(item is not None for item in results) or manifest is not None:
                raise ParisonError(_METADATA_ERROR)
            return value
        _object(routing, "receipt files")
        receipt = _object(
            routing["receipt"],
            "inputs route_rows staged_bytes partitions" + (" derived_recipe_bytes" if is_hash else ""),
        )
        _object(receipt["inputs"], "baseline candidate")
        _object(receipt["route_rows"], "baseline candidate")
        for side in _SIDES:
            _descriptor(receipt["inputs"][side], limits["max_input_bytes"])
            _integer(receipt["route_rows"][side], 0, limits["max_rows_per_input"])
        if receipt["inputs"] != identity["inputs"]:
            raise ParisonError(_METADATA_ERROR)
        names = {
            "derived-recipe.json",
            *(f"snapshot-{side}.csv" for side in _SIDES),
            *(f"{side}-{i}.csv" for side in _SIDES for i in range(count)),
        }
        files = routing["files"]
        if type(files) is not dict or set(files) != names:
            raise ParisonError(_METADATA_ERROR)
        for name, item in files.items():
            limit = (
                262144
                if name == "derived-recipe.json"
                else limits["max_input_bytes"]
                if name.startswith("snapshot-")
                else limits["max_partition_bytes"]
            )
            _descriptor(
                item, limit, minimum=1 if name == "derived-recipe.json" or not name.startswith("snapshot-") else 0
            )
        if files["derived-recipe.json"]["sha256"] != identity["derived_recipe_sha256"] or any(
            files[f"snapshot-{side}.csv"] != identity["inputs"][side] for side in _SIDES
        ):
            raise ParisonError(_METADATA_ERROR)
        if is_hash:
            _integer(receipt["derived_recipe_bytes"], 1, 262144)
            if receipt["derived_recipe_bytes"] != files["derived-recipe.json"]["bytes"]:
                raise ParisonError(_METADATA_ERROR)
        partitions = receipt["partitions"]
        if type(partitions) is not list or len(partitions) != count:
            raise ParisonError(_METADATA_ERROR)
        totals = dict.fromkeys(_SIDES, 0)
        staged = sum(
            item["bytes"]
            for name, item in files.items()
            if is_hash or (name != "derived-recipe.json" and not name.startswith("snapshot-"))
        )
        _integer(receipt["staged_bytes"], 0, limits["max_staged_bytes"])
        for index, record in enumerate(partitions):
            label = "bucket" if is_hash else "upper"
            _object(record, f"{label} baseline candidate")
            expected = index if is_hash else plan["ranges"][index]["upper"]
            if type(record[label]) is not type(expected) or record[label] != expected:
                raise ParisonError(_METADATA_ERROR)
            for side in _SIDES:
                item = _descriptor(
                    record[side], limits["max_partition_bytes"], minimum=1, rows=limits["max_rows_per_partition_side"]
                )
                if files[f"{side}-{index}.csv"] != {name: item[name] for name in ("sha256", "bytes")}:
                    raise ParisonError(_METADATA_ERROR)
                totals[side] += item["rows"]
        if totals != receipt["route_rows"] or staged != receipt["staged_bytes"]:
            raise ParisonError(_METADATA_ERROR)
        return value
    except (ParisonError, KeyError, TypeError, ValueError, OverflowError, UnicodeError):
        raise ParisonError(_METADATA_ERROR) from None


def _derived(data, journal, plan):
    """Bind a canonical derived recipe, without opening the caller's original recipe."""

    try:
        if len(data) > 262144 or hashlib.sha256(data).hexdigest() != journal["identity"]["derived_recipe_sha256"]:
            raise ParisonError(_METADATA_ERROR)
        discovery._parse_json(data)
        recipe = load_recipe_text(data.decode("utf-8"))
        if data != _canonical(recipe) or recipe["scope"]["expected_empty"] is not True:
            raise ParisonError(_METADATA_ERROR)
        keys = recipe["keys"]
        is_hash = plan["partition_plan_version"] == 2
        if (
            recipe["comparison_mode"] != "keyed"
            or not 1 <= len(keys) <= (16 if is_hash else 1)
            or any(
                recipe["columns"][key]["type"] not in ({"integer", "string"} if is_hash else {"integer"})
                for key in keys
            )
            or recipe["output"]["sensitivity"] != "summary"
            or any(
                recipe.get(name)
                for name in ("column_mappings", "field_projection", "input_projection", "excluded_columns")
            )
            or set(recipe["columns"]) != set(journal["identity"]["columns"])
        ):
            raise ParisonError(_METADATA_ERROR)
        # Mechanical derivation changes exactly expected_empty. The original may
        # have either value; neither candidate requires reading original inputs.
        originals = [
            _checked_policy_sha256({**recipe, "scope": {**recipe["scope"], "expected_empty": empty}})
            for empty in (False, True)
        ]
        if journal["identity"]["policy_sha256"] not in originals:
            raise ParisonError(_METADATA_ERROR)
        return recipe
    except (ParisonError, KeyError, TypeError, ValueError, UnicodeError, OverflowError):
        raise ParisonError(_METADATA_ERROR) from None


def _checkpoint(value, index, journal, recipe):
    """Check claimed result arithmetic and bindings, not authenticity of execution."""

    try:
        _object(value, "partition_checkpoint_version index policy_sha256 engine_sha256 inputs result")
        _integer(value["partition_checkpoint_version"], 1, 1)
        _integer(value["index"], index, index)
        record = journal["routing"]["receipt"]["partitions"][index]
        _object(value["inputs"], "baseline candidate")
        for side in _SIDES:
            _descriptor(value["inputs"][side], 1000000000, minimum=1, rows=1000000)
        if (
            value["policy_sha256"] != _checked_policy_sha256(recipe)
            or value["engine_sha256"] != hashlib.sha256(_canonical(journal["identity"]["engine"])).hexdigest()
            or value["inputs"] != {side: record[side] for side in _SIDES}
        ):
            raise ParisonError(_METADATA_ERROR)
        result = _object(value["result"], "counts field_counts discrepancy_count outcome complete")
        fields, counts, complete = result["field_counts"], result["counts"], result["complete"]
        if (
            type(complete) is not bool
            or not discovery._counts(counts)
            or not discovery._field_counts(fields)
            or set(fields) != set(recipe["columns"]) - set(recipe["keys"])
            or not discovery._consistent_counts(counts, fields, complete)
            or any(counts[side] != record[side]["rows"] for side in _SIDES)
            or (complete and any(counts["common_keys"] + counts[f"{side}_only"] != counts[side] for side in _SIDES))
        ):
            raise ParisonError(_METADATA_ERROR)
        if type(result["discrepancy_count"]) is not int or result["discrepancy_count"] < 0:
            raise ParisonError(_METADATA_ERROR)
        differences = (
            counts["baseline_only"]
            + counts["candidate_only"]
            + sum(item["different"] + item["within_tolerance"] for item in fields.values())
        )
        outcome = (
            "INCONCLUSIVE"
            if not complete
            else "FAIL"
            if counts["baseline_only"] or counts["candidate_only"] or counts["matched_with_required_difference"]
            else "PASS"
        )
        if result["discrepancy_count"] != differences or result["outcome"] != outcome:
            raise ParisonError(_METADATA_ERROR)
        return value
    except (ParisonError, KeyError, TypeError, ValueError, UnicodeError, OverflowError, IndexError):
        raise ParisonError(_METADATA_ERROR) from None


def _metadata(data):
    """Decode a bounded committed journal/child; not an uncommitted next slot."""
    try:
        if len(data) > 1048576:
            raise ParisonError(_METADATA_ERROR)
        value = discovery._parse_json(data)
        if type(value) is not dict or data != _canonical(value) + b"\n":
            raise ParisonError(_METADATA_ERROR)
        return value
    except (ParisonError, TypeError, ValueError, UnicodeError, RecursionError):
        raise ParisonError(_METADATA_ERROR) from None
