# Parison 0.8 roadmap

Date: 9 October 2026

Status: **planned**. Research is complete; implementation has not started.

## Goal

Add exact, keyless, duplicate-aware multiset comparison for complete local datasets. This is one wide vertical slice: recipe policy, typed row identity, validation, execution, canonical results, reports, drafting, examples, resource controls and release evidence change together.

Parison will then support three explicit proof modes:

- keyed comparison proves equality by stable unique identity;
- aggregate comparison proves declared group coverage and measures;
- multiset comparison proves whole-row equality, including duplicate multiplicity, when row order is irrelevant and no stable key exists.

Multiset mode must never activate as a fallback from invalid or duplicated keys.

## Product boundary

A reviewed multiset recipe declares a nonempty set of canonical typed columns. Every included column participates in exact row identity after the existing mappings and normalization policies. Null equals null in the same column; empty string remains distinct from null. Exclusions require the existing rationale.

For each canonical row `r`, comparison uses its complete multiplicity on both sides:

```text
common(r)         = min(baseline(r), candidate(r))
baseline_only(r)  = max(baseline(r) - candidate(r), 0)
candidate_only(r) = max(candidate(r) - baseline(r), 0)
```

A run passes only when every canonical row has equal multiplicity. Multiset-v1 has no tolerance, fuzzy pairing, positional pairing, subset allowance, nested values, expressions or automatic deduplication.

## Compatibility strategy

- Preserve recipe/result v1 for keyed mode and v2 for aggregate mode.
- Introduce strict recipe/result/preflight v3 for `comparison_mode: "multiset"`.
- Keep the existing command surface and bundle layout; dispatch by declared mode and schema version.
- Reuse local readers, parsing, normalization, limits, input digests, mutation checks, sensitivity levels, fingerprints and manifest verification.
- Add no required runtime dependency.

## Ordered implementation

### 1. Freeze multiset-v1 semantics

- [x] Write the normative contract with duplicate, null, normalization, empty-scope and mixed-format examples.
- [x] Define the canonical typed row tuple and a collision-free, versioned encoding for ordering and evidence.
- [x] Define occurrence and distinct-shape conservation equations.
- [x] Specify PASS, FAIL, INCONCLUSIVE, ERROR and INTERRUPTED boundaries before implementation.

Acceptance: an independent reviewer can calculate every example and explain why `[A, A]` differs from `[A]` without reading code.

### 2. Versioned policy and schemas

- [x] Add strict recipe-v3 validation without making keys optional in v1 or reinterpreting v2.
- [x] Add mode-aware policy explanation and stable fingerprinting for columns and encoding version; add execution limits with the engine slice.
- [x] Add result-v3 and preflight-v3 schemas with multiset-specific counts and evidence.
- [ ] Make schema discovery, publication and verification dispatch across all three versions.

Acceptance: old recipes and bundles retain their meaning, and mode-specific fields cannot leak across schemas.

### 3. Multiset-aware preflight

- [x] Validate all identity columns using existing readers, mappings, types and normalization.
- [x] Report privacy-safe invalid-row and invalid-field counts without row values.
- [x] Add a positive `--max-distinct-rows` bound to record preflight and comparison.
- [ ] Reject unsupported values before counting; retain complete-input and mutation guarantees.

Acceptance: preflight proves that both inputs can enter exact multiset comparison without publishing row identities.

### 4. Reference comparison engine

- [x] Count canonical typed rows exactly with an in-memory dictionary or `Counter`.
- [x] Enforce the distinct-row bound; never sample toward PASS.
- [x] Compare multiplicities and maintain independent occurrence and distinct-shape conservation totals.
- [x] Make outcomes independent of row, file, partition and hash iteration order.

Acceptance: hand-audited and generated oracles agree under reordered inputs, duplicate skew, mappings and mixed formats.

### 5. Results, terminal output and reports

- [x] Emit total and common occurrences, one-sided occurrences, total distinct shapes and surplus-shape counts.
- [x] Keep summary results free of row values and canonical row keys.
- [x] In raw mode, publish a bounded deterministic sample of row shapes with both multiplicities and classification.
- [x] Render multiset-specific terminal and HTML summaries without describing duplicate rows as invalid keys.
- [x] Keep failure, error and interruption bundles schema-valid and verifiable.

Acceptance: a reviewer can distinguish a missing row shape from a duplicate-count mismatch in JSON and the static report.

### 6. Drafting and end-to-end workflow

- [x] Add explicit `draft-recipe --multiset`; never infer the mode from failed key discovery.
- [ ] Draft only shared scalar structure and require review of mappings, exclusions and normalization.
- [x] Add a checked-in duplicate-aware example spanning two supported input formats.
- [ ] Document how to choose keyed, aggregate or multiset mode and what each mode does not prove.

Acceptance: an unfamiliar user can draft, review, lock, preflight, compare, publish and verify the example without editing generated artifacts.

### 7. Scale decision and release evidence

- [ ] Benchmark total rows, distinct-row ratio, row width, duplicate skew and mismatch rate.
- [ ] Measure an optional standard-library SQLite spill prototype against the same semantic oracle.
- [ ] Keep the bounded in-memory engine unless the prototype demonstrates a material need and preserves identical results.
- [ ] Pass canonical-encoding collision tests, privacy checks, cancellation, mutation and cardinality-limit cases.
- [ ] Pass Python 3.11–3.14, macOS and Windows CI plus installed-wheel smoke workflows for all three modes.

Acceptance: 0.8 has an evidence-backed support envelope and makes no unqualified larger-than-memory claim.

## Implementation seam

```text
load_recipe
  keyed v1 -> keyed policy
  aggregate v2 -> aggregate policy
  multiset v3 -> multiset policy

compare
  keyed -> keyed engine -> result v1
  aggregate -> aggregate engine -> result v2
  multiset -> counted-row engine -> result v3

publish / verify
  dispatch by result schema version
  preserve one bundle and manifest contract
```

Typed canonicalization should remain a shared deep module. Each mode owns its identity rules, conservation checks and result vocabulary.

## Stop conditions

Pause implementation if a slice would:

- reinterpret an existing keyed or aggregate recipe;
- compare digests without collision resolution;
- make tolerant or fuzzy equality part of row identity;
- rely on input order to pair or select duplicates;
- expose row values in summary output;
- return PASS after sampling, truncation or a breached resource limit;
- add a database engine before the bounded reference implementation is measured;
- require remote access, a server, plugins or a new UI.

## Deferred beyond 0.8

Tolerant row assignment, subset comparison, spill-backed execution, nested values, custom expressions, remote inputs, recursive discovery, a server and a local UI remain separate product decisions.

The evidence and alternatives behind this choice are recorded in [the multiset research](64-multiset-research.md).
The normative implementation target is [the multiset-v1 contract](66-multiset-contract.md).
Encoding details and the required golden/property tests are recorded in [canonical row encoding research](67-canonical-row-encoding-research.md).
