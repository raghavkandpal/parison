# Changelog

All notable changes will be documented in this file.

## Unreleased

### Added

- Machine-readable missing, unexpected, mapped and excluded-column diagnostics from `validate-inputs`.
- A data-free `explain` command that renders every effective recipe policy and source-column mapping.
- Versioned Draft 2020-12 JSON Schemas for recipe and result artifacts.
- Installed-schema discovery through `parison schema recipe|result`.
- Canonical effective-policy SHA-256 fingerprints in explanations and comparison evidence.
- An optional comparison gate that rejects policies not matching a reviewed fingerprint before reading inputs.
- Opt-in machine-readable manifest output from `parison verify --json`.

### Fixed

- Recipes that omit `output` now consistently apply the documented summary-sensitivity default.
- Bundle verification now rejects incomplete manifests and metadata that disagrees with `result.json`.
- Bundle staging and publication I/O failures now return controlled operational errors and clean up partial staging directories.
- Bundle verification rejects symlinked manifests, and staging cleanup also covers permission-setting failures.

## 0.3.0 - 2026-10-07

### Added

- Explicit baseline/candidate column mappings under canonical recipe field names.
- Partitioned CSV, JSON Lines and Parquet directories as logical inputs.
- Opt-in, ordered string normalization for trimming, case folding and Unicode NFC.
- Schema-only input preflight for recipes, mappings, exclusions and partition layouts.

## 0.2.0 - 2026-10-07

### Added

- Reviewable recipe drafting from local inputs, with inferred keys, types, scope defaults and exclusion rationales.
- Concise human terminal summaries while preserving machine-readable stdout and existing exit codes.
- Dependency-free filtering in self-contained HTML reports.
- Local JSON Lines inputs and read-only SQLite table locators, including mixed-format comparison.
- A tested GitHub Actions evidence-upload reference that restores Parison's outcome code after artifact retention.

### Changed

- Bundle input provenance now records source format and SQLite table names without recording local paths.
- Bundle verification explains that integrity does not change the recorded comparison outcome.

### Security

- CI reference artifacts require summary sensitivity and avoid privileged fork execution.
- SQLite access is local, read-only and limited to one ordinary table; active journal sidecars, arbitrary SQL and BLOB values are rejected.

## 0.1.0 - 2026-10-06

### Changed

- Renamed the project, Python package and CLI from Parity to Parison.

### Added

- Strict keyed CSV, Parquet and mixed-format comparison from reviewed JSON recipes.
- Exact, symmetric numeric-tolerance, null, decimal-scale and timezone-aware timestamp semantics.
- Summary-only or bounded raw-evidence JSON and self-contained HTML result bundles.
- Bundle integrity manifests, verification, deterministic exit codes and safe error/interruption bundles.
- Input byte and row guards, generated semantic fixtures and accuracy-checked performance benchmarks.
- MIT license.

### Performance

- One-sided streaming summary comparison for CSV and Parquet.
- Fresh-process benchmarks with Python allocation and peak RSS measurements.
- Tested standard and adversarial input envelopes.
