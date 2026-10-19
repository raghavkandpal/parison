# XLSX defined-name engineering checkpoint

Status: **implementation complete; qualification pending**

The third feature in the 1.9 release train is implemented. An explicit
`xlsx:path#defined-name=Name` locator performs case-sensitive lookup of one
non-reserved workbook-scoped defined name, then admits only one static local
worksheet destination with an absolute bounded rectangle containing a header
and at least one data row.

The reader audits raw workbook metadata before trusting openpyxl's normalized
collection. Empty declarations, duplicate names within a scope, global/local
conflicts, invalid local sheet scopes and excessive declaration counts fail
closed. A streaming pre-load scan rejects non-ASCII-compatible metadata, DTDs
and entity declarations before parsing. Constants, formulas, dynamic or relative references, unions, external
workbooks, missing worksheets, 3-D references and whole-row or whole-column
ranges remain outside the contract.

The resolved rectangle reuses the released XLSX header, formula/error,
semantic-scalar, ZIP, physical/decoded byte and row limits. Keyed, aggregate
and multiset modes pass under memory and SQLite execution. Portable suite-v2
plans preserve the exact defined name while resolving only the workbook path.
Summary comparison evidence hides the name, worksheet and range; full and
preflight evidence retain them. Strict preflight schemas v19--v24 add the six
recipe/mode combinations without changing v1--v18.

Fresh blind Spec review found one coverage gap and no behavior defect: recipe
versions 4--6 now exercise both engines with record-validating preflight.
Fresh blind Standards/security review drove pre-load metadata bounds, numeric
scope normalization and DTD/entity plus UTF-16 bypass rejection; final
re-review passed with no remaining blocker. Full `make check` passes 399 tests
on Python 3.14 with 11 optional dependency skips. Exact-commit built-wheel CI
remains required before this checkpoint is qualified. This is not a release
candidate and must not be tagged or published independently.
Internal evidence does not establish extraction truth, policy approval,
migration approval or cutover authorization.
