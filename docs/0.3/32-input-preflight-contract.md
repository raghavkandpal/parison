# Input-preflight contract

Date: 7 October 2026

## Purpose

`validate-inputs` checks whether the current physical input schemas fit a reviewed recipe before Parison performs a comparison. It is suitable as a quick local or CI gate when a full record comparison belongs to a later step.

```sh
parison validate-inputs \
  --recipe comparison.recipe.json \
  --baseline baseline/ \
  --candidate candidate.parquet
```

A successful command exits zero and writes a small JSON object to standard output. The object records `status`, comparison mode, canonical column count, key names, and each side's format, bytes, physical column count and partition count. SQLite table names are included when applicable. It contains no record values or local paths.

## Checks

Preflight performs normal strict recipe validation and then checks:

- the combined input size against `--max-input-bytes`;
- supported regular, non-symlink inputs and partition boundaries;
- consistent schemas across immediate partition files;
- required physical columns after side-specific mappings;
- unexpected columns unless the recipe explicitly excludes them;
- duplicate or empty physical column names.

CSV preflight reads the header. Parquet preflight reads schema metadata. SQLite preflight opens the named ordinary table read-only and inspects its columns. JSON Lines has no separate schema, so preflight parses the first object in each file; it does not scan later objects.

## Boundary

Preflight does not parse all values, validate types, count rows, detect null or duplicate keys, compare records, calculate source digests, or prove that an input remains unchanged afterward. `compare` remains the authoritative operation and repeats relevant validation while reading the complete logical input.

The byte limit is a processing guard, not a statement that the command loads that many bytes into memory.
