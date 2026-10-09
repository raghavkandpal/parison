# Multiset comparison user guide

Multiset mode is for complete local exports where row order is irrelevant and no stable unique key exists. It compares whole canonical rows and preserves duplicate multiplicity.

Use keyed mode when a stable unique key exists. Use aggregate mode when only declared totals or grouped measures are meaningful. Do not choose multiset mode merely because keyed validation found duplicate or null keys; that is a policy decision requiring review.

## Draft and review

```sh
parison draft-recipe \
  --multiset \
  --baseline baseline.csv \
  --candidate candidate.jsonl \
  --output multiset.recipe.json
parison validate-recipe multiset.recipe.json
parison explain multiset.recipe.json
```

The draft suggests shared scalar columns and mappings. Review every included column, exclusion rationale, normalization rule, snapshot, cutoff and expected-empty policy before running it. Normalization changes row identity: trimming and case-folding can intentionally make different source spellings one canonical row.

## Preflight and comparison

```sh
parison validate-inputs \
  --records \
  --max-distinct-rows 100000 \
  --recipe multiset.recipe.json \
  --baseline baseline.csv \
  --candidate candidate.jsonl

parison compare \
  --max-distinct-rows 100000 \
  --recipe multiset.recipe.json \
  --baseline baseline.csv \
  --candidate candidate.jsonl \
  --output run
parison verify run
```

The distinct-row limit is a hard safety bound, not a sample size. Exceeding it returns `ERROR`; Parison never samples toward `PASS`. Existing byte, decoded-byte, row, mutation and publication integrity checks remain active.

## Reading the result

`PASS` means both complete inputs have equal multiplicity for every canonical row. `FAIL` means at least one row shape has a surplus on one side. The result reports total rows, common occurrences, one-sided occurrences, distinct-row counts and surplus-shape counts. These counts conserve independently:

```text
baseline_rows  = common_occurrences + baseline_only_occurrences
candidate_rows = common_occurrences + candidate_only_occurrences
```

Summary sensitivity contains counts only. Raw sensitivity includes a bounded, deterministic sample of row shapes with baseline and candidate multiplicities. Raw evidence is sensitive and must remain customer-side.

An equal aggregate total is not row equality. A set of rows is not a multiset: `[A, A]` versus `[A]` fails because occurrence counts differ.

## Supported identity rules

All configured scalar columns participate in exact identity. Null equals null in the same column; empty string differs from null. Decimal values use their declared scale. Timestamps compare as timezone-aware instants. Floats must be finite. Tolerances, fuzzy pairing, positional pairing, subset allowances, nested values and custom expressions are not supported by multiset-v1.

Multiset comparison is local and deterministic. It does not upload source data, require a server or infer a mode from failed key discovery.
