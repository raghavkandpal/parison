# Null-token contract

Date: 8 October 2026

## Decision

Delimited exports may encode null with text such as `NULL` or `\N`. A recipe can map those tokens independently for each input:

```json
"null_tokens": {
  "baseline": ["NULL"],
  "candidate": ["\\N"]
}
```

Tokens are exact, case-sensitive, nonempty strings. Each side's list must be unique. An omitted policy defaults to empty lists, and `draft-recipe` emits empty lists rather than guessing from record values. Reviewers must opt into every destructive text-to-null conversion.

## Semantics

Token mapping applies only while reading CSV or TSV, before configured column types are parsed. It therefore works consistently for strings, numbers, dates and other declared types. Native nulls in JSON Lines, Parquet and SQLite keep their existing semantics and text values in those formats are not reinterpreted.

The empty string cannot be a null token. For string columns, an empty field remains `""` and compares differently from null. Existing non-string empty-field parsing remains unchanged.

Configured tokens appear in `parison explain`, contribute to `policy_sha256`, and are recorded in preflight and comparison input metadata. Tokens are parsing policy, not sampled record values; summary mode still records no keys or field values.
