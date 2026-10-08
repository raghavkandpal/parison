# Parison 0.6 roadmap

Date: 8 October 2026

## Goal

Find invalid records before comparison while preserving Parison's local, bounded and summary-safe workflow.

## Ordered slices

### 1. Opt-in record validation

- [x] Add an opt-in full record scan to `validate-inputs`; keep schema-only validation as the default.
- [x] Apply configured parsing, types, mappings, normalization and key policy exactly as comparison does.
- [x] Report row counts, null-key rows and duplicate-key counts without publishing keys or values.

### 2. Trust boundaries and evidence

- [x] Enforce physical-byte, decoded-byte, row and policy-fingerprint limits before or during the scan.
- [x] Reject inputs changed during record validation.
- [x] Extend the installed preflight schema and tests with optional record diagnostics.

### 3. Workflow completion

- [x] Document the fast schema-only and full record-validation paths.
- [x] Add CI smoke coverage using the checked-in 0.5 migration example.
- [ ] Reassess the next 0.6 slice after real record validation is complete; do not add new comparison modes speculatively.

### 4. Privacy-safe parse failures

- [x] Prevent standard-library parse exceptions from echoing rejected source values.
- [x] Retain safe, actionable column/type context and authored policy diagnostics.
- [x] Apply the same privacy boundary to comparison and record validation.

## Deferred

No-key multiset comparison, aggregate comparison, remote inputs, recursive discovery, a server and a local UI remain separate product decisions. Record validation will not silently repair or pair invalid keys.
