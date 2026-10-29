# Selective exact difference investigation research

Date and primary-source access: 29 October 2026
Status: research supporting the frozen 2.3 feature 4 contract

## Existing evidence and target

The [six-feature roadmap](246-six-feature-roadmap.md) calls for bounded
case-level evidence from **verified suspect partitions**, under the same
policy and input identities, with raw keys and values confined to a sensitive
local artifact. Feature 3's [contract](254-partition-discovery-contract.md)
and [implementation](../../src/parison/partition_discovery.py) produce a
private per-range receipt, a summary-safe aggregate and a source-backed
verifier. The verifier re-routes both original local CSV inputs and reruns
every range before returning `verification: "exact-source-backed"`.
`verification: "integrity-only"` checks evidence bytes and arithmetic but
cannot establish that source rows were routed or classified correctly.

The released keyed [comparator](../../src/parison/comparison.py) already
defines normalized keys, exact and tolerated field classifications, missing
records, global empty-side behavior and bounded raw discrepancy samples.
Its raw mode puts source keys and values in `discrepancy_sample`; summary mode
does not. The existing [analysis drill-down](../../src/parison/analysis.py)
selects items from **already published raw samples**, so it cannot recover
the cases omitted by feature 3's summary-only receipt.

These repository sources are the semantic authority for this note. The
[feature 3 research](253-partition-discovery-research.md) records the official
Python CSV/temporary-file and SQLite sources relevant to routing, cleanup and
the reference engine.

## Design consequences

1. **Bind before selecting.** Feature 4 must require successful feature 3
   source-backed verification against the exact original recipe and both
   input bytes. Bind the feature 3 manifest digest, reviewed plan digest,
   effective policy digest, input digests and sizes, and selected private
   partition records. A source-free integrity check alone is insufficient.
   A copied file with identical bytes may be an equivalent local input;
   matching paths or timestamps are not identity proof.
2. **Select only actual suspects.** Derive suspect ranges from verified
   private per-range counts: baseline-only, candidate-only, required field
   differences, or explicitly included within-tolerance differences. A
   caller may choose a subset of these ranges for priority, but cannot mark
   an omitted suspect as investigated. The selected range indexes and
   integer bounds are private; the summary-safe view reports only aggregate
   counts and completion. Empty/exact ranges require no raw investigation.
3. **Keep the policy mechanically bound.** Feature 3 accepts only a summary
   keyed recipe. Raw case generation needs an internal raw-sensitivity
   projection, and empty individual ranges may need the same mechanical
   `expected_empty` allowance. Both derivations must be narrowly specified,
   recorded with their effective digests and checked against the original
   reviewed policy. Neither is a new operator approval or a changed scope.
   The published feature 3 receipt and released result bytes remain unchanged.
4. **Revisit selected ranges, preserve exact semantics.** Read both original
   CSV inputs under the feature 3 parser and normalized integer key routing.
   Materialize or stream **only** selected range rows into private bounded
   staging, while checking source digests before and after. Reuse the released
   keyed comparator's classification rules for missing, exact, tolerated and
   required differences. Feature 3's current `verify()` discards its
   temporary routed files. The first version can run that full source-backed
   verification and then scan the inputs again for selected raw cases. This
   rechecks **all** ranges to establish trust, but creates raw detail only for
   selected suspects; it must not claim that it reads only selected source
   bytes. Record the extra source passes and wall time. Refactor to retain one
   verified temporary workspace only if the measured budget requires it,
   because that broadens the lifecycle and cleanup surface.
5. **Bound cases and state truncation.** Set explicit positive limits on
   selected ranges, returned cases, per-range cases, staged bytes, output
   bytes and work time where enforceable. Record the total exact discrepancy
   population separately from returned cases; `returned < population` means
   a bounded sample, not completed enumeration. The released raw comparator
   orders missing-record samples before field samples and a missing-record
   item carries its key but not a full source row. If operators need full
   missing-row values, feature 4 needs a dedicated case shape rather than
   relabeling that existing sample as a complete record.
6. **Version sensitive and safe views separately.** Canonical private case
   bytes need a strict manifest and source-backed verifier that recomputes
   every returned case from the same inputs/policy. A summary-safe view may
   expose counts, completion, truncation and opaque digests, but no paths,
   selected range identifiers, keys, values or examples. Reuse the
   [publication primitives](../../src/parison/_safe_fs.py) for atomic
   no-replace output and remove sensitive staging on failure/interruption.

## Threats and adversarial gate

- **False provenance:** integrity-only feature 3 evidence, altered source
  bytes, changed policy, forged or omitted partition records, or a selected
  range absent from the verified receipt must not produce exact case claims.
- **False case:** a case from a different range, a tolerated difference
  reported as required, a missing-key row given the wrong side, or a field
  value changed after routing must fail source-backed verification. Every
  returned item must match the released full raw-reference run under the
  same policy, accounting for the internal sensitivity projection.
- **False completion:** a cap breach, truncated sample, interrupted run,
  missing selected range or partial output cannot be labeled a complete
  enumeration. Comparison completion and enumeration completion are distinct.
- **Sensitivity and custody:** raw keys, values, range bounds, source paths
  and discrepancy samples must stay in private local evidence. Symlinked
  parents, output collisions, concurrent evidence substitution and cleanup
  after interruption need hostile tests. Summary-safe CLI and Workbench
  surfaces must not accidentally serialize a private case.

## Non-goals for the first slice

No source queries, remote workers, automatic policy or range approval,
repair, extraction-truth claim, migration approval or cutover authorization.
No promise to enumerate every difference when the caller requested a bound.
No inference that two PostgreSQL instances share a snapshot from matching
local CSV digests or timestamps. Generalizing beyond feature 3's one-integer-
key local CSV subset waits for its own exactness gate.
