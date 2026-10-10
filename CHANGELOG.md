# Changelog

All notable changes will be documented in this file.

## Unreleased

### Added

- Bounded local suite concurrency through `run-suite --jobs N`, using cross-platform spawned workers and deterministic plan-order reduction.
- Concurrent workspace resume, a local-concurrency GitHub Actions example, and verified tiny-fixture plus mixed-mode 100k-row performance/memory evidence.

### Fixed

- Unexpected or abruptly terminated suite workers now produce verifiable summary-safe ERROR evidence without disclosing arbitrary exception text.
- Interrupted concurrent runs checkpoint every completed verified workspace child before returning exit 130, allowing conservative reuse on the next explicit resume.

Bounded early worker termination remains required before the 0.12 release; current interruption waits for active workers to finish safely.

## 0.11.0 - 2026-10-10

### Added

- Strict suite-v2 plans with tags, deterministic selection, canonical plan fingerprints and effective per-case resource limits.
- Portable suite-shard bundles, recursive verification and exact-coverage atomic assembly.
- Conservative resumable workspaces that revalidate child integrity, policies, limits, versions and current input digests.
- Bounded summary-safe Markdown and JUnit-style CI reports plus a sharded GitHub Actions reference workflow.

## 0.10.0 - 2026-10-09

### Added

- Strict ordered comparison suites spanning keyed, aggregate and multiset cases.
- Atomic suite bundles with recursively verified child bundles, safe aggregate inspection and installed plan/result/manifest schemas.

## 0.9.0 - 2026-10-09

### Added

- Verified bundle inspection with safe evidence-coverage, policy and bundle provenance metadata.
- Bounded JSON Lines export of published raw evidence with classification, evidence-kind and exact field/measure filters.

### Fixed

- Evidence export now uses collision-safe staging and atomic no-overwrite publication.

## 0.8.0 - 2026-10-09

### Added

- Exact keyless multiset comparison with duplicate-aware occurrence conservation.
- Recipe, preflight and result v3 schemas with bounded deterministic evidence.
- Canonical typed row encoding, explicit multiset drafting, cross-format examples and CI smoke coverage.
- Privacy-safe multiset preflight diagnostics and hard distinct-row resource limits.

## 0.7.0 - 2026-10-09

### Added

- Normative aggregate-v1 semantics for global and grouped reconciliation, including empty, null, ordering, exact-decimal and disclosure rules.
- Strict aggregate recipe v2 validation, an installed `recipe-v2` JSON Schema, and stable mode-aware effective-policy fingerprints.
- Deterministic global and grouped aggregate execution with exact integer/scaled-decimal sums, bounded groups, result v2 bundles, aggregate terminal output and HTML reports.
- Aggregate-aware schema and record preflight with preflight v2 output, privacy-safe invalid group/measure counts and explicit group bounds.
- Explicit `draft-recipe --aggregate` suggestions and a checked-in cross-format aggregate workflow.
- Aggregate measure-conservation totals and schema-valid aggregate error/interruption bundles.
- Hand-audited aggregate adversarial coverage for empty shapes, all-null measures, missing and exploding groups, exact decimal reordering and tolerance boundaries.
- Reproducible global, low-cardinality and high-cardinality aggregate accuracy/performance profiles plus CI smoke coverage.

## 0.6.0 - 2026-10-08

### Added

- Opt-in full-record validation through `validate-inputs --records`, with aggregate type and key-identity diagnostics.
- Record validation completes its scan after configured type failures and reports privacy-safe invalid-row and per-field counts.

### Fixed

- Type-parse errors identify the configured column and type without echoing rejected source values into diagnostics or summary error bundles.

## 0.5.0 - 2026-10-08

### Added

- Bounded local gzip CSV and JSON Lines inputs, including partitions and mixed compressed/plain comparisons.
- Separate combined physical and decoded input byte limits with compression provenance in results and preflight diagnostics.
- Explicit one-character baseline and candidate delimiters, TSV and gzip TSV inputs, and delimiter provenance in effective policy, preflight and comparison evidence.
- Reviewed baseline and candidate null tokens for delimited inputs, with safe empty defaults and preserved empty-string semantics.

### Fixed

- Recipe drafting now rejects inputs changed during row inspection, not only during schema inspection.

## 0.4.0 - 2026-10-08

### Added

- Machine-readable missing, unexpected, mapped and excluded-column diagnostics from `validate-inputs`.
- A data-free `explain` command that renders every effective recipe policy and source-column mapping.
- Versioned Draft 2020-12 JSON Schemas for recipe and result artifacts.
- A versioned Draft 2020-12 JSON Schema for bundle manifests.
- A versioned Draft 2020-12 JSON Schema for structured input-preflight results.
- Installed-schema discovery through `parison schema recipe|result|manifest|preflight`.
- Canonical effective-policy SHA-256 fingerprints in explanations and comparison evidence.
- An optional comparison gate that rejects policies not matching a reviewed fingerprint before reading inputs.
- Opt-in machine-readable manifest output from `parison verify --json`.
- Effective-policy fingerprints and optional policy locking in structured input preflight results.

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
