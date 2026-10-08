# Parison 0.4 roadmap

Date: 7 October 2026

## Goal

Make Parison's existing policy and validation modules easier to automate and review without changing keyed-v1 comparison outcomes or weakening summary privacy.

## Ordered slices

### 1. Structured preflight diagnostics

- [x] Return side-specific missing and unexpected columns as stable JSON.
- [x] Surface effective mappings and present exclusions without source record values or local paths.
- [x] Preserve exit zero for valid schemas and exit two for invalid schemas.
- [x] Keep malformed recipes, unreadable inputs and unsupported formats as operational errors.

### 2. Policy explanation

- [x] Render the effective recipe policy without reading input data.
- [x] Keep one machine-readable representation shared by terminal and future report views.

### 3. Versioned JSON schemas

- [x] Publish recipe and result JSON Schemas from the existing contracts.
- [x] Validate committed examples against those schemas in CI.

### 4. Schema distribution

- [x] Ship both schemas inside wheel and source distributions.
- [x] Expose installed schemas through the dependency-free CLI.
- [x] Smoke-test schema discovery from built wheels in CI.

### 5. Effective-policy fingerprint

- [x] Hash the canonical effective policy independently from recipe-file formatting.
- [x] Record the fingerprint in explanations, comparison results and reports.
- [x] Preserve readability of older result-v1 bundles where the additive field is absent.

### 6. CI policy lock

- [x] Allow comparisons to require an expected effective-policy fingerprint.
- [x] Reject malformed or mismatched fingerprints before opening either input.
- [x] Preserve summary-only error bundles and deterministic exit code two on rejection.

### 7. Bundle verification hardening

- [x] Require manifests to cover the canonical result and report files.
- [x] Validate manifest outcome, sensitivity, runtime and digest shapes.
- [x] Cross-check recorded manifest metadata against the integrity-checked result.

### 8. Publication failure handling

- [x] Translate staging and final-publication I/O failures into controlled Parison errors.
- [x] Remove partial staging directories after publication failures.
- [x] Preserve the rule that the final run directory appears only after every artifact is complete.

## Deferred

Compressed inputs remain a later adapter slice because decompressed-byte accounting needs a separate resource contract. Remote connectors, fuzzy identity, arbitrary transformations and publication of grouped source values remain out of scope.
