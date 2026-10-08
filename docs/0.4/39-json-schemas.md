# Versioned JSON Schemas

Date: 8 October 2026

Parison publishes Draft 2020-12 schemas for its durable JSON interfaces:

- [`recipe-v1.schema.json`](../../src/parison/schemas/recipe-v1.schema.json) describes recipe version 1, including mappings and normalization.
- [`result-v1.schema.json`](../../src/parison/schemas/result-v1.schema.json) describes result schema version 1 for completed and terminal outcomes.
- [`manifest-v1.schema.json`](../../src/parison/schemas/manifest-v1.schema.json) describes integrity metadata and covered bundle files.
- [`preflight-v1.schema.json`](../../src/parison/schemas/preflight-v1.schema.json) describes structured input-schema diagnostics.

Installed distributions expose the same artifacts without requiring repository access:

```sh
parison schema recipe
parison schema result
parison schema manifest
parison schema preflight
```

The runtime loader remains authoritative for semantic relationships JSON Schema cannot express concisely, including key names existing in `columns`, mapping uniqueness, finite non-negative numeric tolerance text, and columns not overlapping exclusions.

The schemas are tested for validity and applied to committed recipes, the checked-in result and manifest, a fresh preflight result, a fresh 0.3 comparison result and a terminal error result. CI also reads them from the built wheel. The validator is a test-only dependency; Parison's runtime remains dependency-free unless Parquet support is installed.
