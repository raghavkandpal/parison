# Changelog

All notable changes will be documented in this file.

## Unreleased

### Changed

- Added pinned Ruff lint and formatting gates to local development and CI, plus a single contributor guide for setup, testing, compatibility and evidence-safety standards.
- Split policy, input, comparison, evidence and suite implementation out of `parison.core` while preserving its released import surface as a compatibility facade.

### Fixed

- Consolidated atomic no-replace directory publication and output-parent safety so run, suite, editor-schema, reconciliation and dataset-evidence publishers resist concurrently created destinations consistently across supported platforms.

## 1.4.0 - 2026-10-16

### Added

- Strict local `dataset-manifest-v1` creation and verification with mandatory existing-policy binding, canonical fingerprints, descriptor-relative safe paths, optional reviewed closed-scope membership, atomic no-overwrite publication and exact SHA-256 byte identity.
- Separate `reproducibility-diagnostic-v1` capture and deterministic informational comparison over a closed, summary-safe runtime vocabulary.
- Atomic `dataset-evidence` bundles that separately digest and semantically bind the canonical manifest, full verification result, effective policy, reproducibility diagnostic and recursively verified suite/reconciliation result, with standard verification and summary-safe inspection.

### Fixed

- Dataset resource and evidence verification now resist component/member replacement races, reject extra bundle members, recheck SQLite sidecars, and clean private staging after publication races or interruption.

## 1.3.0 - 2026-10-16

### Added

- Frozen opt-in `time-alignment-v1` and `reconciliation-v1` authoring contracts with strict installed schemas, semantic cross-reference validation, deterministic canonical bytes and fingerprints.
- CLI validation and explanation for fixed UTC half-open event windows, source-owned snapshot/watermark/cutoff claims, and the closed identity/reference/grouped-sum relationship vocabulary.
- Deterministic alignment preflight that verifies receipt, alignment and effective-policy fingerprints before scanning both dataset sets; enforces exact window edges and resource limits; detects changed inputs; and emits a strict installed result schema with conservative PASS, FAIL or INCONCLUSIVE outcomes.
- Per-side identity and reference execution with explicit null semantics, duplicate-parent protection, aggregate-only diagnostics, deterministic ordering, input-change detection and equivalent bounded memory/SQLite engines.
- Per-side grouped-sum conservation over matching integer or scaled-decimal measures, including exact and symmetric tolerance comparison, closed null behavior, distinct failure counts and equivalent bounded memory/SQLite engines.
- A composed `reconcile` gate that runs alignment, existing per-dataset parity and all declared relationships under one input-change guard, applies conservative FAIL-before-INCONCLUSIVE reduction and offers a summary-safe projection without dataset/check identifiers or detailed counts.
- Atomic no-overwrite reconciliation bundles with private staging, manifest-bound full and summary evidence, normalized declarations, standard verification and summary-safe inspection.

### Fixed

- Reconciliation publication uses platform-native atomic no-replace directory operations, and verification binds receipt and per-dataset policy identities back to the effective declarations.

### Compatibility

- The 1.3 alignment preflight is a separate opt-in command and does not execute parity or relationship checks. Released recipes, suites, results, bundles, fingerprints, canonical bytes and exit codes remain unchanged.

## 1.2.0 - 2026-10-15

### Added

- Opt-in `semantic-scalar-v1` projection for keyed, aggregate and multiset recipes, with a closed policy-directed source-type allowlist across delimited text, JSON Lines, SQLite and Parquet.
- Pre-materialization Parquet schema validation that rejects nested, binary, unknown, timezone-naive and nanosecond timestamp representations, including unsupported excluded columns.
- A normative cross-format projection contract and task guide that preserve legacy recipe behavior while making lossy conversions explicit upstream work.
- Strict local `schema-evolution-v1` declarations with stable logical field identity, deterministic canonical bytes and installed JSON Schema.
- Deterministic `policy-diff-v1` assessment of effective policies, including full and summary-safe output, closed reason codes and explicit `ACCEPT`, `DENY` or `INCONCLUSIVE` compatibility labels.
- A pinned semantic-scalar compatibility corpus proving canonical convergence across CSV, TSV, JSON Lines, SQLite and Parquet in keyed, aggregate and multiset modes, plus complete admitted Parquet dtype and rejected scalar-class coverage.

