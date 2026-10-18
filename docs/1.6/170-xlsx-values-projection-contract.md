# XLSX values projection contract

Status: **implementation contract**

## Locator and selection

An XLSX input is selected with:

```text
xlsx:path/to/export.xlsx#Worksheet!A1:F1000
```

The `xlsx:` prefix, local `.xlsx` path, exact worksheet name and bounded
rectangle are mandatory. The first row is the header. Every subsequent row in
the rectangle is one record, including an all-blank row. Header cells must be
non-empty strings and unique. Query parameters, missing selections, whole-row
or whole-column ranges, symlinks and partition directories are rejected.

Shells may interpret `!`, so quote the complete locator when needed.

## Values and policy

XLSX inputs require the existing recipe field:

```json
{"input_projection": "semantic-scalar-v1"}
```

Strings, booleans, finite numeric values, nulls and style-declared dates enter
the existing closed projection. Recipe column types still decide whether each
source scalar is admissible and how it is parsed. Formula and error cells in
the selected data rectangle are errors. Spreadsheet datetimes are
timezone-naive and therefore cannot satisfy a timestamp column; export a
timezone-bearing ISO 8601 string instead.

Parison does not apply filters, hidden-row state, formatting or calculation.
It reads the declared rectangle's stored values only. `null_tokens` and
delimiters do not apply to XLSX cells.

## Limits and evidence

`--max-input-bytes` bounds the workbook's physical size and
`--max-decoded-bytes` bounds the combined uncompressed ZIP member sizes.
`--max-rows` counts data rows after the header. Workbooks with encrypted ZIP
members or more than 10,000 members fail closed.

Full input evidence records `format: xlsx`, `worksheet`, `range`,
`compression: zip`, physical `bytes`, `decoded_bytes` and the complete-file
SHA-256 digest. It does not record the source path. XLSX-aware preflight emits
schema v4 for keyed, v5 for aggregate and v6 for multiset recipes; released
preflight schemas v1--v3 are unchanged.

## Compatibility boundary

Comparison modes, recipe versions, policy fingerprints, canonical scalar and
row encodings, comparison result schemas, evidence bundles, CLI exit codes and
historical readers are unchanged. `dataset-manifest-v1` remains unchanged and
does not admit XLSX resources; publish upstream workbook-to-supported-format
extraction evidence separately when a manifest-bound handoff is required.
