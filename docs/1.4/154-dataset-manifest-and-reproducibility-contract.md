# Dataset manifest and reproducibility contract

Date: 16 October 2026

Status: **frozen for 1.4 implementation**

## Claim boundary

`dataset-manifest-v1` PASS means the explicitly declared local regular files exist under the supplied root and match their declared byte counts and SHA-256 digests. It does not prove upstream completeness, freshness, provenance authenticity, semantic equality, approval or cutover safety.

`reproducibility-diagnostic-v1` describes selected runtime facts. Differences are informational and never change a comparison or manifest outcome in v1.

## Manifest authoring shape

```json
{
  "manifest_version": 1,
  "collection_id": "september-backfill",
  "policy": {"kind": "reconciliation", "sha256": "..."},
  "resources": [
    {
      "id": "payments",
      "role": "candidate",
      "format": "jsonl",
      "path": "candidate/payments.jsonl",
      "bytes": 917004,
      "sha256": "...",
      "schema_sha256": "..."
    }
  ]
}
```

Top-level and nested objects are closed. Duplicate JSON keys are errors. `collection_id` and resource IDs use Parison's released identifier grammar. Policy kind is `suite` or `reconciliation`; its digest is required. Roles are `baseline`, `candidate`, `receipt` or `supporting`. Formats are `csv`, `tsv`, `json`, `jsonl`, `parquet` or `sqlite`; `json` is reserved for receipt/supporting artifacts rather than comparison inputs.

Resources are canonicalized by `(id, role, path)`. `(id, role)` pairs and paths are unique. `schema_sha256` is optional. Unknown fields and invalid integers or digests fail closed.

## Paths and opened resources

Paths are non-empty relative POSIX paths already in lexical normal form. Absolute paths, URI-like prefixes, backslashes, empty/`.`/`..` segments, NULs and Windows drive or namespace forms are rejected. Portable collision keys use NFC plus case folding; two paths with the same collision key are rejected.

Creation and verification reject a symlink at any path component. The final object must be a regular file. Opened `(device, inode)` aliases are rejected within one manifest operation. Hashing streams one descriptor at a time and compares descriptor size, modification nanoseconds and identity before and after reading. Mutation is `ERROR`, never an automatic retry.

SQLite resources are accepted only without adjacent `-wal`, `-journal` or `-shm` state. Parison does not checkpoint, back up or mutate SQLite. Whole-file identity is independent of logical table equality.

## Canonical identity

Canonical bytes are UTF-8 JSON with sorted object keys, compact separators and no trailing newline, prefixed for hashing with the ASCII domain `parison:dataset-manifest-v1\0`. The fingerprint is lowercase SHA-256. Runtime facts, absolute root, manifest location, timestamps, permissions, ownership, inode and device are excluded.

## Creation and verification

Creation receives an explicit root, policy binding, collection ID and one or more resource declarations. It reads local files, fills byte count and digest, canonicalizes the manifest and writes it atomically with no overwrite.

Verification revalidates the declaration, safely reopens every resource, compares byte count before digest, compares SHA-256, and returns:

- `PASS` when every declared member matches;
- `FAIL` for missing members, size mismatch, digest mismatch or undeclared members under an explicitly supplied closed scope;
- controlled `ERROR` for malformed declarations, unsafe paths, aliases, unsupported objects, ambiguous SQLite state or mutation during reading.

Results contain the manifest fingerprint, policy binding, outcome, complete flag, aggregate counts and stable reason codes. Full output may include resource IDs and roles but never values. Summary-safe output excludes paths, filenames and resource IDs.

## Diagnostic shape

```json
{
  "diagnostic_version": 1,
  "manifest_sha256": "...",
  "runtime": {
    "parison_version": "1.4.0",
    "python_implementation": "cpython",
    "python_version": "3.14.0",
    "os_family": "darwin",
    "architecture": "arm64",
    "sqlite_version": "3.50.4",
    "parquet_reader": null
  },
  "observations": []
}
```

The closed runtime fields exclude paths, hostnames, users, environment variables, arguments and package inventories. `parquet_reader`, when present, contains only distribution and version. Observations use a closed reason-code vocabulary and sorted string details where the schema permits them.

Diagnostic canonical bytes use the domain `parison:reproducibility-diagnostic-v1\0`. Comparison requires two valid diagnostics for the same manifest fingerprint and emits fields in schema order with status `same`, `different`, `missing-left` or `missing-right`. Its outcome is always `INFORMATIONAL`.

## Compatibility

Both artifacts are opt-in additions. Released recipes, suites, results, manifests, bundles, canonical bytes, fingerprints, CLI JSON and exit codes remain unchanged.

## Dataset evidence bundle

`dataset-evidence` schema version 1 is a new opt-in bundle kind. It atomically publishes exactly four separately digested members: canonical `dataset-manifest.json`, full `manifest-result.json`, normalized `effective-policy.json`, and `reproducibility-diagnostic.json`. Its outer manifest binds both artifact fingerprints, the policy kind and fingerprint, and the verification outcome.

Verification checks exact member coverage and bytes, revalidates every closed artifact, recomputes manifest, diagnostic and policy fingerprints, derives result counts, reason codes and outcome from ordered resource statuses, and checks every cross-member binding. It verifies preserved evidence only; it does not reopen source resources. Standard inspection exposes aggregate counts, reason codes, closed runtime facts and fingerprints but no paths, filenames or resource IDs.

Publication uses private staging, atomic no-overwrite installation and cleanup after failure or interruption. Released bundle kinds keep their existing readers and bytes; old readers reject this new kind rather than partially interpreting it.
