"""Explicit local index of safe metadata from verified Parison bundles."""

from __future__ import annotations

import json
import hashlib
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .core import ParisonError, inspect_bundle


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    path TEXT PRIMARY KEY,
    catalog_order INTEGER,
    bundle_sha256 TEXT NOT NULL,
    kind TEXT NOT NULL,
    outcome TEXT NOT NULL,
    metadata TEXT NOT NULL
);
"""
_INDEXES = """
CREATE INDEX IF NOT EXISTS runs_bundle_sha256 ON runs(bundle_sha256);
CREATE UNIQUE INDEX IF NOT EXISTS runs_catalog_order ON runs(catalog_order);
"""
_SAFE_RUN_FIELDS = ("outcome", "complete", "counts", "discrepancy_count", "runtime", "resource_limits", "input_sha256")


def _normalized_path(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _open(database: str | Path) -> sqlite3.Connection:
    path = Path(database)
    existed = path.exists()
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ParisonError(f"catalog is not a regular file: {path}")
    connection = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in {0, 1, 2}:
            connection.close()
            raise ParisonError(f"catalog schema version is unsupported: {version}")
        connection.executescript(_SCHEMA)
        if version == 1:
            connection.execute("ALTER TABLE runs ADD COLUMN catalog_order INTEGER")
        connection.execute("UPDATE runs SET catalog_order = rowid WHERE catalog_order IS NULL")
        connection.executescript(_INDEXES)
        connection.execute("PRAGMA user_version = 2")
        connection.commit()
        if not existed:
            os.chmod(path, 0o600)
        return connection
    except (OSError, sqlite3.Error) as exc:
        if connection is not None:
            connection.close()
        raise ParisonError(f"cannot open catalog: {exc}") from exc


def _kind(metadata: dict[str, Any]) -> str:
    return metadata.get("kind", "run")


def add(database: str | Path, bundle: str | Path) -> dict[str, Any]:
    """Verify a bundle and explicitly index only its safe inspection projection."""
    bundle_path = _normalized_path(bundle)
    database_path = _normalized_path(database)
    if bundle_path == database_path or bundle_path in database_path.parents:
        raise ParisonError("catalog database must be outside the indexed bundle")
    path = str(bundle_path)
    metadata = inspect_bundle(path)
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    try:
        with closing(_open(database)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute("SELECT bundle_sha256 FROM runs WHERE path = ?", (path,)).fetchone()
            status = "added" if existing is None else ("unchanged" if existing[0] == metadata["bundle_sha256"] else "updated")
            catalog_order = connection.execute("SELECT COALESCE(MAX(catalog_order), 0) + 1 FROM runs").fetchone()[0]
            connection.execute(
                "INSERT INTO runs(path, catalog_order, bundle_sha256, kind, outcome, metadata) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET bundle_sha256=excluded.bundle_sha256, kind=excluded.kind, "
                "outcome=excluded.outcome, metadata=excluded.metadata",
                (path, catalog_order, metadata["bundle_sha256"], _kind(metadata), metadata["outcome"], encoded),
            )
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot update catalog: {exc}") from exc
    return {"status": status, "path": path, "bundle_sha256": metadata["bundle_sha256"], "kind": _kind(metadata), "outcome": metadata["outcome"]}


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_integrity_matches(directory: Path, expected_manifest_digest: str) -> bool:
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file() or _digest(manifest_path) != expected_manifest_digest:
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict):
        return False
    for name, expected in files.items():
        path = directory / name
        if Path(name).name != name or path.is_symlink() or not path.is_file() or _digest(path) != expected:
            return False
    cases = manifest.get("cases", {})
    if not isinstance(cases, dict):
        return False
    return all(
        isinstance(identifier, str) and isinstance(digest, str)
        and _bundle_integrity_matches(directory / "cases" / identifier, digest)
        for identifier, digest in cases.items()
    )


def _state(path: str, expected_digest: str) -> str:
    directory = Path(path)
    if not directory.is_dir():
        return "missing"
    if directory.is_symlink():
        return "modified"
    try:
        current = _bundle_integrity_matches(directory, expected_digest)
    except (OSError, json.JSONDecodeError, TypeError):
        return "modified"
    return "current" if current else "modified"


def _decoded_entry(row: tuple[Any, ...], duplicate_paths: int) -> dict[str, Any]:
    catalog_order, path, digest, kind, outcome, metadata = row
    try:
        decoded = json.loads(metadata)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ParisonError(f"catalog contains invalid metadata: {exc}") from exc
    return {
        "catalog_order": catalog_order, "path": path, "bundle_sha256": digest, "kind": kind,
        "outcome": outcome, "state": _state(path, digest), "duplicate_paths": duplicate_paths, "metadata": decoded,
    }


def _entries(
    database: str | Path,
    outcome: str | None = None,
    kind: str | None = None,
    *,
    insertion_order: bool = False,
) -> list[dict[str, Any]]:
    clauses, parameters = [], []
    if outcome is not None:
        clauses.append("outcome = ?")
        parameters.append(outcome)
    if kind is not None:
        clauses.append("kind = ?")
        parameters.append(kind)
    query = "SELECT catalog_order, path, bundle_sha256, kind, outcome, metadata FROM runs"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY catalog_order, path" if insertion_order else " ORDER BY path"
    try:
        with closing(_open(database)) as connection:
            rows = connection.execute(query, parameters).fetchall()
            duplicates = dict(connection.execute("SELECT bundle_sha256, COUNT(*) FROM runs GROUP BY bundle_sha256"))
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot read catalog: {exc}") from exc
    return [_decoded_entry(row, duplicates[row[2]]) for row in rows]


def _entry(database: str | Path, bundle: str | Path) -> dict[str, Any]:
    path = str(_normalized_path(bundle))
    try:
        with closing(_open(database)) as connection:
            row = connection.execute(
                "SELECT catalog_order, path, bundle_sha256, kind, outcome, metadata FROM runs WHERE path = ?", (path,),
            ).fetchone()
            duplicates = 0 if row is None else connection.execute(
                "SELECT COUNT(*) FROM runs WHERE bundle_sha256 = ?", (row[2],),
            ).fetchone()[0]
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot read catalog: {exc}") from exc
    if row is None:
        raise ParisonError(f"bundle is not in catalog: {path}")
    return _decoded_entry(row, duplicates)


def _policy_matches(metadata: dict[str, Any], policy_sha256: str) -> bool:
    return metadata.get("policy_sha256") == policy_sha256 or any(
        case.get("policy_sha256") == policy_sha256 for case in metadata.get("cases", [])
    )


def _validate_policy_sha256(policy_sha256: str) -> None:
    if len(policy_sha256) != 64 or any(character not in "0123456789abcdef" for character in policy_sha256):
        raise ParisonError("catalog policy filter must be a lowercase SHA-256 digest")


def _run_projection(entry: dict[str, Any], *, include_order: bool = False) -> dict[str, Any]:
    projection = {
        "path": entry["path"], "bundle_sha256": entry["bundle_sha256"], "state": entry["state"],
        **{name: entry["metadata"].get(name) for name in _SAFE_RUN_FIELDS},
    }
    if include_order:
        projection = {"catalog_order": entry["catalog_order"], **projection}
    return projection


def list_runs(
    database: str | Path,
    outcome: str | None = None,
    kind: str | None = None,
    *,
    policy_sha256: str | None = None,
    state: str | None = None,
) -> list[dict[str, Any]]:
    """Return compact path-ordered entries with a live deterministic state."""
    if policy_sha256 is not None:
        _validate_policy_sha256(policy_sha256)
    if state is not None and state not in {"current", "modified", "missing"}:
        raise ParisonError("catalog state filter must be current, modified or missing")
    entries = _entries(database, outcome, kind)
    if policy_sha256 is not None:
        entries = [entry for entry in entries if _policy_matches(entry["metadata"], policy_sha256)]
    if state is not None:
        entries = [entry for entry in entries if entry["state"] == state]
    return [{name: value for name, value in entry.items() if name not in {"metadata", "catalog_order"}} for entry in entries]


def history(database: str | Path, policy_sha256: str) -> dict[str, Any]:
    """Return insertion-ordered safe run summaries and outcome transitions for one policy."""
    _validate_policy_sha256(policy_sha256)
    entries = [
        entry for entry in _entries(database, kind="run", insertion_order=True)
        if entry["metadata"].get("policy_sha256") == policy_sha256
    ]
    runs = [_run_projection(entry, include_order=True) for entry in entries]
    transitions = [
        {
            "from_catalog_order": before["catalog_order"],
            "to_catalog_order": after["catalog_order"],
            "outcome": {"before": before["outcome"], "after": after["outcome"]},
            "discrepancy_count": {
                "before": before["discrepancy_count"], "after": after["discrepancy_count"],
                "delta": after["discrepancy_count"] - before["discrepancy_count"],
            },
        }
        for before, after in zip(runs, runs[1:])
    ]
    return {"policy_sha256": policy_sha256, "runs": runs, "transitions": transitions}


def diff(database: str | Path, left_bundle: str | Path, right_bundle: str | Path) -> dict[str, Any]:
    """Compare safe stored projections for two run bundles with exactly the same policy."""
    left, right = _entry(database, left_bundle), _entry(database, right_bundle)
    if left["kind"] != "run" or right["kind"] != "run":
        raise ParisonError("catalog diff currently supports run bundles only")
    left_policy = left["metadata"].get("policy_sha256")
    right_policy = right["metadata"].get("policy_sha256")
    if not left_policy or left_policy != right_policy:
        raise ParisonError("catalog diff requires matching policy SHA-256 digests")
    left_projection, right_projection = _run_projection(left), _run_projection(right)
    changes = {
        name: {"before": left_projection[name], "after": right_projection[name]}
        for name in _SAFE_RUN_FIELDS if left_projection[name] != right_projection[name]
    }
    return {
        "policy_sha256": left_policy, "changed": bool(changes), "changes": changes,
        "left": left_projection, "right": right_projection,
    }


def show(database: str | Path, bundle: str | Path) -> dict[str, Any]:
    """Return one catalog entry selected by its normalized bundle path."""
    return {name: value for name, value in _entry(database, bundle).items() if name != "catalog_order"}


def remove(database: str | Path, bundle: str | Path) -> dict[str, Any]:
    """Remove one normalized path from the disposable index, never the bundle."""
    path = str(_normalized_path(bundle))
    try:
        with closing(_open(database)) as connection, connection:
            removed = connection.execute("DELETE FROM runs WHERE path = ?", (path,)).rowcount
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot update catalog: {exc}") from exc
    if not removed:
        raise ParisonError(f"bundle is not in catalog: {path}")
    return {"status": "removed", "path": path}
