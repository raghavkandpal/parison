# PostgreSQL 16→18 rehearsal: primary-source findings

Date and source access: 29 October 2026
Status: design input for feature 5; implementation and qualification pending

## Question and decision

How can a migration engineer combine two independently reviewed PostgreSQL
pair exports, exact local differences and order/line reconciliation without
mistaking equal rows for complete migration coverage? The
[six-feature roadmap](246-six-feature-roadmap.md) requires one local rehearsal,
not a new migration runner. Reuse the pair verifier, partition discovery,
selective investigation and released identity/reference/conservation checks.
Freeze a new composition contract without reinterpreting their old formats.

The research conclusion is to bind reviewed scope and the exact source and
target acquisition evidence before evaluating parity. Treat cross-instance
coordination as a separately declared source-owned claim. Matching counts,
timestamps, snapshot strings or local digests cannot establish it. Report the
claim boundary explicitly even when the mechanically checked result is PASS.

## PostgreSQL facts and consequences

1. **16→18 can be tested directly.** PostgreSQL permits major upgrades without
   installing every intervening version, but requires reading intervening
   release notes and testing application compatibility. Physical data
   directories are not a logical migration method. For this feature's
   controlled fixture, use two disposable clusters and an operator-run logical
   dump/restore; it is repeatable without making Parison own the upgrade.
   [Major upgrade guidance](https://www.postgresql.org/docs/18/upgrading.html).

2. **Use the target-version dump tools.** PostgreSQL 18 `pg_dump` can read
   PostgreSQL 16; dumping newer servers with older-major clients is rejected.
   Cross-version use benefits from quoted identifiers. A dump is consistent
   for one database, and archive formats restore through `pg_restore`.
   Restores execute source-chosen SQL, so this gate must use a synthetic,
   controlled fixture. A successful restore alone is no parity or coverage
   assertion. Record exact server/client versions and command completion in
   the operator evidence; do not import dump execution into the offline core.
   [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html).

3. **Independent snapshots are not a shared cutover.** Repeatable read fixes
   the view at the first query in each transaction. Starting transactions at
   similar times does not synchronize their views. An exported snapshot is
   importable only while its exporting transaction remains open; import must
   occur before the importing transaction's first query. These mechanisms
   coordinate database sessions, not independently migrated clusters. The
   cross-cluster conclusion is a design inference from those documented
   mechanisms. Keep each pair's internal snapshot check, and require an
   explicit external claim binding both exact pair identities for any claimed
   migration point. Absent or unestablished coordination remains INCONCLUSIVE.
   [Snapshot synchronization](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION),
   [SET TRANSACTION](https://www.postgresql.org/docs/18/sql-set-transaction.html).

4. **Collation is not byte identity.** A collation affects ordering and
   character operations; nondeterministic collations can treat different
   byte strings as equal, including case, accent or Unicode-normalization
   variants. Local exact parity must retain the reviewed recipe's string
   semantics and integer partition keys; it must not adopt either server's
   equality rules silently. Include distinct Unicode and case values in the
   corpus, with explicit changed-policy rejection where a normalization or
   key change was not reviewed.
   [Collation support](https://www.postgresql.org/docs/18/collation.html).

5. **A refreshed collation version is not proof of repaired indexes.** Provider
   version changes can invalidate indexes. PostgreSQL documents rebuilding
   affected objects before refreshing the recorded version; refresh itself
   does not verify that rebuilding happened. Therefore local row agreement
   cannot certify index correctness, database collation health or application
   behavior. Keep those as operator responsibilities and explicit non-goals.
   [ALTER COLLATION](https://www.postgresql.org/docs/18/sql-altercollation.html).

6. **Money and timestamps require explicit semantics.** PostgreSQL `numeric`
   is exact while floating types are inexact; constrained numeric scales can
   round values on assignment. Keep amount conservation on reviewed integer
   or scaled-decimal domains, with exact comparisons in the first fixture.
   Floating-point acquisition remains outside the existing reader allowlist:
   rejection is the correct gate, not a new implicit conversion.
   [Numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html).
   Timestamps with and without timezone have different semantics; timezone
   output depends on the session. Retain the adapter's fixed formatting and
   use explicit aware instants for event-time policies. Exercise equivalent
   offsets, changed instants, precision loss and naive-time rejection.
   [Date/time types](https://www.postgresql.org/docs/18/datatype-datetime.html).

7. **Intervening incompatibilities matter to the gate.** PostgreSQL 17 renamed
   ICU locale catalog columns and changed interval parsing. Avoid introducing
   an unversioned catalog query or expanding admitted types merely to report
   metadata. [PostgreSQL 17 migration notes](https://www.postgresql.org/docs/17/release-17.html).
   PostgreSQL 18 changed timezone-abbreviation precedence and CSV end-marker
   behavior, and introduced virtual generated columns. Preserve the current
   adapter's generated-column exclusion and COPY settings. Include literal
   `\.` text, quoted/empty text and explicit timezone values in the controlled
   fixture rather than relying on a happy-path numeric-only export.
   [PostgreSQL 18 migration notes](https://www.postgresql.org/docs/18/release-18.html).

8. **Rows do not establish replication readiness.** Logical replication does
   not copy DDL or sequence state. A two-table local rehearsal therefore cannot
   certify future identifier allocation, complete schema migration or CDC
   catch-up. A lagged or partial backfill is a negative data fixture, not a
   request to add replication orchestration. These exclusions remain visible
   when reporting the result.
   [Logical replication restrictions](https://www.postgresql.org/docs/18/logical-replication-restrictions.html).

## Contract consequences to freeze before implementation

- Verify each unchanged pair bundle, then bind its reconstructed reviewed
  acquisition-plan identity and exact manifest identity to the new rehearsal
  declaration. A plan derived only from the supplied receipt cannot serve as
  independent scope review. Bind the source major version to 16 and target
  major version to 18 for this named workflow.
- Bind exact policy identities for both logical tables and their relationship
  declaration. Reuse explicit key, normalization, null, decimal and timestamp
  semantics; no inferred rename, widening, rounding, tolerance or exclusion.
- Preserve parity and relationship outcomes separately. Run order identity,
  line identity, line-to-order references and per-order amount conservation on
  each side. A database-wide total cannot substitute for per-order sums, and
  conserved sums cannot substitute for exact line parity.
- Distinguish complete adapter coverage of the reviewed selections from
  extraction truth and coordinated migration-point claims. Exact reviewed
  pair bindings detect stale/substituted evidence; they cannot authenticate a
  fully forged claim or discover omitted rows that every upstream claim also
  omits. Such unverifiable scope must never become an unconditional PASS.
- Reuse FAIL-before-INCONCLUSIVE reduction. Malformed, mutated or mismatched
  input is an input error; an established discrepancy is FAIL; unavailable
  coordination/coverage stays INCONCLUSIVE when no failure supersedes it.
- Publish canonical private evidence and a closed summary-safe projection
  atomically, with no overwrite or symlink traversal. Offline verification
  must recompute all derived outcomes from retained bound evidence, not trust
  a status plus recomputed hashes. Preserve source-free operation and all
  released exit codes and wire bytes.

## Adversarial and measured gate

Use a synthetic PostgreSQL 16 `orders`/`order_lines` fixture, operator-frozen
writes, PostgreSQL 18 dump/restore, and the existing read-only pair acquisition
on both instances. Record the independently reviewed plans before acquiring.
Capture exact versions and the external fixture's freeze/restore claim.
Evaluate locally, remove or stop the source instances, then verify again.
This controlled exercise supports a rehearsal claim only; it is not evidence
of production coordination or customer adoption.

| Mutation or boundary | Required observation |
| --- | --- |
| Complete golden pair, reviewed policies and bound coordination claim | Exact parity and every relationship agree under the declared claim |
| Matching omission on both sides | Parity may agree; changed reviewed scope or exact binding is rejected, and unproven intended coverage is not promoted |
| Stale pair, swapped selector, changed snapshot or source identity | Reviewed binding mismatch is rejected even with internally valid digests |
| Duplicate parent/line key or equal-count ID replacement | Identity or exact parity fails; counts alone cannot pass |
| Orphan line or partially null reference tuple | Reference fails independently on the affected side |
| Amounts offset across different orders | Per-order conservation fails despite unchanged global sum |
| Offsetting line changes within one order | Exact line parity fails even when per-order conservation agrees |
| Tombstone, one-sided omission, incomplete backfill or simulated CDC lag | Exact parity fails; no implicit exclusion/window broadening |
| Null/empty, Unicode/case, decimal scale loss, timestamp drift | Reviewed scalar behavior is preserved; real drift fails or unsupported input is rejected |
| Unsupported float, unreviewed key/type/column change | Fail closed; never invent a conversion policy |
| Missing child/file/partition, forged outcome, modified source bytes | Verification rejects or recomputes; hashing alone is insufficient |
| Cancellation, over-budget run, symlink/no-overwrite collision | No complete publication; sensitive staging removed |
| Summary and CLI errors | No names, paths, queries, tokens, keys, values or samples |

Retain the roadmap's 100,000 and 250,000 total rows per side, three fresh-process
runs, median/maximum time, peak process-tree RSS, temporary disk, bytes and
source-query/load accounting on a named machine. Time acquisition plus local
rehearsal and verification, with the ten-minute target reported as a provisional
machine-specific observation. A one-million-row stretch does not replace the
mandatory smaller gates. Qualify narrow tests, canonical byte fixtures,
independent Standards/Spec review and exact-head built-wheel CI before merge.

## Threats and non-goals

Threats include receipt laundering, paired omissions, plausible stale evidence,
policy substitution, equality changes from collation/coercion, raw-data leaks,
resource exhaustion and interrupted publication. Stronger local binding helps
detect substitution but does not authenticate the source or an external claim.

No database writes, dump/restore execution, credential custody, live CDC,
automatic snapshot synchronization, schema repair, index certification,
sequence verification, arbitrary SQL, new connector, automatic policy approval,
signing or cutover authorization belongs in this local feature. The portable
decision dossier remains feature 6. All six capabilities stay together before
the 2.3 release decision.
