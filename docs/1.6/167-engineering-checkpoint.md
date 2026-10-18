# Parison 1.6 engineering checkpoint

Date: 18 October 2026

Status: **expanded candidate qualified**

## Delivered capability

- One maintained task guide and a deterministic reference generated from the
  real CLI parser cover the complete current 1.x workflow.
- The opt-in `xlsx:path#Worksheet!A1:F1000` locator reads only one explicit
  worksheet rectangle through the released `semantic-scalar-v1` projection.
- Keyed, aggregate and multiset drafting, record preflight, comparison,
  mixed-format execution, SQLite-backed execution, suites and verifiable
  bundles use the same projected values.
- Strict installed preflight schemas v4--v6 add XLSX worksheet, range and ZIP
  metadata without changing released schemas v1--v3.
- Formula and error cells, including headers, malformed archives, duplicate
  headers and archive members, symlinks, implicit selection, resource-limit
  overruns and timezone-naive datetimes fail closed.

## Qualification

- `make check` passes 358 tests with 11 expected optional-Polars skips.
- Exact implementation checkpoint
  `54ab13a473440a46f43c32842fa0de283129476e` passed
  [built-wheel CI run 39118401039](https://github.com/raghavkandpal/parison/actions/runs/39118401039)
  on Python 3.11--3.14, Linux, macOS and Windows; the separate
  [quality run 39118401059](https://github.com/raghavkandpal/parison/actions/runs/39118401059)
  also passed.
- A clean archive of that checkpoint produced a wheel with the pinned
  `openpyxl==3.1.5` XLSX extra. A fresh Python 3.14 environment installed the
  wheel, passed all 12 XLSX workflow tests and reported version 1.6.0.
- Candidate SHA-256:
  - wheel: `07498b8d23c7321e664ae11fadecdb001269f353648d2f703c1ef78db0bb15de`
  - source: `68245ebe717e0d40a59ac701f08a97fecc00586494defe365e78e01c7f62a69c`
- Independent Standards review found no documented-standard violations.
  Independent Spec review found one header-cell rejection defect and two
  proof gaps; all were corrected and covered before the exact checkpoint.

## Preserved boundaries

XLSX support is explicit, local and read-only. It does not evaluate formulas,
discover sheets or ranges, fetch remote workbooks, repair inputs or infer
policy. Recipe versions, comparison result schemas, bundle semantics,
canonical bytes, CLI JSON and exit codes remain unchanged. PASS still means
agreement under the explicit policy, not extraction truth, approval or
cutover authorization.
