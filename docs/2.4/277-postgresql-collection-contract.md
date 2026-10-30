# Bounded PostgreSQL snapshot collection contract

Date and primary-source access: 30 October 2026
Status: frozen feature 1 implementation contract; runtime and qualification pending

This contract implements feature 1 of the [ten-feature roadmap](275-ten-feature-research-and-roadmap.md).
It generalizes acquisition to 1–16 explicitly selected base tables in one database
and one transaction. A collection is private source-visible adapter evidence,
not parity, extraction truth, migration approval or cross-instance coordination.
All ten features must integrate and qualify before a 2.4 candidate. Released
2.3 plans, source/pair receipts, CLI aliases, readers and canonical fixtures stay
unchanged. Broader project rehearsal formats belong to later features.

## Reviewed plan and fixed bounds

`postgres-collection-plan-v1` is a strict JSON object with exactly
`collection_plan_version: 1`, `source_id`, `tables`, and `limits`. All objects
are closed; duplicate JSON names, non-finite numbers, booleans in integer fields,
invalid UTF-8, unknown fields and unsupported versions are rejected. The local
plan is at most 256 KiB and must be a regular, non-symlink file.

`source_id` follows the released source-v1 nonempty printable-text rule. It is
an opaque caller declaration, never authenticated identity. `tables` is an
object with 1–16 entries. Each ID matches `[a-z][a-z0-9_-]{0,31}`; IDs are unique
case-sensitive private aliases, never source names in a safe summary. Object
insertion order has no semantics. Each value has exactly `schema`, `table`,
`columns`, and `primary_key`, following source-v1: exact printable identifiers
of at most 63 UTF-8 bytes, 1–100 unique ordered columns and keys, every key
selected. Reject repeated exact `(schema, table)` tuples even under different
IDs. Identifiers are compared as supplied, without case folding or Unicode
normalization, and quoted separately; PostgreSQL quoted-name resolution is
authoritative. No caller SQL, filter, expression, view or implicit search path.

`limits` has exactly `max_rows`, `max_output_bytes`, `statement_timeout_ms`, and
`wall_timeout_ms`, all positive integers, respectively at most 300,000,
1,073,741,824, 300,000, and 600,000. The row/CSV-byte limits apply independently
to each child **and to the sum of all children**. There are no per-table
custom limits in v1. Runtime remaining allowances can only tighten execution;
they never alter the reviewed plan or a child's recorded limits.

Every JSON evidence member is at most 256 KiB. There are exactly 67 regular
files at the 16-table cap: three collection files plus four files per table.
CSV-byte totals exclude JSON metadata. Total staged regular-file content is
bounded by `max_output_bytes + (3 + 3 * table_count) * 262144`; check actual
content totals before publication. Filesystem allocation overhead is measured,
not claimed to equal content bytes. Sixteen is a finite structural bound,
not a performance or production-capacity claim. It requires the 16-table
boundary probe below before integration; existing released limits do not grow.

## One transaction and representation profile

Use the separately maintained [version/capability matrix](278-postgresql-capability-matrix.md).
The optional adapter owns libpq environment/service access and Psycopg outside
the offline verifier. It never records credentials, DSNs, hosts or raw server
exception text. No database connection is opened during offline verification.

1. Validate the entire plan and missing output path before connecting. Create
   private staging under the destination parent using the existing safe filesystem
   primitives; the caller owns an explicitly trusted local parent.
2. Open one connection, set UTF-8 client encoding, and begin one `REPEATABLE READ
   READ ONLY` transaction. Apply transaction-local `search_path=pg_catalog`, `DateStyle='ISO, YMD'`, UTC,
   `row_security=off`, statement timeout, derived lock timeout
   `min(10000, statement_timeout_ms)`, and 60,000 ms idle-in-transaction timeout.
3. Acquire `ACCESS SHARE` locks on all declared relations in ascending Python
   Unicode code-point tuple order `(schema, table)`, each separately quoted.
   No metadata, version, role, snapshot, count or other snapshot-taking query
   may precede the final lock. Duplicate relations are already rejected.
