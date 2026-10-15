# Parison 1.3.0 release checklist

Date: 15 October 2026

Status: **candidate preparation**

## Capability gate

- [x] Frozen `time-alignment-v1` and `reconciliation-v1` contracts preserve the local-first and explicit-policy boundary.
- [x] Alignment, per-dataset parity, identity, reference and conservation predicates reduce conservatively without changing released recipe or bundle meanings.
- [x] Memory and bounded SQLite relationship engines produce identical deterministic evidence.
- [x] Reconciliation publication is atomic, no-overwrite, symlink-safe and cleans private staging/temporary state on failure or interruption.
- [x] Full evidence binds inputs and receipt identity; summary-safe output excludes paths, dataset/check/column names, keys, groups, values, tokens, receipt contents and samples.
- [x] The realistic cross-format payout fixture passes both engines and standard bundle verification.
- [ ] Independent Standards and Spec reviews report no release blockers.

## Exact candidate

- [ ] `make check` passes from the final candidate worktree.
- [ ] Version and release records identify 1.3.0 without changing released compatibility fixtures.
- [ ] Exact candidate passes built-wheel CI on Python 3.11–3.14, macOS and Windows with pinned Polars 1.44.2.
- [ ] A clean archive builds inspected wheel/source artifacts.
- [ ] A fresh environment installs the candidate wheel and passes the complete reconciliation smoke workflow.
- [ ] Candidate commit, CI run and artifact SHA-256 digests are recorded here.

## Publication

- [ ] Reviewed candidate is merged to `main`; exact-merge CI passes.
- [ ] Publishable wheel, source archive and checksums are built from the exact merge.
- [ ] Annotated tag `1.3.0` and GitHub release publish the exact tested artifacts; PyPI remains intentionally deferred.
- [ ] Public assets are re-downloaded, checksum-verified and smoke-tested in a fresh environment.
- [ ] Roadmap, checklist, changelog, README, documentation index and current-state record identify the published release.

Do not mark 1.3.0 released until the code, tag, public assets and release records identify the same tested commit.
