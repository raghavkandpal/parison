# 2.4 post-feature engineering release gate

Date: 10 November 2026
Status: required release work; implementation pending
Owner direction: assess the non-adoption points in [audit316](316-tool-audit-and-recommendations.md)
and complete this work after feature implementation, by release 2.4.

## Sequence and scope

Complete and qualify all ten features in [roadmap275](275-ten-feature-research-and-roadmap.md)
first. Then execute the engineering work below before opening a 2.4 candidate or
proposing release. Keep [audit307's clarity gate](307-product-clarity-cause-and-effect-audit.md)
and every existing compatibility, review and exact-head CI gate. This work is
release hardening, not an eleventh feature and not permission to ship only the
first three features. Contract296's v1 preservation guarantee remains unchanged.

Audit316 is an independent assessment against `a88f286`, not proof that every
suggested cause or fix is correct. Reproduce each finding against the completed
feature train, inspect all affected callers and record the evidence before
choosing a fix. A disproved finding needs an independently reviewed, explicit
no-change disposition; it must not quietly disappear from the checklist.

Adoption research, external-user quotas, PyPI/uvx distribution, marketing,
warehouse/export guides, new feature candidates, release-cadence changes and
G2's reduced release boundary are outside this instruction. Existing audit307
requirements remain in force; this does not expand them through316's adoption
recommendations. The accepted product direction and all-ten boundary stay intact.

## 1. Input, acquisition and publication hardening

- [ ] **V1 — SQLite ordinary-table boundary.** Reproduce virtual/shadow-table
  admission through Parison, not only a SQLite metadata query. Disable trusted
  schema where supported and enforce the documented ordinary-table rule with
  qualified metadata checks. Cover virtual/shadow tables, views, ordinary tables
  and supported SQLite versions, with hostile-input regression evidence. Existing
  ordinary-table workflows and released output bytes must remain compatible.
- [ ] **V2 — PostgreSQL search path.** Verify single, pair and collection paths
  pin catalog resolution before unqualified privilege/catalog operations. Deepen
  shared transaction setup where appropriate; test all callers, rollback/read-only
  behavior and hostile role/database search-path settings in the supported live
  qualification lanes. A hostile database administrator is not a new trust claim.
- [ ] **V3 — fail closed on unsupported publication primitives.** Exercise every
  platform branch of no-overwrite publication. Preserve actual atomic no-overwrite
  behavior on qualified Linux/macOS/Windows; other platforms must reject before
  unsafe mutation unless a primitive is separately qualified. Include existing
  file/empty-directory targets and a deterministic raced-target regression.
- [ ] **V5 — Workbench capability comparison.** Use constant-time comparison in
  the shared capability check and verify valid, missing, malformed and wrong
  capabilities across guarded routes without weakening Host/Origin enforcement
  or exposing the token in errors, logs or responses.
- [ ] **V6 — catalog creation permissions.** Reproduce the file-creation window
  and ensure a new catalog is private from creation, with exclusive/no-overwrite
  handling, while preserving existing-catalog ownership, validation and failure
  behavior. Qualify actual permission/ACL semantics on supported native platforms;
  POSIX mode assertions alone do not establish Windows privacy.
- [ ] **V7 — publication parent identity and cleanup.** Audit every staging and
  publication caller for parent/ancestor substitution. Establish a concrete pinned
  identity protocol, deterministic last-boundary substitution preservation and
  interruption/failure cleanup on supported native lanes. Merely adding another
  pathname check or a directory fd is not clearance for the whole protocol. Reject
  unsupported cases safely; retain the existing preservation/publication contract.

## 2. Shared lifecycle code

- [ ] **C1 — stage/publish/cleanup lifecycle.** Recount and inspect the actual
  callers after feature integration. Consolidate the common lifecycle in the
  existing safe-filesystem module where one implementation can preserve each
  caller's ownership, sensitivity, budget and publication guarantees. Migrate
  callers in coherent reviewed slices. Test cleanup failure together with the
  original error: cleanup must not mask it or silently leave sensitive staging.
  Preserve canonical files, no-overwrite behavior and interruption outcomes.
  Resolve V3/V7 in the shared design rather than copying an unqualified protocol.
- [ ] **C2 — SQLite spill lifecycle.** Consolidate genuinely shared temporary
  workspace, page-budget setup and teardown after tracing comparison and
  reconciliation callers. Verify exact budget boundaries, exhaustion, errors,
  interruption and result equivalence for every affected engine. Do not merge
  different semantics merely because setup statements look alike.

## 3. Security maintenance and compatibility decisions

- [ ] **V4 — security reporting and dependency watch.** Add SECURITY.md with an
  actual verified private reporting route and explicit supported-version policy;
  do not invent a contact address or promise an unstaffed response SLA. Configure
  pip and GitHub Actions update monitoring against the repository's dependency
  declarations. Keep deterministic qualification pins and review/update gates;
  monitoring never auto-approves or auto-merges dependency changes. Validate the
  configuration and reporting route before claiming this item complete.
- [ ] **C3 — command-surface assessment.** Reconcile the finding with the already
  released task namespaces and [alias contract273](../2.3/273-cli-command-alias-contract.md). Record a command inventory,
  maintenance/coverage gaps and whether clearer advanced-command guidance is
  justified. Preserve all five installed executables, released aliases, help/JSON
  and exit-code obligations. No command removal or incompatible consolidation is
  authorized for 2.4; a reviewed no-change disposition is valid if the concern is
  already covered. Any additive help change needs its own compatibility treatment.
- [ ] **C4 — optional dependency constraints.** Measure the claimed co-installation
  conflict and assess retaining exact runtime pins versus a supported/tested range
  backed by exact CI constraints. Widen only with version/format compatibility evidence and a
  deterministic qualification strategy; otherwise record why exact pins remain.
  No speculative untested range is a completion shortcut. Packaging changes
  require exact-head full built-wheel qualification.
- [ ] **C5 — module responsibilities.** Review format-reader and engine boundaries
  in the final train. Record concrete maintainability problems and deepen/split
  only where an affected change benefits from a clear interface. No module split
  is required for line count alone. A reviewed no-change disposition with evidence
  completes the assessment; do not create an architecture rewrite to satisfy it.

## 4. Supported-platform UI behavior

- [ ] **G7 — Linux folder-picker fallback.** Verify the actual support matrix and
  show the supported workspace-relative manual-path action before a user invokes
  an unavailable native picker. Preserve manual entry, validation, keyboard/focus
  and announced status/error behavior; verify macOS/Windows picker flows remain
  functional. Coordinate with audit307's affected-flow checks. Do not imply that
  Linux cannot use Workbench merely because its native chooser is unavailable.

## Completion evidence

Every checkbox needs an implementation or explicit permitted disposition, its
reproduction/verification evidence, affected-callers list and scoped PR/head.
For C3–C5 the required deliverable is the compatibility/maintainability decision
and any justified compatible changes, not automatic adoption of316's prescription.
For retained defects, require the smallest coherent corrective implementation and
regression coverage. If a guarantee cannot be established, keep the release gate
open; do not waive it by documenting a limitation that contradicts the contract.

Use the existing focused suites, `make check`, independent Standards/Spec review
and exact-head CI rules. CLI/schema/packaging/platform changes require local
preflight followed by the manual **full** built-wheel Python 3.11–3.14
Linux/macOS/Windows matrix; preflight alone never qualifies integration. Use
actual live/native evidence where the item concerns those systems. Optional
Polars skips are valid only when Polars is absent.

Before the2.4 candidate, reconcile this checklist with all-ten feature evidence,
audit307, the active release checklist, docs/CURRENT.md and CHANGELOG.md. A green
unit suite alone does not close an unexercised hostile-input, live-database,
permission, publication-race or browser-flow gate. Release publication still
follows RELEASING.md and requires its separate authorization.
