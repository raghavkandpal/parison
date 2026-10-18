# Parison 1.6 roadmap

Status: **active**

Theme: one maintained workflow entry point backed by the real CLI

## Scope

1. Record the adoption evidence, boundary and completion gate.
2. Add a deterministic standard-library command-reference generator and pin
   its output with a focused drift test.
3. Replace the frozen 0.19 entry point with a stable current 1.x guide that
   covers all released workflows through discrepancy analysis.
4. Make the README and documentation index point to the stable current pages;
   preserve versioned guides as historical records.
5. Verify focused documentation tests, the full local check and the required
   built-wheel platform matrix before preparing 1.6.0.

## Compatibility

This release changes documentation and contributor checks only. It does not
change recipe, result, schema, bundle, canonical-byte, CLI JSON or exit-code
contracts. The generated reference describes the existing parser and creates
no independently supported machine-readable interface.

## Completion gate

- `python scripts/generate_command_reference.py --check`
- `make test TEST=tests.test_documentation`
- `make check`
- built-wheel CI on Python 3.11--3.14, Linux, macOS and Windows
- fresh-wheel smoke of the documented entry workflow
