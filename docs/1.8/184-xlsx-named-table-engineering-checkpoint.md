# XLSX named-table engineering checkpoint

Date: 19 October 2026

Status: **released in 1.8.0**

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

Exact feature checkpoint `2631575988a545aa655a3aa3b836d17522237d28`
passes 380 local tests with 11 expected optional-Polars skips, the full
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39200813257)
and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39200813324).

This completed all three required 1.8 features. Combined review, exact-merge
qualification and public-asset verification are recorded in the 1.8 release
checklist.
