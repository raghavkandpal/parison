# Parison 0.9 release checklist

Status: **released**

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
- [x] Run the full Python/platform matrix from the release candidate.
- [x] Build and install a clean wheel, then run inspect/export smoke tests.
- [x] Record candidate checksums and attach the reproducible evidence before publication.

Do not tag 0.9 until every unchecked item has a reproducible result.

Released as [0.9.0](https://github.com/raghavkandpal/parison/releases/tag/0.9.0) from commit `e849f7c3e801f9d61dbdc2e74d11c7a5fec638b4`.
