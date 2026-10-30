# N-table acquisition: contract prerequisites and handoff

Date and primary-source access: 30 October 2026
Status: research checkpoint; no runtime or frozen wire contract

## Findings and design consequences

PostgreSQL `ACCESS SHARE` conflicts with `ACCESS EXCLUSIVE`, while ordinary
writers use `ROW EXCLUSIVE`. Acquire the former for every reviewed relation
before reading the shared snapshot: this blocks conflicting DDL without
pretending to stop ordinary writes. It does not block every schema-related
operation. PostgreSQL recommends consistent lock order to avoid deadlocks;
ordering reduces one deadlock mechanism, not every possible source conflict.
[Explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html).

Repeatable read establishes its snapshot at the first non-transaction-control
statement that needs it. Preserve the current pair reader's sequence: configure
transaction, lock all tables, then run metadata/count/COPY reads. A new catalog
query inserted before the locks could establish the snapshot prematurely.
Test actual statement ordering and concurrent DDL rather than assuming `BEGIN`
anchors the snapshot. Cross-instance equality remains a source-owned claim.
[Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

RLS can hide rows; owners, superusers and `BYPASSRLS` roles have special bypass
behavior. `row_security=off` causes an error when a query would apply a policy;
it does not disable policy enforcement. Preserve a dedicated non-owner,
non-superuser, non-`BYPASSRLS` role and fail closed for every table. Successful
count/COPY agreement remains adapter evidence for the declared selection,
not independent proof of extraction truth.
[Row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).

## Existing implementation to deepen

`postgres_ingress._lock_tables` already sorts `(schema, table)` tuples and
quotes both identifier components before taking `ACCESS SHARE` locks.
`postgres_pair.export_postgres_pair` configures one read-only repeatable-read
transaction, locks both tables before `_acquire_table`, decrements shared row
and byte allowances, compares snapshot facts, and commits before publication.
The collection should reuse these seams while retaining released pair readers.

Keep deterministic relation lock order separate from caller table order and
public opaque IDs. Reject duplicate physical relations under different aliases;
freeze exact identifier ordering and equivalence rules before implementation.
Do not resolve names using an unreviewed search path or caller SQL.

## Budgets and publication

The roadmap's 1–16 tables is a proposed scope cap, not measured capacity.
Keep explicit per-table and collection totals for rows and emitted bytes, one
whole-operation monotonic deadline, bounded lock wait and statement timeouts,
and bounded private staging. Repeated per-table timeouts must not multiply the
collection wall budget. Existing 2.3 limits remain unchanged; new caps require
versioned validation and measurements. Include local verification/publication
in the declared wall-budget boundary, or state a separately bounded phase.

Commit and all receipt/data verification must succeed before one atomic
no-overwrite installation. A failed final table, commit, verification or rename
leaves no published collection and removes private staging. Never resume a
terminated acquisition transaction; later recoverability concerns immutable
local evidence only. Core verification remains offline and credential-free.

## Decisions to freeze next

- Exact table ID grammar, duplicate-relation policy and deterministic lock order.
- Per-table versus collection row/byte limits, staging allowance and deadline phases.
- Supported version/capability matrix, closed table/column shapes and role checks.
- Collection plan/receipt/summary/manifest versions and child identity bindings.
- Failure classification, value-free errors, cancellation and cleanup boundaries.

## Adversarial contract gate

Use a six-table commerce fixture and an optional 16-table cap probe. Reorder
caller plans while asserting identical lock order; include quoted/Unicode names,
alias duplicates, concurrent writers, conflicting DDL before the first read,
RLS on a late member, a changed owner/role, empty tables and substituted receipts.
Exercise aggregate exhaustion on the final member, blocked lock timeout,
wall cancellation, broken COPY, commit failure, symlinked output, interruption
and existing-output rejection. Verify all-or-nothing publication, private
staging cleanup, shared snapshot facts and offline replay after server shutdown.
These are planned checks, not claims of completed qualification.

## Copy-ready continuation

Continue Parison 2.4 from the current clean `develop` after this research PR.
Research began at `d99f9f283c82b5040684c1068fdd0d6b4ff41a0f`; 2.3.0 is released
at tested main/tag commit `a2884534d3ffa7364e3344dc3d514aa775ac79a9`.
Start with `make context`; read AGENTS.md, ignored AGENTS.local.md,
docs/CURRENT.md, roadmap 275 and this note. Freeze feature 1's bounded collection
contract and explicit PostgreSQL version/capability matrix before runtime edits.
Preserve released pair/dossier contracts, standalone CLI aliases, canonical bytes
and local-first boundaries. Retain 16→18 regression replay; broader live pairs
need explicit qualification. All ten 2.4 capabilities must integrate and qualify
before a candidate; releases need a separate decision. No 2.4 runtime work or
feature qualification has started. Check usage and stop near 95% with a handoff.
