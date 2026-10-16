# Parison 1.4 roadmap

Date: 16 October 2026

Status: **release candidate**

## Theme

Bind a reviewed local dataset collection to exact bytes and explain whether a later rehearsal ran under materially different reader/runtime conditions.

The governing input is [dataset manifest and reproducibility research](152-dataset-manifest-and-reproducibility-research.md). The release is one larger opt-in capability composed from two separate claims:

1. `dataset-manifest-v1` proves closed membership and byte identity under an explicit local root.
2. `reproducibility-diagnostic-v1` records and compares a closed set of explanatory runtime facts without changing verification outcomes.

## Scope

1. Freeze strict schemas, canonical bytes and domain-separated fingerprints for manifests and diagnostics.
2. Create manifests only from explicitly named regular local files; reject unsafe paths, symlinks, aliases and ambiguous SQLite state.
3. Verify exact membership, byte counts and SHA-256 identities with mutation detection and aggregate-only summary-safe results.
4. Bind each manifest to one existing suite or reconciliation policy fingerprint without duplicating its semantics.
5. Record Parison, Python, OS, architecture, SQLite and supported Parquet-reader facts in a separate diagnostic.
6. Compare diagnostics deterministically with closed statuses and reason codes; differences remain informational in 1.4.
7. Qualify canonical bytes, publication races, supported platforms and a realistic copied-artifact backfill workflow.

## Non-goals

- connectors, URLs, object stores, catalogs, extraction or source completeness;
- globs, ignore files, implicit directory discovery or recursive remote manifests;
- byte normalization, archive creation, repair or SQLite snapshot creation;
- environment locking, package inventories, hostnames, usernames or absolute-path evidence;
- diagnostic differences changing PASS, FAIL or INCONCLUSIVE;
- signing, approval, cutover authorization or reinterpretation of released evidence.

## Delivery gates

1. Contracts: schemas, canonical fixtures, path/role/format vocabulary and explicit outcome semantics.
2. Local integrity: safe creation, exact verification, summary-safe rendering and atomic no-overwrite publication.
3. Explanation: deterministic diagnostic capture/comparison and reader-specific observations.
4. Integration: bind manifests and diagnostics into versioned evidence without changing old bundle readers.
5. Qualification: full local gate, independent review, built-wheel matrix and fresh-wheel workflow.

Named resources remain the default. Operators may additionally declare up to 100 reviewed, non-overlapping relative directory scopes; those scopes are enumerated without following links so undeclared files fail closed. A glob/include-exclude language or runtime-compatibility gate requires new evidence and a later explicit contract version.
