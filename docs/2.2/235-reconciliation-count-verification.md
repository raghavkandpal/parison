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

## Independent review follow-up

24 October 2026: Standards review found uncontrolled errors for malformed
component entries/outcomes; Spec review found malformed dataset collections and
impossible placement of child rows in conservation groups. All were corrected
with digest-valid public-verifier regressions. Both reviewers independently
cleared their findings. Producer-based alignment fixtures cover PASS,
INCONCLUSIVE and FAIL, including failure precedence over declared-cutoff
coordination. Narrow tests pass 29 tests; local full checks pass 437 tests with
11 optional-Polars skips (Polars absent). Broader null/tolerance/empty producer
qualification and exact-head full-platform CI remain pending.

Producer-edge follow-up: composed bundles now qualify empty inputs, zero-valued
parents without children, null-as-zero conservation and a non-exact discrepancy
within declared tolerance. Each fixture asserts expected counts and overall
outcomes before public verification. Both independent reviewers cleared the
strengthened fixtures. Local `make check` passes 438 tests with 11 absent-Polars
skips. The earlier exact head `39ad001ed08754489749cd26790900e90191a3f6`
passed the [full platform matrix](https://github.com/raghavkandpal/parison/actions/runs/40074490311);
new fixture commits require their own exact-head qualification before merge.
