# Feature 2 integration and next contract gate

Date: 31 October 2026
Status: feature 2 integrated; two of ten 2.4 features qualified

Feature 2, explicit database representation and schema assessment, integrated
through PR [#127](https://github.com/raghavkandpal/parison/pull/127) at
`7c18ee5f65a0e7a1b76b797fff8d9759580489ee`. The exact reviewed final source head
`4bdfe023d09e6d8e2451daa6d78ed2a16e6455f8` passed:

- `make check`:640 tests on Python3.14.7.
- All19 focused assessment tests on Python3.11.18,3.12.5,3.13.18 and3.14.7,
  including all four versions from a clean Git archive.
- Independent Standards and Spec review of the implementation and correction.
- Exact-head [quality CI](https://github.com/raghavkandpal/parison/actions/runs/41192428350).
- Manually dispatched exact-head [built-wheel Python3.11–3.14 Linux/macOS/Windows CI](https://github.com/raghavkandpal/parison/actions/runs/41192426180).

The prior head's Python3.11/3.12 help failure is resolved by explicit usage text;
the frozen help/error bytes remain unchanged. No parser abstraction, dependency
or installed project script was added. Commit subjects retain the established
`feat:`, `fix:` and `docs:` format.

## Combined feature evidence

Feature 1 remains integrated through PR #121. Feature 2's staged gates are:

| Gate | Integration | Qualified evidence |
| --- | --- | --- |
| Representation schemas and wire fixtures | PR #124, `6d051bb` | 605 tests, independent review, full matrix |
| Offline collection-v2 verifier | PR #125, `9b71e64` | 615 tests, independent review, full matrix |
| Same-snapshot collection-v2 capture | PR #126, `2c6652e` | 621 tests, 40/42/43 live gates on16.15/17.11/18.6, repeated100k/250k measurements, review/full matrix |
| Explicit proposals, assessment and replay | PR #127, `7c18ee5` | 640 tests, both migration pairs, review/full matrix |

The capture source and machine-specific measurement evidence remain in
[287](287-representation-capture-checkpoint.md). Assessment computation source
`04a2ded` passed18 live gates and10 cases across16→18 and17→18, with every source
cluster stopped before derived operations; [288](288-representation-assessment-runtime.md)
and its raw report retain that qualification. The later CLI usage correction
changes no native rules, publication, canonical artifact, summary or exit code.

ACCEPT is compatibility under the explicit native representation scope, not row
parity, extraction truth, approval or cutover authorization. Proposals stay
unapproved; old inventories stay unavailable; unknown facts cannot satisfy a
non-null guarantee. Source-v2 ONLY scope, released2.3 aliases/canonical bytes and
local-first boundaries remain. No future PostgreSQL version is admitted by
inheritance from another profile. No release or2.4 candidate is proposed: all ten
features must integrate and qualify first.

## Next step: feature 3 contract

Start with `make context`, read AGENTS.md, ignored AGENTS.local.md, docs/CURRENT.md
and [roadmap275](275-ten-feature-research-and-roadmap.md). From current clean
develop, research and freeze exact discovery for composite/text keys before
implementation. Deepen existing partition discovery and released canonical
scalar/key semantics. Hashes may route normalized tuples only; exact comparison
remains authoritative and released range-v1 remains readable and unchanged.

The bounded contract and adversarial gate must cover injected hash collisions,
Unicode normalization, null/empty distinctions, delimiter ambiguity, composite
tuples, duplicate normalized keys and skew. Require exact outcomes/counts to
match the released full engine for every bucket plan. Do not infer keys,
normalization, exclusions or scope approval. Record primary sources, design
consequences, bounds and non-goals before implementation, then follow scoped
review and exact-head qualification. Do not begin feature3 as part of this
integration handoff.
