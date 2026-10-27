# Verified suite rehearsal series contract

Date: 27 October 2026
Status: frozen before implementation

Feature 5 accepts 2–16 distinct, caller-ordered, recursively verified complete
suite parents (v1 or v2), never shards. Selection, suite policy, ordered case
identity, child policy and comparison mode must match. Selected non-shard v2
suites are allowed when every selected member is complete. At most 100 cases
and 10,000 groups across cases are admitted; exceeding a bound fails rather
than truncating. Repeated identical children across distinct parents are valid.

The producer composes the existing ordinary-run discrepancy groups. It includes
zero counts and preserves each group's units: keyed record/field counts,
aggregate group/measure counts and multiset surplus-shape counts. No cross-case
or cross-mode total is reported. Adjacent transitions use the released introduced,
resolved, increased, decreased and unchanged labels; positive unchanged groups
show recurrence. Caller order does not establish chronology or improvement.

## Frozen wire shape

The canonical UTF-8 compact sorted-key JSON payload ends with one newline and
contains exactly `suite_series_version: 1`, `kind: suite-series`, `sensitivity:
summary`, `suite_version`, `suite_policy_sha256`, `selection_sha256`, `runs` and
`cases`. Each parent run records `bundle_sha256` and `outcome`. Cases retain
suite order and contain `case_ref`, `policy_sha256`, `comparison_mode`, `runs`,
`groups` and `input_transitions`. Each child run records `bundle_sha256`,
`outcome` and `inputs` (baseline/candidate digests).

Groups are ordered by source group digest and contain `group_id`,
`source_group_id`, `kind`, `classification`, `counts` and `transitions`.
Transitions have exactly the released fields `group_id`, `from_run`, `to_run`,
`before`, `after`, `delta`, `status`. Input transitions contain `from_run`,
`to_run`, `baseline_changed`, `candidate_changed`.

`case_ref` hashes the domain `parison:suite-case:v1` plus NUL and canonical JSON
`[suite_policy_sha256, original_case_id]`. `group_id` similarly hashes domain
`parison:suite-group:v1` plus NUL and `[case_ref, source_group_id]`.
`selection_sha256` hashes canonical selection JSON (null for v1). These opaque
identifiers support pseudonymous linkage, not a confidentiality guarantee.
No case/field names, paths, policy fragments, values, keys or samples are emitted.

Publication reuses the atomic analysis publisher with a new outer
`schema_version: 2`, `kind: discrepancy-analysis`, `analysis_kind: suite-series`;
other manifest fields retain the existing digest layout. Released v1 bytes stay
unchanged. The installed `suite-series` schema closes the payload. The independent
verifier checks strict types, vocabulary, ordering, cardinalities, bounds, IDs,
all transition derivations, outcome reduction, canonical bytes and digests without
source files or parent bundles. It establishes internal consistency of preserved
summaries, not authenticity, reconstruction of omitted names, or source reexecution.

CLI `analyze-suites BUNDLE... --output NEW` publishes the artifact;
`verify-analysis` verifies it. Workbench Compare accepts one explicit path per
line, displays the summary and separately exports the reviewed series to a new
path after fresh verification and matching canonical identity. No catalog scan,
automatic order inference, rerun or raw-sample aggregation is added.

Acceptance includes four rehearsals with mixed modes and introduced/resolved/
recurring groups; same descriptors in different cases; changed bytes with equal
counts; caller-order reversal; duplicate/incomplete/sharded/tampered/mismatched
inputs; source-free verification, hostile recomputed digests, canonical fixture,
summary disclosure, atomic no-overwrite cleanup and CLI/Workbench parity.
Narrow tests, `make check`, independent Standards/Spec review and exact-head
built-wheel matrix gate integration. Six features remain required for a candidate.

Implementation checkpoint: the first producer, strict verifier, schema, canonical
fixture, CLI commands and Workbench review/export are implemented. Focused tests
cover v1/v2 parents, mixed modes, case-scoped group identity, caller order,
source-free verification, hostile payloads, path rejection and interrupted
staging. Exact local full-gate result, independent review and exact-head CI
remain to be recorded before integration.