### Compatibility

- Recipes 1–3 that omit `input_projection` retain their released parsing behavior and policy fingerprints. Selecting `semantic-scalar-v1` is explicit and fingerprinted without changing comparison contracts, result schemas, canonical encodings or historical bundle readability.

### Fixed

- Windows installations include Python's first-party IANA timezone fallback so aware Parquet timestamps project consistently instead of failing when the operating system has no zone database.
- Semantic timestamp projection rejects text precision beyond microseconds across all accepted date-time separators instead of allowing the standard parser to truncate distinct values, without changing legacy recipes.
- Policy diff denies optional fields that actively participate in comparison; optionality remains review metadata only for fields outside comparison.
- Policy evolution rejects boolean versions and structured enum values as controlled input errors, compares excluded-field contract metadata before compatibility, and emits only closed versioned policy paths.
- Aggregate tolerance addition/removal now emits the closed `measures[].tolerance` path instead of an unknown-path record; the installed policy-diff schema enumerates the complete path vocabulary.
- Empty text remains a valid semantic string while continuing to fail closed for every non-string type.

## 1.0.0 - 2026-10-14

### Compatibility

- Promotes the qualified 0.19 surface unchanged as the stable 1.x baseline. Recipe semantics, schemas, bundle verification, canonical bytes, exit codes, CLI JSON and summary-safety boundaries are unchanged.
- Existing commands and the consolidated 0.19 command guide remain authoritative for 1.0. No new parser, dependency, comparison mode or execution engine is introduced.
- PASS continues to mean agreement under the explicit policy—not extraction truth, policy approval, signer authentication or cutover authorization.

## 0.19.0 - 2026-10-14

### Added

- A frozen compatibility contract and automated upgrade corpus covering immutable keyed, aggregate, multiset, suite-v1 and suite-v2 bundles from their original releases.
- A built-wheel acceptance workflow spanning project initialization, repeated rehearsal history, suite execution, Statement verification and cutover reporting on the supported CI matrix.
- A consolidated machine-qualified performance envelope covering released comparison modes and explicitly recording the evidence gaps that remain before 1.0.
- Accuracy-verified 100,000-row aggregate measurements for global, low-cardinality and maximum-default-cardinality profiles.
- Accuracy-verified raw high-mismatch measurements at 10,000 and 100,000 rows plus repeated mixed-mode suite concurrency medians.
- A checkable 1.0 readiness gate separating local automation, exact-commit CI, human workflow validation and public-release reconciliation.
- A consolidated 0.19 user guide covering every supported CLI command plus inputs, comparison modes, rehearsals, suites, investigation, limits and authenticated evidence handoff.

### Compatibility

- Recipe versions 1–3 retain their keyed-v1, aggregate-v1 and multiset-v1 meanings; released schemas, outcome names, exit codes, policy fingerprints, canonical encodings and deterministic evidence ordering remain stable through 1.x.
- Current Parison continues to verify released run result schemas 1–3 and suite-v1/v2 bundles. Verification and derived evidence never rewrite historical artifacts or invent unavailable provenance.
- Existing commands, required arguments and machine-readable fields remain supported through 1.x. Additive optional fields are allowed, while changed meanings or defaults require an explicit versioned contract.
- Summary-safe output continues to exclude source paths, keys, values and discrepancy samples. Verification remains an integrity and semantic check—not extraction truth, policy approval, signer authentication or cutover authorization.
- Version 0.19 introduces no user-visible incompatibility. Native workbook and unstructured-document ingestion remain deferred rather than silently changing the supported input boundary.

## 0.18.0 - 2026-10-13

### Added

