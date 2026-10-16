# Parison 1.3 engineering checkpoint

Date: 15 October 2026

Status: **released**

## Delivered capability

- Frozen strict `time-alignment-v1` and `reconciliation-v1` declarations, semantic cross-reference validation, canonical bytes and fingerprints.
- Fixed UTC `[start, end)` scanning with source-owned snapshot, watermark or declared-cutoff coordination and conservative PASS/FAIL/INCONCLUSIVE semantics.
- Existing keyed, aggregate and multiset parity composed for every logical dataset pair.
- Per-side identity, exact reference and grouped-sum conservation checks with closed null/tolerance behavior and aggregate-only diagnostics.
- Byte-identical memory and bounded SQLite evidence with private temporary state and cleanup on failure or interruption.
- Atomic no-overwrite reconciliation bundles with manifest-bound full/summary evidence, normalized declarations, standard verification and summary-safe inspection.

## Local evidence

- `make check` passes 303 tests with 11 expected skips when optional Polars is absent.
- Canonical byte fixtures cover both authoring contracts.
- Focused tests cover all coordination modes, exact window edges, malformed timestamp rejection, duplicate IDs/checks, token-domain mismatch, negative lateness, type/arity mismatch, cycles, receipt mismatch, policy mismatch, FAIL-before-INCONCLUSIVE reduction and bundle tampering.
- Memory/SQLite byte identity is asserted for identity/reference, conservation and composed results.
- Three end-to-end workflows cover a checked-in cross-format payout reconciliation, a relational migration where per-dataset parity passes but a reference fails, and a partitioned historical backfill where data checks pass but declared-cutoff alignment remains INCONCLUSIVE.
- Alignment qualification includes exact edges, pre-epoch timestamps, upstream offset normalization, null and malformed times, missing or mismatched receipts, watermark boundaries and all three coordination modes.
- Relationship qualification exercises forbid, all-null-exempt, match-null and zero-null behavior; conservation includes tolerance boundaries, decimal signed zero and negative-value normalization.
- Interruption and concurrent-target tests prove SQLite workspace cleanup, publication staging cleanup and preservation of a racing publisher's output.
- Released compatibility fixtures remain byte-identical and readable through the unchanged standard verifier.

## Candidate evidence

- Exact candidate `b25db9962698a370ff0703da8cc7d7c23abcabc5` passed built-wheel CI on the full Python 3.11–3.14 × Linux/macOS/Windows matrix with pinned Polars 1.44.2.
- A clean archive produced inspected wheel/source artifacts, and a fresh Python 3.14 environment passed the complete checked-in SQLite reconciliation workflow from the candidate wheel.

## Release evidence

- Pull request 38 merged the reviewed candidate at `3aec4fb0b7355aea94aa81d8a8a7c5e3372414ea`; exact-merge CI run 38862675947 passed.
- Public 1.3.0 wheel/source/checksum assets were re-downloaded and checksum-verified, and the released wheel passed the complete SQLite reconciliation workflow in a fresh Python 3.14 environment.

## Boundaries retained

Core execution remains local, deterministic and credential-free. Receipts and opaque source tokens are bound but not authenticated. Parison does not acquire snapshots, advance watermarks, wait on clocks, connect to sources, infer relationships, repair data, approve policy or authorize cutover. PASS remains agreement under the explicit policy.

Independent Standards and Spec review against `origin/main...develop` found and closed two blockers: publication now uses an atomic OS-native no-replace operation on every supported platform, and bundle verification binds receipt and dataset-policy identities to the normalized declarations. Both review axes report no remaining release blockers.
