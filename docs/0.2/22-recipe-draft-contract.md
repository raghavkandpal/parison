# Recipe draft contract

Date: 6 October 2026

## Purpose

`parison draft-recipe` removes JSON transcription work by inspecting two local inputs and writing a complete starting recipe. Inferred values are suggestions for human review, not proof that the comparison policy is correct.

This is scaffolding, not automatic approval.

## Command

```sh
parison draft-recipe \
  --baseline path/to/baseline.csv \
  --candidate path/to/candidate.csv \
  --output comparison.recipe.json
```

The output path must not already exist. Inputs follow the same regular-file, symlink, size and supported-format boundaries as comparison. The command reads row values for inference but does not retain or publish them.

## Suggested draft

- Exact column names present on both sides become `columns` entries in baseline order.
- Types are inferred conservatively from both inputs. Empty columns default to strings, numeric-looking values with significant leading zeroes remain strings, decimals retain the largest observed scale, and comparisons default to exact.
- `keys` contains a unique, non-null combination, preferring identifier-like columns (`id`, `key` or `code`). Other columns are considered only when those columns cannot form a key.
- `scope.snapshot` names the two input stems and `scope.cutoff` uses the newer file modification time. Filters default to none, completeness to `full`, and expected-empty reflects whether both inputs have no rows.
- Identity rules are fixed to rejecting null keys and duplicates. Those safety invariants are not configurable in keyed-v1.
- `nulls_equal` defaults to true.
- Columns present on only one side appear in `excluded_columns` with a side-specific rationale.
- Output sensitivity is `summary`. Raw evidence is never suggested.
- No tolerance is generated. An author may add a keyed-v1 numeric policy and tolerance only after selecting a numeric type.

The generated structure passes recipe validation so the reviewer edits concrete values instead of filling blanks. Validation checks structure, not whether an inference is semantically correct.

## Refusals

Drafting fails without writing output when either schema cannot be read, a column name is duplicated, no columns are shared, an input changes during inspection, the combined byte limit is exceeded, or the destination already exists. Empty inputs are acceptable only when their format still provides a schema, such as a header-only CSV or typed Parquet file.

The command never infers tolerances or claims that suggested identity and scope are approved. If no unique combination exists, it falls back to the first shared column so the uncertainty remains visible during review and comparison preflight.

## Review workflow

1. Run `draft-recipe` once. It refuses to overwrite an existing file.
2. Review the exact shared-column list and reconcile unintended one-sided columns.
3. Confirm the suggested key columns and their exact comparison policy.
4. Replace the suggested snapshot, cutoff, filters, completeness and empty-scope values with the actual extraction contract where needed.
5. Confirm null equality and every inferred type. Add numeric tolerance only where the policy needs it.
6. Confirm every intentional exclusion and its rationale.
7. Run `parison validate-recipe comparison.recipe.json`.
8. Run `parison compare` with the reviewed recipe. Drafting alone never authorizes comparison.

The generated file is the checklist. Its concrete values make review faster, but the reviewer remains the authority for semantic choices.

## Compatibility

The draft is ordinary JSON shaped like recipe v1; no second recipe model or permissive parser is introduced. Existing validation remains the authority. `compare` continues to accept only a valid recipe, so an unresolved draft cannot produce PASS.
