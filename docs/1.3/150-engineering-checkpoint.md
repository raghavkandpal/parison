# Parison 1.3 engineering checkpoint

Date: 15 October 2026

Status: **local capability gate passed; exact-commit CI pending**

## Delivered capability

- Frozen strict `time-alignment-v1` and `reconciliation-v1` declarations, semantic cross-reference validation, canonical bytes and fingerprints.
- Fixed UTC `[start, end)` scanning with source-owned snapshot, watermark or declared-cutoff coordination and conservative PASS/FAIL/INCONCLUSIVE semantics.
- Existing keyed, aggregate and multiset parity composed for every logical dataset pair.
- Per-side identity, exact reference and grouped-sum conservation checks with closed null/tolerance behavior and aggregate-only diagnostics.
- Byte-identical memory and bounded SQLite evidence with private temporary state and cleanup on failure or interruption.
- Atomic no-overwrite reconciliation bundles with manifest-bound full/summary evidence, normalized declarations, standard verification and summary-safe inspection.

## Local evidence

- `make check` passes 294 tests with 11 expected skips when optional Polars is absent.
- Canonical byte fixtures cover both authoring contracts.
- Focused tests cover all coordination modes, exact window edges, malformed timestamp rejection, duplicate IDs/checks, token-domain mismatch, negative lateness, type/arity mismatch, cycles, receipt mismatch, policy mismatch, FAIL-before-INCONCLUSIVE reduction and bundle tampering.
- Memory/SQLite byte identity is asserted for identity/reference, conservation and composed results.
- Three end-to-end workflows cover a checked-in cross-format payout reconciliation, a relational migration where per-dataset parity passes but a reference fails, and a partitioned historical backfill where data checks pass but declared-cutoff alignment remains INCONCLUSIVE.
- Alignment qualification includes exact edges, pre-epoch timestamps, upstream offset normalization, null and malformed times, missing or mismatched receipts, watermark boundaries and all three coordination modes.
- Interruption tests prove SQLite workspace and publication staging cleanup.
- Released compatibility fixtures remain byte-identical and readable through the unchanged standard verifier.

## Remaining release evidence

- Independent Standards and Spec review of `origin/main...develop`.
- Exact-candidate built-wheel CI on Python 3.11–3.14, macOS and Windows.
- Fresh-wheel smoke of the complete checked-in reconciliation workflow.
- Exact-merge CI, public artifact checksum verification and post-release smoke.

## Boundaries retained

Core execution remains local, deterministic and credential-free. Receipts and opaque source tokens are bound but not authenticated. Parison does not acquire snapshots, advance watermarks, wait on clocks, connect to sources, infer relationships, repair data, approve policy or authorize cutover. PASS remains agreement under the explicit policy.
