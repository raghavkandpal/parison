# Recipe draft contract

Date: 6 October 2026

## Purpose

`parison draft-recipe` removes JSON transcription work without converting observed data into trusted comparison policy. It inspects two local inputs, writes a deterministic draft, and exits successfully when the draft file is written. The draft is intentionally rejected by `parison validate-recipe` until a person or calling agent resolves every policy choice.

This is scaffolding, not automatic approval.

## Command

```sh
parison draft-recipe \
  --baseline path/to/baseline.csv \
  --candidate path/to/candidate.csv \
  --output comparison.recipe.json
```

The output path must not already exist. Inputs follow the same regular-file, symlink, size and supported-format boundaries as comparison. The command reads schema information only; it does not need to retain or publish row values.

## Deterministic draft

- Exact column names present on both sides become `columns` entries in baseline order.
- Every shared column starts with `{"type": "REVIEW_REQUIRED", "comparison": "exact"}`. Types are not inferred from values or storage metadata because string identity, decimal scale and timestamp policy are semantic choices.
- `keys` is empty.
- `scope.snapshot` and `scope.cutoff` are empty; `scope.filters` is empty; `scope.completeness` is `REVIEW_REQUIRED`; `scope.expected_empty` is null.
- Identity rules are fixed to rejecting null keys and duplicates. Those safety invariants are not configurable in keyed-v1.
- `nulls_equal` is null.
- Columns present on only one side appear in `excluded_columns` with an empty rationale. The author must either justify each exclusion or reconcile the inputs.
- Output sensitivity is `summary`. Raw evidence is never suggested.
- No tolerance is generated. An author may add a keyed-v1 numeric policy and tolerance only after selecting a numeric type.

These sentinels deliberately violate recipe v1 validation. The draft becomes valid only after keys, scope, null equality, every column type, every exclusion rationale and any desired tolerance have been reviewed.

## Refusals

Drafting fails without writing output when either schema cannot be read, a column name is duplicated, no columns are shared, an input changes during inspection, the combined byte limit is exceeded, or the destination already exists. Empty inputs are acceptable only when their format still provides a schema, such as a header-only CSV or typed Parquet file.

The command never guesses key candidates, treats a unique observed column as identity, infers tolerances, approves exclusions, or claims the two datasets have comparable scope.

## Compatibility

The draft is ordinary JSON shaped like recipe v1; no second recipe model or permissive parser is introduced. Existing validation remains the authority. `compare` continues to accept only a valid recipe, so an unresolved draft cannot produce PASS.
