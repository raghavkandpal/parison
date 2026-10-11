# Parison 0.13 roadmap

Date: 11 October 2026

Status: **in development**

## Focus: reviewed authoring and zero-custody run discovery

Parison 0.13 joins two adjacent workflow gaps: editors should understand every supported recipe and suite version before execution, and users should be able to find their verified local runs without uploading evidence or adopting a daemon.

The release remains one workflow slice: **author a reviewed policy, run it locally, then explicitly index safe result metadata for later discovery**.

## Release capabilities

1. Installed `recipe-authoring` and `suite-authoring` Draft 2020-12 schemas select the correct existing versioned schema offline.
2. Stable raw-content `$id` values, descriptions, examples and a VS Code association example support validation, completion and hover help without a YAML dialect.
3. `parison catalog add --database DB RUN` verifies a bundle before storing its safe `inspect` projection.
4. `catalog list` filters by outcome, kind, policy fingerprint and live state, rechecks each bundle and reports `current`, `modified` or `missing` deterministically.
5. `catalog show` selects one normalized local path and exposes duplicate-path counts for copied bundles; `catalog remove` deletes only that index entry.
6. Catalog writes are explicit, transactional and local. Comparison commands never mutate a catalog implicitly.

## Compatibility and non-goals

- Runtime recipe and suite validation remains authoritative and unchanged.
- Catalog deletion never changes a run bundle; bundle deletion never silently edits the catalog.
- The database stores no discrepancy samples, source values, credentials or copied evidence.
- No hosted history, daemon, filesystem watcher, automatic repair, remote connector, UI or YAML syntax is introduced.
- Relocation is represented as one missing path plus an explicitly added path; Parison does not guess user intent.

## Release gates

1. Every checked-in recipe and suite validates through the offline authoring schemas and its existing runtime path.
2. Raw-sensitivity bundle values cannot be found in the catalog database.
3. Current, modified, missing and duplicate-copy states are deterministic across platforms.
4. A built wheel contains both authoring schemas and runs the catalog workflow outside the source checkout.
5. Python 3.11–3.14 plus macOS and Windows pass without adding a runtime dependency.
