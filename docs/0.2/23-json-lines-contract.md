# JSON Lines input contract

Date: 6 October 2026

## Scope

Parison accepts local `.jsonl` and `.ndjson` files as tabular inputs to keyed-v1. Either side may independently be CSV, Parquet or JSON Lines. Format changes do not create a new recipe type or result model.

## Records and schema

- Input is UTF-8 with one JSON object per physical line. Empty files, blank lines and non-object records are errors.
- Object keys must be nonempty strings. Duplicate JSON keys are errors rather than last-value-wins.
- The first record establishes column order for drafting. Every later record must contain exactly the same keys; missing or additional fields are errors.
- Recipe header validation is unchanged: compared columns must exist, undeclared columns require an explicit exclusion, and names are exact.
- Values must be JSON scalars: string, number, boolean or null. Arrays and objects are rejected, including in excluded columns, so unsupported data cannot hide behind policy.

## Scalar mapping

JSON scalar spellings enter the existing recipe parser without binary-float coercion: strings retain their contents, numbers retain their JSON lexical text, booleans map to lowercase `true` or `false`, and JSON null maps to null. The recipe remains responsible for string, integer, decimal, float, boolean, date and timezone-aware timestamp semantics.

Nonstandard `NaN`, `Infinity` and `-Infinity` tokens are errors. Decimal scale and finite-float checks remain unchanged. This mapping makes a CSV/JSONL comparison equivalent when both encode the same logical scalar text under the same recipe.

## Safety and limits

The existing regular-file and symlink refusal applies. Combined input bytes are checked before reading, rows count against `--max-rows`, and Ctrl-C follows the existing interrupted-bundle path. Parsing stops at the first malformed line and reports its line number without copying row values into summary artifacts.

Drafting reads JSON Lines records to validate the schema and suggest types and keys from observed values. These suggestions require review. An empty JSON Lines file cannot supply a schema and is rejected.

## Usage

No format flag or JSONL-specific recipe is needed. File suffixes select the reader, so mixed inputs use the normal commands:

```sh
parison draft-recipe --baseline baseline.csv --candidate candidate.jsonl --output comparison.recipe.json
# review and complete the draft
parison validate-recipe comparison.recipe.json
parison compare --recipe comparison.recipe.json \
  --baseline baseline.csv --candidate candidate.jsonl --output runs/mixed-input
```

Use `.jsonl` or `.ndjson`; a generic `.json` file is not assumed to be record-delimited. The resulting `result.json`, report and manifest have the same schema as CSV/Parquet comparisons.

## Rejections

Reject malformed UTF-8/JSON, duplicate keys, blank lines, non-object records, empty keys, inconsistent field sets, nested values, unsupported suffixes, changing inputs and resource-limit overruns. None of these conditions may be converted into an empty comparison or PASS.
