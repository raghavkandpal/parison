# Parison 0.5 roadmap

Date: 8 October 2026

## Goal

Make Parison practical for real-world local exports: compressed files, explicit delimited-text parsing and reviewed null-token semantics, without changing keyed-v1 comparison outcomes or weakening resource and privacy controls.

## Ordered slices

### 1. Compression-aware input adapter

- [x] Recognize `.csv.gz`, `.jsonl.gz` and `.ndjson.gz` as their underlying text formats.
- [x] Support single files and same-format partition directories without temporary decoded copies.
- [x] Keep Parquet and SQLite behavior unchanged.

### 2. Decoded-byte limits

- [x] Retain the existing combined physical-byte limit.
- [x] Add an explicit combined decoded-byte limit for compressed text inputs.
- [x] Enforce the decoded limit during schema inspection, drafting and comparison.

### 3. Evidence and automation

- [x] Record compression and physical bytes in preflight and comparison provenance.
- [x] Keep policy locks, input-change detection and summary privacy intact.
- [x] Cover malformed streams, decoded overruns, mixed compressed/plain inputs and partitions.

### 4. Explicit delimited-text parsing

- [x] Support TSV and one-character CSV delimiters through reviewed recipe policy rather than filename guessing.
- [x] Apply parsing settings consistently in drafting, preflight, comparison, policy explanation and fingerprints.
- [x] Record effective parsing settings in evidence without publishing record values.

### 5. Reviewed null tokens

- [ ] Allow explicit text tokens such as `NULL` and `\\N` to map to null while preserving the distinction between null and an empty string.
- [ ] Keep null-token policy type-aware, reviewable and included in the effective-policy fingerprint.
- [ ] Reject ambiguous or invalid parsing policies before opening inputs.

### 6. Drafting and migration workflow

- [ ] Draft safe delimiter and null-token suggestions that remain visibly unapproved until reviewed.
- [ ] Extend preflight diagnostics and schemas with effective parsing metadata.
- [ ] Add one checked-in migration example combining compression, delimiters, null tokens, mappings and normalization.
- [ ] Cover plain/compressed CSV, TSV and JSON Lines across files and partitions without adding new dependencies.

## Deferred

ZIP archives, additional compression codecs, recursive discovery, encrypted archives, remote objects, arbitrary encodings and compression auto-detection by file contents remain out of scope. File extensions and reviewed parsing policy are part of the explicit local-input contract.
