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

The scan uses the same readers, delimiters, null tokens, column mappings, types, normalization and keys as comparison. A configured value that cannot be parsed makes the structured validation status `invalid`; malformed input syntax or an unreadable source remains an operational error. Null key components or duplicate typed keys also make the status `invalid`.

## Diagnostics and privacy

Each input gains a `records` object containing `status`, `rows`, `invalid_rows`, `invalid_fields`, `null_key_rows` and `duplicate_keys`. `invalid_rows` counts each affected record once, while `invalid_fields` maps canonical configured field names to failure counts. Duplicate counts describe distinct duplicated identities, matching comparison's identity rule. A record with an invalid non-key field still contributes to identity diagnostics; a record whose key cannot be parsed cannot. The output never includes a key, field value or parser exception.

Standard output remains the complete machine-readable preflight object. When `--records` is active, standard error also prints concise row, invalid-row, null-key and duplicate-key counts for each side. Per-field counts remain in the JSON diagnostics.

The installed preflight JSON Schema accepts these diagnostics while keeping them optional for schema-only callers.

## Limits and stability

The existing combined physical-byte, decoded-gzip-byte and policy-fingerprint gates apply. `--max-rows` defaults to five million per input. Record validation rejects a source whose digest changes during the scan.

The command validates each side independently; it does not compare coverage or field equality and cannot return PASS or FAIL. Use `compare` after validation for that decision.
