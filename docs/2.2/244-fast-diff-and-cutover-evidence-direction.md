# Post-2.2 direction: fast differences with defensible cutover evidence

Date and primary-source access: 27 October 2026
Decision update: 28 October 2026
Status: sequence selected by the user; first target and gates chosen through an
independent blind review; implementation contracts and release commitment pending

## Decision proposed

Aim for Parison to be the best independent verification product for high-stakes
data changes. It should answer both questions in one workflow:

1. **Where do source and target differ, quickly and precisely?**
2. **What was actually checked, under which policy and snapshot, and is the
   evidence sufficient for a human cutover decision?**

The first requires practical access to large live datasets and efficient
difference discovery. The second requires complete coverage accounting,
explicit semantics, reproducible results and portable evidence. Neither can be
a substitute for the other. A sampled or approximate pass must state its
limited coverage and cannot become a full-scope PASS.

This extends the existing [product direction](../0.15/104-product-direction-and-release-arc.md)
and follows completion of the accepted [2.2 train](232-accepted-roadmap.md).
It does not change the released 2.2 contract or authorize a cutover.

## First target and measurable gate

The first target user is a database migration engineer rehearsing an upgrade
of an order and ledger service from PostgreSQL 16 to PostgreSQL 18. The first
end-to-end pair is two independently operated PostgreSQL instances, with
`orders` and `order_lines` as the related-table workflow. This is an internal
product hypothesis, not observed customer demand. It tests a real migration
without adding a second connector or silently equating the two instances'
snapshots. Heterogeneous warehouse migration and CDC remain later candidates;
they add conversion and coordination questions before this first evidence
boundary is proven.

Start acquisition with one explicitly selected table, ordered columns and one
read-only repeatable-read transaction. The two-table rehearsal is the later
integration gate. The adapter may claim only the source-visible selected rows
and the local bytes it emitted; offline verification can check receipt/output
consistency but cannot authenticate the source or prove extraction truth. See
the [PostgreSQL ingress research](../2.3/245-postgresql-ingress-research.md)
for primary-source snapshot, row-security and `COPY` constraints.

Use 100,000 and 250,000 total rows per side across the two related tables for
the first measured rehearsal. Measure 1,000,000 rows per side as a stretch
case, not an initial capacity claim. The first adapter must enforce explicit
per-export guards of 300,000 rows, 1 GiB of output and five minutes of source
statement time, plus a ten-minute client wall cap; limit breaches produce no
complete output. A provisional operator target is at most ten minutes for the
250,000-row two-table rehearsal on a named machine. Report three cold-process
runs with median and maximum elapsed time, peak process-tree RSS, temporary
disk, bytes read, and source query/load observations; record CPU, RAM, storage,
PostgreSQL and Python versions before interpreting results. Revise the target
after measurement. The existing
[nine-case mixed-mode 100k benchmark](../../benchmarks/results-2026-10-10-suite-concurrency-mixed-100k.json)
measures local suite execution only, not acquisition or this migration pair.
Its one-, two- and four-job results (17.278s/264 MiB, 10.288s/572 MiB and
6.384s/about 1.0 GiB) are machine-specific context, not a speed promise.

The acceptance corpus must include a golden complete export and mutations
that can otherwise create a misleading full-scope PASS: the same rows omitted
on both sides; missing file or partition; wrong predicate, window, selector or
snapshot; a swapped selector over unchanged bytes; concurrent writes; an
unexpected empty result; equal totals with swapped, duplicated or missing
IDs; duplicate keys; null versus empty CSV; decimal, float, timestamp,
timezone and Unicode boundaries; renamed columns; tombstones and partial
backfills; orphan lines, duplicated parents, partial-null references and
offsetting grouped sums; interrupted or over-budget reads; leaked raw data;
and digest-valid forged PASS receipts. Matching omission on both sides may
still produce parity PASS, so coverage remains unproven unless an independently
reviewed closed scope and source-side receipt support the claim. The corpus
must keep extraction truth and cross-instance snapshot equivalence upstream.

## Why broaden the boundary

Parison already has an unusually strong local evidence foundation: explicit
policy, deterministic comparisons, reconciliation, verification-first derived
evidence and portable bundles. The adoption gap is getting complete,
well-scoped, repeatable data from operational systems into that foundation and
finding differences fast enough for large migrations.

The adjacent products show the expected workflow. Datafold advertises
cross-database, row-level differences with UI, API and CI access. AWS DMS can
validate source and target rows during full load and CDC, while documenting
requirements such as suitable keys and additional source/target query load.
These are vendor claims and contracts, not independently reproduced Parison
benchmarks. Parison should differentiate through explicit coverage and
independently verifiable claims as well as useful speed.

