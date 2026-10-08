# Compressed-input contract

Date: 8 October 2026

Parison accepts local gzip-compressed CSV and JSON Lines inputs whose names end in `.csv.gz`, `.jsonl.gz` or `.ndjson.gz`. They may be compared with plain inputs and used in partition directories containing one logical underlying format. ZIP archives, compressed Parquet and content-based compression detection are unsupported.

## Resource limits

`--max-input-bytes` continues to limit the combined physical size of both sources. `--max-decoded-bytes` separately limits the combined UTF-8 bytes produced by gzip inputs; both default to 1 GB and must be positive.

Before schema inspection or record parsing, Parison reads gzip streams in bounded binary chunks to establish their decoded size. Parsing is then capped at the checked size, so a stream changed after inspection cannot expand beyond the accepted amount. Normal before/after source digests still reject any input changed during drafting or comparison.

The decoded limit applies to `draft-recipe`, `validate-inputs` and `compare`. No decoded temporary file is written.

## Evidence

Preflight and comparison provenance retain physical `bytes` and the underlying `format`, and add `compression: "gzip"` plus `decoded_bytes` for compressed sources. Summary sensitivity remains unchanged: these fields contain sizes and format metadata, never record keys or values.
