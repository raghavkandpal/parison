# Parison 0.5 user guide

This guide extends the [0.3 user guide](../0.3/33-user-guide.md) with reviewed parsing policy for common local exports.

## 1. Draft and review parsing policy

`draft-recipe` writes explicit `delimiters` and `null_tokens` for both sides. It safely suggests tab for a `.tsv` container and comma otherwise. It never guesses null tokens from data; both lists start empty. Review these fields alongside keys, types, mappings and normalization before validation.

## 2. Declare source representations

Set a one-character delimiter and any exact, case-sensitive null tokens independently for each side:

```json
"delimiters": {"baseline": "\t", "candidate": "|"},
"null_tokens": {"baseline": ["NULL"], "candidate": ["\\N"]}
```

An empty string is not a null token. Tokens apply only to CSV and TSV; JSON Lines, Parquet and SQLite retain native null handling.

## 3. Preflight and compare

The checked-in [`examples/0.5`](../../examples/0.5) workflow combines a gzip TSV baseline, pipe-delimited candidate, renamed columns, different null tokens and string normalization:

```sh
parison validate-inputs \
  --recipe examples/0.5/migration.recipe.json \
  --baseline examples/0.5/baseline.tsv.gz \
  --candidate examples/0.5/candidate.csv

parison compare \
  --recipe examples/0.5/migration.recipe.json \
  --baseline examples/0.5/baseline.tsv.gz \
  --candidate examples/0.5/candidate.csv \
  --output runs/0.5-example
```

The comparison passes while preserving the reviewed representations in the policy fingerprint and summary-only evidence.

## Support boundary

Parison still uses file extensions rather than content sniffing. ZIP, additional codecs, recursive discovery, arbitrary encodings and automatic delimiter or null-token inference remain out of scope.
