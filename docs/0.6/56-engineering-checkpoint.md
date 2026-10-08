# Parison 0.6 engineering checkpoint

Date: 8 October 2026

## Verified head

Commit `b2c139f` passed 122 tests on Python 3.11–3.14, macOS and Windows in [run 37780670159](https://github.com/raghavkandpal/parison/actions/runs/37780670159). Every matrix job installed Polars 1.44.2; the main jobs also validated all installed JSON Schemas and ran the checked-in record-validation smoke command.

## Covered behavior

- Schema-only `validate-inputs` remains backward-compatible and does not scan all records.
- `validate-inputs --records` applies the same formats, parsing policy, types, mappings, normalization and typed keys as comparison.
- Structured results report only aggregate row, invalid-row, invalid-field, null-key and duplicate-key counts and validate against the installed preflight schema.
- Physical, decoded and row limits plus the reviewed policy fingerprint remain enforced.
- Input mutation during a record scan is rejected.
- Invalid source values cannot escape through standard-library parse messages, terminal diagnostics or summary error bundles.
- Record validation continues after configured type failures, while malformed source syntax remains an operational error.
- Interactive summaries use standard error, preserving machine-readable JSON on standard output.

## Next boundary

Do not add multiset, aggregate or remote comparison modes merely to fill 0.6. The next slice should respond to observed workflow friction or deepen the completed validation path without changing keyed-v1 outcomes.
