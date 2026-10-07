# Parison 0.3 autonomous roadmap

Date: 7 October 2026

## Goal

Deepen Parison's core migration workflow: compare renamed and partitioned outputs under explicit, reviewable semantics, then make large discrepancies easier to interpret. Preserve local execution, keyed-v1 outcomes, existing recipes and readable 0.1/0.2 bundles.

Each slice is independently shippable and lands as a focused commit only after the full supported suite passes.

## Ordered slices

### 1. Explicit column mappings

- [x] Map side-specific physical columns to canonical recipe fields.
- [x] Apply mappings once at the row-reading seam for every supported format.
- [x] Surface canonical and physical names in evidence and reject ambiguous mappings.

### 2. Partitioned local datasets

- [x] Accept a directory of same-format files as one logical input.
- [x] Use deterministic non-recursive file ordering and reject empty, mixed-format, symlinked or schema-inconsistent partitions.
- [x] Apply byte and row limits across the whole logical input and detect duplicate keys across partitions.
- [x] Record a stable combined digest, total bytes, format and partition count without publishing local paths.
- [x] Cover partitioned CSV, JSON Lines and Parquet plus mixed single/partitioned comparisons.

### 3. Explicit normalization

- [x] Add opt-in string rules for trimming, case folding and Unicode normalization.
- [x] Apply normalization after parsing and before identity/comparison, including keys.
- [x] Keep defaults exact and report every active normalization rule.
- [x] Preserve original raw values in bounded raw evidence so normalization never hides what was received.

### 4. Schema-only preflight

- [x] Validate both physical schemas, mappings and exclusions without running a comparison.
- [x] Cover single files, partition directories and SQLite locators with the existing byte guard.
- [x] Emit a small machine-readable result containing schema metadata but no record values.
- [x] Document the JSON Lines first-record boundary and what preflight cannot prove.

### 5. Release integration

- [x] Verify old recipes and bundles remain readable.
- [ ] Run the full Python 3.11–3.14 and optional-Parquet CI matrix.
- [x] Update the user guide, examples, support envelope and changelog.
- [x] Build and smoke-test release artifacts from a clean archive before any 0.3 tag.

## Stop conditions

Stop and narrow the active slice if it requires fuzzy matching, automatic policy approval, recursive filesystem discovery, arbitrary expressions, a plugin system, remote credentials, hosted storage, or a change to PASS/FAIL/INCONCLUSIVE semantics. Do not begin the next slice while the current one has failing tests or undocumented trust-boundary behavior.

## Deferred

Grouped summaries are deferred because publishing useful group labels would conflict with summary mode's promise to store no source keys or values. Additional connectors, YAML, a local server, fuzzy identity, cross-run storage, automatic repairs and arbitrary transformations remain outside 0.3.
