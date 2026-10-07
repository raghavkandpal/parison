# Parison 0.3 user guide

This guide extends the [0.2 user guide](../0.2/27-user-guide.md). The safety model, outcomes, bundle format and comparison contract remain unchanged.

## 1. Map renamed columns

Recipe policies use stable canonical names. Add a physical name for each side only when it differs:

```json
"columns": {
  "order_id": {"type": "string", "comparison": "exact"},
  "status": {"type": "string", "comparison": "exact"}
},
"column_mappings": {
  "order_id": {"baseline": "legacy_order_id", "candidate": "order_id"}
}
```

Mappings are explicit; drafting does not guess renames. Keys, counts and evidence continue to use canonical names.

## 2. Declare harmless string representation differences

Add an ordered `normalize` list to a string policy:

```json
"status": {
  "type": "string",
  "comparison": "exact",
  "normalize": ["trim", "casefold", "unicode_nfc"]
}
```

Rules run after parsing and before identity and comparison, including on keys. Omit the list to preserve exact behavior. Raw discrepancy samples retain the received pre-normalization values, but values made equivalent by policy do not produce discrepancies.

## 3. Compare partition directories

Pass a directory wherever `--baseline` or `--candidate` accepts a local CSV, JSON Lines or Parquet file:

```sh
parison compare \
  --recipe comparison.recipe.json \
  --baseline exports/baseline/ \
  --candidate exports/candidate/ \
  --output runs/migration
```

Each directory must contain immediate regular, non-symlink files of one supported format. Hidden entries are ignored. Nested directories, mixed formats, empty directories and inconsistent partition schemas are rejected. Ordering is deterministic, while duplicate keys and limits apply across the complete logical input.

## 4. Preflight physical schemas

Run preflight after recipe review and before an expensive comparison:

```sh
parison validate-inputs \
  --recipe comparison.recipe.json \
  --baseline exports/baseline/ \
  --candidate candidate.jsonl
```

Exit zero means both current physical schemas satisfy mappings and exclusions. Standard output is machine-readable JSON without record values or paths. Preflight is not a comparison: it cannot validate types, keys, row values or source stability. For JSON Lines it reads only the first object in each file because the format has no independent schema.

## 5. Try the combined example

The [`examples/0.3`](../../examples/0.3) migration example combines a renamed baseline schema, partitioned CSV input, mixed JSON Lines candidate and explicit normalization:

```sh
parison validate-inputs \
  --recipe examples/0.3/migration.recipe.json \
  --baseline examples/0.3/baseline \
  --candidate examples/0.3/candidate.jsonl

parison compare \
  --recipe examples/0.3/migration.recipe.json \
  --baseline examples/0.3/baseline \
  --candidate examples/0.3/candidate.jsonl \
  --output runs/0.3-example
```

The comparison passes: physical names, partitioning and declared string representation differences do not change the canonical records.

## Support boundary

Parison remains local-only and requires Python 3.11 or newer. CI covers Python 3.11–3.14, the pinned optional Polars dependency, Linux, macOS and Windows. Recursive discovery, remote connectors, fuzzy matching, arbitrary transformations and grouped publication of source values remain out of scope.
