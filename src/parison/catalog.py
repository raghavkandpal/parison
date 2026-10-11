"""Explicit local index of safe metadata from verified Parison bundles."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .core import ParisonError, inspect_bundle


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    path TEXT PRIMARY KEY,
    bundle_sha256 TEXT NOT NULL,
    kind TEXT NOT NULL,
    outcome TEXT NOT NULL,
    metadata TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_bundle_sha256 ON runs(bundle_sha256);
"""


def _open(database: str | Path) -> sqlite3.Connection:
    path = Path(database)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ParisonError(f"catalog is not a regular file: {path}")
    connection = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in {0, 1}:
            connection.close()
            raise ParisonError(f"catalog schema version is unsupported: {version}")
        connection.executescript(_SCHEMA)
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
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
    path = str(Path(bundle).absolute())
    metadata = inspect_bundle(path)
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    try:
        with closing(_open(database)) as connection, connection:
            existing = connection.execute("SELECT bundle_sha256 FROM runs WHERE path = ?", (path,)).fetchone()
            status = "added" if existing is None else ("unchanged" if existing[0] == metadata["bundle_sha256"] else "updated")
            connection.execute(
                "INSERT INTO runs(path, bundle_sha256, kind, outcome, metadata) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET bundle_sha256=excluded.bundle_sha256, kind=excluded.kind, "
                "outcome=excluded.outcome, metadata=excluded.metadata",
                (path, metadata["bundle_sha256"], _kind(metadata), metadata["outcome"], encoded),
            )
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot update catalog: {exc}") from exc
    return {"status": status, "path": path, "bundle_sha256": metadata["bundle_sha256"], "kind": _kind(metadata), "outcome": metadata["outcome"]}


def _state(path: str, expected_digest: str) -> str:
    if not Path(path).is_dir():
        return "missing"
    try:
        current = inspect_bundle(path)
    except ParisonError:
        return "modified"
    return "current" if current["bundle_sha256"] == expected_digest else "modified"


def list_runs(database: str | Path, outcome: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    """Return stored safe metadata plus a live deterministic bundle state."""
    clauses, parameters = [], []
    if outcome is not None:
        clauses.append("outcome = ?")
        parameters.append(outcome)
    if kind is not None:
        clauses.append("kind = ?")
        parameters.append(kind)
    query = "SELECT path, bundle_sha256, kind, outcome, metadata FROM runs"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY path"
    try:
        with closing(_open(database)) as connection:
            rows = connection.execute(query, parameters).fetchall()
            duplicates = dict(connection.execute("SELECT bundle_sha256, COUNT(*) FROM runs GROUP BY bundle_sha256"))
    except sqlite3.Error as exc:
        raise ParisonError(f"cannot read catalog: {exc}") from exc
    return [
        {
            "path": path,
            "bundle_sha256": digest,
            "kind": row_kind,
            "outcome": row_outcome,
            "state": _state(path, digest),
            "duplicate_paths": duplicates[digest],
            "metadata": json.loads(metadata),
        }
        for path, digest, row_kind, row_outcome, metadata in rows
    ]


def show(database: str | Path, bundle: str | Path) -> dict[str, Any]:
    """Return one catalog entry selected by its normalized bundle path."""
    path = str(Path(bundle).absolute())
    matches = [entry for entry in list_runs(database) if entry["path"] == path]
    if not matches:
        raise ParisonError(f"bundle is not in catalog: {path}")
    return matches[0]
