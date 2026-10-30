# Parison 2.3.0 release checklist

Date: 30 October 2026
Status: candidate qualification in progress; no release decision

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
- [ ] Merge this qualification record to `develop` through a green PR with the
  exact record head passing the full built-wheel matrix.

## Publication decision and later gates

Release merge, tag and publication require a separate decision under
[RELEASING.md](../../RELEASING.md). If authorized, merge a release PR from
`develop` to `main`, require CI on the exact merge, build fresh artifacts from
that merge, complete external gates, tag and publish, re-download and smoke the
public assets, then reconcile release records. Internal qualification does not
approve migration policy, extraction truth or cutover.
