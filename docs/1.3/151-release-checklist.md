# Parison 1.3.0 release checklist

Date: 15 October 2026

Status: **released**

## Capability gate

- [x] Frozen `time-alignment-v1` and `reconciliation-v1` contracts preserve the local-first and explicit-policy boundary.
- [x] Alignment, per-dataset parity, identity, reference and conservation predicates reduce conservatively without changing released recipe or bundle meanings.
- [x] Memory and bounded SQLite relationship engines produce identical deterministic evidence.
- [x] Reconciliation publication is atomic, no-overwrite, symlink-safe and cleans private staging/temporary state on failure or interruption.
- [x] Full evidence binds inputs and receipt identity; summary-safe output excludes paths, dataset/check/column names, keys, groups, values, tokens, receipt contents and samples.
- [x] The realistic cross-format payout fixture passes both engines and standard bundle verification.
- [x] Independent Standards and Spec reviews report no release blockers.

## Exact candidate

- [x] `make check` passes from the final candidate worktree (303 tests; 11 expected optional-Polars skips).
- [x] Version and release records identify 1.3.0 without changing released compatibility fixtures.
- [x] Exact candidate `b25db9962698a370ff0703da8cc7d7c23abcabc5` passes [built-wheel CI run 38862223479](https://github.com/raghavkandpal/parison/actions/runs/38862223479) on Python 3.11–3.14, Linux, macOS and Windows with pinned Polars 1.44.2.
- [x] A clean archive builds inspected wheel/source artifacts.
- [x] A fresh Python 3.14 environment installs the candidate wheel and passes version inspection plus the complete SQLite reconciliation, verification and summary-safe inspection workflow.
- [x] Candidate commit, CI run and artifact SHA-256 digests are recorded here.

Candidate SHA-256:

- `parison-1.3.0-py3-none-any.whl`: `8320feaed9e940604de0a8f434ab50b68f7172b0af91050e5099334380ce4b6b`
- `parison-1.3.0.tar.gz`: `e1032fefd9c07d213c7653e238c3f6643cdfeb5c78234ae19daedfc69275f9a1`

## Publication

- [x] [Pull request 38](https://github.com/raghavkandpal/parison/pull/38) merged the reviewed candidate to `main` at `3aec4fb0b7355aea94aa81d8a8a7c5e3372414ea`; exact-merge [CI run 38862675947](https://github.com/raghavkandpal/parison/actions/runs/38862675947) passed.
- [x] Publishable wheel, source archive and checksums were built from a clean archive of the exact merge.
- [x] Annotated tag `1.3.0` identifies the exact merge and [GitHub release 1.3.0](https://github.com/raghavkandpal/parison/releases/tag/1.3.0) publishes the tested artifacts; PyPI remains intentionally deferred.
- [x] Public assets were re-downloaded and checksum-verified, then installed fresh under Python 3.14; the complete SQLite reconciliation, verification and inspection workflow passed.
- [x] Roadmap, checklist, changelog, README, documentation index and current-state record identify the published release.

Published SHA-256:

- `parison-1.3.0-py3-none-any.whl`: `97b837e594a11160c04cdda43a29ffde5e0b7ee77b7fb8abcbdcdcbd95233cbf`
- `parison-1.3.0.tar.gz`: `e20fa5d1f6aa6e6b6a516e7208d146138a7d77d3f75d651e78a6c882c095982a`

Do not mark 1.3.0 released until the code, tag, public assets and release records identify the same tested commit.
