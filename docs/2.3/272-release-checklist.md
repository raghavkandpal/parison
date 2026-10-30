# Parison 2.3.0 release checklist

Date: 30 October 2026
Status: **released** at exact tested merge `a2884534d3ffa7364e3344dc3d514aa775ac79a9`

## Completed train

All six substantial capabilities in the [roadmap](246-six-feature-roadmap.md)
are integrated on `develop` at `92c9799`:

1. PostgreSQL one-table evidence ingress: [PR #93](https://github.com/raghavkandpal/parison/pull/93).
2. Coordinated multi-table acquisition: [PR #96](https://github.com/raghavkandpal/parison/pull/96).
3. Fast exact partition discovery: [PR #99](https://github.com/raghavkandpal/parison/pull/99).
4. Selective exact investigation: [PR #102](https://github.com/raghavkandpal/parison/pull/102).
5. PostgreSQL 16→18 rehearsal: [PR #104](https://github.com/raghavkandpal/parison/pull/104).
6. Portable decision dossier: [PR #106](https://github.com/raghavkandpal/parison/pull/106).

The additive [CLI command-name migration](273-cli-command-alias-contract.md)
merged through [PR #109](https://github.com/raghavkandpal/parison/pull/109)
before candidate qualification. Its exact head `e448218` passed 575 local
tests, independent Standards/Spec review, quality CI and the [full built-wheel
matrix](https://github.com/raghavkandpal/parison/actions/runs/41008120189).
The four shipped standalone commands remain supported. CLI consolidation is
not a seventh feature credit.

## Candidate qualification

- [x] The rebased 2.3 candidate passes `make check` with Python 3.14:
  Ruff, generated command reference, 575 tests and diff checks. Workbench
  tests required local loopback socket permission.
- [x] Exact source candidate `c6d0f7e5bfb3ea16dee70971f0fdf947d8bfa4d8`
  passed the [full built-wheel Python 3.11–3.14 Linux/macOS/Windows
  matrix](https://github.com/raghavkandpal/parison/actions/runs/41008538770)
  and PR quality CI.
- [x] Independent Standards and Spec review of `origin/main...c6d0f7e`
  found no cross-feature code blocker. The record drift it found is corrected
  in this qualification update; historical CRLF fixture bytes remain intact.
- [x] A clean `git archive` of `c6d0f7e` built
  `parison-2.3.0-py3-none-any.whl` (SHA-256
  `5a52d3efc729d1e71f982a9c71ab6e56b7de655e3ff6b6dc68a14d549631f63e`)
  and `parison-2.3.0.tar.gz` (SHA-256
  `b959b41a8f68371397c12873229f2a3ce3bafcf23bee5d811858c29a89c95db9`).
  Wheel metadata reports 2.3.0 and Python >=3.11; it contains 31 Python
  modules, 90 schemas and all four shipped standalone scripts. The source
  archive contains 56 test files.
- [x] A fresh Python 3.14 environment installed that wheel from the archive,
  imported Parison from site-packages and passed all 575 tests (11 optional
  Polars skips). Its installed `parison` command verified the portable dossier
  fixture offline and exposed the new PostgreSQL, partition and rehearsal help.
- [x] [Qualification PR #108](https://github.com/raghavkandpal/parison/pull/108)
  merged to `develop` at `853ba219ba553d5c8fb580d2b57075bdd92b4db9`.
  Its exact record head `1991393bd25d6ee217558f93421dce154c5a8c44`
  passed PR quality CI and the [full built-wheel
  matrix](https://github.com/raghavkandpal/parison/actions/runs/41008901275).
  The exact integration merge also passed the [full built-wheel
  matrix](https://github.com/raghavkandpal/parison/actions/runs/41009134595).

## Publication

- [x] The owner authorized release on 30 October 2026. [Release PR
  #111](https://github.com/raghavkandpal/parison/pull/111) merged `develop` to
  `main` at `a2884534d3ffa7364e3344dc3d514aa775ac79a9`. The exact merge
  passed [quality CI](https://github.com/raghavkandpal/parison/actions/runs/41009685519)
  and the [full built-wheel Python 3.11–3.14 Linux/macOS/Windows
  matrix](https://github.com/raghavkandpal/parison/actions/runs/41009685413).
- [x] A fresh `git archive` of that merge built
  `parison-2.3.0-py3-none-any.whl` (SHA-256
  `e074c4bceddb5c23499aa7a94d7ee0d2810996a869f815b1e723947a0159f52c`)
  and `parison-2.3.0.tar.gz` (SHA-256
  `80936617cd349896677bf8174f0db74d0d3a25f41214f80c1a111b72b949de2e`).
  Wheel metadata reports 2.3.0 and Python >=3.11, with 31 modules, 90 schemas
  and all four shipped standalone commands. A fresh Python 3.14 installation
  passed 575 tests with 11 optional Polars skips, then verified the portable
  dossier fixture offline through the installed command.
- [x] No release-specific external gate was required before tagging. Annotated
  tag [`2.3.0`](https://github.com/raghavkandpal/parison/releases/tag/2.3.0)
  peels to the exact tested merge. The [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/2.3.0)
  publishes that merge-built wheel, source archive and `SHA256SUMS`; PyPI was
  not requested.
- [x] All three public assets were re-downloaded. Both archives matched the
  published `SHA256SUMS` (SHA-256
  `bbcaf3c37e67916f93610262edbc6bd1618a33cd3d39e64fe9d532ba59c99fbc`)
  and the merge-built bytes. A fresh Python 3.14 install of the public wheel
  imported from site-packages, passed all 575 tests with 11 optional Polars
  skips, exposed the new command paths, and verified the offline dossier
  fixture.
- [x] Reconcile this checklist, changelog, documentation index, maintained
  user guide, README and current state in the post-release records PR to
  `develop`.

Internal qualification and public release do not establish extraction truth,
policy approval, signer identity, migration approval or cutover authorization.
