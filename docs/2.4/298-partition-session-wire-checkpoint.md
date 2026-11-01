# Partition session structures and reference corpus

Date: 1 November 2026
Status: structural implementation; review and exact-head qualification pending

This is feature4's first gate under frozen [contract296](296-partition-recovery-contract.md)
and [continuation297](297-partition-recovery-continuation.md). Expose standalone
`partition-session-v1`, `partition-checkpoint-v1` and
`partition-session-result-v1` through existing `parison schema`. There is no
new project script, dependency, retained-session command or execution flag.
Ordinary range-v1/hash-v2 discovery, evidence bytes and aliases remain unchanged.

Schemas close journal, identity, routing, checkpoint and invocation shapes,
constrain state-dependent fields and distinguish query/abandon responses from
fresh/reused publication. References are local definitions, so schema validation
requires no resolver network access. Physical-file caps, exact JSON tokens,
canonical bytes, source/plan/layout/engine/runtime bindings, arithmetic and
ownership remain semantic reader obligations. Structural validity never grants
reuse permission, authenticates a cache or establishes source-backed replay.

The synthetic corpus in tests/fixtures/partition_session contains both range-v1
column orders and hash-v2 PASS/FAIL/INCONCLUSIVE examples. Each profile includes
all six persisted states, bound routed files/children, safe invocation responses
and ordinary final four-file references. Derived recipe bytes deliberately have
no LF, as the existing comparator requires; other canonical JSON has one LF.
Fixture profile directories are example collections, not directly executable
session roots; the future reader must materialize only the contract's fixed root
members and chosen journal, including its one-byte lock.

Tests bind every descriptor to exact bytes, check child results against the
unchanged exact engine, and reproduce ordinary discovery's final files, including
both legacy physical column orders. Schema-negative vectors reject closed-shape,
state, token-type and unsafe-filename violations. Structurally valid semantic
counterexamples cover mismatched bindings, routing profile/row counts, slots and
mathematically integral float tokens. Explicit recovery vectors freeze committed
primary authority over truncated/apparently later next files and known-slot
uncommitted-child handling. Those decisions are future reader tests, not a
recovery implementation claimed by this gate.

A coherently rehashed child classification forgery satisfies structure and count
arithmetic but differs from a fresh exact comparison. Its assurance remains
reused-integrity-checked, never exact-source-backed. Incomplete children are
structurally representable but ineligible for reuse. Package fingerprints and
runtime descriptors in this corpus are synthetic claims, not execution
attestation. Native ownership, locks, retention/budgets and interrupted cleanup
remain separate implementation/qualification gates.

Narrow check: `make test TEST=tests.test_partition_session_wire`. Run it on all
four Python minors and in the manual built-wheel macOS/Windows matrix, alongside
Linux tests, before integration. Independent Standards/Spec review, full local
checks and exact-head quality/full matrix must pass. Feature4 stays incomplete;
features1–3 are integrated (3/10). All ten precede any2.4 candidate.

Local gate:692 repository tests pass under `make check`; all nine session-wire
tests pass on CPython3.11.18,3.12.5,3.13.18 and3.14.7. Independent review and
exact-head quality/manual full matrix remain required before integration.

Independent Spec review corrected a fixture-binding defect: checkpoint
policy_sha256 is the effective mechanically derived comparison-policy fingerprint,
not the derived-recipe file digest. The latter stays in identity.derived_recipe_sha256.
Child descriptors, journals, negatives and the coherent-forgery record were
refreshed; direct exact-engine policy assertions lock this distinction.
Corrected-head review and CI are required; earlier head11efc00 cannot qualify it.
