# Parison 1.8.0 release checklist

Date: 19 October 2026

Status: **candidate preparation**

## Capability gate

- [x] JSON document projection selects one flat record array through an
  explicit RFC 6901 JSON Pointer across all comparison modes, drafting,
  portable suites and strict preflight schemas v7--v9.
- [x] XML record projection selects repeated flat records through an explicit
  bounded QName path and namespace bindings, with streaming depth, node and
  text limits plus DTD/entity and nested-field rejection in schemas v10--v12.
- [x] XLSX named-table projection resolves one exact table name and stored
  rectangle while preserving formula/error rejection, ZIP limits,
  `semantic-scalar-v1`, all comparison modes, portable suites and strict
  preflight schemas v13--v15.
- [x] Released recipes, result schemas, bundle readers, canonical values, CLI
  JSON and exit codes remain unchanged; schemas v1--v12 remain readable and
  byte-stable.

## Qualification

- [x] Feature checkpoints received fresh blind review and their recorded
  exact-commit built-wheel and quality CI passed.
- [x] Combined Standards and Spec review findings are corrected with
  regressions; `make check` passes 380 tests with 11 expected optional-Polars
  skips.
- [x] Exact combined checkpoint
  `defb65fac85ac0bc8eac48b2f6f70af3ebb07bcc` passes the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39201282230)
  on Python 3.11--3.14, Linux, macOS and Windows, plus the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39201282259).
- [x] The exact combined CI wheel passes fresh Python 3.14 named-table
  preflight, comparison and bundle verification.
- [ ] Review `origin/main...develop`, run the exact candidate CI, and qualify
  clean-archive artifacts with hashes and a fresh primary-workflow smoke.

## Publication

- [ ] Reviewed candidate is merged to `main` and exact-merge CI passes.
- [ ] Exact-merge wheel, source and checksums are published under annotated
  tag `1.8.0` and publicly re-verified.
- [ ] All release records identify the same tested commit and assets.

Internal qualification supports deterministic development evidence only. It
does not establish extraction truth, policy approval, migration approval or
cutover authorization.