- Explicit SQLite-backed keyed comparison for direct commands and suite-v2 cases, with the existing keyed-v1 semantics, deterministic evidence ordering, a hard temporary-storage ceiling and private-workspace cleanup.

### Fixed

- SQLite keyed raw evidence preserves pre-normalization values, and suite-generated SQLite ERROR and INTERRUPTED bundles retain engine and temporary-limit metadata.

## 0.17.0 - 2026-10-13

### Added

- Deterministic unsigned in-toto Statements for verified run, suite and suite-shard bundles, with a strict installed schema and atomic no-overwrite export.
- Semantic verification that binds an already-authenticated Statement to a recursively verified local bundle without adding cryptography, OIDC or network dependencies.
- Evidence handoff guidance for identity-constrained detached Cosign signatures and source-owned extraction receipts.
- Deterministic Markdown cutover cover sheets for verified runs, suites and suite shards.

## 0.16.0 - 2026-10-12

### Added

- `parison init DIRECTORY` creates a no-overwrite, runnable keyed migration starter with summary-only evidence defaults.
- Failed comparisons print copyable bundle verification and safe inspection commands, plus evidence export only for raw-sensitivity bundles; non-passing suites also point to a bounded Markdown CI report.
- Installed-wheel CI runs the generated-project quickstart on Linux, macOS and Windows; the public GitHub Actions example now pins the latest release.
- Tested dbt, Airflow and Dagster references keep snapshot extraction and credentials outside Parison while treating the verified bundle as the portable gate artifact.

## 0.15.0 - 2026-10-12

### Added

- Policy-locked catalog history with deterministic insertion order and explicit outcome and discrepancy-count transitions.
- Safe catalog diff for two ordinary run bundles with matching effective-policy fingerprints.
- Baseline and candidate content digests in verified safe run inspection metadata.
- A synthetic payout-reconciliation starter suite with aggregate conservation, keyed diagnosis and an intentionally failing fixture.
- A synthetic feature-pipeline parity suite combining reviewed numeric tolerances and exact keyless occurrence matching.

### Fixed

- Catalog history now uses a durable explicit sequence that survives deletion and `VACUUM`, with automatic schema-v1 migration.
- Catalog paths are normalized lexically, safe history/diff projections share one disclosure boundary, and live-state checks no longer parse result evidence.

## 0.14.0 - 2026-10-11

### Added

- An explicit SQLite-backed multiset engine with canonical typed equality, deterministic evidence, a hard database-size ceiling and private-workspace cleanup.
- Suite-v2 execution policy for disk-backed multiset cases, plus a synthetic warehouse-backfill workflow combining aggregate conservation and exact occurrence matching.
- Reproducible cross-engine benchmarks recording accuracy, elapsed time, Python allocation, process peak RSS and SQLite storage.

### Fixed

- SQLite ERROR and INTERRUPTED bundles retain the selected engine and temporary-storage ceiling.
- Suite interruption contains disposable spill state inside the suite staging area or explicit workspace.

## 0.13.0 - 2026-10-11

### Added

- Offline editor schemas spanning every supported recipe and suite version, with stable raw-content identifiers, descriptions, examples, atomic local export and a VS Code association example.
- An explicit local SQLite run catalog with add, outcome/kind/policy/state filtering, show and non-destructive remove operations that store only verified safe inspection metadata and report current, modified, missing and duplicate bundle paths.

## 0.12.0 - 2026-10-11

### Added

- Bounded local suite concurrency through `run-suite --jobs N`, using cross-platform spawned workers and deterministic plan-order reduction.
- Concurrent workspace resume, a local-concurrency GitHub Actions example, and verified tiny-fixture plus mixed-mode 100k-row performance/memory evidence.

### Fixed

- Unexpected or abruptly terminated suite workers now produce verifiable summary-safe ERROR evidence without disclosing arbitrary exception text.
- Interrupted concurrent runs stop admission, terminate the active worker set within a fixed shutdown bound, remove incomplete scratch, and checkpoint every completed verified workspace child before returning exit 130.

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
