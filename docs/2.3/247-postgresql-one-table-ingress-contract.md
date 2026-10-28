# PostgreSQL one-table evidence ingress contract

Date: 28 October 2026
Status: frozen for feature 1 implementation; not a release commitment

This is the first capability in the [2.3 roadmap](246-six-feature-roadmap.md).
It is an opt-in, one-table acquisition path outside core comparison execution.
The reader handles PostgreSQL connection details; Parison's verifier reads
only local files. A valid receipt is a mechanically consistent adapter claim,
not proof that the database returned truthful or complete business data.
Released recipes, bundles, schemas, CLI JSON and canonical bytes do not change.

## Review input and source boundary

`postgres-export-plan-v1` is strict JSON with exactly `plan_version: 1`,
`source_id`, `schema`, `table`, `columns`, `primary_key` and `limits`.
`source_id` is a nonempty user-declared opaque instance label, not an
authenticated server identity. `columns` and `primary_key` are nonempty,
unique, ordered identifier lists; every key appears in columns. The reader
confirms the declared key exactly matches a valid, nondeferrable PostgreSQL
primary key. The plan contains no connection string, credentials, arbitrary
SQL, filter, expression, view or partition selector. The separate
`parison-postgres` command reads standard libpq service/environment settings;
the ordinary `parison` commands do not import the network reader. The reader
must not echo connection details or PostgreSQL exception text to stdout,
stderr, logs or summary results.

The first reader accepts only one permanent base table and supported scalar
columns. It resolves schema, table and columns exactly through `pg_catalog`
and quotes each identifier separately in generated SQL. It rejects views,
partitioned, foreign, temporary and unlogged relations, caller expressions,
missing columns, duplicate output names and unsupported source types. The
initial type allowlist is `smallint`, `integer`, `bigint`, `numeric`, `boolean`,
`text`, `varchar`, `uuid`, `date`, `timestamp` and `timestamptz`; later types
require a versioned conversion rule. The generated selection is an unfiltered
base-table `SELECT` over the declared columns, ordered by the primary key.

The adapter uses one `REPEATABLE READ READ ONLY` transaction for metadata,
`COUNT(*)` and `COPY (SELECT ...) TO STDOUT`. It sets row security to fail
closed, uses a dedicated non-owner, non-superuser role without `BYPASSRLS`, and rejects a
filtered RLS result. Matching count and COPY rows qualify only the adapter's
all-rows, selected-columns claim for that one source snapshot. They do not
authenticate source identity, prove extraction truth or align an independent
target snapshot. The private receipt records the snapshot token; no released
comparison treats equal-looking tokens from different instances as proof of
coordination. [PostgreSQL ingress research](245-postgresql-ingress-research.md)
records the underlying server semantics and access date.

## Output and canonical records

The reader publishes one new local directory containing exactly `data.csv`,
`receipt.json`, `summary.json` and `manifest.json`. Publication is private,
atomic, no-overwrite and symlink-safe. `data.csv` is UTF-8 PostgreSQL CSV with
one header in declared column order. The adapter fixes `client_encoding` to
UTF-8, `DateStyle` to `ISO, YMD` and `TimeZone` to UTC, and generates COPY with
`FORMAT CSV`, `HEADER TRUE`, `ENCODING 'UTF8'` and an exact
`\\N` NULL marker. Because Parison's CSV reader cannot distinguish a quoted
literal marker from an unquoted NULL after parsing, the adapter rejects any
selected text/varchar value equal to `\\N` in the source snapshot. A later
format may remove this restriction without changing these bytes. The
comparison recipe must explicitly review `\\N` as a null token; acquisition
does not approve or mutate a recipe.

The closed plan fields are `plan_version`, `source_id`, `schema`, `table`,
`columns`, `primary_key` and `limits`. The closed limits are `max_rows`,
`max_output_bytes`, `statement_timeout_ms` and `wall_timeout_ms`. The adapter
may apply a smaller positive limit, never a larger one. The plan digest is
SHA-256 over compact sorted-key UTF-8 JSON without a trailing newline.

