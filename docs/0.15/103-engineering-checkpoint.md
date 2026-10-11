# Parison 0.15 engineering checkpoint

Date: 11 October 2026

Status: **first feature slice complete on `develop`**

## Implemented

- `catalog history` returns insertion-ordered safe summaries and adjacent outcome/discrepancy transitions for one exact policy fingerprint.
- `catalog diff` compares two ordinary run projections and rejects missing or unequal policy fingerprints.
- Safe run inspection now includes baseline and candidate content digests without source paths or values.
- A synthetic payout-reconciliation suite combines exact-decimal/category conservation with keyed transaction diagnosis and includes an intentionally failing fixture.
- Installed-wheel CI exercises history, diff and the payout suite; unit tests cover successful, mismatched-policy and failing-ledger behavior.

## Verification

- Local dependency-complete suite: **203 passed, 6 skipped**. The skips are the expected optional-Polars cases in the non-Parquet environment.
- Push CI for commits before this checkpoint passed on Python 3.11–3.14, macOS and Windows.
- The implementation adds no runtime dependency, remote service or catalog schema migration.

## Remaining before 0.15 release

1. Wait for the installed-wheel CI that includes the new CLI smoke workflow.
2. Review the diff against the frozen contract, with special attention to ordering language and digest disclosure.
3. Decide whether the release remains this focused history/reconciliation slice or also includes the separately researched feature-pipeline example.
4. Prepare version, release checklist, clean-build artifacts and installed-wheel verification only after scope freezes.

Do not release from this checkpoint alone. The branch is deliberately left at a coherent, resumable boundary.
