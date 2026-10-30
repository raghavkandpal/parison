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
- [ ] Full built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix passes on
  the exact candidate head.
- [ ] Review `origin/main...develop` against the six contracts and repository
  invariants; resolve every release blocker.
- [ ] Build wheel and source archive from a clean `git archive` of the exact
  candidate commit; inspect metadata, contents and SHA-256 hashes.
- [ ] Install the wheel in a fresh supported-Python environment and exercise
  the primary six-feature workflow from the installed package.
- [ ] Record exact candidate commit, CI run, artifact hashes, smoke results and
  merge the qualified checkpoint to `develop` through a green PR.

## Publication decision and later gates

Release merge, tag and publication require a separate decision under
[RELEASING.md](../../RELEASING.md). If authorized, merge a release PR from
`develop` to `main`, require CI on the exact merge, build fresh artifacts from
that merge, complete external gates, tag and publish, re-download and smoke the
public assets, then reconcile release records. Internal qualification does not
approve migration policy, extraction truth or cutover.
