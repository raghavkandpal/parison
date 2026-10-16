# Parison 1.4.0 release checklist

Date: 16 October 2026

Status: **released**

## Capability gate

- [x] Frozen manifest and diagnostic contracts preserve zero custody and explicit policy.
- [x] Named resources and optional reviewed scopes fail closed on traversal, links, aliases, mutation, SQLite sidecars and undeclared membership.
- [x] Dataset evidence atomically binds full verification, effective policy, diagnostic and complete semantic result.
- [x] Summary-safe output excludes source paths, resource identifiers, keys, values and samples.
- [x] Independent Standards and Spec reviews report no release blockers.

## Exact candidate

- [x] `make check` passes (318 tests; 11 expected optional-Polars skips).
- [x] Exact implementation checkpoint `e81e92b27cc6823b8a511e41cfda733fd95648da` passes [built-wheel CI run 38895998570](https://github.com/raghavkandpal/parison/actions/runs/38895998570) on Python 3.11–3.14, Linux, macOS and Windows.
- [x] Exact versioned candidate `55012d72a8e62e91a92ee2b1487cea134814f21a` passes [built-wheel CI run 38896322656](https://github.com/raghavkandpal/parison/actions/runs/38896322656); clean-archive artifact hashes are recorded below.
- [x] A fresh Python 3.14 environment installed the candidate wheel and passed version, manifest, SQLite reconciliation, dataset-evidence publication, verification and summary-safe inspection.

Candidate SHA-256:

- `parison-1.4.0-py3-none-any.whl`: `ce461967c006a58723d950f2077672a888b1f7d987cc57239ad8a4233a1cb039`
- `parison-1.4.0.tar.gz`: `9a4b5ead96deb62805bb1f42bc2a7c0a7e25692b5c764222562335e5e764ebc6`

## Publication

- [x] [Pull request 40](https://github.com/raghavkandpal/parison/pull/40) merged the reviewed candidate to `main` at `13eb551f216595297d012d3ea4b06fbe65670d0e`; exact-merge [CI run 38896813377](https://github.com/raghavkandpal/parison/actions/runs/38896813377) passed.
- [x] Wheel, source archive and checksums were built from a clean archive of the exact merge.
- [x] Annotated tag `1.4.0` identifies the exact merge and [GitHub release 1.4.0](https://github.com/raghavkandpal/parison/releases/tag/1.4.0) publishes the tested artifacts; PyPI remains intentionally deferred.
- [x] Public assets were re-downloaded and checksum-verified, then installed fresh under Python 3.14; the complete manifest, SQLite reconciliation, dataset-evidence publication, verification and inspection workflow passed.
- [x] Roadmap, checklist, changelog, README, documentation index and current-state record identify the release.

Published SHA-256:

- `parison-1.4.0-py3-none-any.whl`: `ccc887a2977d5ae031815bec28d9fa885c9ae59d78289cccb22958a560672b25`
- `parison-1.4.0.tar.gz`: `989705efbd2edefe1a692f1dafb89259c439c76f3234373c67fd441e44a59851`

Do not mark 1.4.0 released until code, tag, public assets and release records identify the same tested commit.
