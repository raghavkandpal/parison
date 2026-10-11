# Catalog history and safe diff contract

Status: **implementation contract**

## Commands

```text
parison catalog history --database CATALOG --policy-sha256 HASH
parison catalog diff --database CATALOG LEFT_BUNDLE RIGHT_BUNDLE
```

Both commands read the disposable local catalog. They do not mutate bundles or refresh stored metadata.

## History

`history` accepts exactly one lowercase SHA-256 policy fingerprint and includes ordinary run bundles whose last verified inspection projection has that fingerprint. Results are ordered by SQLite row identity assigned when a path was first added. Updating the same path retains its position.

Each run contains its catalog order, normalized local path, bundle digest, live state, outcome, completeness, counts, discrepancy count, runtime, resource limits and baseline/candidate content digests. Adjacent entries produce explicit outcome and discrepancy-count transitions.

Catalog order is reproducible for one database but is not an execution timestamp or proof of causality. If chronology matters, callers must add bundles in the intended order. Empty history is a successful empty result.

## Diff

`diff` accepts two paths already present in the catalog. Both entries must be ordinary run bundles and have the same non-empty policy fingerprint. A mismatch is an error.

The result contains left and right safe projections plus a `changes` object for differing outcome, completeness, counts, discrepancy count, runtime, resource limits or input content digests. Paths, bundle digests and live states identify the operands but are not themselves treated as semantic changes.

The operation uses only metadata captured after bundle verification by `catalog add`. It never opens raw inputs, samples or exported evidence. `state` still checks the current path: `modified` or `missing` warns that the stored projection no longer describes a currently verified bundle at that location.

## Security and interpretation

Input SHA-256 digests disclose content equality and should be treated as pseudonymous identifiers. They contain neither source paths nor values, but low-entropy source files may still be guessable by an attacker who possesses candidate content.

A PASS transition means the supplied snapshots satisfy the same effective comparison policy. It does not prove snapshot coordination, extraction completeness, accounting correctness or production cutover safety beyond the assertions and data supplied to Parison.
