# Parison 1.6.0 release checklist

Date: 18 October 2026

Status: **candidate preparation**

## Capability gate

- [x] One stable task guide covers every current 1.x workflow family.
- [x] The generated reference covers every root and nested CLI command.
- [x] Drift checks bind reference text, guide syntax and repository-local links
  to the checked-in parser and tree.
- [x] Historical contracts and guides remain unchanged.
- [x] Recipes, schemas, evidence, canonical bytes, CLI JSON and exit codes are
  unchanged.

## Exact candidate

- [x] The post-correction local gate passes (345 tests; 11 expected
  optional-Polars skips).
- [x] Exact implementation checkpoint
  `891f377bf70cc13e3a80e7982c62e4f6ea547d29` passes
  [built-wheel CI run 39100830901](https://github.com/raghavkandpal/parison/actions/runs/39100830901)
  on Python 3.11--3.14, Linux, macOS and Windows.
- [x] Exact versioned candidate
  `f70e990a383bf367c4b8e344ee921704bd85088d` passes
  [built-wheel CI run 39100944127](https://github.com/raghavkandpal/parison/actions/runs/39100944127)
  and [quality run 39100944155](https://github.com/raghavkandpal/parison/actions/runs/39100944155).
- [x] Clean-archive wheel and source hashes are recorded below.
- [x] A fresh Python 3.14 environment installs the wheel and completes version,
  initialization, recipe/input validation, direct comparison and bundle
  verification.
- [x] Review of `origin/main...develop` reports no release blockers.

Candidate SHA-256:

- `parison-1.6.0-py3-none-any.whl`:
  `495e1dd0424a8d4cb9a561602f9ceec166c157a5db9328159ca8abab8bbc12d0`
- `parison-1.6.0.tar.gz`:
  `1c4ca256d484ab900deff9ef8429eca9a4b8dadc0ec8e0436a65314e77c37dd7`

## Publication

- [ ] The reviewed pull request is merged to `main` and exact-merge CI passes.
- [ ] Exact-merge assets are rebuilt from a clean archive.
- [ ] Annotated tag `1.6.0` identifies the exact merge and the GitHub release
  publishes wheel, source archive and checksums.
- [ ] Public assets are re-downloaded, checksum-verified and smoke-tested.
- [ ] Roadmap, checklist, changelog, README, documentation index and current
  state identify the release.

Do not mark 1.6.0 released until code, tag, public assets and release records
identify the same tested commit.
