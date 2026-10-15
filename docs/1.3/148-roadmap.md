# Parison 1.3 roadmap

Status: **contracts frozen; execution pending**

## Theme

Verify coordinated, related dataset sets without becoming an extractor, database, stream processor or cutover authority.

The governing input is [time alignment and multi-dataset reconciliation research](147-time-alignment-and-multi-dataset-reconciliation-research.md). The proposed release is one opt-in `reconciliation-v1` capability that composes existing per-dataset parity with explicit time alignment and a small closed relationship vocabulary.

## Proposed scope

1. Freeze canonical `time-alignment-v1` and `reconciliation-v1` JSON contracts with one UTC `[start, end)` event window.
2. Bind one explicit source-owned coordination mode: snapshot tokens, watermark claims or an always-INCONCLUSIVE declared cutoff.
3. Run existing keyed, aggregate or multiset parity for every logical dataset pair without changing released recipes or suites.
4. Evaluate identity, exact referential coverage and grouped-sum conservation independently inside baseline and candidate sets.
5. Publish deterministic full and summary-safe evidence with conservative `PASS`, `FAIL` and `INCONCLUSIVE` reduction.
6. Qualify canonical bytes, memory/SQLite equivalence, supported formats, interruption cleanup and built wheels across the supported matrix.

## Non-goals

- source connectors, credentials, snapshot creation, watermark advancement or clock-dependent waiting;
- arbitrary SQL, expressions, joins, repair, inferred keys or relationship discovery;
- temporal interval joins, CDC monitoring, fuzzy matching, currency conversion or accounting certification;
- receipt authentication, extraction-truth claims, approval or cutover orchestration;
- reinterpretation of released recipes, suites, results, bundles, exit codes or canonical bytes.

## First gate

Completed in [`time-alignment-v1` and `reconciliation-v1` contract](149-time-alignment-and-reconciliation-contract.md): the written contract, installed strict schemas, semantic validators, canonical fixtures and fingerprints now freeze dataset identity, coordination semantics, event-window failures, relationship null rules, conservation numeric policy, result ordering and summary-safe disclosure.

Window and coordination preflight is now implemented over existing timestamp projection, including receipt and policy binding, exact edge handling, resource limits, input-change detection and PASS/FAIL/INCONCLUSIVE outcomes.

Identity and reference execution now uses the existing canonical scalar encoding for both memory and bounded SQLite engines, with per-side results, deterministic aggregate diagnostics and changed-input checks.

Grouped-sum conservation now uses matching integer or scaled-decimal domains, aggregate-v1 tolerance semantics and equivalent bounded memory/SQLite engines, with per-side aggregate-only diagnostics.

Composition now runs alignment, existing per-dataset parity and all declared relationship checks under one input-change guard, then applies conservative FAIL-before-INCONCLUSIVE outcome reduction. A summary-safe projection removes dataset/check identifiers and detailed counts.

Deterministic atomic no-overwrite reconciliation bundles now bind the full result, summary-safe projection, normalized declarations, input identities and receipt identity. Standard verification checks integrity plus semantic membership/outcome/summary consistency; safe inspection exposes no dataset or check identifiers.

The next gate is realistic end-to-end qualification across formats and engines, failure/interruption hardening, and built-wheel CI. The promotion gate in the research note remains authoritative.
