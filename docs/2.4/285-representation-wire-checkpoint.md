# Feature 2 representation wire checkpoint

Date: 31 October 2026
Status: structural gate implemented; independent review and exact-head CI pending

This slice materializes [contract 284](284-representation-assessment-contract.md)
without introducing capture or assessment execution. Feature 2 is not integrated
or qualified by this checkpoint. The all-ten 2.4 release boundary remains.

Eleven closed, standalone Draft 2020-12 schemas cover collection plan/receipt/
summary/manifest v2, representation metadata v1, assessment plan/result/summary/
manifest v1 and private proposal/safe proposal summary v1. Existing schema names
keep their released definitions; the new names are available through the existing
`parison schema` command. No new project script or execution command is added.

The synthetic fixture tree `tests/fixtures/postgres_representation/` pins a
PostgreSQL 16.15 baseline and 18.6 candidate with two selected tables, canonical
source-v2 ONLY children, complete metadata inventories and exact digest bindings.
The collection plan hashes omit LF; published members include LF; copied CSV
members retain their released CRLF bytes through explicit Git attributes. The
ACCEPT assessment and unapproved proposal are expected future outputs, not
runtime-generated evidence or live PostgreSQL qualification.

Structural negative cases reject unknown members, boolean versions, incompatible
version-specific shapes, invalid rules and unsafe proposal states. Separate
schema-valid negative cases make future runtime obligations explicit: wrong plan
or snapshot bindings, unsupported selected types, duplicate ordinals, a false
PostgreSQL 18 non-key not-null guarantee, child type disagreement, incomplete
lineage, proposal numbering and JSON number-token identity. Passing a JSON schema
never claims verification. Runtime must reproduce all derived facts and outcomes.

Rule cases pin directional integer/numeric widening, signed negative numeric
scale, unknown nullability, cross-parent collation provider versions and missing
old inventory. Precedence cases pin DENY above INCONCLUSIVE above ACCEPT. These
are evaluator acceptance inputs; the structural test does not pretend to execute
the future assessment rules. The 32-entry disjoint table-union boundary is tested.

The narrow gate is `make test TEST=tests.test_representation_wire`; the branch
also requires `make check`, independent Standards and Spec review, and the full
built-wheel Python 3.11–3.14 Linux/macOS/Windows matrix on the exact PR head
because schemas and schema CLI choices changed. Live PostgreSQL qualification is
pending runtime, including both 16→18 and 17→18 assessment pairs and the complete
adversarial inventory in contract 284. The capture/assess/propose/verify CLI help
and error fixtures must be frozen with the execution interface before runtime
integration; no current command advertises those operations.

Next implement collection-plan-v2 capture using the existing locked one-snapshot
acquisition path, bounded native catalogs and source-v2 ONLY children. Add strict
offline collection-v2 verification before deriving proposals or assessments.
Preserve all old collection-v1 readers and bytes. Then replay the schema-valid
negative corpus through runtime rejection and exercise rule fixtures through the
real evaluator. No data parity, approval or cutover authority follows from ACCEPT.
