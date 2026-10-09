# Aggregate-v1 comparison contract

Date: 9 October 2026

Status: **normative for Parison 0.7 development**. The recipe, explanation, preflight, execution, result and drafting workflow are implemented; release hardening remains.

## Claim and boundary

Aggregate-v1 proves that two complete inputs have the same declared group coverage and compatible declared aggregate measures. It does not prove row equality, find matching rows, or repair an input without stable keys.

A recipe uses `recipe_version: 2` and `comparison_mode: "aggregate"`. Keyed recipe v1 keeps its existing meaning.

## Recipe

`group_by` is an ordered list of configured column names. An empty list defines one global group. Group values are parsed and normalized using their column policies, compared exactly, and may not be null.

`measures` is a nonempty object whose property names are stable measure identities:

- `count` has no source column and counts every row in its group;
- `sum` requires an integer or scaled-decimal source column;
- `min` and `max` accept any configured source type;
- non-count measures declare `nulls: "reject"` or `nulls: "ignore"`;
- non-count measures default to exact comparison and may instead declare `numeric` comparison with the existing `symmetric-v1` absolute-plus-relative tolerance. Numeric measures require integer or decimal sources.

Column policies own parsing and normalization. Measure policies own the aggregate operator, null handling and comparison. This prevents one source column used by two measures from acquiring contradictory parsing rules.

Example:

```json
{
  "recipe_version": 2,
  "comparison_mode": "aggregate",
  "group_by": ["region"],
  "measures": {
    "orders": {"operator": "count"},
    "revenue": {
      "operator": "sum",
      "column": "amount",
      "nulls": "reject",
      "comparison": "numeric",
      "tolerance": {"formula": "symmetric-v1", "absolute": "0.01", "relative": "0"}
    },
    "last_order": {"operator": "max", "column": "ordered_at", "nulls": "ignore"}
  },
  "scope": {
    "snapshot": "orders-v4",
    "cutoff": "2026-10-08T00:00:00Z",
    "filters": ["status != 'test'"],
    "completeness": "full",
    "expected_empty": false
  },
  "columns": {
    "region": {"type": "string", "normalize": ["trim", "casefold"]},
    "amount": {"type": "decimal", "scale": 2},
    "ordered_at": {"type": "timestamp", "timezone": "require-aware"}
  },
  "output": {"sensitivity": "summary"}
}
```

## Accumulation

Every input row contributes exactly once to one group count. For every non-count measure in a group:

```text
contributing_count + ignored_null_count = group_count
```

Under `reject`, a null measure value makes execution inconclusive before comparison. Under `ignore`, null contributes only to `ignored_null_count`. A measure with no contributing values has the explicit `no_value` state; it is not numeric zero.

Integers accumulate as unbounded integers. A decimal with scale `s` accumulates as an unbounded integer coefficient in units of `10^-s`, then converts to canonical decimal text at the result boundary. Tolerance applies only to completed aggregates. This makes sums independent of row and partition order.

`min` and `max` use the parsed type's total order. Boolean values order `false` before `true`; strings order by Unicode code point after normalization; dates and aware timestamps order chronologically. Float sources are allowed only for exact `min` and `max`, not sums or numeric tolerance.

## Empty and null states

- An empty global input has one group with `count = 0`; every other measure is `no_value` with zero contributing and ignored counts.
- An empty grouped input has no groups.
- An all-null ignored measure is `no_value` with a nonzero ignored count.
- Null group components are invalid; aggregate-v1 does not import SQL null-group semantics.

With `scope.expected_empty: false`, either empty input is INCONCLUSIVE. With `expected_empty: true`, two complete inputs with the same empty shape may PASS. One empty grouped input and one nonempty grouped input FAIL on group coverage.

## Comparison and ordering

Parison compares group-key sets before measures. Baseline-only or candidate-only groups always produce FAIL, even if totals across all groups offset. Measures are compared only for common groups. A common-group measure is `exact`, `within_tolerance`, or `different`; `no_value` equals only `no_value`.

Raw evidence orders groups lexicographically by the declared group columns using type-aware ordering: null is absent by contract, then native parsed order for like-typed values. Measure evidence follows recipe declaration order. Serialized group identities are arrays, never delimiter-joined strings or JSON object keys.

Summary mode publishes only total group-classification and measure-classification counts. It never publishes group keys, per-group row counts, per-group aggregates or source values. Raw mode may publish a deterministic bounded sample and is sensitive output. Aggregate output is reconciliation evidence, not anonymized or de-identified data.

## Outcomes

- **PASS:** execution is complete, group coverage is identical, and every common-group measure is exact or within tolerance.
- **FAIL:** execution is complete and a group exists on one side only or a common-group measure differs beyond policy.
- **INCONCLUSIVE:** the declared comparison cannot be completed, including unexpected empty scope, null group values, a rejected null measure, invalid records, resource exhaustion, or input mutation.
- **ERROR:** the recipe, input container, or execution environment is invalid or unreadable before a trustworthy comparison can be formed.

Parse failures are reported without rejected source values. Resource and mutation checks retain the keyed-v1 safety contract.

## Worked outcomes

For groups `east` and `west`, baseline counts `2, 1` versus candidate counts `1, 2` FAIL twice by measure even though both global counts are `3`. If candidate has only `east` with count `3`, it also FAILs group coverage because `west` is baseline-only.

For decimal sum `100.00`, symmetric tolerance `{absolute: 0.01, relative: 0}`, candidate `100.01` is `within_tolerance`; candidate `100.02` is `different`. Values `999999999999.99`, `-999999999999.99`, and `0.01` sum to `0.01` in every input order.

For an ignored measure over three rows containing only nulls, both sides produce `no_value`, `contributing_count = 0`, and `ignored_null_count = 3`. A side with zero rows has `no_value` but ignored count `0`; the distinct group counts still prevent these states from being confused.
