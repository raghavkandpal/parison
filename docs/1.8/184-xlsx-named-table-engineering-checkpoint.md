# XLSX named-table engineering checkpoint

Date: 19 October 2026

Status: **feature gate complete locally; exact-commit CI pending**

The third feature in the 1.8 parser train is implemented. The explicit
`xlsx:path#table=Name` locator resolves one exact openpyxl table name, uses its
normalized `ref` as the bounded header-and-data rectangle, and feeds the
released `semantic-scalar-v1` row boundary. The released worksheet rectangle,
all three comparison modes, both engines, drafting, portable suites, ZIP
limits, formula/error rejection and summary-safe source identity remain
unchanged. Strict preflight schemas v13--v15 add named-table metadata without
changing schemas v1--v12.

Table discovery reads only bounded package metadata while values remain
read-only streaming. Missing or inconsistent relationships, escaping package
targets, duplicate relationship/table names, identifiers or targets, malformed
part counts, absent/wrong-case names, header-only or unbounded refs, totals,
calculated formulas, stored-cell formulas/errors and table/header disagreement
fail closed.

Fresh blind review found and corrected ignored missing relationships, unsafe
package targets, incomplete workbook-wide identity checks, loose v13--v15
discrimination, missing preflight projection enforcement, unnormalized table
refs and unchecked table-part counts. Regression coverage pins every finding.

Local completion gate: `make check` passes 380 tests on Python 3.14 with 11
expected optional-Polars skips. A coherent commit, push, exact-commit
built-wheel matrix and fresh-wheel named-table smoke remain.

This completes all three required 1.8 features locally. It is not a release
candidate and must not be tagged or published before combined review and
qualification.
