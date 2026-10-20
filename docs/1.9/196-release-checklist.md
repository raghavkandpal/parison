# Parison 1.9.0 release checklist

Date: 20 October 2026

Status: **released**

## Capability gate

- [x] JSON per-field projection uses explicit RFC 6901 pointers relative to
  selected document records under recipe versions 4--6.
- [x] XML field projection uses exact record attributes or bounded unique
  child paths with policy-owned namespaces and a closed record shape.
- [x] XLSX defined-name projection resolves one exact non-reserved,
  workbook-scoped static name to one local absolute bounded rectangle.
- [x] All three capabilities cover keyed, aggregate and multiset comparison,
  memory and SQLite execution, portable suites, strict preflight evidence and
  summary-safe output.
- [x] Recipe versions 1--3, released schemas, canonical values, result and
  bundle readers, CLI JSON and exit codes remain unchanged.

## Qualification

- [x] Every feature checkpoint received fresh blind Standards and Spec review
  and passed exact-commit built-wheel and quality CI.
- [x] Combined Standards and Spec review passed after correcting strict
  preflight source/projection pairing in schemas v16--v18 and v22--v24.
- [x] Full `make check` passes 400 tests with 11 expected optional dependency
  skips.
- [x] Exact combined checkpoint
  `75e5ea03b0fe6d837273379959a9c65dcf4a88d4` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39369155164)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39369155085).
- [x] Exact candidate commit
  `6876da905bc795fa49568b80ccf13866cc80f31d` passed the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39369300738)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39369300726).
- [x] A clean `git archive` of that commit produced inspected 1.9.0 artifacts.
  Wheel SHA-256 is
  `add915edb3f7c390902f9d3c1e1f54e082eaf7acaa43c4f2b2d149a0b48d560b`;
  source SHA-256 is
  `619cec591992bafc217d7eebaea6d2ab99a72ef44334686f234e6495a01b4581`.
- [x] A fresh Python 3.14 environment installed the clean-archive wheel with
  declared test/XLSX dependencies, reported version 1.9.0 and passed all 20
  JSON, XML and XLSX structured-selection workflow tests, including bundle
  verification.

## Publication

- [x] [Pull request #52](https://github.com/raghavkandpal/parison/pull/52)
  merged the reviewed candidate as
  `703e5b9daa39e9165f7bced933354061af0d5f89`; exact-merge
  [built-wheel CI](https://github.com/raghavkandpal/parison/actions/runs/39369665801)
  and [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39369665788)
  passed.
- [x] Exact-merge wheel SHA-256 is
  `7c02fc36d5c3d8d516d2fb33476164377478522f712743a340250c1fd8751ea2`;
  source SHA-256 is
  `f09c3e7da0b8539becfab910e9a339a433c703bb5c9029bac5cb7eb9a0645cd6`.
- [x] Annotated tag `1.9.0` identifies the exact merge and the
  [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/1.9.0)
  publishes the wheel, source archive and checksums.
- [x] Public assets were downloaded fresh and checksum-verified. A fresh
  Python 3.14 environment installed the public wheel, reported version 1.9.0
  and passed all 20 JSON, XML and XLSX structured-selection workflow tests,
  including bundle verification.
- [x] All release records identify the same tested commit and assets.
- [x] Development stops after the verified 1.9.0 release; no 2.0 implementation
  begins.

Internal qualification supports deterministic development evidence only. It
does not establish extraction truth, policy approval, migration approval or
cutover authorization.
