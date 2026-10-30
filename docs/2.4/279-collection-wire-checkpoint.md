# Collection wire-format checkpoint

Date: 30 October 2026
Status: wire gate integrated through PR #117; no collection runtime or live qualification

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

Exact head `a61b686da20c9b996f455baf3d87c3d20ddcf713` passed 579 local tests,
independent Standards/Spec review after preserving committed CRLF child bytes,
quality CI and the [full built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix](https://github.com/raghavkandpal/parison/actions/runs/41045356038).
[PR #117](https://github.com/raghavkandpal/parison/pull/117) merged at
`9e0e1a6a7a20889bc3dab2bfb820967712cfdaff`. A clean archive independently
passed the four focused wire tests.

Next: implement validation, offline verification and
acquisition through existing seams. Materialize command-help/error fixtures with
the real commands and run semantic/adversarial tests plus all pending live rows
in [matrix 278](278-postgresql-capability-matrix.md). No feature credit or live
support follows from schemas. All ten features remain required before a 2.4
candidate; released 2.3 readers and commands stay compatible.

## Continuation

Start with `make context`, AGENTS.md, ignored AGENTS.local.md and docs/CURRENT.md.
Read contracts 277/278 and this checkpoint. Implement collection plan validation
and offline verification first, enforcing every semantic-negative fixture and
pinned-read safety; then deepen acquisition and add command help/error fixtures.
Run live PostgreSQL 16.15/17.11/18.6 gates before advertising collection support.
Keep all ten 2.4 features together before a candidate. Check both usage windows;
this session stopped after reaching 95% weekly usage with the wire gate complete.
