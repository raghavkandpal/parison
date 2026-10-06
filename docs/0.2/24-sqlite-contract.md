# SQLite read-only input contract

Date: 6 October 2026

## Locator and scope

SQLite is a local read-only connector selected with a source locator:

```text
sqlite:path/to/database.db#table_name
```

The path may be relative to the current working directory or absolute. The fragment is one exact table name. Empty paths/fragments, URI parameters, views, virtual tables, attached databases and arbitrary SQL are rejected. Supporting a table covers the intended local snapshot workflow without creating a query language or connector framework.

Either comparison side may independently be a file input or SQLite locator. Recipes and result JSON remain format-neutral keyed-v1 artifacts.

## Read-only behavior

Parison opens the resolved database through SQLite's `mode=ro` URI and enables `PRAGMA query_only`. It confirms the requested name is an ordinary table in `sqlite_schema`, quotes the verified identifier, and runs only `SELECT * FROM <table>`.

The database must be a regular non-symlink file. `-wal` and `-journal` sidecars are rejected because hashing only the main file would not identify the complete snapshot. Users must checkpoint/close writers or copy a stable database before comparison. The main database digest is checked before and after reading. Parison never creates, updates, checkpoints or vacuums the database.

## Schema and scalar mapping

Cursor column names must be unique and nonempty. Every selected row has that fixed schema. SQLite NULL, INTEGER, REAL and TEXT values enter the existing recipe parser; BLOB values are rejected. Booleans, dates, timestamps and decimals should be stored as recipe-compatible TEXT when SQLite's dynamic typing would otherwise be ambiguous. In particular, binary REAL is not promoted into an exact decimal representation.

Drafting reads table metadata only and emits the same unresolved recipe draft used for files. It does not infer policy from declared SQLite affinities or sample values.

## Limits, cancellation and evidence

The database file counts toward `--max-input-bytes`; selected rows count toward `--max-rows`. Iteration checks the row limit before retaining an additional row. Ctrl-C uses the existing INTERRUPTED outcome and bundle path. Errors identify the database/table and failure class but do not include row values.

The recipe's snapshot, cutoff, filters and full-completeness fields remain user assertions. Parison can prove which database bytes and table it read, not that an upstream export is complete. The table locator is local execution input; credentials and network databases are outside 0.2.

## Usage and data handling

Quote locators in the shell and use them anywhere a baseline or candidate path is accepted:

```sh
parison draft-recipe \
  --baseline baseline.jsonl \
  --candidate 'sqlite:exports/candidate.db#orders' \
  --output orders.recipe.json
# review, complete and validate the draft
parison compare --recipe orders.recipe.json \
  --baseline baseline.jsonl \
  --candidate 'sqlite:exports/candidate.db#orders' \
  --output runs/orders
```

The database is opened locally with no credential mechanism and no network transport. Parison does not copy it into the bundle. Evidence contains its byte count, SHA-256 digest, source kind and selected table name; it omits the local path. Table and column names may still be sensitive, so protect bundles according to repository visibility and output sensitivity.

## Rejections

Reject malformed locators, missing/unsafe databases, active journal sidecars, nonexistent or non-table objects, duplicate/empty columns, BLOB or unsupported values, size/row overruns, input changes and SQLite read errors. These conditions cannot produce PASS.
