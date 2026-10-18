# Parison 1.7.0 release checklist

Date: 18 October 2026

Status: **implementation in progress**

## Capability gate

- [ ] Direct aggregate SQLite execution matches the memory semantic oracle.
- [ ] Suite-v2 supports aggregate SQLite cases and verifiable child bundles.
- [ ] Storage limits, cleanup and interruption fail closed.
- [ ] Accuracy-checked machine-specific benchmarks cover aggregate spill.
- [ ] Released recipes, result schemas, bundle readers and canonical semantics
  remain unchanged.

## Qualification

- [ ] Focused aggregate, suite, benchmark and documentation tests pass.
- [ ] `make check` passes.
- [ ] Independent Standards and Spec reviews report no blockers.
- [ ] Exact candidate built-wheel CI passes on Python 3.11--3.14, macOS and
  Windows.
- [ ] Clean-archive artifacts and fresh-wheel aggregate smoke pass.

## Publication

- [ ] Reviewed candidate is merged to `main` and exact-merge CI passes.
- [ ] Exact-merge wheel, source and checksums are published under annotated
  tag `1.7.0` and publicly re-verified.
- [ ] All release records identify the same tested commit and assets.
