# Parison 0.13.0 release checklist

Date: 11 October 2026

Status: **candidate verified; publication pending**

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

- [ ] Pass the versioned release commit through the full matrix.
- [ ] Merge to `main`, tag `0.13.0`, and publish wheel, source archive and checksums.
- [ ] Download the immutable wheel, verify its checksum, install it cleanly and repeat editor export plus catalog smoke tests.
- [ ] Mark the release complete in the README and documentation index.

PyPI publication remains intentionally deferred.
