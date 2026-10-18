# Parison 1.7.0 release checklist

Date: 18 October 2026

Status: **candidate qualified**

## Capability gate

- [x] Direct aggregate SQLite execution matches the memory semantic oracle
  across PASS, FAIL, INCONCLUSIVE, empty, raw and summary cases after removing
  only the three documented operational fields.
- [x] Suite-v2 supports aggregate SQLite cases and verifiable success and
  controlled-error child bundles.
- [x] Row, group and storage limits, invalid parents, cleanup and interruption
  fail closed.
- [x] Accuracy-checked machine-specific benchmarks cover 10,000-row low- and
  high-cardinality aggregate workloads under both engines.
- [x] Released recipes, result schemas, bundle readers and canonical semantics
  remain unchanged.

## Qualification

- [x] Focused aggregate, suite and benchmark tests pass.
- [x] `make check` passes with 363 tests and 11 expected optional-Polars skips.
- [x] Independent Standards and Spec re-reviews report no blockers.
- [x] Exact implementation checkpoint
  `74a87f48564190f6637a37682dcd55790904bc21` passes
  [built-wheel CI run 39140670513](https://github.com/raghavkandpal/parison/actions/runs/39140670513)
  on Python 3.11--3.14, Linux, macOS and Windows, plus
  [quality run 39140670525](https://github.com/raghavkandpal/parison/actions/runs/39140670525).
- [x] Clean-archive artifacts and a fresh Python 3.14 SQLite aggregate smoke
  pass; hashes and results are recorded in the engineering checkpoint.

## Publication

- [ ] Reviewed candidate is merged to `main` and exact-merge CI passes.
- [ ] Exact-merge wheel, source and checksums are published under annotated
  tag `1.7.0` and publicly re-verified.
- [ ] All release records identify the same tested commit and assets.
