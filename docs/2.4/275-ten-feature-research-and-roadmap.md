# 2.4.0: ten-feature migration verification workbench

Date and primary-source access: 30 October 2026
Status: researched proposal; ten-feature release boundary requested by owner;
individual implementation contracts remain to be frozen

## Product decision

Broaden the PostgreSQL rehearsal into a complete local migration project:
multiple related tables, explicit representation review, backfill coverage,
recoverable exact execution, cross-table invariants, repeated decision evidence,
and an accessible Workbench path. Keep **all ten substantial capabilities in
one 2.4.0 release**. No individual feature is a release candidate. A smaller
train requires an explicit owner scope decision, not quietly counting screens,
refactors, tests or documentation as features.

The target expands the existing PostgreSQL 16→18 order/ledger rehearsal to a
bounded commerce project with customers, orders, order lines, payments,
refunds and ledger entries. This is an internal product hypothesis, not
customer adoption evidence. Breadth comes from useful verification operations
across that project rather than from connector count. The accepted
[through-v5.0 direction](../0.15/104-product-direction-and-release-arc.md)
and [post-2.2 direction](../2.2/244-fast-diff-and-cutover-evidence-direction.md)
remain authoritative.

## Durable PostgreSQL support and the reference scenario

The product capability is **verification of explicitly qualified PostgreSQL
migration pairs**. PostgreSQL 16→18 is the retained reference scenario and
regression corpus, rather than a permanent restriction on new project formats.
The ten features and their release boundary are unchanged by this distinction.

PostgreSQL normally releases a major version annually and supports each major
for five years. Its policy table, accessed 30 October 2026, lists PostgreSQL 16
support through 9 November 2028 and PostgreSQL 18 through 14 November 2030.
This motivates a maintained qualification matrix rather than tying the product
identity to either version. These are upstream support dates, not Parison
support promises. [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/).

