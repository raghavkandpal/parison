# Parison 0.13.0 release checklist

Date: 11 October 2026

Status: **released**

## Feature and safety gates

- [x] Installed authoring schemas cover every supported recipe and suite version with stable published IDs, descriptions and examples.
- [x] `export-editor-schemas` atomically emits seven locally resolving files, refuses overwrite and requires no network during validation.
- [x] Catalog writes are explicit and transactional; no compare or suite command silently mutates history.
- [x] Only recursively verified safe inspection metadata is stored; raw discrepancy keys and values are absent from the database.
- [x] Add, compact filtered list, full show and non-destructive remove cover the local catalog lifecycle.
- [x] Current, modified, missing and duplicate-copy states are deterministic; policy filters cover standalone and nested suite cases.
- [x] Catalog databases are versioned, reject unsafe paths and corrupt metadata, and cannot be placed inside indexed evidence bundles.

## Candidate evidence

- [x] 192 local tests passed on arm64 macOS; six optional Parquet tests were skipped where Polars was absent.
- [x] GitHub Actions run [38128658514](https://github.com/raghavkandpal/parison/actions/runs/38128658514) passed on Linux Python 3.11–3.14, macOS and Windows from `147413e4deb83c5e92dc05513ecfd520a872047d`.
- [x] The development wheel contained both authoring schemas and the catalog module; a clean Python 3.12 environment printed the union schema, indexed a verified three-mode suite and found it by PASS suite filters.

## Publication

- [x] Versioned release commit `5632209` passed [the full matrix](https://github.com/raghavkandpal/parison/actions/runs/38128767709) on Linux Python 3.11–3.14, macOS and Windows.
- [x] Pull request [#20](https://github.com/raghavkandpal/parison/pull/20) merged to `main` as `3cde49a2ab0b404e1f16fee45005ca3edb207b03`; annotated tag `0.13.0` and the [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/0.13.0) publish the wheel, source archive and checksums.
- [x] Downloaded release assets matched their published checksums. The wheel SHA-256 was `2cb1b6372871249a75ca2f7086fb8483759243b5e15639842ea197a6fddacfd2`; the source archive SHA-256 was `8398bf859604f32d66cc9a8e3bce20c69fde1776c2f3e10e2080ffa2e24c477f`.
- [x] A clean install from the downloaded wheel reported `parison 0.13.0`, exported all seven offline schemas, and added and listed an existing verified suite in a fresh catalog.
- [x] The README and documentation index mark the release complete.

PyPI publication remains intentionally deferred.
