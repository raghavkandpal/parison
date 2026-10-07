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

- [ ] Render the effective recipe policy without reading input data.
- [ ] Keep one machine-readable representation shared by terminal and future report views.

### 3. Versioned JSON schemas

- [ ] Publish recipe and result JSON Schemas from the existing contracts.
- [ ] Validate committed examples against those schemas in CI.

## Deferred

Compressed inputs remain a later adapter slice because decompressed-byte accounting needs a separate resource contract. Remote connectors, fuzzy identity, arbitrary transformations and publication of grouped source values remain out of scope.
