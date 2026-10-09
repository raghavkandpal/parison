# Parison 0.7.0 release checklist

Date: 9 October 2026

Status: **in development**. Product behavior is implemented; cross-platform and packaging gates remain.

- [x] Freeze aggregate-v1 semantics and privacy boundaries.
- [x] Add strict recipe v2, preflight v2 and result v2 schemas.
- [x] Preserve keyed-v1 recipe, result and bundle behavior.
- [x] Implement bounded global and grouped aggregation with exact decimal accumulation.
- [x] Add aggregate-aware drafting, preflight, comparison, reporting and verification.
- [x] Check in a cross-format example and user guide.
- [x] Add adversarial empty, null, missing-group, tolerance, reordering and group-limit fixtures.
- [x] Add reproducible global, low-cardinality and high-cardinality benchmark oracles.
- [ ] Pass Python 3.11–3.14 CI with all installed schemas and optional Parquet.
- [ ] Pass macOS and Windows smoke jobs.
- [ ] Build and inspect clean wheel and source archives.
- [ ] Install the wheel in an empty environment and repeat keyed and aggregate smoke workflows.
- [ ] Move changelog entries to 0.7.0 and set the final package version.
- [ ] Merge the release commit, tag `0.7.0`, publish checksums and verify downloaded assets.
