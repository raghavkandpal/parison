# Parison 1.2 engineering checkpoint

Date: 15 October 2026

Status: **candidate implementation complete**

## Delivered capability

Parison now provides two explicit, local-first boundaries without changing released recipe meanings:

1. `semantic-scalar-v1` projects supported scalar representations from CSV, TSV, JSON Lines, SQLite and optional Parquet through a closed source-type allowlist shared by keyed, aggregate and multiset comparison.
2. `schema-evolution-v1` records reviewed field lineage, while `policy-diff-v1` deterministically assesses two effective policies without reading datasets, transforming values, changing approval state or authorizing cutover.

## Compatibility and safety evidence

- Recipes that omit `input_projection` retain their released parsing behavior and policy fingerprints.
- Canonical semantic rows are pinned byte-for-byte across formats, scalar boundaries, null/empty cases and row-order permutations.
- Timestamp projection rejects precision beyond microseconds before parser truncation across extended/basic ISO forms; Parquet rejects nanosecond and timezone-naive timestamp representations before materialization.
- Evolution declarations are strict JSON with deterministic canonical identity, stable IDs and explicit change cardinality.
- Policy diff uses a closed path vocabulary, accounts for every compared and excluded field, denies optional compared fields and unsafe transformations, and fails unknown semantic paths closed.
- Summary output omits policy paths, source paths, names, IDs, values, defaults, filters, rationales and policy fragments.

## Qualification evidence

- Semantic corpus commit `0b07f1cd1705020e7fe039089ea8f8f1e98ac47b` passed [built-wheel CI run 38693629443](https://github.com/raghavkandpal/parison/actions/runs/38693629443) on Python 3.11–3.14, macOS and Windows with pinned Polars 1.44.2.
- Policy mutation commit `8007120318be689b38c354ba4f624fbe4fb42d40` passed [built-wheel CI run 38694026911](https://github.com/raghavkandpal/parison/actions/runs/38694026911) on the same matrix.
- Release-review correction commit `0eb334c41a9102cc6eacf20f4f7b29df6400dad9` passed [built-wheel CI run 38694494205](https://github.com/raghavkandpal/parison/actions/runs/38694494205).
- At the final implementation checkpoint, `make check` passes 276 tests with 11 documented optional-Polars skips. The semantic and evolution suites also pass under Python 3.12 with Polars 1.36.1.
- Independent Standards and Spec reviews of `origin/main...develop` report no implementation blockers at `8c6c2106f96a671d4d42101bfc9274a9d1d9b174`.

Exact candidate and publication evidence belongs in the [1.2.0 release checklist](146-release-checklist.md).
