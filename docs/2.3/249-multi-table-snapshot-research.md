# Coordinated two-table PostgreSQL acquisition: research

Date and source access: 28 October 2026
Status: research for 2.3 feature 2; contract and implementation are not frozen

## Question

What can the optional reader claim when it exports `orders` and
`order_lines` from one PostgreSQL source, while keeping the core verifier
local and source-free? The [six-feature roadmap](246-six-feature-roadmap.md)
requires one source snapshot, independently verifiable table receipts, and a
coordination record that fails closed on partial or substituted output.
Feature 1's [one-table contract](247-postgresql-one-table-ingress-contract.md)
remains readable and unchanged.

## Primary-source findings and decisions

1. **Prefer one transaction and one connection for the first pair.** PostgreSQL
   `REPEATABLE READ` uses the snapshot fixed by the first query for later reads
   in that transaction. Two separate transactions can observe a commit between
   their starts. For exactly two bounded tables, one connection can count and
   copy both under one `REPEATABLE READ READ ONLY` transaction. This removes
   exported-snapshot lifecycle and worker coordination from the first pair.
   A common snapshot does not prove that application transactions preserved
   order/line business invariants. [Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

2. **Lock both named relations before the first snapshot read.** The feature 1
   reader locks its relation before catalog qualification. For a pair, acquire
   `ACCESS SHARE` on both in a stable identifier order before any catalog
   `SELECT`, `COUNT` or `COPY`; keep the locks through commit. This blocks
   concurrent DDL replacement while allowing ordinary row writes. PostgreSQL
   recommends consistent multi-object lock order to reduce deadlocks.
   Keep finite lock and transaction timeouts. A DDL or lock failure leaves no
   complete pair. [Explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html),
   [LOCK](https://www.postgresql.org/docs/18/sql-lock.html).

3. **Keep exported snapshots deferred.** `pg_export_snapshot()` lets another
   transaction import a shared view only while the exporter remains open.
   `SET TRANSACTION SNAPSHOT` must precede its first query in an appropriate
   isolation level. A token is not a durable proof and cannot coordinate
   source and target PostgreSQL instances. Parallel workers may justify this
   later if measurements show one connection cannot meet the reviewed budget.
   [Snapshot synchronization](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION),
   [SET TRANSACTION](https://www.postgresql.org/docs/18/sql-set-transaction.html).

4. **Bind the pair without promoting either receipt.** Each table needs the
   same qualified scope checks as feature 1 and its own data digest and
   receipt. A new versioned coordination record should bind the reviewed pair
   plan, exact table identities and receipt/manifest digests, common source
   transaction and snapshot, and completion. Publish the pair only after both
   counts, copies, local verifications and commit succeed. Offline verification
   can reject a missing/swapped table, changed selection or mismatched
   coordination bytes; it cannot authenticate a forged source claim with
   recomputed local digests. [COPY](https://www.postgresql.org/docs/18/sql-copy.html),
   [snapshot functions](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION).

## Threats and acceptance evidence

- A concurrent writer commits between table exports; both data files must
  reflect the one established snapshot, not a split source view.
- A relation is renamed/replaced before qualification or between tables;
  locked identities and strict metadata checks must fail closed.
- One table exceeds row, byte or time budget after the other has staged;
  interruption, cancellation or commit failure must remove the entire staged
  pair and publish no complete coordination record.
- A table, receipt or plan is substituted after publication; the offline
  verifier must detect changed local bytes and membership. Digest-valid
  forgery remains an unauthenticated adapter claim.
- The two-table test corpus should include matching source/target omissions,
  orphan lines, offsetting sums, duplicate keys and conversion drift. The
  acquisition claim alone cannot classify any of those as parity or cutover.

## Non-goals and next gate

No cross-instance snapshot equivalence, CDC, arbitrary query, parallel
exported snapshot, automated policy choice, repair, signing or cutover. Before
implementation, freeze a strict pair plan, canonical coordination bytes,
per-table receipt compatibility, total and per-table budgets, publication
layout, and a controlled concurrent-writer/DDL/cancellation corpus. Measure
source load and elapsed time on a named machine; do not infer capacity from
PostgreSQL documentation.
