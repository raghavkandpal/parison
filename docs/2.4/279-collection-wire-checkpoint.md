# Collection wire-format checkpoint

Date: 30 October 2026
Status: schemas and fixture candidate; no collection runtime or live qualification

Four standalone Draft 2020-12 schemas materialize [contract 277](277-postgresql-collection-contract.md).
They are installed through the existing registry and `parison schema` using
`postgres-collection-plan`, `postgres-collection-receipt`,
`postgres-collection-summary` and `postgres-collection-manifest`.
Acquisition and collection verification commands remain unimplemented.

`tests/fixtures/postgres_collection/plan.json` and `expected/` pin canonical
parent records and unchanged source-v1 child bytes. These are synthetic released
pair children, not live collection evidence. Tests check child verification,
plan/manifest/receipt digests, totals, elapsed bindings and byte compatibility.

The schema-negative corpus covers counts, IDs, unknown fields, boolean versions
and limits, profiles, digests, partial status and summary leakage. One/sixteen
examples establish structural bounds only. The semantic-negative corpus
intentionally passes schemas: unselected keys, duplicate relations, UTF-8 byte
limits, forged totals, wrong plan/summary and swapped bindings must later fail
runtime verification. Schemas cannot replace strict JSON token parsing,
printable-text checks, canonical bytes, filesystem safety or cross-record checks.

Next: review this wire gate, then implement validation, offline verification and
acquisition through existing seams. Materialize command-help/error fixtures with
the real commands and run semantic/adversarial tests plus all pending live rows
in [matrix 278](278-postgresql-capability-matrix.md). No feature credit or live
support follows from schemas. All ten features remain required before a 2.4
candidate; released 2.3 readers and commands stay compatible.
