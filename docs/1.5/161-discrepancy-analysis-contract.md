# `discrepancy-analysis-v1` contract

Date: 17 October 2026

Status: **implementation contract**

## Claims

A per-run analysis claims only that its exhaustive reason-group counts are a deterministic projection of one verified ordinary run bundle. A series claims only how those counts change across the supplied order under one exact `policy_sha256`. Neither claim establishes upstream cause, chronology, policy correctness, repair, approval or cutover readiness.

## Per-run analysis

The canonical object contains `analysis_version: 1`, `kind: "run"`, the verified bundle and policy SHA-256 digests, comparison mode, summary sensitivity, scope references, and ordered groups. Each group contains a domain-separated SHA-256 `group_id`, a closed descriptor (`analysis_version`, `comparison_mode`, `kind`, `classification`, optional `logical_name`), exact count, closed count source and reason codes, and ordered RFC 6901 policy references with data-free values. Descriptor kinds are `record`, `field`, `group`, `measure` and `row`.

Supported groups are keyed missing records plus field `within_tolerance`/`different`; aggregate missing groups plus measure `within_tolerance`/`different`; and multiset baseline/candidate surplus shapes. Zero-count groups remain present so series alignment is total and deterministic. Unknown result versions, classifications or required policy locations fail closed.

Group IDs hash `b"parison:discrepancy-group:v1\\0"` followed by compact sorted-key UTF-8 JSON of the descriptor. Groups sort by closed mode/kind/classification ordinals, UTF-8 logical name bytes and group ID.

## Series analysis

A series requires two or more distinct verified ordinary bundles with the same nonempty policy SHA-256 and result mode. Caller order is authoritative. Catalog-backed selection additionally requires every matching entry to be current and every bundle identity to have exactly one catalog path; modified, missing, symlinked and aliased identities fail closed. The group union contains every canonical group and its counts in run order; adjacent transitions are `introduced`, `resolved`, `increased`, `decreased` or `unchanged` from exact integer deltas. Paths and timestamps are not emitted in summary output.

## Drill-down

Drill-down may select only exact group IDs from each verified bundle's already-published `discrepancy_sample`. It preserves bundle and sample order, applies explicit positive global/per-run limits and reports bundle and policy provenance, population count, published sample size, matched sample size, returned size and whether the published sample is complete. Summary bundles cannot produce raw drill-down. Inputs are never reopened. `discrepancy-drilldown-v1` is strict canonical JSON; duplicate fields, unknown fields, invalid provenance and unreconciled counts fail verification.

## Safety and compatibility

Analysis and series outputs are summary-safe and exclude source paths, keys, raw values and sample items. Raw drill-down is a separate sensitive artifact. Publication uses private staging, atomic no-replace commit and cleanup on error or interruption. Existing artifacts are never rewritten; new schemas and bundle kinds are versioned and strict.
