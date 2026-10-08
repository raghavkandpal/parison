# Record-validation contract

Date: 8 October 2026

## Decision

`parison validate-inputs` remains a fast schema-only preflight by default. Passing `--records` additionally scans both complete logical inputs under the reviewed recipe:

```sh
parison validate-inputs --records \
  --recipe comparison.recipe.json \
  --baseline baseline.tsv.gz \
  --candidate candidate.csv
```

The scan uses the same readers, delimiters, null tokens, column mappings, types, normalization and keys as comparison. A malformed configured value is an operational error. Null key components or duplicate typed keys make the structured validation status `invalid`.

## Diagnostics and privacy

Each input gains a `records` object containing `status`, `rows`, `null_key_rows` and `duplicate_keys`. Duplicate counts describe distinct duplicated identities, matching comparison's identity rule. The output never includes a key or field value.

The installed preflight JSON Schema accepts these diagnostics while keeping them optional for schema-only callers.

## Limits and stability

The existing combined physical-byte, decoded-gzip-byte and policy-fingerprint gates apply. `--max-rows` defaults to five million per input. Record validation rejects a source whose digest changes during the scan.

The command validates each side independently; it does not compare coverage or field equality and cannot return PASS or FAIL. Use `compare` after validation for that decision.