4. Qualify every relation and the live server against the matrix before copying
   any table: permanent ordinary base tables only; exact valid, ready, immediate,
   nondeferrable primary key; no partition flag or observed `pg_inherits` membership as
   parent or child;
   SELECT-only non-owner role, no superuser or
   `BYPASSRLS`, including inherited owner membership and write privileges.
   Reject missing/unsupported columns and any late member that fails qualification.
5. Count and copy children in ascending table-ID order under that snapshot.
   Each child's selection, CSV controls, null-marker collision rejection and
   exact source type allowlist are the unchanged source-v1 rules. In PostgreSQL
   internal names the allowlist is `int2`, `int4`, `int8`, `numeric`, `bool`,
   `text`, `varchar`, `uuid`, `date`, `timestamp`, `timestamptz`. Domains, enums,
   arrays and other types remain outside this profile. Require the actual
   built-in `pg_catalog` type identity, not only a matching custom type name.
   Check shared remaining
   row/byte allowances during acquisition, including CSV headers in byte totals.
6. Require identical source/database/role/server version and snapshot facts
   across all children, count/COPY equality and successful transaction commit.
   Then write and verify all evidence before one atomic no-overwrite install.
   Counts, collision scans and COPY use `ONLY` so later inheritance attachment
   cannot expand the declared base-table row scope.

