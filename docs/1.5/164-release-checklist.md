# Parison 1.5.0 release checklist

Date: 17 October 2026

Status: **candidate preparation**

## Capability gate

- [x] Frozen contract preserves zero custody and explicit policy.
- [x] All released comparison modes produce exhaustive, deterministic and summary-safe groups.
- [x] Series require distinct runs under one exact policy and preserve caller order.
- [x] Raw drill-down is bounded to already-published samples and never reopens inputs.
- [x] Strict summary/raw schemas, semantic verification, atomic publication, realistic rehearsal and user guide are present.
- [x] Review findings for canonical fixtures, policy explanations, descriptor vocabulary, raw verification, catalog integrity and the completion matrix are corrected locally.
- [x] Independent Standards and Spec re-review report no release blockers.

## Exact candidate

- [x] The post-review local gate passes (342 tests; 11 expected optional-Polars skips).
- [x] Exact implementation checkpoint `957fe2a47cec26e46c7de7da4317a317c69b23a7` passes [built-wheel CI run 39016303344](https://github.com/raghavkandpal/parison/actions/runs/39016303344) on Python 3.11–3.14, Linux, macOS and Windows.
- [x] Corrected candidate `d19b8b769c5fb8cf5764a380c3fcde53c194c2c8` passes [CI run 39036296368](https://github.com/raghavkandpal/parison/actions/runs/39036296368) on Python 3.11–3.14, Linux, macOS and Windows.
- [x] Clean local build hashes are recorded: wheel `9be77df7bb7f857053d0c74b00d0782ce183d3de59c55eda324308ef30a0cd83`; source archive `ccc23132ae2be7dfe408f603d587eea53a27a1e875b75312e683d0283215126d`.
- [x] A fresh Python 3.12 environment installs the candidate wheel, discovers both installed analysis schemas and passes the complete three-run analysis and drill-down workflow.

## Publication

- [ ] Reviewed candidate is merged to `main` and exact-merge CI passes.
- [ ] Wheel, source archive and checksums are rebuilt from the exact merge.
- [ ] Annotated tag `1.5.0` and GitHub release identify that merge; PyPI remains intentionally deferred.
- [ ] Public assets are re-downloaded, checksum-verified and smoke-tested fresh.
- [ ] Roadmap, checklist, changelog, README, documentation index and current-state record identify the release.

Do not mark 1.5.0 released until code, tag, public assets and release records identify the same tested commit.
