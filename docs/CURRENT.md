# Current development state

- Version: **1.1 planned**
- Branch: `develop`
- Theme: versioned cross-format semantic-scalar projection
- Released: the qualified 0.19 surface unchanged as the stable 1.x compatibility baseline
- Verified: exact merge `6b9219c9ed6b4276ba267f3ba4d4760444281471` passed the full CI matrix; public assets were checksum-verified and the fresh wheel passed direct, suite, Statement and cutover smoke workflows
- Next gate: complete the semantic-scalar compatibility corpus and exact built-wheel platform qualification

## Recorded next steps

- Follow the [1.1 roadmap](1.1/138-roadmap.md): contract first, then the reader boundary, compatibility corpus and built-wheel qualification.
- The [`semantic-scalar-v1` contract](1.1/139-semantic-scalar-contract.md) and reader seam are implemented locally across keyed, aggregate and multiset modes; public release still requires the complete compatibility and platform gates.
- After 1.1 qualification, follow the [1.2 roadmap](1.2/142-roadmap.md) as one larger paired capability: explicit schema evolution plus meaningful policy diffs.
- Preserve recipe versions 1–3 unchanged. New coercion or rejection semantics require an explicit versioned policy boundary.
- Use `1.x.0` for the next release line, advancing the minor component through `1.20.0`; reserve patch releases for compatible fixes.
- Treat the completed [cross-format projection research](1.1/137-cross-format-semantic-projection-research.md) as the design input: recipe-directed scalar conversion is safe only through a closed source-type allowlist; lossy or inferred conversion stays explicit or upstream.
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

1. Specify and qualify `semantic-scalar-v1` because it turns existing mixed-format behavior into a narrow compatibility promise without changing comparison modes.
2. Implement the researched `schema-evolution-v1` and `policy-diff-v1` pair because mappings and reviewability must share one explicit contract.
3. Research time alignment and multi-dataset reconciliation because they unlock broader cutover workflows but introduce the most policy-sensitive semantics.

Adopt a feature only when the research produces a narrow versioned contract, a realistic workflow, explicit non-goals and a checkable compatibility gate. Keep the remaining inventory as options rather than promises.

Authoritative detail: [1.2 roadmap](1.2/142-roadmap.md), [schema evolution and policy-diff research](1.2/141-schema-evolution-and-policy-diff-research.md), [1.1 roadmap](1.1/138-roadmap.md), [cross-format semantic projection research](1.1/137-cross-format-semantic-projection-research.md), [0.19 consolidated user guide](0.19/131-user-guide.md), [compatibility contract](0.19/126-compatibility-contract.md), [performance envelope](0.19/127-performance-envelope.md) and [post-1.0 direction research](0.20/134-post-1.0-direction-research.md).

Update this page when the active version, completion state, or next gate changes. Keep historical evidence in the version folder.
