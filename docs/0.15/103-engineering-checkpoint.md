# Parison 0.15 engineering checkpoint

Date: 11 October 2026

Status: **release-candidate implementation complete on `develop`**

## Implemented

- `catalog history` returns insertion-ordered safe summaries and adjacent outcome/discrepancy transitions for one exact policy fingerprint.
- `catalog diff` compares two ordinary run projections and rejects missing or unequal policy fingerprints.
- Safe run inspection now includes baseline and candidate content digests without source paths or values.
- A synthetic payout-reconciliation suite combines exact-decimal/category conservation with keyed transaction diagnosis and includes an intentionally failing fixture.
- A synthetic feature-pipeline suite combines keyed numeric tolerance with exact duplicate-aware keyless parity.
- Installed-wheel CI exercises history, diff and the payout suite; unit tests cover successful, mismatched-policy and failing-ledger behavior.
- Release review replaced implicit SQLite `rowid` ordering with a durable schema-v2 sequence, normalized equivalent paths, consolidated the safe projection boundary, targeted single-entry lookup and stopped live-state checks from parsing result evidence.

## Verification

- Local dependency-complete suite after review fixes: **208 passed, 6 skipped**. The skips are the expected optional-Polars cases in the non-Parquet environment.
- Push CI for commits before this checkpoint passed on Python 3.11–3.14, macOS and Windows.
- The implementation adds no runtime dependency, remote service or catalog schema migration.

## Remaining before 0.15 release

1. Push the review fixes and require installed-wheel CI on every supported Python and operating-system lane.
2. Prepare version metadata and the release checklist.
3. Build from the reviewed commit, verify artifact contents and checksums, and run a clean installed-wheel history/diff workflow.

Do not release from this checkpoint alone. The branch is deliberately left at a coherent, resumable boundary.
