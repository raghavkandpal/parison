# Combined parser-train qualification

Date: 19 October 2026

Status: **combined review corrections complete locally; exact-commit CI pending**

The JSON Pointer, bounded QName XML and XLSX named-table features are complete
as one three-feature 1.8 train. Exact XLSX checkpoint
`2631575988a545aa655a3aa3b836d17522237d28` passed the full
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39200813257)
and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39200813324).

Independent combined review covered the complete diff from train freeze
`82f11569a2e03c47041e978e5af13c8164331e7f` along separate Standards and Spec
axes. Standards found extra EOF whitespace in schemas v7--v12; Spec found that
summary-mode XLSX results exposed the named selector and XML accepted an
explicit non-UTF-8 declaration. All findings are corrected with regressions.
Named-table tests also exercise keyed, aggregate and multiset comparison under
both memory and SQLite engines. The maintainability review noted repeated
internal format dispatch as a judgement-call smell; it remains deliberately
unchanged during qualification to avoid widening released-path risk.

The corrected combined gate passes `make check` with 380 tests on Python 3.14,
11 expected optional-Polars skips, and a clean
`git diff --check 82f1156...HEAD`. Exact-commit CI and a fresh built-wheel
named-table smoke remain before any candidate decision.

This evidence is internal development qualification only. It does not establish
extraction truth, policy approval, migration approval or cutover authorization.
