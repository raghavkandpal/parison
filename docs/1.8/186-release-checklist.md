# Parison 1.8.0 release checklist

Date: 19 October 2026

Status: **released**

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
- [x] Fresh Standards review of `origin/main...develop` reports no code or
  contract blocker. Combined independent Spec review covers all semantic
  implementation through `defb65f`; the subsequent candidate-only delta is
  version and release-evidence metadata and was checked directly.
- [x] Exact candidate-preparation commit
  `7e16e69011b86ac4fcc7af0a2ba57d6dbe240df0` passes the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39201636279)
  and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39201636500).
- [x] A clean `git archive` of that commit built the 1.8.0 wheel and source
  archive. Wheel SHA-256 is
  `8dba9465008dfb65f7986d1560ca1fe304e13047f721ebd5a16142697a533863`;
  source SHA-256 is
  `820a046f7b7366f011c5e703b8b33d6b281bff95a9f976ee628c37c20a1bf876`.
- [x] A fresh Python 3.14 environment installed the clean-archive wheel with
  its declared test/XLSX dependencies. JSON Pointer, bounded XML path and XLSX
  named-table inputs each produced a two-row PASS with two exact matches, and
  each published bundle verified successfully.

## Publication

- [x] [Pull request #50](https://github.com/raghavkandpal/parison/pull/50)
  merged the reviewed candidate as
  `511b1bbc9c68a581760939b72690255ec545dbbb`; exact-merge
  [test run 39230867633](https://github.com/raghavkandpal/parison/actions/runs/39230867633)
  and [quality run 39230867642](https://github.com/raghavkandpal/parison/actions/runs/39230867642)
  passed.
- [x] Exact-merge wheel SHA-256 is
  `17dc6fcdb93d129a4ebbbf1ff90bf192574ab8d8010e5e1ee5f8b8dd271da82f`;
  source SHA-256 is
  `c41514a93718408e2d02e55633deb36d6ae66cd8758a2ed9aa22d7d537ff7a0b`.
- [x] Annotated tag `1.8.0` identifies the exact merge and the
  [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/1.8.0)
  publishes the wheel, source archive and checksums.
- [x] Public assets were re-downloaded and checksum-verified. A fresh Python
  3.14 environment installed the public wheel; JSON Pointer, bounded XML path
  and XLSX named-table comparisons each produced a two-row PASS and a valid
  verified bundle.
- [x] All release records identify the same tested commit and assets.

Internal qualification supports deterministic development evidence only. It
does not establish extraction truth, policy approval, migration approval or
cutover authorization.
