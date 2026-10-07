# Partitioned local input contract

Date: 7 October 2026

## Purpose

A directory path represents one logical baseline or candidate assembled from multiple local files. Partitioning changes physical storage only; schemas, identity, comparison rules and outcomes remain the same as a single-file input.

```sh
parison compare --recipe orders.recipe.json \
  --baseline snapshots/baseline-parts \
  --candidate snapshots/candidate-parts \
  --output runs/orders
```

## Discovery

- Discovery is non-recursive and deterministic by filename.
- Hidden entries are ignored.
- The directory must contain at least one visible entry.
- Every visible entry must be a regular, non-symlink file.
- All files must use one logical format: CSV, JSON Lines (`.jsonl`/`.ndjson`) or Parquet (`.parquet`/`.pq`).
- SQLite locators remain single-table inputs and cannot be partition directories.

## Semantics and limits

Every partition is validated against the same side-specific mapped schema. Row order and partition order do not affect keyed comparison. Null and duplicate keys are checked across the entire logical input, including duplicates split across files.

`--max-input-bytes` applies to the combined bytes of both logical inputs. `--max-rows` applies to the total rows in each logical input, not to each file independently. Drafting inspects all partitions under the same boundaries.

## Evidence

Input provenance records the logical format, total bytes, partition count and a stable SHA-256 digest derived from sorted filenames and file contents. Local directory and file paths are not published. Changing a filename or any file content changes the digest.

## Refusals

Empty directories, nested directories, visible unsupported files, mixed logical formats, symlinked entries and schema-inconsistent partitions are errors. Parison does not recursively discover data, infer partition columns from paths, expand globs, or read remote/object-store datasets.
