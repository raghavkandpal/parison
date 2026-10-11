# SQLite multiset execution contract

Date: 11 October 2026

Status: **release-candidate contract**

## Selection and scope

The default engine remains `memory`. SQLite execution is opt-in through `parison compare --engine sqlite` or a suite-v2 case:

```json
"execution": {
  "engine": "sqlite",
  "max_temp_bytes": 5000000000
}
```

Only multiset-v1 recipes are accepted. Selecting SQLite for another comparison mode is an error before either input is opened.

## Semantics

Parison parses and normalizes every field and produces the existing typed-length-prefixed-v1 encoding. SQLite stores that encoding as a binary key and counts occurrences. SQLite collation, numeric coercion and row ordering never define equality.

The engine must produce the same outcome, counts, discrepancy count and bounded raw sample as the memory engine for the same ordered input snapshots and limits. Discrepancy rows are ordered by canonical encoding.

Runtime metadata records `execution_engine` and, after successful SQLite execution, `temporary_bytes`. Resource-limit metadata records `max_temp_bytes`, including in handled ERROR and INTERRUPTED bundles. These operational fields are expected cross-engine differences. With journaling disabled, the database grows monotonically, so its final size is the invocation's peak database size.

## Storage and cleanup

Each invocation creates a new private temporary directory and one SQLite database. `--temp-directory` chooses only the existing non-symlink parent; it does not preserve a resumable database. The database uses no rollback journal because it is disposable and never published.

SQLite's maximum-page setting enforces the configured database ceiling. An undersized ceiling or disk-full condition is a controlled error. The connection closes before the private directory is removed on success and handled errors, including parse and distinct-row-limit failures.

The database contains canonical encodings and JSON renderings of supplied rows. Treat its parent filesystem as sensitive even when the final result uses summary sensitivity. Parison does not provide temporary-file encryption or secure erasure.

## Limits

Existing input byte, decoded byte, row and distinct-row limits still apply. `max_temp_bytes` limits only the SQLite database, not filesystem metadata, input files, Python allocations or the final evidence bundle.

## Interruption

Ordinary exception and Ctrl-C paths clean the private workspace. Suite cases place spill directories inside the suite's private staging or explicit workspace; forced worker shutdown removes those directories before publication or preserves no published reference to them. An uncatchable process or host termination can still leave an orphan, so operators should periodically inspect an explicitly selected parent.
