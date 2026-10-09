# Suite-v1 contract

Status: **normative for 0.10 development**

## Plan

A suite plan is a UTF-8 JSON object with `suite_version: 1` and a nonempty ordered `cases` array of at most 100 entries. Unknown fields are errors.

Each case contains exactly:

- `id`: a unique portable identifier matching `[a-z0-9]+(?:-[a-z0-9]+)*`;
- `recipe`, `baseline` and `candidate`: nonempty path strings resolved relative to the plan file;
- optional `expected_policy_sha256`: 64 lowercase hexadecimal characters.

Case order is plan-array order. Plans do not contain globs, inline recipes, semantic overrides, commands or per-case limits. Each referenced recipe remains the sole comparison-policy authority.

`validate-suite` validates the plan and every referenced recipe without scanning input records. Missing or unsafe references fail validation.

## Execution and outcomes

`run-suite --plan PLAN --output DIRECTORY` runs cases sequentially in declared order. The ordinary comparison and publication path produces every child bundle. FAIL, INCONCLUSIVE and ERROR do not stop later cases; user interruption stops execution and records the interrupted case when publication remains possible.

Suite outcome is the highest-precedence case outcome:

```text
INTERRUPTED > ERROR > INCONCLUSIVE > FAIL > PASS
```

PASS means every declared case completed and passed. FAIL means all cases were conclusive and at least one found required differences. The suite records total and completed case counts plus counts by outcome.

## Parent bundle

The suite output contains:

- `suite-result.json`, `effective-suite.json`, `report.html` and `manifest.json`;
- ordinary child bundles under `cases/<id>/`.

The suite result records safe per-case metadata: ID, outcome, completeness, result schema, comparison contract, policy fingerprint, child manifest digest and relative location. It never copies discrepancy samples, source keys, groups, rows or values.

The parent manifest has a distinct suite kind and binds every case ID to its child manifest digest. Verification recursively verifies each child, recomputes its digest and checks parent/result/child metadata agreement. Hashes prove integrity relative to the supplied manifest, not authorship.

The complete suite is staged beside its destination and published atomically. Existing destinations are never overwritten and unfinished staging directories are not valid bundles.

## Inspection and privacy

`verify` and `inspect` dispatch by manifest kind while preserving the 0.9 ordinary-bundle output contract. Suite inspection returns aggregate counts and safe per-case metadata only.

Raw evidence remains inside ordinary raw-sensitivity child bundles. `export-evidence` continues to target one child bundle and cannot target the suite parent.
