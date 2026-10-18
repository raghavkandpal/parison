# XLSX values projection research

Date: 18 October 2026

Status: **accepted after explicit scope approval**

## Question and evidence

Can Parison admit local spreadsheet exports without inheriting spreadsheet
execution semantics or weakening deterministic input policy?

ECMA-376 packages an `.xlsx` workbook as an Open Packaging Conventions ZIP
package containing workbook, worksheet, style, relationship and shared-string
parts. A file suffix alone therefore does not identify a logical table, and
compressed size is not a sufficient resource bound. The normative format is
published by [Ecma International](https://ecma-international.org/publications-and-standards/standards/ecma-376/).

openpyxl documents read-only mode as lazy loading for large files and requires
the workbook to be explicitly closed. Its loading API also distinguishes
formula text from the last cached value through `data_only`; cached values are
workbook state, not formula evaluation. See the primary
[optimized-mode documentation](https://openpyxl.readthedocs.io/en/stable/optimized.html)
and [`load_workbook` API](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html#openpyxl.reader.excel.load_workbook).

These facts support a values adapter only when table selection and formula
handling are explicit. They do not support active-sheet selection, used-range
inference, formula calculation or general spreadsheet compatibility.

## Design consequences

- Require `xlsx:path#worksheet!range`; never infer a sheet or range.
- Require one bounded rectangular range whose first row is a unique,
  non-empty string header and whose remaining rows are records.
- Load read-only with formula text visible and external-link preservation
  disabled; reject formulas and error cells instead of trusting cached values.
- Require `semantic-scalar-v1`; admit only values already allowed by the
  closed policy-directed scalar projection. Convert a style-declared Excel
  date to a Python date; reject timezone-naive spreadsheet datetimes for a
  timestamp policy.
- Hash and size the complete workbook. Bound both physical bytes and the sum
  of ZIP members' declared uncompressed sizes before XML parsing; reject
  encrypted archives and excessive member counts.
- Record format, worksheet, range, ZIP compression and decoded bytes in full
  evidence while keeping source paths out of result JSON.
- Use the pinned optional `openpyxl==3.1.5` dependency and exercise the built
  wheel on Python 3.11--3.14, Linux, macOS and Windows.

## Threats

- ZIP bombs and oversized XML can exhaust resources; physical and decoded
  limits plus a member-count ceiling are mandatory.
- Formula caches can be stale or absent; rejecting formulas avoids presenting
  workbook calculation state as extracted truth.
- Workbook display can conceal merged cells, hidden rows, formatting and
  filters. The adapter reads only cell values in the declared rectangle and
  makes no claim that displayed content or business intent was reproduced.
- Spreadsheet dates use styles and workbook epochs. Date-only styles are
  normalized to calendar dates; timestamps remain safe only as explicit
  timezone-bearing text.
- External relationships can disclose or depend on remote state. Core
  execution does not follow or preserve them.

## Non-goals

- `.xls`, `.xlsb`, `.xlsm`, OpenDocument, macros, charts, pivots or images;
- formula evaluation, cached-formula acceptance or Excel recalculation;
- active-sheet, table, named-range or used-range discovery;
- partitioned workbook directories;
- editing, repair, password handling or remote workbook access;
- treating a successful parse as extraction truth or cutover approval.

## Acceptance gate

The feature is accepted only when direct and mixed-format comparisons,
drafting and record preflight pass in all three comparison modes; malformed,
implicit, formula-bearing, oversized and semantically lossy inputs fail
closed; released artifacts remain readable; installed schemas validate new
preflight output; and the built-wheel platform matrix plus a fresh-wheel XLSX
smoke pass.
