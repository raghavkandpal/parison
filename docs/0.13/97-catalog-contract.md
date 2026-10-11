# Local catalog contract

Date: 11 October 2026

Status: **development contract**

## Ownership

A catalog is an ordinary user-selected SQLite file. Parison creates its parent directory when needed, rejects a symlink or non-file database path, restricts a newly opened database to owner read/write permissions where supported, and rejects unknown schema versions.

The database must be outside every bundle it indexes so catalog mutation cannot place untracked operational state inside an evidence directory.

The catalog is disposable derived state. It never becomes part of bundle verification, comparison semantics or resume identity.

## Stored projection

`catalog add` first runs the same recursive verification and safe inspection used by `parison inspect`. It stores:

- the absolute bundle path;
- manifest SHA-256 identity;
- bundle kind and recorded outcome; and
- the complete summary-safe inspection projection as canonical JSON.

It does not store discrepancy samples, source records, keys, values or bundle files. Adding the same unchanged path is idempotent; adding a newly verified bundle at that path replaces its prior projection explicitly.

## Live state

`list` and `show` combine stored metadata with one live state:

- `current`: recursive verification succeeds and the manifest digest matches;
- `modified`: the path exists but verification fails or its manifest digest differs; or
- `missing`: the indexed path is no longer a directory.

Copied bundles may share a digest. `duplicate_paths` reports how many indexed paths share it; duplicates are not deleted or collapsed. Results are ordered by normalized path, independent of insertion order.

`remove` deletes one normalized path from the disposable index. It never deletes or edits the referenced bundle.

## Failure and privacy behavior

Invalid bundles are rejected before a write. SQLite and filesystem failures are controlled `parison:` errors. Listing a new database yields an empty catalog. An incompatible catalog version fails closed.

Catalog files may reveal bundle paths and summary outcomes, so they should still be protected as operational metadata. A raw bundle remains sensitive even though its catalog projection is summary-safe.
