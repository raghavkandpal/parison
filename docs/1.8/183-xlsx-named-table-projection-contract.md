# XLSX named-table projection contract

Status: **implementation contract**

## Locator and selection

```text
xlsx:path/to/export.xlsx#table=Orders
```

The `xlsx:` prefix, local `.xlsx` regular file and `#table=` selector are
mandatory. The non-empty table name is matched exactly against openpyxl's
worksheet table collections. Case folding, prefix matching, worksheet hints,
named ranges, active-sheet selection and table discovery are rejected.

The selected table's `ref` is the complete rectangle. It must be bounded,
contain exactly one header row and at least one data row, and declare no totals
row. Table-column names must exactly equal the stored header cells in order.
The table rectangle is never expanded or reduced from populated cells.

The released `xlsx:path#worksheet!A1:F1000` rectangle remains unchanged.

## Values and policy

Named-table inputs require `input_projection: semantic-scalar-v1`. Every data
row in the table rectangle is one record, including an all-blank row. The
released scalar, date, formula, error and timezone rules apply unchanged.
Calculated-column and totals-row formulas in table metadata are rejected in
addition to formulas and errors in any selected cell.

Filters, hidden state, styles, sort state, calculation, cached values, query
refresh and external links do not affect selection or projected values.

## Limits and evidence

The released physical-byte, decoded-ZIP-byte, member-count, encryption, row
and symlink limits apply before table metadata is trusted. Metadata resolution
reads bounded workbook parts and cell extraction remains read-only streaming.

Full evidence records `format: xlsx`, exact `table`, resolved `worksheet` and
normalized `range`, ZIP compression, physical and decoded byte counts and the
whole-file SHA-256. Summary-safe output continues to exclude source paths,
selection names, keys, values and discrepancy samples. Keyed, aggregate and
multiset preflight use strict schemas v13--v15; schemas v1--v12 are unchanged.

## Compatibility boundary

Drafting, portable suites, both execution engines and all three comparison
modes preserve the exact table selector. Recipe versions, policy fingerprints,
canonical scalar and row encodings, results, bundles, CLI exit codes and
historical readers are unchanged. Selection is not extraction truth, policy
approval, migration approval or cutover authorization.

Named ranges, dynamic tables, totals interpretation, formula evaluation,
`.xls`, `.xlsb`, `.xlsm`, macros, editing and repair are out of scope.
