# Parison comparison semantics

This document is a proposed behavioral contract. It is the most important implementation prerequisite: a reliable-looking report with ambiguous semantics can be worse than an explicit error.

## Modes and scope

MVP mode is keyed comparison of two tabular outputs expected to describe the same records. Record order is irrelevant. No implicit aggregation, bag matching, fuzzy identity or correspondence by row position is permitted.

No-key multiset comparison and declared group-aggregate comparison may be separate future modes with their own contracts. They must not silently replace keyed comparison when keys are invalid. Temporal drift analysis is also a distinct product mode, not a fallback.

Require a scope declaration describing source snapshot, cutoff, intended filters and whether all records are evaluated. A user's assertion is provenance, not proof. Mismatch in declared comparable scope should prevent a PASS.

Default to requiring nonempty comparable inputs. Empty/header-only datasets produce INCONCLUSIVE unless the recipe explicitly declares that an empty scope is expected; that exception is visible in the report. An empty inner join cannot establish success.

## Outcome versus classifications

| Run outcome | Meaning | Proposed exit code |
| --- | --- | --- |
| PASS | Complete declared evaluation; every required check meets the pinned policy | 0 |
| FAIL | Complete evaluation found a required policy violation | 1 |
| ERROR | Invalid command, unreadable input, failed parsing, internal fault or resource failure | 2 |
| INCONCLUSIVE | Inputs or identity cannot support the intended comparison, or evaluation is intentionally incomplete | 3 |
| INTERRUPTED | User cancellation or signal | 130 |

Within a successful execution, record-level categories include baseline-only, candidate-only, matched-exact, matched-within-tolerance and matched-with-required-difference. Field-level differences overlap across records; their sum must not be called the number of mismatched records.

Known preflight blockers dominate the headline. They may coexist with diagnostic schema/aggregate information, but diagnostic information does not rescue an invalid keyed comparison. A sampled run never returns PASS in the strict MVP contract.

## Identity rules

Composite keys are typed tuples, not delimiter-concatenated strings. Reject null key components by default. Reject duplicate keys on either side before joining. Preserve identifiers as strings where declared: `001` is not `1`.

Key normalization is a separate explicit policy and requires checking uniqueness again after normalization. If trimming or case folding causes a collision, return INCONCLUSIVE. Do not use input order to pair duplicates; do not apply many-to-many joins and count multiplied rows.

For complete valid keyed runs, enforce these invariants:

```text
baseline_count = common_key_count + baseline_only_count
candidate_count = common_key_count + candidate_only_count
common_key_count = exact_rows + tolerated_rows + violating_rows
```

Missing/extra records fail by default. Any future bounded allowance must be separately declared and visible; numerical field tolerance never excuses missing identity.

## Parsing and schema

CSV identity-sensitive fields use explicit types. Do not silently reinterpret leading zeros, locale numbers, boolean tokens, empty strings or timestamps. Report parse failures rather than discarding offending rows. No default “ignore errors” parser option.

Column names are exact and unique; mappings are one-to-one and validated before execution. Extra or missing columns fail the schema policy unless explicitly excluded/allowed. Excluded columns are listed in every report with rationale. Missing a required mapped field cannot be downgraded to an empty comparison.

Parquet's declared types do not automatically settle semantic compatibility. Decimal scale, timezone, nested types and categorical encodings still need policies. Unsupported nested fields produce explicit coverage gaps; do not stringify them and claim semantic equality. MVP may reject such schemas entirely.

## Value policies

| Type/case | Proposed default |
| --- | --- |
| Strings | Exact code-point equality; no trimming or case normalization |
| Empty string versus null | Different unless an explicit reviewed rule says otherwise |
| Two nulls in non-key values | Equal only under the declared null-equality policy |
| One null | Different; never zero or empty by coercion |
| Integers/decimal quantities | Exact in their declared representation; no implicit float conversion |
| Floating values | Exact by default; finite numerical tolerance only when configured |
| NaN/infinity | Block numerical comparison by default; opt-in handling requires explicit tests |
| Dates | Exact calendar-date equality; no automatic timestamp truncation |
| Timestamps | Exact instant after an explicitly declared timezone policy |
| Naive timestamps | No guessed timezone; require a declared policy |

Unicode normalization, whitespace and case operations belong to an allowlisted rule system. Keep original-value comparison counts alongside normalized outcomes. These operations can hide upstream defects and are not universally harmless.

## Numerical tolerance

For finite values with tolerance enabled, propose a symmetric formula:

```text
delta = abs(candidate - baseline)
allowance = absolute_tolerance
          + relative_tolerance * max(abs(baseline), abs(candidate))
within_tolerance = delta <= allowance
```

Both tolerances must be finite and non-negative; default is zero. Record the formula identifier and rule version in the recipe and report. This proposal is deliberately not assumed equivalent to another library's directional relative-tolerance formula. Adapter compatibility must be tested at negative, zero, near-zero and boundary cases.

Use decimal arithmetic for declared decimal comparisons and documented precision/rounding. Do not coerce all numbers to binary floats. A tolerance suitable for currency is not automatically suitable for counts or IDs. Normalizing keys with numerical tolerances is prohibited.

## Counts, aggregates and groups

Headline mismatch counts are complete, not derived from samples. Evidence samples are deterministic, bounded and labelled with total discrepancy counts. If full counting is impossible, publish incomplete coverage and a nonzero outcome.

Aggregate checks are optional declared checks, not proof of row equality. Keep group keys exact and show missing groups. Sums can cancel errors; means can hide distribution changes. Floating aggregate reduction order and precision must be pinned/tested or marked within an explicit numeric policy.

Do not count every within-tolerance cell as an exact match. Keep exact, tolerated and violating counts separate. Schema checks, parsing checks and coverage are first-class results rather than footnotes.

## Reproducibility

Freeze input content digests, effective recipe, parse decisions, engine versions, runtime bindings, scope, coverage and report schema. Use stable ordering for published discrepancies. A raw-file hash identifies exact bytes; differently encoded files can be logically equal while having different hashes.

Semantic result equality excludes volatile timestamps, temporary paths and run IDs. Preserve those in the manifest without pretending reruns are byte-identical. A content hash detects accidental changes relative to a trusted reference; it is not proof of authorship or a signature.

## Review annotations

A note can state “expected due to a documented change” while the computational result remains FAIL. New allowances require a new recipe/run. An annotation attaches to run digest, discrepancy identity, actor and timestamp; it cannot replace original evidence. Local actor labels are user-entered claims until a separate authenticated team system exists.