The closed receipt fields are `postgres_source_receipt_version`, `kind`,
`plan_sha256`, `source`, `transaction`, `selection`, `limits` and `observed`.
`source` has exactly `source_id`, `database`, `schema`, `table`, `columns`,
`primary_key`, `types`, `server_version_num`, `role`, `role_is_owner`,
`role_bypassrls` and `role_superuser`. `transaction` has exactly `isolation`,
`read_only`, `row_security`, `snapshot`, `client_encoding`, `date_style` and
`time_zone`. `selection` has exactly `sql`, `format`, `null_marker` and
`null_marker_collision`. `limits` repeats the exact plan limits. `observed`
has exactly `server_rows`, `local_rows`, `output_bytes`, `output_sha256`,
`elapsed_ms` and `complete`. The verifier reconstructs the plan and generated
SQL from the receipt fields before accepting their digests/claims.

`receipt.json` is canonical UTF-8 compact sorted-key JSON plus one newline,
versioned as `postgres_source_receipt_version: 1`. Its closed private fields
record the plan digest, declared source and relation/columns/key, server
version, role/ownership/RLS qualification, transaction isolation/read-only
settings, snapshot token, exact generated unfiltered selection and format
and session settings, applied row/byte/statement/wall limits, completed source
count, parsed local row count, output bytes/SHA-256 and elapsed time. It
contains no password, DSN or host credentials. The source identity, query
scope and snapshot fields are sensitive and remain private even though their
digests may be linked pseudonymously.

`summary.json` is a separately closed, canonical `postgres_source_summary_version:
1` projection containing only `kind`, `complete`, `coverage_claim`, row and
byte totals, output SHA-256 and receipt SHA-256. `coverage_claim` is fixed to
`adapter-all-rows-selected-columns` for this first version; it is never
`source-truth` or a parity outcome. No source ID, names, paths, query,
snapshot token, key, value or sample may appear in this file or CLI JSON.
`manifest.json` has a separate version and binds the exact other three files
by SHA-256. A verified result is source-free local consistency, not database
attestation. The offline verifier rechecks strict shapes, canonical bytes,
file membership, symlink absence, digests, CSV header and row count, receipt
arithmetic and exact summary derivation. A digest-valid forged source claim
cannot be authenticated offline and must never be reported as such.

The summary's exact fields are `postgres_source_summary_version`, `kind`,
`complete`, `coverage_claim`, `rows`, `bytes`, `output_sha256` and
`receipt_sha256`. The manifest's exact fields are
`postgres_source_manifest_version`, `kind`, `complete` and `files`, where
`files` contains exactly `data.csv`, `receipt.json` and `summary.json` digests.

The producer's state is unpublished until COPY completes, the server count
equals the parsed local count, byte/row/wall limits hold, the transaction
commits, all local files verify and the directory is atomically installed.
Any error, cancellation, broken connection, count mismatch, unsupported
format, symlinked output or interruption removes sensitive staging and
publishes no complete bundle. Post-publication source removal does not affect
offline verification.

## Budgets and acceptance fixtures

The first adapter enforces at most 300,000 rows and 1 GiB output bytes per
export, a five-minute PostgreSQL statement timeout and ten-minute client wall
cap. It also uses finite lock and idle-in-transaction timeouts. Limit breach
is an incomplete acquisition, never a truncated PASS. The roadmap's 100k and
250k two-table corpus is a later performance gate; no capacity claim follows
from one-table unit tests.

Pin canonical plan, private receipt, summary and manifest bytes. Test an
empty table, quoted identifiers, UTF-8, decimals and timestamp boundaries,
NULL/empty/literal `\\N`, missing or reordered columns, duplicate/nonprimary
keys, owner and `BYPASSRLS` roles, an RLS policy, views and partitioned tables,
unsupported types, concurrent writer, changed table or plan, count mismatch,
row/byte/time limit, cancellation, broken COPY, commit failure, symlinked
destination, no-overwrite race, sensitive staging cleanup, source removal and
digest-valid forged receipt/summary. The controlled PostgreSQL test proves
one source snapshot by writing concurrently after its first read. Offline
verification must succeed without PostgreSQL or the adapter dependency, while
old 2.2 byte fixtures remain unchanged.

No second database, CDC, parallel exported snapshot, source pushdown,
automated policy choice, signing, repair or cutover is part of feature 1.
