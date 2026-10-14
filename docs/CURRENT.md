# Current development state

- Version: **1.0.0 released**
- Branch: `develop`
- Theme: stable 1.x compatibility baseline
- Released: the qualified 0.19 surface unchanged as the stable 1.x compatibility baseline
- Verified: exact merge `6b9219c9ed6b4276ba267f3ba4d4760444281471` passed the full CI matrix; public assets were checksum-verified and the fresh wheel passed direct, suite, Statement and cutover smoke workflows
- Next gate: shape the post-1.0 roadmap from adoption evidence and the priorities below

## Recorded next steps

- Use `1.x.0` for the next release line, advancing the minor component through `1.20.0`; reserve patch releases for compatible fixes.
- Research deterministic cross-format comparison, including which conversions are safe projections and which must remain explicit upstream extraction.
- Prefer coherent capabilities that materially improve how Parison is developed or used over release-filling collections of small improvements. Features must still preserve the 1.x compatibility contract and explicit local-first boundaries.
- Audit documentation for duplication, stale guidance and deprecated paths. Design a consolidated current guide and clearer topic-based navigation across versions; preserve historical contracts and release evidence, using redirects or archive labeling before deleting anything still needed for compatibility or provenance.

## Feature research inventory

- Explainable failures that connect discrepancies to explicit policy, scope and normalization without suggesting repair.
- Versioned schema-evolution comparison for renamed, added, removed, split and merged fields.
- Explicit time-window alignment using cutoff, watermark and lateness policies.
- Referential and reconciliation checks across related datasets without becoming a database.
- Distribution and drift contracts for reviewed histograms, quantiles, categories and null rates, distinct from exact equality.
- Cross-format semantic projection across CSV, JSONL, SQLite and Parquet first, with workbook semantics researched separately.
- Deterministic discrepancy grouping and bounded drill-down across rehearsal runs.
- Meaningful policy diffs and compatibility impact around approval-ready fingerprints, without implementing approval.
- Dataset manifests covering declared file, partition and table collections.
- Reproducibility diagnostics for environment, parser, dependency, input-identity and policy differences.
- A strict local extraction manifest or receipt contract for unsupported upstream formats.
- Additional evidence interoperability without adding signing, credentials or network custody.
- Streaming, external-sort and other bounded execution improvements only where benchmarks show a real ceiling.
- Contributor tooling for contract fixtures, golden bundles and compatibility testing.
- One task-oriented current guide, generated command reference, concept pages and clearly archived historical contracts.

## Recommended order

1. Research cross-format semantic projection because it expands real migration coverage while testing the input boundary directly.
2. Research schema evolution together with policy diffs because mappings and reviewability must be designed as one explicit contract.
3. Research time alignment and multi-dataset reconciliation because they unlock broader cutover workflows but introduce the most policy-sensitive semantics.

Adopt a feature only when the research produces a narrow versioned contract, a realistic workflow, explicit non-goals and a checkable compatibility gate. Keep the remaining inventory as options rather than promises.

Authoritative detail: [1.0 roadmap](1.0/135-roadmap.md), [1.0.0 release checklist](1.0/136-release-checklist.md), [0.19 consolidated user guide](0.19/131-user-guide.md), [compatibility contract](0.19/126-compatibility-contract.md), [performance envelope](0.19/127-performance-envelope.md) and deferred [post-1.0 direction research](0.20/134-post-1.0-direction-research.md).

Update this page when the active version, completion state, or next gate changes. Keep historical evidence in the version folder.
