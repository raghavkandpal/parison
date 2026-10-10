# Investigation contract

Status: **frozen for 0.9**

This contract covers local inspection and evidence export for verified Parison bundles. It does not change keyed-v1, aggregate-v1 or multiset-v1 comparison semantics.

## Bundle inspection

`parison inspect RUN_DIRECTORY` verifies the bundle before reading its result and emits one JSON object. The 0.9 fields are:

- `schema_version`, `outcome`, `complete`, `sensitivity` and `runtime` copy verified result metadata.
- `counts`, `problems` and `resource_limits` preserve their result meanings.
- `discrepancy_count`, `discrepancy_sample_size` and `discrepancy_sample_limit` describe published evidence coverage without exposing evidence values.
- `policy_sha256` identifies the effective comparison policy when the result contract provides it.
- `bundle_sha256` is the SHA-256 digest of the verified manifest file.
- `manifest_files` is the sorted list of files covered by the manifest.

Inspection never emits `discrepancy_sample`, source values, keys, groups or row shapes. Consumers must ignore unknown fields so later releases can add safe metadata without breaking them.

## Evidence export

`parison export-evidence` accepts only verified raw-sensitivity bundles. It selects from the already-published `discrepancy_sample`; it never rereads inputs or claims completeness beyond that sample.

The output is UTF-8 JSON Lines. The first line has one `_parison_export` object containing:

- `bundle_sha256`, `schema_version` and `policy_sha256` provenance;
- the applied `classification`, `kind`, `name` and `limit` filters.

Remaining lines are selected evidence objects in their original deterministic result order. The positive `limit` is applied after all filters. No matches is a successful export containing only the provenance line.

Classification values are `baseline_only`, `candidate_only`, `within_tolerance`, `different`, `baseline_surplus` and `candidate_surplus`. Kind values are `record`, `field`, `group`, `measure` and `row`; multiset-v1 evidence is treated as `row` without changing its stored result shape. `name` matches an exact keyed field or aggregate measure name.

Exports use a private temporary file and atomic no-overwrite publication. Existing targets are never replaced.

## Compatibility and privacy

- Result schema versions 1, 2 and 3 remain readable.
- Summary bundles cannot be promoted to raw evidence.
- Unknown classifications and kinds are rejected instead of silently broadening an export.
- Adding an optional inspection field or provenance field is backward compatible; removing or changing an existing field requires a new investigation contract.
- Evidence objects retain their result-schema meaning. Consumers should branch on the provenance `schema_version`.