`ACCESS SHARE` permits ordinary writers and blocks only conflicting lock modes;
it is not a blanket schema freeze. Locks must precede the first snapshot-taking
query, and concurrency/DDL tests must prove the intended ordering. Catalog
metadata under that snapshot is an adapter observation. Unsupported relation
changes, query failure or inconsistent facts abort the whole operation.
[PostgreSQL locking](https://www.postgresql.org/docs/18/explicit-locking.html),
[repeatable read](https://www.postgresql.org/docs/18/transaction-iso.html),
[row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).

The single monotonic deadline starts before staging/connection. Connection
wait is at most `min(10, ceil(wall_timeout_ms / 1000))` seconds, with a minimum
libpq timeout of one second; elapsed deadline checks still apply after connect.
Cancel active database work when its remaining wall allowance expires. Statement
and lock timeouts never restart the collection deadline. Receipt `elapsed_ms`
is the floor of elapsed milliseconds through successful commit, not an assertion
about source latency alone. Record that same value in every child receipt and
the collection receipt. Local evidence writing and verification remain inside
the deadline, checked at phase boundaries and immediately before rename.
Rename admission must occur before expiry; OS scheduling/rename latency is not
a hard real-time guarantee. Never advertise the elapsed field as total
post-publication wall time. Cleanup is required even after the deadline.

## Canonical evidence and child derivation

The output has exactly `receipt.json`, `summary.json`, `manifest.json`, and
`tables/`; `tables/` contains exactly the declared ID directories, each with
versioned source-v2 receipt and the existing source-v1 CSV/summary/manifest layouts.
Source-v2 uses `postgres_source_receipt_version: 2` and `plan_version: 2`
in its reconstructed child plan, with exact `FROM ONLY` selection SQL. Source-v1
records and canonical fixtures remain readable and unchanged.
All directories and members are private and reject symlinks. The filesystem
checks must cover ancestors/parent policy as in existing publication helpers,
regular files, exact membership, no-overwrite races and pinned reads on POSIX.

For ID `i`, derive its source-v2 plan with exactly `plan_version: 2`, parent
`source_id`, the four selection fields at `tables[i]`, and identical parent
`limits`. Its `plan_sha256` is SHA-256 of `_canonical(derived_plan)` without a
newline. The collection plan digest is likewise SHA-256 of `_canonical(plan)`.
JSON records use compact sorted-key UTF-8 plus one LF; `_canonical` retains the
released serialization, including escaping behavior. SHA-256 strings are
exactly 64 lowercase hexadecimal characters. Counts are nonnegative integers.

The collection receipt has exactly:

| Field | Fixed value or closed shape |
| --- | --- |
| `postgres_collection_receipt_version` | integer `1` |
| `kind` | `postgresql-table-collection-export` |
| `collection_plan_sha256` | canonical reviewed plan digest |
| `capability_profile` | `postgresql-base-table-only-csv-v1` |
| `source` | exactly `source_id`, `database`, `role`, `server_version_num` |
| `transaction` | exactly `isolation: "repeatable read"`, `read_only: true`, `row_security: "off"`, `snapshot` |
| `table_manifests` | exact ID→SHA-256 mapping of each child's canonical manifest bytes |
| `limits` | identical reviewed four-field limits |
| `observed` | exactly `rows`, `bytes`, `elapsed_ms`, `complete: true` |

Source/transaction field validation inherits source-v1. Private receipts contain
names, selection and snapshot facts through their children. They are sensitive;
predictable identifier hashes are pseudonymous, not confidential. Rows/bytes
are exact child sums; every child elapsed equals parent commit elapsed and
fits the shared wall limit. Every source/settings/snapshot/limits field must
agree with the parent and all other children. No collection receipt is emitted
for a failed or partial acquisition.

The summary has exactly `postgres_collection_summary_version: 1`, `kind`,
`complete: true`, `coverage_claim: "adapter-table-collection-one-source-snapshot"`,
`tables` (1–16 integer count), `rows`, `bytes`, and `receipt_sha256`. `kind`
is the receipt kind; totals derive solely from its verified observations.
No table ID, source name, path, role, version token, snapshot, query, key, value,
raw sample or per-table identifying digest appears. This is not a parity outcome.

The manifest has exactly `postgres_collection_manifest_version: 1`, `kind`,
`complete: true`, `files`, and `table_manifests`. `files` has exactly
`receipt.json` and `summary.json` digests. `table_manifests` repeats the receipt's
exact ID→child-manifest map; its separate field avoids reserved-name collisions.
All versions and complete flags require exact types, not truthy equivalents.

## Offline verification and CLI

Offline verification pins and checks exact directory membership, safe member
handles, strict/canonical JSON, metadata/content size caps, CSV header/count,
version-aware child verification, every digest, exact parent/child facts and
elapsed/limit consistency, reconstructed plan digest, totals and derived summary.
Read child receipts and hash their manifests through the same pinned handles
used for child verification. Reject mutation/substitution rather than combining
observations from different reads. Child IDs are private and path-safe; do not
walk unbounded arbitrary trees or follow links. Unknown fields and extra members
fail. A recomputed, internally consistent forged source claim is not authenticated
by offline verification; never label it source truth or qualified live support.

The live allowlist is not an offline validation dependency. Preserve source-v1's
released server-version parsing and old source/pair readers. An old valid bundle
remains readable when the live matrix changes or its server reaches end-of-life.

Add only `parison postgres collection --plan FILE --output DIR` and
`parison verify-postgres-collection DIR`, using the existing command parser,
safe errors and generated reference. Successful acquisition/verification writes
only the exact compact canonical summary JSON plus LF and exits 0. Invalid or
incomplete input/acquisition/verification exits 2 with one fixed value-free
error; acquisition stderr is exactly `parison postgres collection: invalid or incomplete collection evidence\n`
and verification stderr is exactly `parison verify-postgres-collection: invalid or incomplete collection evidence\n`.
Interruption exits 130 with the respective command prefix followed by
`: interrupted\n`. Here `\n` denotes one LF byte. Freeze command-help fixtures
before runtime changes. No new project
script and no mutation of old CLI JSON or exits.

Any failure, interruption, connection loss, limit breach, failed commit,
verification, output race or rename removes sensitive staging and publishes
no collection. Roll back an open transaction where possible; cleanup errors
must be surfaced as a fixed value-free error rather than silently claimed
successful. After successful rename ownership transfers to the caller and
staging cleanup must never remove the published destination. No live-session
resume, source pushdown, parallel acquisition, arbitrary SQL, repair, signing,
CDC or automatic cutover is included.

## Frozen adversarial and compatibility gate

Before feature integration, freeze four strict installed schemas and canonical
plan/receipt/summary/manifest byte fixtures plus unchanged child byte fixtures.
The implementation must pass all of the following:

- Plan shape/type/digest failures, 0/1/16/17 tables, 100/101 columns, ID/path
  traversal/case collisions on Windows, duplicate physical aliases, hostile
  quoted/Unicode identifiers, unknown fields, non-finite/duplicate JSON names.
- Six-table commerce and 16-table structural probe, one/last empty member,
  shared snapshot with concurrent writes after first read, conflicting DDL
  before first read, asserted pre-snapshot lock order and reordered input maps.
- Exact primary key and representation rules; all allowed types; inherited
  ownership/write privilege, superuser, `BYPASSRLS`, RLS on the final member,
  views/partitioned/inheritance/foreign/temp/unlogged tables, custom types with
  allowlisted names and unsupported source types.
- Last-table aggregate row/byte exhaustion, header-only byte exhaustion, lock
  wait, statement/wall timeout, late connection/COPY failure, cancellation,
  commit failure and failed verification/rename; no partial output or staging leak.
- Missing/swapped/rehashed child, source/snapshot/settings/limits/elapsed
  mismatch, wrong totals/plan, corrupted summary, symlinks, mutation during
  verification, existing output/race and raw-data canaries in CLI/errors.
- Offline verification with PostgreSQL stopped and Psycopg absent; frozen
  source-v1/pair-v1/dossier-v1 and all shipped CLI fixtures still pass unchanged.
- Every required matrix row in [278](278-postgresql-capability-matrix.md),
  narrow tests, `make check`, independent Standards/Spec review, quality CI and
  manual full built-wheel Python 3.11–3.14 Linux/macOS/Windows CI on the exact PR
  head. Record six-table 100k/250k totals, three cold runs and machine-specific
  time/process-tree RSS/staging bytes/source load before capacity claims.

This commit freezes design and gates only. It does not freeze schema/byte
fixtures that have not yet been authored, implement runtime behavior, or claim
any collection qualification. The next implementation step is to materialize
these schemas and positive/negative canonical fixtures, review them against
this contract, then deepen existing acquisition and offline verification seams.

## Review amendment: inheritance and function resolution

Independent live review found that `ACCESS SHARE` permits concurrent inheritance
attachment. Stronger relation locks require privileges beyond SELECT under
[PostgreSQL LOCK](https://www.postgresql.org/docs/18/sql-lock.html). Pinning a
snapshot or repeating a catalog check cannot replace base-only SQL scope. New
live collections therefore use source-v2 receipts with exact `FROM ONLY`,
truthful version-2 child-plan digests and profile
`postgresql-base-table-only-csv-v1`. The unchanged manifest-v1 and summary-v1
layouts still bind the versioned receipt bytes; no released record is relabeled.
The new derived plan and receipt have explicit `postgres-export-plan-v2` and
`postgres-source-receipt-v2` installed schemas. The initial profile
`postgresql-base-table-csv-v1` remains readable only for
its source-v1 evidence; new acquisition never emits it. Reject mixed profiles
and child receipt versions. Existing collection wire fixtures remain historical
reader compatibility examples; add separate source-v2 canonical fixtures.

Relation qualification rejects observed inheritance membership. This is not a
lifetime catalog freeze: if a child is attached later, acquisition either fails
or exports only the declared base table, never undeclared descendants. Every
count, null-marker scan and COPY must use ONLY. All built-in metadata functions
resolve under transaction-local `search_path=pg_catalog` before snapshot-taking
queries, preventing hostile libpq search paths from spoofing recorded facts.
Add live concurrent-attachment and hostile-function/search-path regressions.
This amendment precedes its runtime implementation and preserves 2.3 contracts.
Primary-source access: 30 October 2026.