Sources: [Datafold Data Diff](https://www.datafold.com/data-diff/),
[AWS DMS validation](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html).

## Product architecture

Keep the deterministic verifier and released bundle formats as the trust core.
Add optional, separately versioned acquisition and fast-execution components:

```text
read-only source adapters -> snapshot and coverage receipt
                          -> fast partitioned difference discovery
                          -> exact policy evaluation and verified evidence
                          -> investigation and cutover dossier
```

- **Acquisition:** opt-in read-only adapters own credentials and network access
  outside the core. Their receipts declare source identity, query/selection,
  snapshot semantics, coverage, exclusions and limits. A receipt is an
  inspectable source claim, not proof that extraction was truthful.
- **Execution:** choose explicit memory, disk or source-pushdown strategies.
  Each strategy must preserve the same comparison semantics and reconcile to
  the same outcome on a reference corpus. Fast filters can locate suspect
  partitions; only completed exact checks over declared scope support a full
  PASS.
- **Evidence:** retain policy and snapshot fingerprints, per-partition
  completion, interrupted/unknown work, input identity and canonical
  verification. Show whether a failure is a data difference, incomplete
  acquisition, policy mismatch or unverifiable scope.
- **Experience:** one workflow takes a user from source/target setup to a
  reviewed plan, bounded run, actionable diff and portable dossier. CI and
  Workbench expose the same result contract.

PostgreSQL is the selected first adapter because its repeatable-read and
exported-snapshot mechanisms are documented. The first version should prove
one reproducible snapshot and a controlled read budget before adding another
database. Cross-system snapshot equivalence must be represented as an explicit
coordination claim, never inferred from similar timestamps.

Sources: [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html),
[PostgreSQL exported snapshots](https://www.postgresql.org/docs/18/functions-admin.html).

## Selected sequence after 2.2

The [2.3 six-feature roadmap](../2.3/246-six-feature-roadmap.md) expands
evidence ingress into features 1–2, fast exact differences into 3–4, the
migration-pair rehearsal into 5 and the dossier into 6. The four stages below
remain the product sequence, not four separate release credits.

1. **Evidence ingress:** freeze a source receipt and coverage contract; build
   one read-only PostgreSQL acquisition path. Preserve offline verification of
   everything it emits.
2. **Fast exact diff:** qualify partitioning and selective drill-down against
   existing deterministic semantics, then publish machine-specific accuracy,
   time, memory, I/O and source-load evidence. Include large low-difference
   and high-difference cases.
3. **Migration-pair rehearsal:** exercise the chosen PostgreSQL 16→18
   order/ledger pair with honest cross-instance coordination and explicit
   conversion policy. Include missing keys, collation
   and type changes, partial backfills, CDC lag, interruption and stale
   snapshots in the acceptance corpus.
4. **Decision dossier:** combine explicit coverage, parity, reconciliation,
   exceptions and human sign-off references without turning PASS into
   automatic approval.

Each step needs a frozen contract, byte fixtures, hostile-input tests,
cross-platform gates and a realistic end-to-end migration. Revisit the first
pair when actual target-user evidence differs from this blind-review hypothesis;
do not optimize for connector count.

## Threats and non-goals

- Credentials and network access introduce a new security boundary. Keep them
  out of the verifier, narrow adapter permissions, and prevent credentials,
  queries, source names and raw values from entering summary-safe evidence.
- Long-lived snapshots and pushdown queries can burden operational sources;
  expose budgets, cancellation and incomplete status instead of hiding work.
- Hash shortcuts, sampling, approximate statistics and eventual consistency
  can misstate coverage. They may guide investigation but cannot silently
  satisfy an exact full-scope gate.
- Connector breadth, orchestration, automatic repair and automatic cutover are
  not initial goals. They can be reconsidered only after one complete workflow
  demonstrates both useful speed and trustworthy evidence.
- LocalStack is a possible test environment for a future AWS adapter, not a
  product boundary or prerequisite.

### Independent credential and snapshot review

An independent review on 28 October 2026 narrowed the first contract further:

- Matching `COUNT` and exported row counts under one repeatable-read snapshot
  establish agreement for the generated selection, not proof that it covered
  every intended row. A whole-table adapter claim requires a reviewed closed
  scope, an unfiltered base-table selection, `row_security=off` fail-closed
  behavior and a dedicated non-owner role without `BYPASSRLS`. Otherwise the
  receipt must state only source-visible selected-row coverage.
  [PostgreSQL row security](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).
- Freeze separate private receipt and summary-safe result field allowlists.
  Keep connection details, source names, queries, snapshot tokens and values
  out of the latter and out of errors, logs and Workbench responses. Stable
  hashes of predictable identifiers are pseudonymous, not confidential.
- Generate only a quoted, schema-qualified `COPY (SELECT ...) TO STDOUT` over
  an explicit base table and columns. Caller SQL, functions, views and
  partitioned relations are outside the first contract. A SELECT-only role
  and `READ ONLY` transaction are both required; neither is a substitute for
  the other. [PostgreSQL COPY](https://www.postgresql.org/docs/18/sql-copy.html),
  [read-only transactions](https://www.postgresql.org/docs/18/sql-set-transaction.html).
- Publish a complete result only after successful COPY, count/byte/digest
  checks, transaction completion and verified atomic installation. Timeout,
  cancellation, broken connection, limit breach or symlinked output must
  leave no published result and clean sensitive staging.

## Roadmap decision gate

The first user, migration pair, provisional table sizes, run budget and
accuracy/coverage corpus are selected above. Independent credential and
snapshot review is recorded above. The next gate is to freeze the evidence
ingress contract with those corrections, then prove one PostgreSQL table can
be exported under a bounded read-only snapshot and verified offline without
weakening released formats.
The success criterion is a user completing a realistic migration rehearsal
faster than their current process while being able to explain and independently
verify exactly what the result covers.
