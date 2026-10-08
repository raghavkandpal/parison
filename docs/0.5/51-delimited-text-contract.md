# Delimited-text contract

Date: 8 October 2026

## Decision

CSV and TSV parsing is controlled by reviewed recipe policy. A recipe may declare independent delimiters for the two inputs:

```json
"delimiters": {
  "baseline": "\t",
  "candidate": "|"
}
```

Each delimiter must be exactly one character and cannot be a quote, newline or NUL. Omitting `delimiters` preserves the existing comma default for both sides.

The `.csv` and `.tsv` extensions identify delimited-text containers; they do not override a reviewed recipe. Drafting uses the extension only to propose a safe starting policy: tab for `.tsv` and comma otherwise. The user must still review the generated recipe. CSV and TSV are distinct partition formats, so one partition directory cannot silently mix them.

## Consistency and evidence

The selected delimiter is used for header inspection, preflight and record comparison, including `.csv.gz` and `.tsv.gz`. Baseline and candidate may use different delimiters.

Effective delimiters appear in `parison explain`, contribute to `policy_sha256`, and are recorded for delimited inputs in preflight and comparison metadata. They contain no record values and do not weaken summary-mode privacy.

JSON Lines, Parquet and SQLite readers ignore delimiter policy. Null-token interpretation is a separate, unfinished 0.5 slice; this contract does not change the existing distinction between null and an empty string.
