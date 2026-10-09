# Aggregate comparison user guide

Date: 9 October 2026

Aggregate comparison reconciles declared group coverage and measures when row identity is unavailable or irrelevant. It does not establish row equality. Prefer keyed comparison whenever stable unique keys exist and row-level evidence matters.

## Run the example

The checked-in example compares CSV with JSON Lines, groups by normalized region, checks row counts exactly, and allows a one-cent absolute difference in regional revenue:

```sh
PYTHONPATH=src python -m parison validate-recipe examples/0.7/revenue.recipe.json
PYTHONPATH=src python -m parison explain examples/0.7/revenue.recipe.json
PYTHONPATH=src python -m parison validate-inputs --records \
  --recipe examples/0.7/revenue.recipe.json \
  --baseline examples/0.7/baseline.csv \
  --candidate examples/0.7/candidate.jsonl
PYTHONPATH=src python -m parison compare \
  --recipe examples/0.7/revenue.recipe.json \
  --baseline examples/0.7/baseline.csv \
  --candidate examples/0.7/candidate.jsonl \
  --output runs/aggregate-example
PYTHONPATH=src python -m parison verify runs/aggregate-example
```

The comparison passes with one exact regional sum and one sum within tolerance. Summary output contains no region names or per-region aggregate values.

## Draft, review and lock

Use `--aggregate` explicitly; Parison never guesses that row identity is unnecessary:

```sh
PYTHONPATH=src python -m parison draft-recipe --aggregate \
  --baseline BASELINE --candidate CANDIDATE --output aggregate.recipe.json
```

The draft suggests at most one repeated, non-null grouping column, always adds a row-count measure, and suggests sums for non-identifier integer and decimal columns. Before approval, review the scope, group semantics, every operator, every null policy, and whether exact or tolerant comparison expresses the intended claim. Then record the fingerprint from `explain` in CI.

Use `--max-groups` on preflight and comparison when the default 100,000-group memory bound is inappropriate. Raising it increases memory exposure; it does not change comparison semantics.

## Reading outcomes

- PASS means group coverage matches and every declared measure is exact or within tolerance.
- FAIL means a group exists on only one side or a common-group measure violates policy.
- INCONCLUSIVE means the run could not form the declared comparison, such as a null group, rejected null measure or unexpected empty input.
- ERROR means the recipe, input container or environment could not be used safely.

Raw sensitivity includes bounded group and aggregate evidence. Treat it as sensitive data. Summary aggregates are reconciliation evidence, not a privacy or de-identification mechanism.
