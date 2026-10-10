# Multiset-v1 comparison contract

Date: 9 October 2026

Status: **normative for Parison 0.8 implementation**

## Purpose

Multiset-v1 compares two complete datasets when row order is irrelevant and no stable unique key exists. It proves that every canonical row shape occurs the same number of times on both sides. Duplicate rows are valid evidence, not an identity error.

This contract is separate from keyed-v1 and aggregate-v1. Parison never changes modes because keys are missing, null or duplicated.

## Recipe

Multiset-v1 uses:

```json
{
  "recipe_version": 3,
  "comparison_mode": "multiset",
  "scope": {
    "snapshot": "orders-v5",
    "cutoff": "2026-10-09T00:00:00Z",
    "filters": [],
    "completeness": "full",
    "expected_empty": false
  },
  "columns": {
    "region": {"type": "string", "normalize": ["trim", "casefold"]},
    "amount": {"type": "decimal", "scale": 2}
  },
  "output": {"sensitivity": "summary"}
}
```

The recipe reuses the existing scope, column mappings, exclusions, delimiters, null tokens, normalization, output sensitivity and scalar types. `columns` is nonempty; canonical column names sorted by Unicode code point define row order, independent of JSON object order. Every configured column participates in row identity.

The recipe has no `keys`, `identity`, `nulls_equal`, `group_by`, `measures`, tolerance or expressions. Null equality is fixed by this contract rather than configurable.

## Canonical row identity

For each input row, Parison:

1. resolves each configured canonical column through its side-specific mapping;
2. applies the configured null tokens;
3. parses the value using the configured scalar type;
4. applies configured string normalization in declared order;
5. forms a typed tuple in canonical sorted column-name order.

Two canonical rows are equal only when they have the same number of values and every value has the same type and value. Null equals null in the same position and differs from every non-null value. Empty string is a string value and differs from null. Booleans do not equal integers. Strings do not acquire numeric, locale or database collation semantics.

Floats must be finite. Decimal values must fit their declared scale. Timestamps must be timezone-aware and compare as the normalized instants already defined by Parison's scalar contract. Nested values are unsupported.

## Multiplicity semantics

Let `B(r)` and `C(r)` be the complete baseline and candidate occurrence counts for canonical row `r`:

```text
common(r)         = min(B(r), C(r))
baseline_only(r)  = max(B(r) - C(r), 0)
candidate_only(r) = max(C(r) - B(r), 0)
```

The result totals are:

```text
common_occurrences         = sum(common(r))
baseline_only_occurrences  = sum(baseline_only(r))
candidate_only_occurrences = sum(candidate_only(r))
baseline_surplus_shapes    = count(r where baseline_only(r) > 0)
candidate_surplus_shapes   = count(r where candidate_only(r) > 0)
```

The following conservation equations are mandatory:

```text
baseline_rows  = common_occurrences + baseline_only_occurrences
candidate_rows = common_occurrences + candidate_only_occurrences
```

`baseline_distinct_rows` and `candidate_distinct_rows` count canonical row shapes, not occurrences.

Example: baseline `[A, A, B]` and candidate `[A, B, B]` have two common occurrences, one baseline-only occurrence of `A`, one candidate-only occurrence of `B`, one surplus shape on each side and outcome `FAIL`.

Input containers do not affect semantics. For example, a CSV baseline row `East ,10.00` and a JSON Lines candidate object `{"area":"east","total":"10.00"}` are the same canonical row when mappings bind `region` to `area` and `amount` to `total`, the declared decimal scale is two, and `region` applies `trim` then `casefold`.

## Outcomes

- `PASS`: both complete inputs were evaluated and both one-sided occurrence totals are zero.
- `FAIL`: both complete inputs were evaluated and either one-sided occurrence total is nonzero.
- `INCONCLUSIVE`: the run is intentionally unable to make the requested claim, including two empty inputs when `scope.expected_empty` is false.
- `ERROR`: the recipe or input is invalid, parsing fails, an input mutates, or a resource limit is exceeded.
- `INTERRUPTED`: execution was cancelled before a complete result.

Two empty inputs pass only when `scope.expected_empty` is true. One empty and one nonempty complete input fails. Parison never samples or truncates toward `PASS`.

## Canonical encoding and order

The implementation may count typed tuples directly. Any byte representation used for persistence, sorting or evidence must be versioned and collision-free.

Encoding-v1 is a sequence of length-prefixed fields. Each field contains a one-byte type tag, an unsigned big-endian payload length and a canonical UTF-8 payload. Null has its own tag and an empty payload. Other payloads use existing canonical scalar renderings. Field and payload boundaries are structural; delimiter concatenation, `repr`, process hashes and unverified digests are forbidden as identity.

Raw evidence is ordered lexicographically by the complete encoding-v1 bytes. Summary counts do not depend on this order. Changing the encoding requires a new encoding version in the effective policy and result provenance.

## Result-v3

A completed result records:

- `schema_version: 3`, `comparison_mode: "multiset"` and contract `multiset-v1`;
- completeness, outcome and problems;
- baseline, candidate and common occurrence counts;
- baseline-only and candidate-only occurrence counts;
- baseline and candidate distinct-row counts;
- baseline- and candidate-surplus shape counts;
- configured and observed distinct-row limits;
- input digests, recipe digest, effective-policy fingerprint and runtime provenance;
- output sensitivity and bounded evidence.

Summary sensitivity contains counts only: no row values, encoded row keys or source values. Raw sensitivity may contain at most the configured sample limit of:

```json
{
  "row": {"region": "east", "amount": "10.00"},
  "baseline_count": 2,
  "candidate_count": 1,
  "classification": "baseline_surplus"
}
```

One evidence item represents one row shape. It is not repeated for each surplus occurrence. Evidence is sorted by encoding-v1 and then bounded, so input order and hash iteration cannot change it. Raw output remains sensitive.

## Preflight-v3

Schema preflight retains existing physical-column, mapping and exclusion checks. Record preflight parses every configured value, counts rows and distinct canonical shapes, and enforces the same distinct-row limit as comparison. It publishes invalid-row and invalid-field counts but no row values.

Preflight does not compare multiplicities and cannot return a comparison `PASS`.

## Resource and integrity rules

The reference engine counts complete typed rows in memory and requires a positive `max_distinct_rows` bound for each input. The bound is checked before accepting a new shape. Exceeding it is `ERROR` and produces no partial equality claim.

Existing byte, decoded-byte and row limits remain in force. Input digests and mutation checks cover every consumed source. Publication remains atomic and bundle verification validates both manifest integrity and result-v3 schema shape.

## Invariants

Every implementation and fixture must preserve:

1. row and partition reordering cannot change the result;
2. JSON object order cannot change identity because sorted canonical column names define tuple order;
3. duplicate multiplicity determines the outcome;
4. normalization happens before identity and may intentionally collapse source spellings;
5. occurrence conservation holds independently for both sides;
6. summary output contains no row identity;
7. a breached limit, parse failure or mutation cannot produce `PASS` or `FAIL`;
8. keyed-v1 and aggregate-v1 recipes and results retain their existing meanings.

## Non-goals

Multiset-v1 does not perform tolerant or fuzzy pairing, subset comparison, bounded surplus, position-based matching, automatic deduplication, nested comparison, custom code, remote reads or larger-than-memory execution.
