# Parison 0.5 roadmap

Date: 8 October 2026

## Goal

Read common local compressed text exports without allowing compressed size to bypass Parison's resource contract or changing keyed-v1 comparison outcomes.

## Ordered slices

### 1. Compression-aware input adapter

- [ ] Recognize `.csv.gz`, `.jsonl.gz` and `.ndjson.gz` as their underlying text formats.
- [ ] Support single files and same-format partition directories without temporary decoded copies.
- [ ] Keep Parquet and SQLite behavior unchanged.

### 2. Decoded-byte limits

- [ ] Retain the existing combined physical-byte limit.
- [ ] Add an explicit combined decoded-byte limit for compressed text inputs.
- [ ] Enforce the decoded limit during schema inspection, drafting and comparison.

### 3. Evidence and automation

- [ ] Record compression and physical bytes in preflight and comparison provenance.
- [ ] Keep policy locks, input-change detection and summary privacy intact.
- [ ] Cover malformed streams, decoded overruns, mixed compressed/plain inputs and partitions.

## Deferred

ZIP archives, recursive discovery, encrypted archives, remote objects and compression auto-detection by file contents remain out of scope. File extensions are part of the explicit local-input contract.
