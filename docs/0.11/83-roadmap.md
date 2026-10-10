# Parison 0.11 roadmap

Date: 10 October 2026

Status: **released**

## Focus: scalable suite execution and CI exchange

0.11 will make reviewed mixed-mode suites practical at larger scale. A user will be able to inspect and select cases, split one plan into deterministic CI shards, transport independently verifiable shard bundles, assemble exact coverage into one ordinary suite bundle, resume interrupted local work conservatively, and export bounded CI summaries.

This is one feature slice: **execute a large reviewed plan efficiently without weakening what suite PASS means**. Existing keyed, aggregate, multiset and suite-v1 semantics remain unchanged.

## Release capabilities

1. **Suite-v2 planning** — optional case tags and descriptions, suite defaults, explicit per-case resource-limit overrides, and one canonical effective-plan fingerprint.
2. **Listing and selection** — deterministic text and JSON preflight with explicit case and conjunctive tag filters; zero matches are an error.
3. **External sharding** — fixed modulo assignment after selection, with atomic `suite-shard` bundles that never claim full-suite completion.
4. **Verified assembly** — recursive verification, exact and disjoint coverage, plan-order restoration, copied child bundles, and atomic publication as an ordinary full suite.
5. **Conservative resume** — an explicitly mutable workspace may reuse a child only after bundle verification plus current plan, policy, limits, version and input-digest checks.
6. **CI projections** — deterministic, summary-safe, size-bounded Markdown and documented JUnit-style exports derived from verified bundles.
7. **Reference workflow and evidence** — a portable GitHub Actions matrix example, installed-wheel cross-platform coverage, adversarial integrity tests, and measured orchestration overhead.

## Ordered implementation

### 1. Freeze suite-v2 identity and scope

- Write the normative suite-v2, selection, sharding, shard-bundle and assembly contracts.
- Define canonical effective-plan encoding and fingerprint golden vectors.
- Specify scope-complete versus execution-complete outcomes and human wording.

Done when independent selection/fingerprint implementations agree on every golden plan and no partial scope can present as a full-suite PASS.

### 2. Add listing, selection and limits

- Add the strict suite-v2 schema and loader without widening suite-v1.
- Implement one selector shared by `list-suite` and execution.
- Resolve and record effective per-case limits.

Done when every listed case executes with the same identity, order and limits shown during preflight.

### 3. Publish verifiable shards

- Implement zero-based fixed-modulo sharding after selection.
- Publish distinct atomic `suite-shard` results and manifests.
- Extend verification and safe inspection to shards.

Done when all generated shard sets are exact and disjoint across filters, reordered plans and shard counts.

### 4. Assemble exact coverage

- Verify every shard and child recursively.
- Reject gaps, duplicates, mixed plans, mixed selections, stale policies and interrupted shards.
- Restore plan order and atomically publish a normal full-suite bundle.

Done when assembly cannot publish unless every selected case is represented exactly once by valid evidence.

### 5. Resume interrupted work

- Keep mutable checkpoints outside immutable result destinations.
- Verify child bundles and recompute current input digests before reuse.
- Start with exact Parison-version compatibility and widen only with evidence.
- Exercise interruption and injected failure at every checkpoint boundary.

Done when clean and resumed executions are semantically equivalent and every stale dependency forces a rerun.

### 6. Export CI summaries

- Add bounded Markdown and a documented JUnit-style subset.
- Escape all untrusted identifiers and descriptions for the target format.
- Keep projections non-authoritative and exclude raw evidence.
- Check in a matrix workflow that transports shards and assembles the result.

Done when a CI reviewer can identify every non-passing case without accessing raw values and the transported final bundle verifies.

### 7. Harden and release

- Test tampering, traversal, symlinks, duplicate inputs, limit changes and no-overwrite behavior.
- Benchmark 10-, 25- and 100-case clean, sharded and resumed runs.
- Run installed-wheel workflows on Python 3.11–3.14, macOS and Windows.
- Re-run the suite-v1 mixed-mode example unchanged.

Done when published measurements separate orchestration, comparison and transport costs and all compatibility evidence is green.

## Boundaries

- No in-process thread/process scheduler, automatic worker sizing or dynamic work stealing.
- No built-in network/object-store transport, remote input connector or hosted coordinator.
- No retries that hide the deterministic first outcome.
- No globs, recursive case discovery, environment interpolation, inline recipes or arbitrary selector expressions.
- No raw evidence in parent or CI summaries.
- No fourth comparison mode or change to existing child outcome semantics.
- No signing, authorship or organizational-approval claims from digest verification.

The evidence, primary sources, security constraints, alternatives and stop conditions are recorded in [the scalable-suite research](82-scalable-suite-research.md).
