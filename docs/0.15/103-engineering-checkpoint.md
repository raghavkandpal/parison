# Parison 0.15 engineering checkpoint

Date: 11 October 2026

Status: **released in 0.15.0 on 12 October 2026**

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
- The implementation adds no runtime dependency or remote service. Catalog schema v1 migrates locally to schema v2 to record durable insertion order.

## Release evidence

- Pull request [#24](https://github.com/raghavkandpal/parison/pull/24) merged the reviewed candidate as `1fba80e4458bab328b8767dd7df1bcf6649649a4`.
- The annotated `0.15.0` tag names that merge commit.
- The public wheel and source archive checksums were verified after download, and the downloaded wheel passed both 0.15 starter suites in a fresh Python 3.12 environment.
