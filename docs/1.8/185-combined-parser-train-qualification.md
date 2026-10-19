# Combined parser-train qualification

Date: 19 October 2026

Status: **released in 1.8.0**

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

The corrected combined checkpoint is
`defb65fac85ac0bc8eac48b2f6f70af3ebb07bcc`. It passes `make check` with 380
tests on Python 3.14, 11 expected optional-Polars skips, and a clean
`git diff --check 82f1156...HEAD`. The exact commit passed the complete
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39201282230)
on Python 3.11--3.14, Linux, macOS and Windows, plus the
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39201282259).

The wheel produced by that exact CI run was downloaded and installed into a
fresh Python 3.14 environment with openpyxl 3.1.5. A new workbook containing
the exact named table `Orders` passed strict record preflight under schema v13,
keyed comparison with two exact matches, and bundle verification. The
comparison used the wheel's installed `parison` command rather than the source
checkout. The combined train advanced as a single 1.8 candidate.

[Pull request #50](https://github.com/raghavkandpal/parison/pull/50) merged that
candidate as `511b1bbc9c68a581760939b72690255ec545dbbb`. Exact-merge CI,
clean-archive rebuilding, annotated tag and public-asset verification completed
before 1.8.0 was recorded as released; full publication evidence is in the
[release checklist](186-release-checklist.md).

This evidence is internal development qualification only. It does not establish
extraction truth, policy approval, migration approval or cutover authorization.
