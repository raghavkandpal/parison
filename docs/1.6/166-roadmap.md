# Parison 1.6 roadmap

Status: **candidate qualified**

Theme: one maintained workflow plus an explicit local XLSX values boundary

## Scope

1. Record the adoption evidence, boundary and completion gate. **Complete.**
2. Add a deterministic standard-library command-reference generator and pin
   its output with a focused drift test.
   **Complete.**
3. Replace the frozen 0.19 entry point with a stable current 1.x guide that
   covers all released workflows through discrepancy analysis.
   **Complete.**
4. Make the README and documentation index point to the stable current pages;
   preserve versioned guides as historical records.
   **Complete.**
5. Verify focused documentation tests, the full local check and the required
   built-wheel platform matrix before preparing 1.6.0.
   **Complete.**
6. Specify and implement a narrow `.xlsx` values projection after explicit
   scope approval: workbook path, worksheet and bounded rectangle are all
   required; formulas and implicit workbook semantics fail closed.
   **Complete.**
7. Qualify keyed, aggregate and multiset comparison, drafting, preflight,
   mixed-format execution and wheel installation across the full platform
   matrix. **Complete.**

## Compatibility

The workflow work changes documentation and contributor checks only. XLSX is
an opt-in input adapter selected by a new locator and the already released
`semantic-scalar-v1` policy. Recipes, comparison and result contracts,
bundles, canonical bytes and exit codes stay unchanged. New preflight schema
versions describe XLSX metadata without changing released schemas.

## Completion gate

- `python scripts/generate_command_reference.py --check`
- `make test TEST=tests.test_documentation`
- `make test TEST=tests.test_xlsx`
- `make check`
- built-wheel CI on Python 3.11--3.14, Linux, macOS and Windows
- fresh-wheel smoke of the documented XLSX workflow
