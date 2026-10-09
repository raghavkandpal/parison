# Parison 0.9 release checklist

Status: **in progress**

## Investigation slice

- [x] Verified bundle inspection with safe metadata only.
- [x] Bundle digest and policy provenance are exposed by inspection.
- [x] Bounded atomic JSON Lines evidence export.
- [x] Classification filtering and hard export limits.
- [x] Summary bundles rejected for evidence export.
- [x] Cross-platform CI inspection smoke coverage.
- [x] Add a dedicated v0.9 raw evidence fixture with a nonzero discrepancy sample.
- [x] Add tampered-bundle and overwrite/refusal integration tests.

## Release gates

- [x] Freeze the inspect/export schema and compatibility contract.
- [ ] Run the full Python/platform matrix from the release candidate.
- [ ] Build and install a clean wheel, then run inspect/export smoke tests.
- [ ] Record checksums and publish only after all evidence is attached.

Do not tag 0.9 until every unchecked item has a reproducible result.
