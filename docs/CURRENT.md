# Current development state

- Version: **1.6.0 in development**
- Branch: `develop`
- Theme: one maintained workflow plus an explicit local XLSX values boundary
- Released: deterministic discrepancy analysis, exact-policy rehearsal series, live catalog selection and bounded verified raw drill-down
- Verified: exact merge `e960a3eb899181d63a28b24c11f31daeaf6f280b` passed [the full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39036693844) on Python 3.11–3.14, Linux, macOS and Windows; public assets were checksum-verified and smoke-tested fresh
- Next gate: merge the reviewed 1.6.0 candidate, qualify the exact merge and publish/reconcile public assets

## Recorded next steps

- Follow the active [1.6 roadmap](1.6/166-roadmap.md), accepted [current-workflow research](1.6/165-current-workflow-research.md) and approved [XLSX values research](1.6/169-xlsx-values-projection-research.md). Keep task guidance hand-written, require explicit worksheet/range selection and preserve every released contract as history.

- The [pre-1.5 repository quality and layout plan](157-repository-quality-and-layout-plan.md) is complete at exact commit `35fe2d0`; see the [maintenance checkpoint](158-repository-maintenance-checkpoint.md). Ruff is mandatory, contributor standards are documented, `core.py` is a compatibility facade and atomic no-replace publication is consolidated in `_safe_fs.py`.
- Exact maintenance commit `35fe2d0578ac54956c58bd4501aba8ae03fb8de2` passed the full built-wheel matrix on Python 3.11–3.14 across Linux, macOS and Windows in [CI run 39015498650](https://github.com/raghavkandpal/parison/actions/runs/39015498650). No product release was created for internal maintenance.
- Per-run reason groups, exact-policy direct/catalog series, bounded raw-sample drill-down, strict installed summary/raw schemas, canonical atomic artifacts and CLI workflows are implemented. Review corrections pass 342 local tests, independent Standards/Spec re-review and exact corrected cross-platform CI.

- Follow the active [1.4 roadmap](1.4/153-roadmap.md) and frozen [manifest/reproducibility contract](1.4/154-dataset-manifest-and-reproducibility-contract.md). Keep exact byte identity, semantic agreement and runtime explanation as separate claims.
- Strict schemas, canonical identities, descriptor-relative named-file verification, reviewed closed scopes, summary-safe results and informational diagnostic comparison are implemented. The opt-in `dataset-evidence` bundle carries the canonical manifest, full verification result, effective policy, diagnostic and recursively verified semantic result as semantically bound members without changing released bundle readers.
- Reject implicit discovery, remote resources, live SQLite state, path traversal, symlinks, aliases and environment inventories. Do not let diagnostic differences alter verification outcomes in v1.

- Follow the active [1.3 roadmap](1.3/148-roadmap.md) and frozen [contract](1.3/149-time-alignment-and-reconciliation-contract.md) as one coherent capability: existing per-dataset parity plus a fixed UTC half-open event window and per-side identity, reference and grouped-sum conservation checks.
- `time-alignment-v1` and `reconciliation-v1` now have strict installed schemas, semantic cross-reference validation, canonical bytes and fingerprints. Alignment preflight binds the receipt and policies, scans both sides under explicit resource limits, and emits strict PASS/FAIL/INCONCLUSIVE JSON without changing released comparison execution.
- Identity and reference checks execute independently on baseline and candidate with deterministic aggregate-only diagnostics and byte-identical memory/SQLite evidence.
- Grouped-sum conservation executes independently on both sides with exact or symmetric tolerance comparison over matching integer/scaled-decimal domains and byte-identical bounded memory/SQLite evidence.
- `parison reconcile` composes alignment, existing keyed/aggregate/multiset parity and all declared relationships under one input-change guard, with conservative FAIL-before-INCONCLUSIVE reduction and a summary-safe projection.
- Reconciliation bundles publish atomically with no overwrite, bind normalized declarations plus every input/receipt identity, verify semantic membership and outcome reduction, and support summary-safe standard inspection.
- Three end-to-end scenarios cover payout reconciliation, relationship failure despite parity, and an alignment-INCONCLUSIVE partitioned backfill; local compatibility, atomic no-replace publication, semantic verification binding and the full 303-test gate pass. Independent review reports no blockers, and exact candidate `b25db99` passed the complete built-wheel matrix plus a fresh Python 3.14 wheel smoke. Merge and publication evidence remain. See the [engineering checkpoint](1.3/150-engineering-checkpoint.md) and active [release checklist](1.3/151-release-checklist.md).
- Preserve extraction ownership upstream. Snapshot tokens and watermarks remain source-owned claims bound by local evidence; a declared cutoff cannot establish coordination and therefore remains `INCONCLUSIVE`.
- Deepen the existing suite, keyed/SQLite and aggregate seams. Do not add connectors, a query language, a graph planner or a second orchestration framework.

- The [`semantic-scalar-v1` contract](1.1/139-semantic-scalar-contract.md) and reader seam passed exact built-wheel CI across Python 3.11–3.14, macOS and Windows at `a12e1783418889cc58718360d25a9a819ce86162`.
- The released [1.2 roadmap](1.2/142-roadmap.md) delivered one larger capability: explicit schema evolution, meaningful policy diffs and qualified semantic-scalar projection.
- `schema-evolution-v1` validation, canonical identity, safe mapping compilation, `policy-diff-v1` classification and summary-safe rendering are qualified and published in 1.2.0.
- The semantic-scalar promotion corpus covers every scalar type, null/empty boundaries, numeric and temporal boundaries, row-order permutations, every supported format and comparison mode, admitted Parquet dtype families, unsupported Parquet families and pinned canonical row bytes. Exact commit `0b07f1cd1705020e7fe039089ea8f8f1e98ac47b` passed the complete built-wheel matrix; see the [1.1 engineering checkpoint](1.1/144-engineering-checkpoint.md).
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
3. [In progress] Specify time alignment and multi-dataset reconciliation because they unlock broader cutover workflows but introduce the most policy-sensitive semantics.

Adopt a feature only when the research produces a narrow versioned contract, a realistic workflow, explicit non-goals and a checkable compatibility gate. Keep the remaining inventory as options rather than promises.

Authoritative detail: [1.3 research](1.3/147-time-alignment-and-multi-dataset-reconciliation-research.md), [1.3 roadmap](1.3/148-roadmap.md), [1.2 release checklist](1.2/146-release-checklist.md), [semantic scalar contract](1.1/139-semantic-scalar-contract.md), [compatibility contract](0.19/126-compatibility-contract.md) and [post-1.0 direction research](0.20/134-post-1.0-direction-research.md).

Update this page when the active version, completion state, or next gate changes. Keep historical evidence in the version folder.
