# Changelog

All notable changes will be documented in this file.

## Unreleased

### Added

- Strict keyed CSV, Parquet and mixed-format comparison from reviewed JSON recipes.
- Exact, symmetric numeric-tolerance, null, decimal-scale and timezone-aware timestamp semantics.
- Summary-only or bounded raw-evidence JSON and self-contained HTML result bundles.
- Bundle integrity manifests, verification, deterministic exit codes and safe error/interruption bundles.
- Input byte and row guards, generated semantic fixtures and accuracy-checked performance benchmarks.

### Performance

- One-sided streaming summary comparison for CSV and Parquet.
- Fresh-process benchmarks with Python allocation and peak RSS measurements.
- Tested standard and adversarial input envelopes.
