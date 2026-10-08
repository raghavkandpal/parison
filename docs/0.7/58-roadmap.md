# Parison 0.7 roadmap

Date: 8 October 2026

Status: **planned**. Implementation has not started.

## Goal

Add explicit global and grouped aggregate reconciliation for outputs that do not have stable unique row keys. This is a wider vertical slice: recipe policy, validation, execution, canonical results, reports, examples and release evidence all change together.

Aggregate comparison is a separate contract. It must never activate because keyed identity is missing, null or duplicated, and matching aggregates must never be described as row equality.

## Product boundary

A reviewed aggregate recipe declares:

- zero or more exact, typed `group_by` columns; an empty list means one global group;
- one or more named measures using `count`, `sum`, `min` or `max`;
- integer or decimal inputs for `sum`, with the existing exact or `symmetric-v1` numeric comparison policy;
- explicit null handling per measure: `reject` or `ignore`;
- the existing scope, source mapping, parsing, normalization, sensitivity and resource policies.

`average`, distinct counts, quantiles, approximate algorithms, expressions and user-supplied code are excluded from aggregate-v1. A future average can be represented transparently by separate `sum` and `count` measures.

## Compatibility strategy

- Existing recipe v1 and result v1 remain accepted, emitted and verifiable for `comparison_mode: keyed`.
- Aggregate mode uses recipe v2 and result v2 rather than making keyed-v1 fields optional or changing their meaning.
- `parison compare`, `validate-recipe`, `explain`, `validate-inputs`, `schema`, `publish` and `verify` remain the command surface; mode dispatch happens after strict recipe validation.
- Exit codes, bundle layout, manifest integrity and summary/raw sensitivity retain their current meanings.
- Policy fingerprints include mode, groups, measures, operators and null behavior.

## Ordered implementation

### 1. Freeze aggregate-v1 semantics

- [ ] Write the normative recipe and outcome contract with worked global, grouped, missing-group, null and tolerance examples.
- [ ] Define canonical measure names, source mappings, accumulation types and deterministic group ordering.
- [ ] Specify invariants: every input row is counted once per declared measure; published group counts reconcile with complete input row counts; missing groups and violating measures produce FAIL.
- [ ] Specify INCONCLUSIVE and ERROR boundaries before implementation, including empty inputs, invalid group values, parse failures and resource exhaustion.

Acceptance: an independent reviewer can calculate every example result without reading implementation code.

### 2. Versioned policy and schemas

- [ ] Add strict recipe-v2 validation and an installed `recipe-v2` JSON Schema without loosening recipe v1.
- [ ] Add a mode-aware effective-policy explanation and stable SHA-256 fingerprint.
- [ ] Add result-v2 and preflight-v2 schemas with explicit `groups`, `measures`, `group_counts` and `measure_counts`; do not reuse keyed row classifications for aggregate outcomes.
- [ ] Teach schema discovery and bundle verification to select the declared schema version.

Acceptance: old checked-in recipes and bundles remain byte-for-byte interpretable, and unknown aggregate fields/operators are rejected.

### 3. Aggregate-aware preflight

- [ ] Reuse existing readers, mappings, types, normalization, byte limits, decoded-byte limits and mutation detection.
- [ ] Validate group and measure columns without requiring unique row identity.
- [ ] Extend `validate-inputs --records` with privacy-safe invalid group/measure counts and null-policy violations.
- [ ] Add `--max-groups` as an explicit positive bound for grouped validation and comparison.

Acceptance: preflight can prove whether both complete inputs are executable under the reviewed aggregate policy without publishing group values.

### 4. Deterministic aggregation engine

- [ ] Introduce one mode dispatcher and one aggregate execution path; keep the keyed implementation intact behind its existing contract.
- [ ] Accumulate exact typed group keys and named measures in one pass per input.
- [ ] Use integer and `Decimal` arithmetic only for aggregate-v1 sums; never reduce decimal measures through binary floats.
- [ ] Compare group coverage first, then measure results using existing exact/tolerance classification.
- [ ] Preserve input digests and reject mutation across both scans.

Acceptance: oracle fixtures pass under row reordering, partition reordering, mixed input formats, mappings, normalization and tolerance boundaries.

### 5. Results, terminal output and reports

- [ ] Emit complete group and measure totals in result v2 with conservation checks.
- [ ] Keep summary mode free of group keys and source values.
- [ ] In raw mode, publish a deterministic bounded sample of missing groups and differing measures, clearly labelled as sensitive.
- [ ] Render aggregate-specific terminal and HTML summaries without pretending groups are records or measures are fields.
- [ ] Keep error and interruption bundles schema-valid for both modes.

Acceptance: a user can distinguish coverage failure, missing groups, exact measures, tolerated measures and violating measures from both JSON and the static report.

### 6. Drafting and migration workflow

- [ ] Keep `draft-recipe` keyed by default; add an explicit aggregate drafting flag rather than guessing that identity is unnecessary.
- [ ] Suggest only structural group/measure candidates and require human confirmation of every operator and null policy.
- [ ] Add a checked-in end-to-end example that reconciles global counts plus grouped decimal sums across different file formats.
- [ ] Document when aggregate comparison is appropriate and when keyed comparison or upstream tests are stronger evidence.

Acceptance: an unfamiliar user can draft, review, lock, preflight, compare and verify the example without editing generated result artifacts.

### 7. Adversarial verification and release

- [ ] Add hand-audited fixtures for offsetting errors, all-null groups, missing groups, decimal scale, tolerance boundaries, empty scopes and group explosion.
- [ ] Extend generated oracles and performance measurements across global, low-cardinality and high-cardinality groups.
- [ ] Pass Python 3.11–3.14, macOS and Windows CI with optional Parquet and all installed schemas.
- [ ] Build and inspect clean archives, install the final wheel in an empty environment, and repeat both keyed and aggregate smoke workflows before tagging 0.7.0.

Acceptance: aggregate mode cannot turn offsetting row errors into a claim of row equality, exceed declared group bounds silently, or regress keyed-v1 evidence.

## Implementation seams

Keep the new surface narrow:

```text
load_recipe
  keyed v1 validation -> existing keyed policy
  aggregate v2 validation -> aggregate policy

compare
  keyed -> existing keyed engine -> result v1
  aggregate -> aggregate engine -> result v2

publish / verify
  dispatch by result schema version
  preserve one bundle layout and manifest contract
```

Do not create a general query engine or expression language. Shared input reading, parsing, limits, fingerprints and publication remain deep modules; mode-specific identity and result semantics remain separate.

## Stop conditions

Pause implementation if any slice would:

- reinterpret a keyed-v1 recipe or result;
- require floating aggregate reproducibility without a pinned arithmetic contract;
- emit group keys or values in summary mode;
- return PASS from sampled or incomplete aggregation;
- require SQL, remote access, plugins or a new runtime dependency;
- make aggregate equality appear to prove row-level equality.

## Deferred beyond 0.7

No-key multiset matching, averages, distinct counts, quantiles, custom expressions, remote inputs, recursive discovery, a server and a local UI remain separate product decisions.
