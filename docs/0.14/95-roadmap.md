# Parison 0.14 roadmap

Date: 11 October 2026

Status: **implementation in progress**

## Focus: exact local comparison beyond process memory

Parison 0.14 targets one repeated operational constraint found in migration, backfill, ledger and feature-pipeline validation: a high-cardinality exact comparison may fit on local disk but not in Python memory.

The release keeps the multiset-v1 semantic contract and adds an explicit SQLite execution engine. Engine choice changes resource use, not equality, evidence ordering or outcomes.

## Planned release slice

1. `parison compare --engine sqlite` supports multiset-v1 recipes without a new runtime dependency.
2. Suite-v2 cases may select the same engine through reviewed `execution` settings.
3. Canonical typed row encodings remain Parison-owned; SQLite stores and counts them but does not define coercion or equality.
4. `--max-temp-bytes` fails closed, and `--temp-directory` provides an explicit protected parent for the private workspace.
5. Success and handled failure remove the spill database; results record the selected engine and storage limit.
6. Cross-engine golden tests, forced-limit tests and benchmarks must pass on Linux, macOS and Windows before release.

## Non-goals

- No silent spill, remote connector, distributed execution or changed multiset semantics.
- No SQLite engine for keyed or aggregate comparison in this release.
- No claim that the operating system encrypts temporary storage or that local disk space is a memory sandbox.
- No universal scale or speed claim; published measurements remain machine-specific.

## Promotion gates

The SQLite engine will remain experimental until representative benchmarks demonstrate lower peak memory, bounded disk behavior and acceptable runtime. If those gates fail, 0.14 will not advertise spill execution as supported merely because the code exists.
