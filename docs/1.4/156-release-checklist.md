# Parison 1.4.0 release checklist

Date: 16 October 2026

Status: **candidate**

## Capability gate

- [x] Frozen manifest and diagnostic contracts preserve zero custody and explicit policy.
- [x] Named resources and optional reviewed scopes fail closed on traversal, links, aliases, mutation, SQLite sidecars and undeclared membership.
- [x] Dataset evidence atomically binds full verification, effective policy, diagnostic and complete semantic result.
- [x] Summary-safe output excludes source paths, resource identifiers, keys, values and samples.
- [x] Independent Standards and Spec reviews report no release blockers.

## Exact candidate

- [x] `make check` passes (318 tests; 11 expected optional-Polars skips).
- [x] Exact implementation checkpoint `e81e92b27cc6823b8a511e41cfda733fd95648da` passes [built-wheel CI run 38895998570](https://github.com/raghavkandpal/parison/actions/runs/38895998570) on Python 3.11–3.14, Linux, macOS and Windows.
- [ ] Exact versioned candidate commit and clean-archive artifact hashes recorded.
- [ ] Fresh-wheel manifest, reconciliation, publication, verification and inspection smoke passed.

## Publication

- [ ] Reviewed pull request merged to `main`; exact-merge CI passed.
- [ ] Wheel, source archive and checksums built from the exact merge.
- [ ] Annotated tag `1.4.0` and GitHub release identify the exact merge.
- [ ] Public assets re-downloaded, checksum-verified and smoke-tested from a fresh install.
- [ ] Roadmap, checklist, changelog, README, documentation index and current-state record identify the release.

Do not mark 1.4.0 released until code, tag, public assets and release records identify the same tested commit.
