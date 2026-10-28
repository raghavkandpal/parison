# PostgreSQL evidence ingress: primary-source findings

Date and source access: 28 October 2026
Status: research for post-2.2 step 1; no runtime contract or release commitment

## Question and existing boundary

Can one optional PostgreSQL reader produce local data and an inspectable
snapshot/coverage receipt without changing Parison's offline verifier? The
[post-2.2 proposal](../2.2/244-fast-diff-and-cutover-evidence-direction.md)
places credentials and network access in an adapter outside the core. The
[agent contract](../../AGENTS.md) keeps core execution local, strict-JSON and
zero-custody. A source receipt is a claim by the acquisition process, not proof
that the database returned all intended rows or that extraction was truthful.

## PostgreSQL facts and design consequences

1. **One-session snapshot first.** In PostgreSQL `REPEATABLE READ`, queries in
   one transaction see the snapshot established by its first non-transaction
   control statement; later commits by other transactions do not enter that
   view. A single read-only transaction can therefore bind discovery, a count
   and an export to one server snapshot. It is still snapshot isolation, not a
   proof of application-level business consistency or of equivalence to a
   snapshot on another system. Use one connection for the first adapter, and
   record transaction isolation and completion in the private receipt.
   [Transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html),
   [SET TRANSACTION](https://www.postgresql.org/docs/18/sql-set-transaction.html).

2. **Exported snapshots are a later coordination tool.** `pg_export_snapshot()`
   returns an identifier available for import only while the exporting
   transaction remains open. Import with `SET TRANSACTION SNAPSHOT` must occur
   at the start of a `REPEATABLE READ` or `SERIALIZABLE` transaction, before
   its first query or `COPY`. This can coordinate several PostgreSQL sessions,
   but an identifier alone is not a durable snapshot or a portable cross-system
   timestamp. The first adapter need not export one. If later partition workers
   use it, keep the exporter open until imports complete and test stale tokens.
   [Snapshot functions](https://www.postgresql.org/docs/18/functions-admin.html),
   [SET TRANSACTION](https://www.postgresql.org/docs/18/sql-set-transaction.html).

3. **Stream only generated reads.** `COPY (SELECT ...) TO STDOUT` sends data
   over the client connection and returns `COPY count` on success. `COPY TO`
   also accepts a table name; its direct-table behavior differs for views,
   partitioned tables and inheritance children. A generated, schema-qualified
   `SELECT` over explicit columns is therefore easier to bind to a declared
   scope than generic SQL. Never accept arbitrary query text: PostgreSQL's
   `COPY (query)` grammar also admits data-modifying commands with `RETURNING`.
   Never use server file or `PROGRAM` variants. Compare the successful COPY
   count with locally parsed rows, record exact output bytes/digest, and treat
   missing completion as incomplete. `COPY count` proves rows sent by that
   command, not full-table coverage.
   [COPY](https://www.postgresql.org/docs/18/sql-copy.html),
   [protocol completion tag](https://www.postgresql.org/docs/18/protocol-message-formats.html).

4. **Read-only needs defense in depth.** PostgreSQL read-only transactions
   disallow ordinary changes to non-temporary tables, but the manual calls
   this a high-level read-only mode and says it does not prevent all disk
   writes. Require a dedicated role with schema `USAGE` and only needed
   table/column `SELECT` privileges, plus `BEGIN ... READ ONLY`; generate
   simple `SELECT` statements with no caller SQL, functions or lock clauses.
   `SELECT FOR UPDATE/SHARE` would require more privilege and is outside scope.
   [SET TRANSACTION](https://www.postgresql.org/docs/18/sql-set-transaction.html),
   [schema privileges](https://www.postgresql.org/docs/18/ddl-schemas.html),
   [SELECT](https://www.postgresql.org/docs/18/sql-select.html).

5. **Row security can narrow coverage silently.** `COPY TO` observes the
   relevant row-security `SELECT` policies. PostgreSQL's `row_security=off`
   does not bypass them; it raises an error where a policy would filter rows,
   except for roles that already bypass every policy. Use this fail-closed
   setting for a full-table coverage claim. A deliberate policy-visible export
   needs a different explicit scope claim and cannot become whole-table PASS.
   [COPY](https://www.postgresql.org/docs/18/sql-copy.html),
   [row_security setting](https://www.postgresql.org/docs/18/runtime-config-client.html),
   [row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).

6. **Budgets belong on both sides of the connection.** Server
   `statement_timeout` limits each statement, `lock_timeout` limits each lock
   wait and `idle_in_transaction_session_timeout` limits an idle open
   transaction. Use finite server settings together with client wall-clock,
   byte and row budgets; a timeout or cancellation must leave no completed
   receipt or published output. PostgreSQL exposes query cancellation, but
   cancellation should still close or roll back the adapter transaction.
   `lock_timeout` at or above `statement_timeout` adds little. Long-lived
   snapshots can burden operational sources, so record elapsed time and
   incomplete work rather than hiding it.
   [Client connection defaults](https://www.postgresql.org/docs/18/runtime-config-client.html),
   [cancellation function](https://www.postgresql.org/docs/18/functions-admin.html).

7. **Identifiers and output bytes are policy-sensitive.** Quoted PostgreSQL
   identifiers preserve case and double embedded quotes; unquoted identifiers
   fold case, and names beyond the server's identifier limit can truncate.
   Resolve declared schema/table/column names exactly and quote each
   identifier separately, with an empty or trusted `search_path`. Do not
   interpolate user text as SQL values or expressions. `COPY` output depends
   on session encoding and formatting settings; datetime output depends on
   `DateStyle`/`TimeZone`, interval output on `IntervalStyle`, and floating
   text on `extra_float_digits`. Freeze the supported source types and session
   settings before promising repeatable local bytes. PostgreSQL CSV has
   distinct quoted-empty versus unquoted-NULL behavior that must survive
   parsing. The first contract should choose explicit UTF-8, CSV options and
   an allowlisted scalar projection, then byte-fixture the result.
   [Lexical structure](https://www.postgresql.org/docs/18/sql-syntax-lexical.html),
   [schema search path](https://www.postgresql.org/docs/18/ddl-schemas.html),
   [COPY formats](https://www.postgresql.org/docs/18/sql-copy.html),
   [datetime output](https://www.postgresql.org/docs/18/datatype-datetime.html),
   [format settings](https://www.postgresql.org/docs/18/runtime-config-client.html).

## Narrow first contract to freeze

Use one explicitly selected PostgreSQL table and explicit ordered columns,
one connection and one `REPEATABLE READ READ ONLY` transaction. Record a
private source descriptor, server version, isolation and session settings,
selected relation/columns, exact generated selection, complete `COPY count`,
local parsed row count, output byte count and SHA-256, elapsed time and each
applied budget. Keep credentials, connection strings, source names, query text,
snapshot token and raw values out of summary-safe evidence. A separate
summary may contain only opaque bindings and status/count totals. Publish
locally only after the transaction and file complete and all checks pass;
verify receipt and output offline without connecting to PostgreSQL.

The receipt should distinguish **server-visible selected rows** from
**whole-table coverage**. Whole-table coverage requires an unfiltered
generated selection, successful row-security fail-closed behavior, no
exclusions or truncation, and completed source/local count agreement. These
are still adapter claims, not extraction truth. Version the receipt separately
from released dataset manifests, reconciliation receipts and bundle schemas.

## Threats, acceptance evidence and non-goals

- Threats: leaked DSN/credentials in errors or logs; unsafe SQL identifiers;
  hostile `search_path`; RLS omission; view/function side effects; format and
  type drift; stale exported snapshots; timeout after partial local output;
  destination symlinks; source load from `COUNT` plus export; long-lived MVCC
  snapshots; forged receipt with recomputed local digests.
- Acceptance corpus: table renamed or changed during review; quoted names and
  long identifiers; null versus empty CSV; Unicode/decimal/timestamp
  normalization; RLS; partitioned table and view rejection; zero rows; output
  byte/row limit; server timeout; client cancellation; broken connection;
  symlinked destination; post-publication source removal; tampered receipt;
  source-free verification. Test a controlled PostgreSQL instance with a
  concurrent writer to prove the one-transaction snapshot claim.
- Non-goals for the first adapter: arbitrary SQL, multiple databases,
  cross-system snapshot equivalence, CDC, parallel snapshot export, automatic
  schema conversion, automatic policy approval, repair, signing, or cutover.
  Benchmark table size, source load and run budget on a named machine before
  claiming useful capacity; no production access is needed for the first
  contract test.
