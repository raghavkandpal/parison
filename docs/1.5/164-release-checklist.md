# Parison 1.5.0 release checklist

Date: 17 October 2026

Status: **candidate preparation**

## Capability gate

- [x] Frozen contract preserves zero custody and explicit policy.
- [x] All released comparison modes produce exhaustive, deterministic and summary-safe groups.
- [x] Series require distinct runs under one exact policy and preserve caller order.
- [x] Raw drill-down is bounded to already-published samples and never reopens inputs.
- [x] Strict schema, semantic verification, atomic publication, realistic rehearsal and user guide are present.
- [ ] Independent Standards and Spec reviews report no release blockers.

## Exact candidate

- [x] `make check` passes (331 tests; 11 expected optional-Polars skips).
- [x] Exact implementation checkpoint `957fe2a47cec26e46c7de7da4317a317c69b23a7` passes [built-wheel CI run 39016303344](https://github.com/raghavkandpal/parison/actions/runs/39016303344) on Python 3.11–3.14, Linux, macOS and Windows.
- [ ] Exact versioned candidate passes the same matrix.
- [ ] Clean-archive wheel and source hashes are recorded.
- [ ] A fresh supported-Python environment installs the candidate wheel and passes the complete three-run analysis and drill-down workflow.

## Publication

- [ ] Reviewed candidate is merged to `main` and exact-merge CI passes.
- [ ] Wheel, source archive and checksums are rebuilt from the exact merge.
- [ ] Annotated tag `1.5.0` and GitHub release identify that merge; PyPI remains intentionally deferred.
- [ ] Public assets are re-downloaded, checksum-verified and smoke-tested fresh.
- [ ] Roadmap, checklist, changelog, README, documentation index and current-state record identify the release.

Do not mark 1.5.0 released until code, tag, public assets and release records identify the same tested commit.
