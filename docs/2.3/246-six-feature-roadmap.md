# 2.3 six-feature roadmap

Date: 28 October 2026
Status: working scope selected in sequence after 2.2.0; each feature contract
and acceptance fixture must be frozen before implementation

This roadmap turns the [post-2.2 direction](../2.2/244-fast-diff-and-cutover-evidence-direction.md)
into six substantial, separately reviewable capabilities. The first target is
a database migration engineer rehearsing a PostgreSQL 16→18 order/ledger
upgrade. The target, size and budget are internal hypotheses chosen through
blind review, not evidence of customer adoption. Revise them when target-user
evidence warrants it. The [primary-source ingress research](245-postgresql-ingress-research.md)
and independent threat review in the direction document constrain the first
feature.

## Six capabilities in order

1. **One-table PostgreSQL evidence ingress.** An optional, read-only reader
   exports one explicit base table and ordered columns from one bounded
   repeatable-read transaction. It publishes a separately versioned private
   source receipt, local data and a summary-safe projection. An offline verifier
   checks the preserved bundle without connecting to PostgreSQL. The receipt
   distinguishes selected-row and qualified whole-table adapter claims, never
   extraction truth. Gate: quoted identifiers, non-owner/non-`BYPASSRLS` role,
   row-security fail-closed behavior, source/local count agreement, frozen
   bytes, limits, cancellation, no-overwrite publication and hostile mutation
   tests pass against a controlled PostgreSQL instance.

2. **Coordinated multi-table acquisition.** Extend the reader to a reviewed
   `orders`/`order_lines` selection under one source snapshot, with one
   independently verifiable receipt per table and a versioned coordination
   record binding both. Changed selection, missing table, stale snapshot,
   partial export and mismatched row counts cannot produce complete coverage.
   Gate: a concurrent writer cannot split the recorded source view; all table
   bytes remain locally and source-free verification detects substitution.

3. **Fast exact partitioned difference discovery.** Add an explicit bounded
   disk-backed strategy over reviewed key ranges for local inputs. Partition
   filters may prioritize work but only completed exact checks over the
   declared scope can produce a full-scope PASS. Preserve existing comparison
   semantics and old bundle bytes; version new partition evidence. Gate:
   reference-corpus outcomes and counts match the released exact engine for
   low-difference, high-difference, skewed and all-different cases, with
   measured time, memory, disk and source load on a named machine.

4. **Selective exact difference investigation.** Revisit only verified suspect
   partitions under the same policy and input identities, produce bounded
   case-level evidence, and keep raw keys/values in an explicit sensitive
   local artifact. A summary-safe view reports counts and completion without
   exposing samples. Gate: source/input substitution, missing partitions,
   changed policy and interrupted drill-down cannot be reported as an exact
   completed result; every returned difference matches a full reference run.

5. **PostgreSQL 16→18 migration-pair rehearsal.** Combine independently
   reviewed source/target receipts, exact parity, order-line references and
   amount conservation in one local rehearsal. Cross-instance snapshot or
   cutover coordination is an explicit source-owned claim, never inferred
   from timestamps or matching row counts. Type, collation and key changes
   require reviewed policy. Gate: the two-table adversarial corpus catches
   matching omissions, stale snapshots, duplicate keys, orphan lines,
   offsetting sums, partial backfills and conversion drift without promoting
   unverifiable scope to PASS.

6. **Portable decision dossier.** Compose verified coverage, parity,
   reconciliation, exceptions and external human sign-off references into a
   separately versioned, unsigned local artifact. Workbench and CI show the
   same summary-safe result contract. Gate: offline verification reproduces
   every derived status, tampered or incomplete evidence fails closed, and
   no PASS or sign-off reference becomes automatic migration or cutover
   authorization.

The first two features establish acquisition claims before fast execution.
Features three and four accelerate exact local difference work. The pair
rehearsal uses those capabilities; the dossier follows verified evidence.
Screens, exports, refactors and tests supporting a capability do not count as
separate features.

## Shared measurement and compatibility gates

Use 100,000 and 250,000 total rows per side across the two related tables for
the first measured rehearsal, with 1,000,000 rows per side as a stretch
measurement. The first adapter enforces 300,000 rows, 1 GiB output, a
five-minute source statement limit and a ten-minute client wall cap per
export. The provisional two-table operator target is ten minutes on a named
machine. Record three cold-process runs, median and maximum elapsed time,
peak process-tree RSS, temporary disk, bytes and source load. These are
machine-specific targets, not a universal capacity guarantee.

The [direction document's corpus](../2.2/244-fast-diff-and-cutover-evidence-direction.md#first-target-and-measurable-gate)
is the shared adversarial gate. It includes same-side omissions that preserve
parity, selector and snapshot substitution, wrong scope, concurrency,
equal-count row swaps, null/empty and type boundaries, relation failures,
forged digests and interruption. Each feature freezes its own wire schema,
canonical bytes and negative fixtures before runtime changes.

Preserve released recipes, schemas, bundles, exit codes, canonical bytes and
CLI JSON. Core comparison and verification stay offline and zero-custody;
optional acquisition owns network and credentials outside that core. Summary
outputs exclude source names, queries, paths, tokens, keys, values and raw
samples. Publication remains deterministic, atomic, no-overwrite and
symlink-safe with sensitive staging cleanup. A source receipt is inspectable
adapter evidence, not authentication of the database or approval of policy.

For each feature, run narrow tests and `make check`, obtain independent
Standards/Spec review, push one green scoped PR to `develop`, and require the
exact-head full built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix when
CLI, schema, packaging or platform behavior changes. Do not open a 2.3
release candidate until all six substantial features are integrated and the
combined train passes [RELEASING.md](../../RELEASING.md). Release merge, tag
and publication require a separate release decision.

## Deferred

Heterogeneous warehouse connectors, CDC monitoring, arbitrary SQL, source
pushdown that changes exact semantics, approximate or sampled full-scope PASS,
remote orchestration, embedded credentials in the verifier, automatic repair,
signing and automatic cutover are outside 2.3. Reconsider a boundary only with
evidence and a versioned contract.
