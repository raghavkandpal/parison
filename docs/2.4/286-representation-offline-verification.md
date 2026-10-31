# Feature 2 offline collection-v2 verification

Date: 31 October 2026
Status: implemented; independent review and exact-head CI pending

The structural gate [285](285-representation-wire-checkpoint.md) merged through
PR #124 at `6d051bb198e33cd838ec6b1540dc071197c78cf0`. Exact source head
`274a1e3d10bb511f250b5f4f6c1c24dd795c1524` passed 605 local tests,
independent Standards and Spec review, [quality CI](https://github.com/raghavkandpal/parison/actions/runs/41172435668)
and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/41172433513).
That integration qualifies structures, not feature 2 runtime or live support.

This slice extends the existing `parison verify-postgres-collection DIRECTORY`
reader to collection-v2 under [contract 284](284-representation-assessment-contract.md).
Its output is the frozen compact collection-summary-v2: receipt identity, counts,
byte totals and completeness, with no private metadata projection. Collection-v1
still uses its released four-member envelope, limits, profiles and summary bytes.
No driver or server is imported by the verifier. No new CLI or project script.

Verification pins representation.json alongside every existing root/child file,
bounds it by both the 16 MiB hard ceiling and the caller's recorded limit before
reading children, and includes it in staged-content, digest and mutation checks.
The version controls exact file membership, receipt/summary/manifest fields and
capability profile. Children remain verified source-v2 ONLY bundles with only
the four source limits, while the reconstructed parent plan retains all five.

Native-fact replay rejects impossible normalization, exact-token substitutions,
invalid version-specific constraints/generated flags, unsupported selected types,
missing selected fields, duplicate names/ordinals and child type disagreement.
Numeric signed scale is decoded from qualified typmod, including raw scale 2045
versus semantic -3; varchar length and timestamp precision are reconstructed.
PG18 non-key unvalidated not-null remains unknown, and unsupported unselected
native types retain unknown guarantees. Collation states, resolved/version shapes
and legitimately non-versioned libc C/POSIX observations remain typed.
Builtin is admitted only under PG17/18 profiles. Primary-source recheck on
31 October found their supported builtin locales report version "1" in
[PG17](https://github.com/postgres/postgres/blob/REL_17_STABLE/src/backend/utils/adt/pg_locale.c)
and [PG18](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/utils/adt/pg_locale_builtin.c).
No unversioned builtin locale is qualified here; the contract's conditional
allowance does not invent one. Absent builtin observations remain unknown,
never a compatibility wildcard. Review added a PG16 provider rejection and
regressions for known, unknown and falsely unversioned PG18 builtin facts.

The reader does not establish extraction truth or invent missing inventories.
It verifies the declared record and its internal bindings. Capture still requires
same-snapshot catalog/information-schema agreement and live qualification.
Collection-plan-v2 validation exists for replay, but the live writer explicitly
rejects it until capture is implemented and qualified. Proposals and assessments
remain pending. Feature 2 is incomplete; only feature 1 of ten is integrated.

Narrow validation: `make test TEST='tests.test_representation tests.test_representation_wire tests.test_postgres_collection tests.test_postgres_collection_acquisition'`.
Full `make check`, independent reviews and exact-head built-wheel CI are required
before integrating this reader extension. Next implement bounded catalog capture
on the existing acquisition transaction, then proposal/assessment/replay, CLI
execution fixtures and all contract-284 live/adversarial gates before feature 2
completion. All ten features must qualify before a 2.4 candidate.
