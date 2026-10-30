# PostgreSQL coordinated two-table acquisition contract

Date: 28 October 2026
Status: frozen for 2.3 feature 2 implementation; not a release commitment

This is capability 2 in the [six-feature roadmap](246-six-feature-roadmap.md).
It narrows coordination to one `orders`/`order_lines` source pair. The names are
logical slots, not proof of business meaning. Each slot declares one permanent
PostgreSQL base table and ordered columns/key under the released feature 1
selection rules. The output is local acquisition evidence, not parity, source
truth, migration approval or cutover authorization. Feature 1 plans, receipts,
bytes, CLI output and verifier remain readable and unchanged.

## Reviewed input and transaction

`postgres-pair-plan-v1` is a strict JSON object with exactly
`pair_plan_version: 1`, `source_id`, `tables`, and `limits`. `tables` has exactly
`orders` and `order_lines`; each has exactly `schema`, `table`, `columns`, and
`primary_key`, with feature 1 identifier, type and exact primary-key rules.
The two selections must name distinct schema/table pairs. `limits` has exactly
`max_rows`, `max_output_bytes`, `statement_timeout_ms`, and `wall_timeout_ms`;
the first two cap both each table and the pair total, at 300,000 rows and
1 GiB, while the latter cap each statement at five minutes and the whole
operation at ten minutes. The plan contains no DSN, credentials, SQL, filters,
exclusions, tolerance or policy approval. Its digest is SHA-256 over compact
sorted-key UTF-8 JSON without a trailing newline.

The optional `parison-postgres-pair` entry point reads libpq service/environment
settings. It opens one connection and one `REPEATABLE READ READ ONLY`
transaction. After transaction-local formatting, RLS and timeout settings,
it acquires `ACCESS SHARE` on both named relations in sorted `(schema, table)`
order **before the first snapshot-taking query**. The locks block relation
replacement and remain held until commit, while ordinary row writers may
continue. It then qualifies both tables/role, counts and copies each under
the same snapshot. The reader records the one snapshot token in each child
receipt and the private pair receipt. Separate connections or exported
snapshots are outside this version. A concurrent writer after the first read
must not split the pair. These are source-visible adapter claims only.

## Local wire format and verification

The new output directory contains exactly `receipt.json`, `summary.json`,
`manifest.json`, and `tables/`. `tables/` contains exactly `orders/` and
`order_lines/`; each is a complete feature 1 four-file export directory with
its **unchanged** `postgres_source_receipt_version: 1` wire format. Its
`plan_sha256` binds the derived feature 1 plan with the common `source_id`,
selection and pair `limits`. The pair is published only after both child
exports complete, both local verifiers succeed, the database transaction
commits, the pair verifier succeeds, and the wall/row/byte totals hold. One
failure or interruption removes the entire sensitive stage; no partial pair
or complete coordination record is published. The shared local publication
primitives preserve no-overwrite and symlink-safe boundaries.

The private canonical `receipt.json` has exactly
`postgres_pair_receipt_version: 1`, `kind:
"postgresql-two-table-export"`, `pair_plan_sha256`, `source`, `transaction`,
`table_manifests`, `limits`, and `observed`. `source` has exactly `source_id`,
`database`, `role`, and `server_version_num`. `transaction` has exactly
`isolation: "repeatable read"`, `read_only: true`, `row_security: "off"`, and
`snapshot`. `table_manifests` has exactly the `orders` and `order_lines`
SHA-256 digests of their canonical `manifest.json` bytes. `observed` has
exactly `rows`, `bytes`, `elapsed_ms`, and `complete: true`; row and byte
counts are the sums of child receipt observations. Child receipt source
identity, settings, snapshot and limits must match the pair receipt exactly.
The verifier reconstructs the strict pair plan from child receipts and checks
`pair_plan_sha256`; a changed selection, missing table or swapped child
cannot retain a valid pair claim without recomputing all local digests.

The canonical `summary.json` has exactly
`postgres_pair_summary_version: 1`, `kind`, `complete`, `coverage_claim:
"adapter-two-tables-one-source-snapshot"`, `tables: 2`, `rows`, `bytes`, and
`receipt_sha256`. It has no source label, database, schema, table, role, query,
snapshot, path, key, value or sample. The canonical `manifest.json` has exactly
`postgres_pair_manifest_version: 1`, `kind`, `complete`, and `files`, where
`files` binds `receipt.json`, `summary.json`, `orders` and `order_lines` by
SHA-256 (the latter two mean the child manifest bytes). All three JSON files
are compact sorted-key UTF-8 plus one newline. The offline
`parison verify-postgres-pair` command uses no Psycopg or database connection,
checks strict shape, canonical bytes, exact membership, symlinks, all digests,
child verification, common source/snapshot/limits, reconstructed plan digest,
total arithmetic and exact safe summary projection. It reports only the
summary. Recomputed digest-valid forgery remains unauthenticated adapter
evidence; offline verification cannot prove extraction truth.

## Adversarial completion gate

Pin canonical plan, pair receipt, summary and manifest bytes, and retain the
feature 1 byte fixtures. On a controlled PostgreSQL 18 source, test an empty
child, UTF-8 and quoted identifiers, concurrent inserts to both tables after
the first snapshot read, DDL replacement attempts, stale/changed selection,
wrong key, source role/RLS rejection, one child row/byte/time budget breach,
mid-second-COPY interruption or connection failure, commit failure,
no-overwrite and symlinked destination, staging cleanup, source removal, a
missing/swapped child, changed snapshot/limits, digest-valid forged pair and
raw leakage from summary/CLI. The two-table corpus should also include
matching omissions, duplicate/orphan lines and conservation offsetting, but
those are **rehearsal** tests for feature 5; acquisition must not promote
them to parity or cutover PASS. Report machine-specific time, memory, disk,
bytes and source load for 100,000 and 250,000 total rows per side, with three
cold runs, before claiming the provisional ten-minute operator target.

No remote orchestration, arbitrary SQL, parallel worker, cross-instance
snapshot equivalence, CDC, automated policy, repair, signing or cutover is in
this feature.