Major upgrades can skip intervening majors, subject to reviewing intervening
release notes. PostgreSQL 18's `pg_upgrade` checks cluster binary compatibility,
but cannot validate external-module binary compatibility. `pg_dump` cannot
read a server newer than its own major and offers no general guarantee of
loading its output into an older major. Tool success therefore does not prove
policy-level row or relationship agreement; migration tooling stays upstream
of Parison. Record the actual source, target and transfer-tool versions used
in qualification. [Versioning policy](https://www.postgresql.org/support/versioning/),
[pg_upgrade](https://www.postgresql.org/docs/18/pgupgrade.html),
[pg_dump compatibility](https://www.postgresql.org/docs/18/app-pgdump.html#APP-PGDUMP-NOTES).

Before 2.4 implementation, freeze an explicit support matrix with source and
target major, tested minor versions, acquisition capabilities, supported types,
encoding/collation facts, transfer method, test platform, qualification commit
and live evidence. The following are planned gates, not current support claims:

| Qualification lane | Purpose and promotion gate |
| --- | --- |
| 16→18 retained | Replay the existing corpus and prove 2.3 bundle/CLI compatibility. |
| 17→18 proposed additional pair | Run the same six-table live adversarial project through the new 2.4 contracts, without pair-specific evaluator code. |
| Future released majors | Review upstream release notes and capabilities, then add explicit live acquisition, representation and offline replay qualification before advertising support. |

Use exact server facts and capability checks in new versioned 2.4 collection
and project contracts; reject unqualified live combinations rather than infer
support from a numeric version range. A green 17→18 lane would establish only
that tested configuration, not every minor, extension, collation or platform.
Pre-release servers may be experimental lanes and confer no stable support.
Update the matrix at each Parison release as upstream support evolves; removing
an old live acquisition lane does not remove its offline evidence reader.

The released 2.3 rehearsal contract requires baseline major 16 and candidate
major 18. Preserve that validation and its canonical fixtures. Broader pairs
belong in new 2.4 versions, with exact version facts bound in private evidence
and only approved summary fields exposed. Keep old bundles readable offline
after server end-of-life without requiring an old server or its credentials.
That readability guarantee is distinct from maintaining a live adapter lane
for an unsupported server. Freeze old-format replay tests independently from
the evolving live-server matrix. No wildcard future-version compatibility,
automatic migration execution or implicit conversion is introduced.

## Repository evidence and gaps

2.3 supplies optional one-table and fixed two-slot acquisition, integer-range
CSV discovery, source-backed investigation, a fixed orders/order-lines
rehearsal and a portable dossier. `source_pair.py` uses two named slots;
`postgres_rehearsal.py` binds those slots and their recipes. Those released
formats must remain readable. `partition_discovery.py` supplies the routing,
resource checks and semantic reference seam; `partition_investigation.py`
already separates enumeration from scope completion. Existing reconciliation,
suite recovery, series, catalog, Workbench and evidence modules should be
extended rather than duplicated. These are repository observations at released
2.3.0, not claims that the proposed work is already implemented.

## Primary-source findings and design consequences

1. PostgreSQL repeatable read holds a transaction snapshot, while exported
   snapshots have transaction-lifetime restrictions. Use one connection and
   reviewed pre-snapshot lock order for the first N-table reader. Do not
   promise resuming a live acquisition after its transaction ends; resume
   only immutable local evidence. Cross-instance coordination stays an
   explicit source-owned claim. [Isolation](https://www.postgresql.org/docs/18/transaction-iso.html),
   [snapshot synchronization](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION).
2. PostgreSQL column catalogs expose type and collation metadata; collation
   behavior can depend on providers and versions. Metadata equality cannot
   prove equivalent application behavior. Record facts privately, assess
   declared changes, and require explicit conversion policy and test values.
   [Column catalog](https://www.postgresql.org/docs/18/catalog-pg-attribute.html),
   [collations](https://www.postgresql.org/docs/18/collation.html).
3. COPY exposes explicit format, null and encoding controls. Continue generated
   quoted selections and fail-closed representation checks; add neither
   arbitrary caller SQL nor implicit conversion as a convenience.
   [COPY](https://www.postgresql.org/docs/18/sql-copy.html).
4. Database constraints distinguish uniqueness, nullability and foreign-key
   relationships. Their existence is useful context, not a substitute for
   independently evaluating the exported rows. Generalized project invariants
   must define null, duplicate and exclusion behavior themselves.
   [Constraints](https://www.postgresql.org/docs/18/ddl-constraints.html).
5. Python 3.11 already provides process futures; cancellation does not undo
   completed work. Bound submitted tasks and total resources explicitly,
   canonicalize results in plan order and test late worker failure.
   [Python 3.11 futures](https://docs.python.org/3.11/library/concurrent.futures.html).
6. SQLite documents journaling and atomic commit assumptions. A recovery
   journal can track local verified work, but database commit alone does not
   make a multi-file evidence publication atomic. Retain the existing staging
   and no-replace installation boundary. [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).
7. GitHub Actions maps zero/nonzero exits to job success/failure. A useful
   offline gate must preserve Parison's richer statuses in its report while
   enforcing a reviewed automation policy explicitly.
   [Actions exit codes](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/set-exit-codes).
8. Accessible status messages should be exposed to assistive technology without
   unnecessary focus changes. Progress, cancellation and verification failures
   need accessible states in the Workbench, not only visual badges.
   [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).

The following ten choices are design inferences from these sources and the
repository gaps. They are proposed scope, not promises made by the sources.

## Ten substantial capabilities

### 1. Bounded multi-table PostgreSQL snapshot collections

**Value:** acquire an explicitly named project of 1–16 base tables under one
source transaction, retaining per-table receipts and collection coverage.
**Seam:** deepen `postgres_pair.py`, `source_pair.py` and ingress helpers; add a
new collection format without reinterpreting pair-v1. Canonical table IDs and
lock order are separate from caller display order. Limits apply per table and
across the collection; 16 is a proposed cap to freeze after a bounded prototype.
**Gate:** six-table live source, concurrent writers and DDL, hostile names,
RLS failure, empty member, missing member, final-table interruption and commit
failure; no partial collection publishes and offline replay needs no server.
**Dependency:** first. Freeze the live acquisition support matrix and capability checks above. No parallel database acquisition in this feature.

### 2. Explicit database representation and schema assessment

**Value:** review source/target column types, precision/scale, nullability,
keys and collation facts before comparing rows; export an unapproved mapping
proposal and a deterministic compatibility assessment.
**Seam:** ingress metadata plus existing evolution/preflight modules. Privately
bind metadata to the acquisition selection; separate unknown from compatible.
No automatic key, tolerance, conversion or exclusion approval. Assess actual recorded server/tool versions and capabilities; matching major versions alone cannot establish compatibility.
**Gate:** dropped/renamed columns, widened/narrowed decimals, timestamp versus
timestamptz, collation-provider/version changes, composite keys and unsupported
types; forged metadata bindings fail, and equal metadata never implies data PASS.
**Dependency:** 1; design may start in parallel with its contract.

### 3. Exact discovery for composite and text keys

**Value:** use partition discovery on realistic natural and compound keys,
without relying on a single integer range column.
**Seam:** `partition_discovery.py` routing and existing canonical scalar/key
semantics. Propose explicit hash buckets over canonical normalized key tuples;
hashes route rows only and never replace exact comparison. Preserve range-v1.
**Gate:** collision injection, Unicode normalization, null/empty boundaries,
delimiter ambiguity, composite tuples, duplicate normalized keys and skew;
outcomes and counts match the released full exact engine for every bucket plan.
**Dependency:** explicit semantics from 2; local fixtures can precede acquisition.

### 4. Recoverable exact discovery sessions

**Value:** resume expensive local discovery after interruption without
repeating already verified immutable work.
**Seam:** deepen discovery with existing suite-recovery patterns and a private
journal; bind full input, policy, plan and engine identities. Recheck inputs
before reuse. Final evidence is an ordinary completed versioned bundle; mutable
session state is never itself a PASS artifact.
**Gate:** kill at routing/comparison/publication boundaries, truncated journal,
changed input bytes, substituted child, stale policy and symlinked workspace;
resume either reproduces a clean run or rejects reuse. Never resume a dead
PostgreSQL transaction by claiming its snapshot still exists.
**Dependency:** 3, with range-v1 interoperability retained.

### 5. Bounded concurrent exact partition execution

**Value:** reduce local elapsed time with an explicit jobs setting while
keeping deterministic evidence and predictable aggregate limits.
**Seam:** existing suite concurrency and discovery execution; one shared
resource budget rather than a full independent budget per worker.
**Gate:** jobs 1/2/4 produce identical canonical semantic evidence; worker
crash, cancellation, disk exhaustion and out-of-order completion cannot publish
success or orphan sensitive staging. Measure time, process-tree RSS and disk
for low/high difference and skew; report machine-specific results only.
**Dependency:** 4. No source pushdown or hidden automatic engine selection.

### 6. Closed-scope backfill coverage verification

**Value:** verify declared backfill windows, excluded regions and tombstone
membership separately from row parity, so matching omissions do not masquerade
as complete work.
**Seam:** explicit scope plans plus acquisition receipts, manifesting and
partition coverage. First scope is reviewed half-open integer or UTC-time
intervals with explicit boundaries and a source-owned expected-scope receipt.
A coverage PASS means conformance to that declaration, not extraction truth.
**Gate:** gaps, overlaps, boundary rows, timezone offsets, tombstone duplicates,
empty windows, missing partition and identical omissions on both sides;
parity may PASS while coverage remains FAIL/INCONCLUSIVE.
**Dependency:** 1–4. No CDC subscriptions, checkpoint polling or source repair.

### 7. Multi-table reconciliation graphs

**Value:** evaluate a project graph of identities, references and per-group
conservation across the six-table commerce fixture, replacing the fixed
order/line-only experience with explicit reusable invariants.
**Seam:** existing reconciliation evaluator and versioned project declaration;
reuse current exact arithmetic and null contracts. Start with bounded declarative
operators, not arbitrary expressions or SQL. Distinguish cycles from invalid
references; do not infer relational policy from catalog metadata.
**Gate:** orphan refunds, duplicated parents, partial-null composite references,
offsetting totals, wrong currency grouping, cyclic valid references and missing
nodes; compare independent small reference results and enforce all graph caps.
**Dependency:** 1–3 and 6 for closed-scope project claims.

### 8. Portable project rehearsal dossiers

**Value:** independently replay the entire N-table project, coverage and
reconciliation graph from one private self-contained package.
**Seam:** deepen rehearsal and `decision_dossier.py`; new project versions
compose verified children and retain 2.3 dossier readers. Keep exception and
sign-off references opaque and unsigned; package completeness is explicit.
**Gate:** a six-table PostgreSQL 16→18 rehearsal verifies after server shutdown
and original-source removal; recomputed-digest forgery, member substitution,
wrong graph, missing scope and interrupted copy fail closed. Budget total files,
bytes and nested verification to prevent decompression/recursion-style abuse.
**Dependency:** 1–7. New project formats accept only explicitly qualified pairs; retain the 2.3 16→18 reader and offline replay fixtures independently.

### 9. Verified dossier comparison and explicit offline CI gates

**Value:** compare two project rehearsals under compatible explicit policies,
identify resolved/new/persistent discrepancies and coverage regressions, then
apply a reviewed offline gate policy to an individual dossier or comparison.
**Seam:** dossier, suite-series, catalog, analysis and `report-ci`; do not make
a second execution engine. This feature adds semantic dossier comparison and
policy evaluation, not just another output format. Bind policy and input
identity changes; incompatible policies produce a blocked comparison.
**Gate:** forged parent, policy drift, missing tables, complete→incomplete,
closed→open exceptions and reordered members; CLI JSON and CI projection agree.
Gate policy can require zero open exceptions, but its PASS remains mechanical
policy satisfaction and never interprets sign-offs as authorization.
**Dependency:** 8; freeze comparison transitions separately from gate exits.

### 10. End-to-end local migration projects in Workbench

**Value:** save and reopen a reviewed local project; inspect metadata and
mappings, review collection/scope/graph plans, launch bounded local verification,
resume sessions, inspect exact failures and export/compare project dossiers.
This is a durable project workflow with policy review and recovery, not ten
screens counted as features.
**Seam:** existing Workbench Plans/Run/Results/History/Investigate/Compare and
CLI-native project documents. Source acquisition remains an explicit external
adapter command; Workbench displays safe receipts and never stores credentials.
**Gate:** keyboard and screen-reader status flow, stale-plan edits, canceled
runs, workspace escape, unsafe raw artifact links, source-path/token leakage,
reload/resume and offline dossier reopening. Browser and CLI projections must
match. No server-side source connection starts from viewing a project.
**Dependency:** incrementally 1–9; final acceptance uses all ten capabilities. Project setup presents the tested support matrix and rejects unqualified live pairs without silently rewriting an older project.

## Sequence and combined acceptance

Freeze each versioned contract and negative/byte fixtures before its runtime
change. Integrate in the numbered order; early Workbench prototypes may inform
contracts but earn no separate feature credit. Each feature needs narrow tests,
`make check`, independent Standards/Spec review and a green scoped PR to
`develop`. CLI/schema/packaging/platform changes require the manual full
built-wheel matrix on the exact PR head under the existing AGENTS contract.
Docs-only research uses generated-doc and diff checks plus quality CI.

The combined gate retains a disposable PostgreSQL 16→18 six-table project and
adds the proposed 17→18 qualification lane using the same project contracts.
Both must pass before claiming their 2.4 support. Measure the reference lane with
100k/250k total rows per side and a 1m stretch measurement. Existing 2.3 caps
remain unchanged; any higher versioned caps need measured justification.
Measure three cold runs, median/max time, process-tree RSS, staging disk,
source reads and bytes on a named machine. Compare serial, resumed and
concurrent semantic results. Keep provisional targets separate from published
capacity claims. Include matching omissions, representation drift, swapped
selectors, duplicate keys, late orphan rows, offsetting grouped sums, interrupted
workers, corrupted journals, forged child digests and raw-data canaries.

**Release boundary: ten of ten integrated and qualified before any 2.4.0
candidate or release proposal.** Follow RELEASING.md for combined review,
clean-archive artifacts, fresh wheel smoke, CI and a separate publication
decision. Preserve all released recipes, command aliases, schemas and canonical
fixtures; use additive versioned formats for changed meanings. Use existing
`parison` task namespaces instead of adding installed project scripts.

## Threats, non-goals and alternatives

A wider project increases source lock duration, disk use, graph work and the
sensitive evidence footprint. Freeze bounded table/edge/window/member counts,
aggregate byte budgets, cancellation and cleanup before implementation. Reject
unknown wire fields and duplicate JSON names; verify every child before deriving
statuses. Summary outputs exclude identifiers, source names/paths, query text,
keys, values and tokens; predictable hashes are not confidentiality.

Defer a second warehouse connector until this generalized project proves its
conversion and coverage model. Defer source hash pushdown because database
collation/canonicalization equivalence requires another trust contract. Defer
live exported-snapshot parallel acquisition until source-load measurements
justify its lifetime complexity. Distributed orchestration, CDC monitoring,
automatic repair/cutover, hosted services, embedded credentials, signing,
fuzzy matching and statistical drift remain outside this train.

An alternative breadth-first connector train would add systems before one
project has general coverage and replay. A performance-only train would leave
schema, backfill and project adoption gaps. The selected ten span acquisition,
policy review, exact execution, integrity, reconciliation, portable evidence,
automation and local UX while sharing one coherent end-to-end gate. If a feature
proves too broad, narrow its first version's operators or caps while retaining
its stated user capability; do not silently drop it from the ten-feature boundary.

## Next step

Review this proposal as a whole, then freeze feature 1's collection plan,
receipt, summary, manifest, table cap and live adversarial gate. No 2.4 runtime
change is included in this research checkpoint.
