# Time alignment and multi-dataset reconciliation research

Date: 15 October 2026

Status: **research recommendation**

## Precise question and boundary

What is the smallest explicit contract that lets Parison verify a coordinated migration or backfill made of several related datasets, when arrival time and extraction time can differ?

The capability should answer two separate questions without conflating them:

1. did every supplied dataset obey one reviewed event-time window and carry adequate source-owned coordination metadata; and
2. do identities, references and conserved quantities agree within and across the baseline and candidate dataset sets?

It must remain local-first and deterministic. Parison may validate strict JSON, local rows, digests and declared metadata. It must not connect to a source, advance a watermark, choose a cutoff, create a snapshot, wait for late data, infer which key is authoritative, repair an orphan, or approve a cutover. PASS continues to mean agreement under the explicit policy, not extraction truth or completeness.

All external sources below are primary specifications or official project documentation and were accessed **15 October 2026**.

## Why the two concerns belong in one release

A multi-table check without time alignment produces false discrepancies when a child export is newer than its parent export. A time-aligned collection of files without relationship checks can still PASS table-by-table while containing orphaned facts or broken totals. Migration and backfill verification therefore needs one evidence graph:

```text
source-owned coordination claim
        +
declared half-open event window
        +
local baseline and candidate artifacts
        |
        v
per-dataset parity -> identity -> references -> conservation
```

This sits directly on Parison's verification ladder: schema/input preflight, aggregate conservation, keyed or multiset parity, then portable evidence. It deepens the existing suite and comparison modules rather than adding connectors or orchestration.

## Established semantics and design consequences

### A transaction snapshot is stronger than a shared wall-clock label

PostgreSQL `REPEATABLE READ` uses one snapshot established by the transaction's first non-transaction-control statement, rather than a fresh snapshot for each query. PostgreSQL can also export a snapshot and import it into other transactions; the exported snapshot remains importable only while the exporting transaction is open ([PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html), [PostgreSQL snapshot synchronization](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION)).

