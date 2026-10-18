# Parison 1.7 roadmap

Status: **candidate qualified**

Theme: bounded SQLite-backed aggregate conservation

## Scope

1. Freeze the operational boundary and cross-engine equivalence oracle.
   **Complete.**
2. Stream aggregate group state through a private SQLite database under an
   explicit hard storage ceiling. **Complete.**
3. Preserve released aggregate-v1 evidence and raw ordering across memory and
   SQLite execution. **Complete.**
4. Support suite-v2 execution, cleanup, controlled failures and interruption,
   including attributable verifiable error bundles. **Complete.**
5. Add deterministic accuracy benchmarks and qualify installed wheels across
   the supported Python and operating-system matrix. **Complete.**

## Compatibility

The engine is explicit operational policy. Recipe-v2, aggregate-v1, result-v2,
policy fingerprints, canonical aggregate values, outcome reduction, CLI JSON
and bundle verification remain unchanged. Memory execution remains the
default and retains its released runtime shape.
