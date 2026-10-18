# Parison 1.7.0 release checklist

Date: 18 October 2026

Status: **released**

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

- [x] [Pull request #48](https://github.com/raghavkandpal/parison/pull/48)
  merged the reviewed candidate as
  `5da6e08dc97c4bdef3f57c6b71a272b42d7ea171`; exact-merge
  [test run 39141006519](https://github.com/raghavkandpal/parison/actions/runs/39141006519)
  and [quality run 39141006521](https://github.com/raghavkandpal/parison/actions/runs/39141006521)
  passed.
- [x] Exact-merge wheel SHA-256 is
  `e95ed71704469998904ad3c631d8a43d81ef98e6eb78938df2fb09a207c51112`;
  source SHA-256 is
  `cd7ed510f930ab9d8150259792525a437eb442ce8a8bdcd8cc4dccded7d362e1`.
- [x] Annotated tag `1.7.0` identifies the exact merge and the
  [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/1.7.0)
  publishes the wheel, source archive and checksums.
- [x] Public assets were re-downloaded and checksum-verified. A fresh Python
  3.14 environment installed the public wheel and completed a 1,000-group
  SQLite aggregate comparison, bundle verification and inspection.
- [x] All release records identify the same tested commit and assets.
