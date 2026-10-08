# Versioned JSON Schemas

Date: 8 October 2026

Parison publishes Draft 2020-12 schemas for its two durable JSON interfaces:

- [`recipe-v1.schema.json`](../../schemas/recipe-v1.schema.json) describes recipe version 1, including mappings and normalization.
- [`result-v1.schema.json`](../../schemas/result-v1.schema.json) describes result schema version 1 for completed and terminal outcomes.

The runtime loader remains authoritative for semantic relationships JSON Schema cannot express concisely, including key names existing in `columns`, mapping uniqueness, finite non-negative numeric tolerance text, and columns not overlapping exclusions.

The schemas are tested for validity and applied to committed recipes, the checked-in result bundle, a fresh 0.3 comparison result and a terminal error result. The validator is a test-only dependency; Parison's runtime remains dependency-free unless Parquet support is installed.
