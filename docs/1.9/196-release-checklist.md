# Parison 1.9.0 release checklist

Date: 20 October 2026

Status: **candidate preparation**

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
- [ ] Exact candidate commit passes built-wheel and quality CI.
- [ ] A clean archive of the exact candidate produces inspected wheel and
  source artifacts with recorded SHA-256 hashes.
- [ ] A fresh supported-Python environment installs that wheel and passes the
  primary JSON, XML and XLSX 1.9 workflows with verified bundles.

## Publication

- [ ] Reviewed candidate is merged to `main` and exact-merge CI passes.
- [ ] Exact-merge wheel, source and checksums are published under annotated
  tag `1.9.0` and publicly re-verified.
- [ ] All release records identify the same tested commit and assets.
- [ ] Development stops after the verified 1.9.0 release; no 2.0 work begins.

Internal qualification supports deterministic development evidence only. It
does not establish extraction truth, policy approval, migration approval or
cutover authorization.