BigQuery `FOR SYSTEM_TIME AS OF` reads the table version current at a constant timestamp expression, but applies only to stored BigQuery tables and fails when the requested point is outside available history ([BigQuery historical data](https://cloud.google.com/bigquery/docs/access-historical-data), [GoogleSQL query syntax](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#system_time_as_of_clause)). Snowflake distinguishes inclusive `AT` from `BEFORE`; its timestamp, offset or statement selector must be a constant expression, historical availability is retention-bounded, and timestamp interpretation can depend on the explicit timestamp type and session time zone ([Snowflake `AT | BEFORE`](https://docs.snowflake.com/en/sql-reference/constructs/at-before), [Snowflake Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)).

Apache Iceberg snapshots have unique snapshot IDs, a parent lineage, sequence numbers and creation timestamps. Its point-in-time guidance uses the snapshot log to choose the table state immediately before a requested timestamp, and requires an informative error when no prior snapshot metadata exists ([Iceberg table specification](https://iceberg.apache.org/spec/#snapshots), [Iceberg point-in-time reads](https://iceberg.apache.org/spec/#point-in-time-reads)).

**Consequence for Parison:** equal timestamps are not portable proof of a mutually consistent snapshot. A coordination declaration must state its mechanism and carry source-owned opaque tokens. Parison can compare tokens and bind their bytes; it cannot translate a PostgreSQL snapshot ID, warehouse timestamp or Iceberg snapshot ID into a universal snapshot.

### Watermarks are progress claims, not observations of wall time

Flink defines a watermark at event time `t` as an assertion that no later record with event time at or below `t` is expected. With multiple active inputs, downstream event time advances at the minimum input watermark, so one lagging input holds the combined computation back ([Flink timely stream processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/), [Flink watermark API](https://nightlies.apache.org/flink/flink-docs-stable/api/java/org/apache/flink/api/common/eventtime/Watermark.html)). Flink also documents that watermarks can be heuristic and that late events may still arrive; bounded-out-of-orderness delays the watermark by a configured maximum, while allowed lateness retains a window after its end and can produce updated late firings ([Flink built-in watermark generators](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/event-time/built_in/), [Flink window allowed lateness](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/operators/windows/#allowed-lateness)).

**Consequence for Parison:** `cutoff`, `watermark`, `lateness allowance` and `snapshot` are different policy fields. A watermark must be an explicit source-owned claim with a named interpretation. Parison must never compute completeness from file modification time, extraction completion time, maximum row timestamp or the current clock.

### Referential integrity and conservation need separate contracts

A relational foreign key says that the non-exempt child value or tuple must match a value in a referenced row; PostgreSQL describes this as maintaining referential integrity between related tables ([PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)). PostgreSQL's `NOT VALID` plus later `VALIDATE CONSTRAINT` workflow also demonstrates why acceptance of new writes and verification of historical rows are separate operations: validation scans existing rows without redefining the constraint ([PostgreSQL `ALTER TABLE`](https://www.postgresql.org/docs/current/sql-altertable.html)).

**Consequence for Parison:** relationship checks should be explicit scans over the supplied historical artifacts. Identity uniqueness, foreign-key coverage and numeric conservation are separate predicates with separate null, grouping and tolerance rules. One passing predicate must not hide another failing predicate.

## Recommended contract: `reconciliation-v1`

Add one opt-in, strict-JSON reconciliation contract without changing any released recipe or suite meaning. A reconciliation names two **dataset sets**, `baseline` and `candidate`. Each set contains the same stable logical dataset IDs; each dataset points to a local input and an existing effective Parison comparison policy. Existing keyed, multiset or aggregate parity runs first for every baseline/candidate dataset pair.

The new layer then applies one alignment policy and a closed list of relationship checks to each side independently. This is important: candidate rows must not satisfy a missing baseline parent, and baseline totals must not be netted against candidate totals. The final result reports per-dataset parity and per-side relationship outcomes before computing the overall result.

Dataset IDs and relationship IDs are stable policy identifiers, not inferred from filenames, paths, table names or values. Source paths remain runtime inputs and stay out of summary-safe output.

### Exact time-alignment policy

Use one normalized UTC interval:

```json
{
  "version": "time-alignment-v1",
  "event_window": {
    "start": "2026-09-01T00:00:00Z",
    "end": "2026-10-01T00:00:00Z",
    "bounds": "start-inclusive-end-exclusive"
  },
  "datasets": {
    "orders": {"event_time_column": "occurred_at"},
    "payments": {"event_time_column": "occurred_at"}
  },
  "coordination": {
    "mode": "source-snapshot",
    "claim_id": "september-close-4",
    "receipt_sha256": "..."
  }
}
```

The exact v1 semantics should be:

- `start` and `end` are RFC 3339 UTC timestamps with `Z`, canonicalized to Parison's existing timestamp precision. RFC 3339 defines `Z` as UTC and a numeric offset as a local-time offset; requiring `Z` removes session-time-zone interpretation from canonical policy bytes ([RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)).
- the interval is always `[start, end)`. Every non-null projected event time must satisfy `start <= t < end`. There is no configurable boundary mode in v1.
- every dataset must declare exactly one semantic timestamp column. Missing, null, naive, unparsable or out-of-window values are controlled failures. Dataset-specific windows are rejected because they make cross-dataset conservation ambiguous.
- timezone conversion and event-time derivation happen in the existing semantic projection or upstream. The reconciliation layer does not select between `created_at`, `updated_at` and business-effective time.
- `coordination.mode` is exactly one of `source-snapshot`, `watermark`, or `declared-cutoff`; unknown modes fail closed.

#### `source-snapshot`

Every dataset carries a nonempty opaque `snapshot_token` and all tokens are bound by one source-owned coordination receipt digest. Tokens may differ by dataset. Equality is required only where the declaration explicitly assigns datasets to one token domain. Parison verifies declared equality and the receipt digest; it does not parse token meaning or claim the snapshots are coherent.

This mode is preferred for database or warehouse exports taken under a documented snapshot mechanism. The receipt remains an attachment identity, not proof that the exporter used the claimed snapshot.

#### `watermark`

Every dataset carries a canonical UTC `watermark` plus a nonnegative `allowed_lateness` duration copied from the reviewed upstream policy. Eligibility requires `watermark >= end`; the set-level `effective_watermark` is the minimum dataset watermark, matching the conservative multi-input rule used by Flink. `allowed_lateness` is recorded and compared exactly across rehearsals but is not added to `end`: a watermark already expresses event-time progress under its generator's lateness strategy.

The result says `watermark_claim_sufficient` only when every declared watermark reaches `end`. It never says the files are complete. A heuristic watermark, a changed lateness policy, a missing idle-partition policy or a receipt digest change must be visible in full evidence and change the effective policy or coordination identity as appropriate.

#### `declared-cutoff`

This fallback binds a source-owned statement that extraction was intended to cover `[start, end)`, plus its digest, without a snapshot token or watermark. It is admissible for batch backfills whose source cannot expose stronger coordination. The alignment status is always `INCONCLUSIVE` with reason `coordination-not-machine-established`, even when all supplied row timestamps are in range. Dataset parity and relationships still run and report their own outcomes.

`allowed_lateness` may be recorded as planning metadata in this mode, but waiting until `end + allowed_lateness` is neither checked against the current clock nor promoted to completeness evidence. This keeps repeated execution deterministic.

### Snapshot coordination outcome

Alignment has its own three-state outcome:

- `PASS`: every row is in `[start, end)`, all required source-owned coordination fields are present and internally consistent, and the selected mode's mechanical criterion passes;
- `FAIL`: a supplied row is outside the window, a required dataset uses the wrong coordination group/token, or a watermark claim is below `end`;
- `INCONCLUSIVE`: coordination uses `declared-cutoff`, a receipt is present but its source semantics are not machine-established, or a known heuristic cannot establish the closed-world claim.

Malformed timestamps, negative durations, duplicate dataset IDs, unknown modes, missing receipt files and digest mismatches are input errors, not neutral-looking `INCONCLUSIVE` results.

## Multi-dataset checks

The v1 relationship vocabulary should remain deliberately small. It must not accept arbitrary SQL or expressions.

### Identity

`identity` declares one dataset and an ordered tuple of one or more projected columns. Its null policy is exactly `forbid` or `equal`; `ignore` is not allowed because it can hide duplicate business identities. PASS requires every identity tuple to be unique under existing canonical scalar encoding. Report duplicate counts and digests in full evidence, never raw keys in summary-safe output.

Run identity before references so an ambiguous parent key cannot make a reference appear satisfied.

### Referential coverage

`reference` declares a child dataset/column tuple and a parent identity of the same arity and semantic types. Each child tuple must match exactly one parent identity tuple. Null handling is explicit:

- `forbid`: any null component fails;
- `all-null-exempt`: the entire all-null tuple is exempt, but a partly null composite fails;
- `match-null`: null participates in canonical equality and therefore requires one matching parent identity.

No cascade, fuzzy match, coercion or inferred relationship is performed. The check reports child row count, exempt count, matched count and orphan count. Full evidence may include bounded canonical key digests; summary-safe evidence includes counts and reason codes only.

### Conservation

`conservation` declares one parent dataset, one child dataset, ordered group-key mappings, one numeric measure on each side, an operator fixed to `sum`, and the existing exact or absolute/relative tolerance policy. For every canonical group key:

```text
parent_expected(group) == sum(child_contribution(group))
```

The parent identity must make the group unique. Parent and child numeric domains, decimal scale, null behavior and tolerance are explicit and reuse existing aggregate semantics. Missing parent groups, child-only groups, duplicate parent groups, overflow, non-finite values and empty groups have distinct reason codes. A future count or multi-measure check should be a versioned addition, not an overloaded expression.

Conservation runs separately on baseline and candidate, then the existing dataset parity result establishes whether the corresponding rows/measures agree across sides. It does not infer that a difference is a legitimate late arrival.

## Concrete migration and backfill workflows

### Coordinated relational migration

An operator exports `customers`, `orders` and `order_lines` from old and new databases under source-owned repeatable snapshots. The reconciliation policy uses one monthly `[start, end)` event window, identities for all three datasets, references from orders to customers and lines to orders, and conservation from order totals to line sums.

The exporter writes local files and a receipt containing the database-specific snapshot tokens. Parison verifies receipt bytes, window membership, each old/new dataset pair, then relationships independently within old and new sets. An orphan in only the candidate is a candidate reference failure even if all three per-table comparisons would otherwise be investigated separately.

### Historical warehouse backfill

A pipeline rebuilds six months of facts and dimension keys. For each month it freezes a half-open event window and records table snapshot IDs or warehouse time-travel selectors in an extraction receipt. Parison runs one reconciliation per month; it does not silently combine months or pick the latest common timestamp.

The final month is promoted only after every dataset's upstream watermark claim reaches its month end. A rerun with a changed late-data policy has a different effective alignment policy and cannot be trended as the same rehearsal. Earlier closed months remain independently reproducible from their local artifacts and receipts.

### Ledger-style payout reconciliation

The baseline and candidate sets each contain payout headers and payout entries. `payout_id` is unique in headers, every entry references one payout, and the signed entry amount sum must equal the declared payout amount per currency and payout ID. Currency belongs in the group key; Parison never converts currencies or chooses a rounding rule.

If the processor supplies only a declared close timestamp and no machine-established snapshot or watermark, relationship checks can PASS while alignment remains INCONCLUSIVE. The overall reconciliation is therefore INCONCLUSIVE, not a cutover PASS.

### Late-arriving correction

A record with September event time arrives after the September watermark and changes an export. Parison does not patch the prior evidence. The operator produces new artifacts and a new source receipt, reruns the same policy, and catalogs the result as a new rehearsal. The old bundle remains verifiable and its PASS retains only its original, bounded meaning.

## Result and evidence semantics

Overall status is conservative:

1. any controlled input error aborts without a result;
2. otherwise any alignment, parity, identity, reference or conservation `FAIL` makes the reconciliation `FAIL`;
3. otherwise any alignment or component `INCONCLUSIVE` makes it `INCONCLUSIVE`;
4. otherwise it is `PASS`.

The full result contains the alignment policy fingerprint, receipt digests, dataset IDs, existing per-dataset policy/result fingerprints, ordered relationship results and deterministic counts. Ordering is fixed by dataset ID, check kind, then relationship ID. Canonical bytes must not depend on recipe member order, filesystem enumeration, worker scheduling, absolute paths or the current clock.

Summary-safe output excludes source paths, physical table names, column names, identity values, group keys, discrepancy samples, snapshot tokens and receipt contents. It may expose policy/result fingerprints, stable reason codes, statuses and aggregate counts. A verified bundle binds every local input digest and receipt digest but does not reinterpret either.

Released recipes, suites, results, bundles, exit codes and canonical bytes remain untouched. `reconciliation-v1` is a new opt-in artifact; old readers reject it as unknown rather than partially execute it.

## Threats and controls

1. **Timestamp theater.** Equal export timestamps can describe inconsistent database states. Require an explicit coordination mode and receipt; never infer snapshot equality from clocks.
2. **Maximum-row watermark.** The latest observed row says nothing about unseen rows. Accept watermarks only as declared source-owned claims and never derive one from data.
3. **Late-data laundering.** A generous lateness value can be used to excuse a discrepancy. Lateness changes policy identity and never converts an observed mismatch into agreement.
4. **Window-edge duplication or loss.** Closed intervals on both sides double-count boundaries; open intervals on both lose them. Fix v1 to `[start, end)` and test exact edges.
5. **Time-zone ambiguity.** Naive timestamps and session-dependent casts can shift membership. Require semantic UTC timestamps and canonical `Z` policy bounds.
6. **Orphan masking through duplicate parents.** Membership alone can pass against duplicate parent keys. Require parent identity uniqueness before reference evaluation.
7. **Null-key ambiguity.** Database and application null semantics differ. Make one of three closed reference null policies mandatory and reject partial-null composites unless explicitly covered.
8. **Cross-side netting.** Candidate surpluses can numerically cancel baseline deficits. Evaluate every invariant per side before any baseline/candidate conclusion.
9. **Floating-point cancellation.** Row order can change a naive sum. Reuse Parison's deterministic numeric domains, stable aggregation order and explicit tolerance semantics.
10. **Sensitive diagnostic leakage.** Orphan keys and financial groups may identify people or accounts. Keep samples and names out of summary-safe output; prefer counts and canonical digests in full evidence.
11. **Receipt overclaim.** A digest proves which receipt bytes were supplied, not that the source statement is true or authorized. Preserve that limitation in result language.
12. **Resource exhaustion.** Multiple large identities and joins can multiply memory/storage use. Reuse the explicit SQLite-backed keyed engine, bounded temporary storage, interruption cleanup and no automatic engine selection.

## Non-goals

- live CDC monitoring, waiting for watermarks or continuous window closure;
- database, warehouse, queue or catalog connections in core execution;
- one universal transaction or snapshot token across systems;
- clock synchronization, receipt authentication or claims that extraction is complete;
- arbitrary SQL, user expressions, transformations, joins or computed repair values;
- automatic discovery of keys, references, groupings, tolerances or lateness;
- fuzzy entity resolution, slowly changing dimension logic or temporal interval joins;
- currency conversion, allocation, rounding-rule selection or double-entry accounting certification;
- cascade simulation, orphan deletion or source repair;
- approval, deployment, rollback or cutover orchestration.

## Alternatives considered

### Only add cross-file foreign keys

This is smaller but unsafe as a migration gate because inconsistent extraction times can manufacture or hide orphans. It also misses the aggregate conservation that motivates many financial and backfill checks.

### Only add common-cutoff filtering

This verifies scope but not completeness or relational coherence. It would encourage users to interpret a timestamp-filtered PASS as a coordinated snapshot.

### Embed source connectors

Connectors could acquire snapshots directly, but would add credentials, network behavior, vendor transaction semantics and failure recovery to the zero-custody core. Keep extraction and receipt creation upstream.

### Accept arbitrary relational queries

SQL is expressive, but query dialect, optimizer behavior, collation, null semantics and nondeterministic functions would become part of Parison's compatibility surface. A closed identity/reference/conservation vocabulary is independently reproducible and reviewable.

## Recommended delivery sequence

1. Specify and fixture canonical `time-alignment-v1` and `reconciliation-v1` JSON, fingerprints and summary-safe rendering.
2. Add window preflight over existing semantic timestamps, including exact start/end edge cases and every controlled failure.
3. Add identity and reference checks using the existing memory and SQLite keyed machinery with semantic-equivalence tests.
4. Add one-parent/one-child grouped sum conservation by reusing aggregate policy and numeric code.
5. Compose existing per-dataset comparisons and the new per-side checks in the suite executor without changing legacy suite scheduling or output.
6. Add realistic relational migration, monthly backfill and payout fixtures, then qualify deterministic execution across input formats and engines.

Do not add a general graph planner, query language or connector abstraction in this release.

## Checkable promotion gate

Promote this capability from research only when all of the following are true:

- a written contract freezes `[start, end)`, UTC bound syntax, the three coordination modes, watermark eligibility, receipt binding and PASS/FAIL/INCONCLUSIVE precedence;
- JSON Schema rejects unknown fields, unknown modes/checks, naive bounds, negative lateness, duplicate IDs, mismatched key arity/types, undeclared datasets, cycles and unsupported expressions;
- fixtures cover exact window edges, pre-epoch timestamps, offsets normalized upstream, missing/null times, a watermark exactly at and just below `end`, unequal snapshot-domain tokens, missing/digest-mismatched receipts and declared-cutoff INCONCLUSIVE;
- identity/reference fixtures cover composite keys, every null policy, duplicate parents, partial-null composites, orphans on each side and deterministic bounded diagnostics;
- conservation fixtures cover negative and decimal amounts, scale, signed zero, null policy, tolerance boundaries, missing/extra groups, duplicate parents, overflow/non-finite rejection and row-order permutations;
- every check produces identical canonical bytes under recipe member reordering, input row/partition reordering, memory versus SQLite execution, repeated process execution and supported CSV/TSV/JSONL/SQLite/Parquet projections;
- at least three end-to-end fixtures model a coordinated relational migration, partitioned historical backfill and payout/ledger reconciliation, including one case where table parity passes but a relationship fails and one where all data checks pass but alignment is INCONCLUSIVE;
- summary-safe regression tests prove that paths, dataset/column names, snapshot tokens, receipt contents, keys, groups, values and samples do not escape;
- failure and interruption tests prove atomic no-overwrite publication, symlink safety and cleanup of sensitive staging and SQLite temporary state;
- all released 1.x recipes, schemas, suites, bundles, exit codes, canonical bytes and verification fixtures remain byte-compatible and readable;
- core execution performs no network access, credential handling, signing, source mutation, clock-dependent waiting, repair or remote orchestration;
- `make check` passes and built-wheel CI passes on Python 3.11–3.14 across Linux, macOS and Windows, with optional-Polars skips only when Polars is absent.

Until that gate passes, operators should export each related table under a source-owned coordinated snapshot where possible, retain the source receipt beside the artifacts, use one explicit half-open event window, and run existing per-table Parison comparisons plus separately reviewed upstream referential and conservation checks.

## Primary source list

Accessed 15 October 2026:

- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL snapshot synchronization](https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION)
- [PostgreSQL foreign-key constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [PostgreSQL `ALTER TABLE` validation](https://www.postgresql.org/docs/current/sql-altertable.html)
- [BigQuery historical data](https://cloud.google.com/bigquery/docs/access-historical-data)
- [GoogleSQL `FOR SYSTEM_TIME AS OF`](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#system_time_as_of_clause)
- [Snowflake `AT | BEFORE`](https://docs.snowflake.com/en/sql-reference/constructs/at-before)
- [Snowflake Time Travel](https://docs.snowflake.com/en/user-guide/data-time-travel)
- [Apache Iceberg table specification](https://iceberg.apache.org/spec/)
- [Apache Flink timely stream processing](https://nightlies.apache.org/flink/flink-docs-stable/docs/concepts/time/)
- [Apache Flink watermark API](https://nightlies.apache.org/flink/flink-docs-stable/api/java/org/apache/flink/api/common/eventtime/Watermark.html)
- [Apache Flink built-in watermark generators](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/event-time/built_in/)
- [Apache Flink window allowed lateness](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/datastream/operators/windows/#allowed-lateness)
- [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339)
