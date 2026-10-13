# Parison 0.18 roadmap

Status: **planned**

## Theme: larger keyed comparisons

Parison 0.18 extends exact keyed verification beyond comfortable process memory while preserving the existing keyed-v1 contract. Engine choice changes resource use, never comparison meaning or evidence shape.

## Planned slices

1. Define an explicit SQLite keyed-engine contract, limits and failure behavior.
2. Implement bounded temporary storage with private staging and interruption cleanup.
3. Prove semantic and deterministic-output equivalence with the memory engine across PASS, FAIL, tolerance, null, mapping and duplicate-key cases.
4. Add suite-v2 engine selection, clean installed-wheel acceptance and cross-platform benchmarks.

## Acceptance gates

- Users opt into SQLite explicitly; Parison does not guess based on input size.
- Both engines produce equivalent outcomes, counts, policy fingerprints and bounded evidence for the same inputs.
- Temporary storage has an explicit byte ceiling and fails closed without publishing a complete bundle.
- Workspaces are private, symlink-safe and removed after success, failure or interruption.
- Benchmarks validate accuracy first and report machine-specific time, peak memory and storage without universal scale claims.

## Non-goals

- Automatic engine selection, distributed execution or remote databases.
- Aggregate spill, fuzzy matching, repair or changed keyed-v1 semantics.
- Hiding SQLite resource tradeoffs behind an unchanged memory limit.

This slice follows the accepted [product direction and release arc](../0.15/104-product-direction-and-release-arc.md).
