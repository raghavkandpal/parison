"""Offline validation of bounded PostgreSQL snapshot collections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import stat
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from ._safe_fs import check_output_parent
from .analysis import _canonical
from .core import ParisonError
from .representation import MAX_REPRESENTATION_BYTES, validate_representation
from .representation import PROFILE as REPRESENTATION_PROFILE
from .source_receipt import (
    MAX_BYTES,
    _bundle_handles,
    _integer,
    _object,
    _read_json,
    _sha,
    _text,
    _verify_handles,
    validate_postgres_plan,
)

KIND = "postgresql-table-collection-export"
PROFILE = "postgresql-base-table-csv-v1"
ONLY_PROFILE = "postgresql-base-table-only-csv-v1"
CLAIM = "adapter-table-collection-one-source-snapshot"
META_LIMIT = 256 * 1024
_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}")
_ERROR = "invalid or incomplete collection evidence"


def _ids(value: Any) -> list[str]:
    if not isinstance(value, dict) or not 1 <= len(value) <= 16:
        raise ParisonError(_ERROR)
    if any(not isinstance(key, str) or _ID.fullmatch(key) is None for key in value):
        raise ParisonError(_ERROR)
    return sorted(value)


def validate_postgres_collection_plan(value: Any) -> dict[str, Any]:
    plan = _object(value, "collection_plan_version source_id tables limits")
    version = _integer(plan["collection_plan_version"], 1, 2)
    limits = plan["limits"]
    if version == 2:
        _object(limits, "max_rows max_output_bytes statement_timeout_ms wall_timeout_ms max_representation_bytes")
        _integer(limits["max_representation_bytes"], 1, MAX_REPRESENTATION_BYTES)
        limits = {name: fact for name, fact in limits.items() if name != "max_representation_bytes"}
    _text(plan["source_id"])
    relations = set()
    for table_id in _ids(plan["tables"]):
        table = _object(plan["tables"][table_id], "schema table columns primary_key")
        validate_postgres_plan({"plan_version": 1, "source_id": plan["source_id"], **table, "limits": limits})
        relation = (table["schema"], table["table"])
        if relation in relations:
            raise ParisonError(_ERROR)
        relations.add(relation)
    return plan


def collection_summary(receipt: dict[str, Any], data: bytes) -> dict[str, Any]:
    version = receipt["postgres_collection_receipt_version"]
    return {
        "postgres_collection_summary_version": version,
        **({"representation_bytes": receipt["observed"]["representation_bytes"]} if version == 2 else {}),
        "kind": KIND,
        "complete": True,
        "coverage_claim": CLAIM,
        "tables": len(receipt["table_manifests"]),
        "rows": receipt["observed"]["rows"],
        "bytes": receipt["observed"]["bytes"],
        "receipt_sha256": hashlib.sha256(data).hexdigest(),
    }


def _receipt(receipt: Any, children: dict) -> None:
    version = _integer(receipt.get("postgres_collection_receipt_version"), 1, 2)
    _object(
        receipt,
        "postgres_collection_receipt_version kind collection_plan_sha256 capability_profile source transaction table_manifests limits observed"
        + (" representation_sha256" if version == 2 else ""),
    )
    if receipt["kind"] != KIND or receipt["capability_profile"] not in (
        (REPRESENTATION_PROFILE,) if version == 2 else (PROFILE, ONLY_PROFILE)
    ):
        raise ParisonError(_ERROR)
    _sha(receipt["collection_plan_sha256"])
    source = _object(receipt["source"], "source_id database role server_version_num")
    for name in ("source_id", "database", "role"):
        _text(source[name])
    # Offline readability is independent of the evolving live support matrix.
    _integer(source["server_version_num"], 160000, 999999)
    transaction = _object(receipt["transaction"], "isolation read_only row_security snapshot")
    if (
        transaction["isolation"] != "repeatable read"
        or transaction["read_only"] is not True
        or transaction["row_security"] != "off"
    ):
        raise ParisonError(_ERROR)
    _text(transaction["snapshot"])
    if _ids(receipt["table_manifests"]) != sorted(children):
        raise ParisonError(_ERROR)
    observed = _object(
        receipt["observed"], "rows bytes elapsed_ms complete" + (" representation_bytes" if version == 2 else "")
    )
    if version == 2:
        _sha(receipt["representation_sha256"])
        _integer(observed["representation_bytes"], 1, receipt["limits"]["max_representation_bytes"])
    child_limits = {name: fact for name, fact in receipt["limits"].items() if name != "max_representation_bytes"}
    plan = {
        "collection_plan_version": version,
        "source_id": source["source_id"],
        "tables": {},
        "limits": receipt["limits"],
    }
    rows = size = 0
    for table_id, (child, digest) in children.items():
        expected_version = 2 if receipt["capability_profile"] in (ONLY_PROFILE, REPRESENTATION_PROFILE) else 1
        if child["postgres_source_receipt_version"] != expected_version:
            raise ParisonError(_ERROR)
        _sha(receipt["table_manifests"][table_id])
        if receipt["table_manifests"][table_id] != digest:
            raise ParisonError(_ERROR)
        if any(child["source"][name] != fact for name, fact in source.items()):
            raise ParisonError(_ERROR)
        if any(child["transaction"][name] != fact for name, fact in transaction.items()):
            raise ParisonError(_ERROR)
        if child["limits"] != child_limits or child["observed"]["elapsed_ms"] != observed["elapsed_ms"]:
            raise ParisonError(_ERROR)
        plan["tables"][table_id] = {
            name: child["source"][name] for name in ("schema", "table", "columns", "primary_key")
        }
        rows += child["observed"]["local_rows"]
        size += child["observed"]["output_bytes"]
    validate_postgres_collection_plan(plan)
    if receipt["collection_plan_sha256"] != hashlib.sha256(_canonical(plan)).hexdigest():
        raise ParisonError(_ERROR)
    _integer(observed["rows"], 0, receipt["limits"]["max_rows"])
    _integer(observed["bytes"], 0, receipt["limits"]["max_output_bytes"])
    _integer(observed["elapsed_ms"], 0, receipt["limits"]["wall_timeout_ms"])
    if observed["complete"] is not True or (rows, size) != (observed["rows"], observed["bytes"]):
        raise ParisonError(_ERROR)


def _directory(stack, path, parent_fd=None):
    if os.name == "posix":
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        stack.callback(os.close, fd)
        return fd
    if path.is_symlink() or not path.is_dir():
        raise ParisonError(_ERROR)
    return None


def _members(path, fd, maximum=4):
    names = set()
    with os.scandir(fd if fd is not None else path) as entries:
        for entry in entries:
            names.add(entry.name)
            if len(names) > maximum:
                raise ParisonError(_ERROR)
    return names


def _stamp(handle):
    info = os.fstat(handle.fileno())
    return _stat_stamp(info)


def _stat_stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _verified_collection(directory: str | Path) -> dict[str, Any]:
    """Verify bounded pinned local evidence without a driver or server."""
    root = Path(directory)
    try:
        check_output_parent(root.parent)
        with ExitStack() as stack:
            root_fd = _directory(stack, root)
            members = _members(root, root_fd, 5)
            base_members = {"receipt.json", "summary.json", "manifest.json", "tables"}
            if members not in (base_members, base_members | {"representation.json"}):
                raise ParisonError(_ERROR)
            tables_path = root / "tables"
            tables_fd = _directory(stack, Path("tables") if root_fd is not None else tables_path, root_fd)
            names = _members(tables_path, tables_fd, 16)
            table_ids = _ids(dict.fromkeys(names))
            directories = [
                (root, root_fd, members),
                (tables_path, tables_fd, set(table_ids)),
            ]
            metadata = {}
            for name in sorted(members - {"tables"}):
                if root_fd is not None:
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
                    handle = stack.enter_context(os.fdopen(fd, "rb"))
                else:
                    path = root / name
                    if path.is_symlink() or not path.is_file():
                        raise ParisonError(_ERROR)
                    handle = stack.enter_context(path.open("rb"))
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    raise ParisonError(_ERROR)
                metadata[name] = handle
            children_handles = {}
            for table_id in table_ids:
                child = Path(table_id) if tables_fd is not None else tables_path / table_id
                child_fd = _directory(stack, child, tables_fd)
                child_path = tables_path / table_id
                directories.append(
                    (child_path, child_fd, {"data.csv", "receipt.json", "summary.json", "manifest.json"})
                )
                children_handles[table_id] = stack.enter_context(
                    _bundle_handles(Path(".") if child_fd is not None else child_path, parent_fd=child_fd)
                )
            directory_stamps = [(fd, _stat_stamp(os.fstat(fd))) for _, fd, _ in directories if fd is not None]
            all_handles = list(metadata.values()) + [
                h for handles in children_handles.values() for h in handles.values()
            ]
            stamps = [(handle, _stamp(handle)) for handle in all_handles]
            for name, handle in metadata.items():
                if os.fstat(handle.fileno()).st_size > (
                    MAX_REPRESENTATION_BYTES if name == "representation.json" else META_LIMIT
                ):
                    raise ParisonError(_ERROR)
            receipt, receipt_data = _read_json(metadata["receipt.json"])
            # Validate configured ceilings before hashing potentially large children.
            version = _integer(receipt.get("postgres_collection_receipt_version"), 1, 2)
            if (version == 2) != ("representation.json" in metadata):
                raise ParisonError(_ERROR)
            _object(
                receipt,
                "postgres_collection_receipt_version kind collection_plan_sha256 capability_profile source transaction table_manifests limits observed"
                + (" representation_sha256" if version == 2 else ""),
            )
            child_data_bytes = 0
            for handles in children_handles.values():
                for name, handle in handles.items():
                    size = os.fstat(handle.fileno()).st_size
                    if size > (MAX_BYTES if name == "data.csv" else META_LIMIT):
                        raise ParisonError(_ERROR)
                    if name == "data.csv":
                        child_data_bytes += size
            # Reuse released limit validation without consulting the live matrix.
            limits = receipt["limits"]
            _object(
                limits,
                "max_rows max_output_bytes statement_timeout_ms wall_timeout_ms"
                + (" max_representation_bytes" if version == 2 else ""),
            )
            for name, maximum in (
                ("max_rows", 300000),
                ("max_output_bytes", MAX_BYTES),
                ("statement_timeout_ms", 300000),
                ("wall_timeout_ms", 600000),
            ):
                _integer(limits[name], 1, maximum)
            representation_limit = 0
            if version == 2:
                representation_limit = _integer(limits["max_representation_bytes"], 1, MAX_REPRESENTATION_BYTES)
                if os.fstat(metadata["representation.json"].fileno()).st_size > representation_limit:
                    raise ParisonError(_ERROR)
            if child_data_bytes > limits["max_output_bytes"]:
                raise ParisonError(_ERROR)
            if (
                sum(stamp[2] for _, stamp in stamps)
                > limits["max_output_bytes"] + representation_limit + (3 + 3 * len(table_ids)) * META_LIMIT
            ):
                raise ParisonError(_ERROR)
            children = {}
            for table_id, handles in children_handles.items():
                _verify_handles(handles)
                handles["receipt.json"].seek(0)
                handles["manifest.json"].seek(0)
                child_receipt, _ = _read_json(handles["receipt.json"])
                _, data = _read_json(handles["manifest.json"])
                children[table_id] = child_receipt, hashlib.sha256(data).hexdigest()
            _receipt(receipt, children)
            representation = representation_data = None
            if version == 2:
                representation, representation_data = _read_json(metadata["representation.json"], representation_limit)
                if (
                    len(representation_data) != receipt["observed"]["representation_bytes"]
                    or hashlib.sha256(representation_data).hexdigest() != receipt["representation_sha256"]
                ):
                    raise ParisonError(_ERROR)
                validate_representation(representation, receipt, children)
            summary, summary_data = _read_json(metadata["summary.json"])
            _object(
                summary,
                "postgres_collection_summary_version kind complete coverage_claim tables rows bytes receipt_sha256"
                + (" representation_bytes" if version == 2 else ""),
            )
            _integer(summary["postgres_collection_summary_version"], version, version)
            if version == 2:
                _integer(summary["representation_bytes"], 1, representation_limit)
            _integer(summary["tables"], 1, 16)
            _integer(summary["rows"], 0, limits["max_rows"])
            _integer(summary["bytes"], 0, limits["max_output_bytes"])
            if summary["complete"] is not True or summary != collection_summary(receipt, receipt_data):
                raise ParisonError(_ERROR)
            manifest, manifest_data = _read_json(metadata["manifest.json"])
            _object(manifest, "postgres_collection_manifest_version kind complete files table_manifests")
            _integer(manifest["postgres_collection_manifest_version"], version, version)
            if (
                manifest["kind"] != KIND
                or manifest["complete"] is not True
                or manifest["table_manifests"] != receipt["table_manifests"]
            ):
                raise ParisonError(_ERROR)
            files = _object(
                manifest["files"], "receipt.json summary.json" + (" representation.json" if version == 2 else "")
            )
            expected_files = {
                "receipt.json": hashlib.sha256(receipt_data).hexdigest(),
                "summary.json": hashlib.sha256(summary_data).hexdigest(),
            }
            if version == 2:
                expected_files["representation.json"] = hashlib.sha256(representation_data).hexdigest()
            if files != expected_files:
                raise ParisonError(_ERROR)
            if any(_stamp(handle) != before for handle, before in stamps):
                raise ParisonError(_ERROR)
            for path, fd, expected in directories:
                if (fd is None and path.is_symlink()) or _members(path, fd, len(expected)) != expected:
                    raise ParisonError(_ERROR)
            if any(_stat_stamp(os.fstat(fd)) != before for fd, before in directory_stamps):
                raise ParisonError(_ERROR)
            return {
                "summary": summary,
                "receipt": receipt,
                "representation": representation,
                "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
            }
    except (
        ParisonError,
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        RecursionError,
        csv.Error,
    ):
        raise ParisonError(_ERROR) from None


def verify_postgres_collection(directory: str | Path) -> dict[str, Any]:
    """Return only the released safe projection of a pinned verified collection."""
    return _verified_collection(directory)["summary"]


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParisonError(_ERROR)


def main(argv: list[str] | None = None) -> int:
    import sys

    parser = _SafeParser(prog="parison verify-postgres-collection")
    parser.add_argument("bundle")
    try:
        args = parser.parse_args(argv)
        summary = verify_postgres_collection(args.bundle)
        print(_canonical(summary).decode("utf-8"))
        return 0
    except (ParisonError, OSError, ValueError, TypeError, KeyError):
        print(f"parison verify-postgres-collection: {_ERROR}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("parison verify-postgres-collection: interrupted", file=sys.stderr)
        return 130
