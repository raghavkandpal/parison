# Reconciliation count verification contract

Date: 23 October 2026
Status: frozen for prerequisite hardening; initial implementation local; qualification pending

The next hardening slice preserves all released producer bytes and rejects only
internally inconsistent evidence. It does not rerun source data or authenticate
an issuer. Counts are exact nonnegative integers (booleans rejected), with closed
keys per kind. Validate every shape before dependent arithmetic or summary access.

Identity counts: rows, distinct_keys, null_key_rows, duplicate_keys.
Require null_key_rows <= rows, duplicate_keys <= distinct_keys <= rows,
distinct_keys + duplicate_keys <= rows, and rows == 0 iff distinct_keys == 0.
If duplicate_keys == 0 then distinct_keys == rows; if duplicate_keys > 0 then
rows > distinct_keys. Outcome FAIL iff duplicates exist or forbidden nulls exist.
Null rows remain included in distinct identities under released producer logic.

Reference counts: child_rows, exempt_rows, matched_rows, orphan_rows,
ambiguous_parent_rows, null_failure_rows. The five classifications sum exactly to
child_rows. Exempt rows require all-null-exempt; null_failure_rows must be zero
for nulls=match-null. Outcome FAIL iff orphan, ambiguous-parent or null-failure counts
are nonzero. Match and ambiguity feasibility must agree with parent identity
counts where preserved. Multiple references to one parent do not bound matched
rows by distinct parent keys.

Conservation counts: parent_rows, child_rows, groups, compared_groups,
exact_groups, within_tolerance_groups, different_groups, child_only_groups,
parent_without_children_groups, duplicate_parent_groups, null_measure_rows.
Require groups = compared + child_only + duplicate_parent and compared = exact +
within_tolerance + different. Parent-without-children is a subset of compared,
not an additional disjoint group. Parent rows >= compared + 2*duplicate_parent;
child rows >= child_only + compared - parent_without_children; groups <= total
rows. If no duplicate-parent groups, parent rows == compared groups. Null measure
rows <= parent_rows + child_rows; nulls=zero requires zero null failures. Exact
comparison requires zero within-tolerance groups. FAIL iff different, child-only,
duplicate-parent or null-measure counts are nonzero. A zero-valued parent without
children can PASS and must stay valid.

Cross-component dataset row totals come from preserved alignment per-side row
counts. Identity dataset rows, reference child rows and conservation parent/child
rows must agree. Alignment classifications sum to rows. Derive alignment outcome
and reason codes from counts plus the normalized coordination declaration using
the released preflight reduction, preserving heuristic INCONCLUSIVE and failure
precedence. Do not assume count arithmetic establishes actual source truth.

Acceptance: all released producer scenarios plus frozen mutation inputs,
missing/extra keys, arrays/null in place of objects, forbidden booleans, forged
PASS/FAIL, same-size inconsistent counts, empty sides, null identity matching,
all-null exemptions, exact/tolerant conservation, child-only and duplicate-parent
cases, and valid parent-without-children. Recompute outer digests and summaries
when mutating to isolate semantic verification rather than file integrity.

## Implementation checkpoint

The shared preserved-bundle verifier now closes count shapes, checks arithmetic
and dataset row consistency, derives alignment/component outcomes and checks
reference feasibility against parent identity counts. All 27 reconciliation tests
pass, including eight frozen hostile mutations, alignment/conservation arithmetic
mutations and a valid composed bundle. Broader null/tolerance/empty-input producer
edge cases, independent Standards/Spec review and exact-head full-platform CI
remain required before integration. This is prerequisite hardening, not feature
6 completion. No released producer serialization is changed.
