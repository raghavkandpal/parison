# Feature 2 offline assessment and replay gate

Date: 31 October 2026
Status: PR #127 unmerged; built-wheel CI found cross-Python help wrapping differences; stopped at usage limit

Capture [287](287-representation-capture-checkpoint.md) merged through PR #126
at `2c6652ef4838e9cd2ef960b6f41f6a9d086a9588`. Its final head
`122035782eab5a555f4aa082937f51e9e17018b2` passed independent reviews,
[quality](https://github.com/raghavkandpal/parison/actions/runs/41174087640),
[full built-wheel CI](https://github.com/raghavkandpal/parison/actions/runs/41174085509)
and 41 clean-archive tests; source `0edccd2` passed 621 full local tests and
40/42/43 live capture gates. Feature 2 still lacks derived runtime operations.

Implement the remaining offline scope of [contract 284](284-representation-assessment-contract.md)
through `parison representation propose|assess|verify`, with no new project
script. The four help fixtures and `cli-errors.json` are frozen in
`tests/fixtures/postgres_representation/` before writing this runtime. Unknown or
missing actions use the parent fixed error prefix; known actions use their exact
contract prefix. No source paths or parser echo appear in errors. Interrupts
return130; assess/verify map ACCEPT/DENY/INCONCLUSIVE to0/1/3, invalid input to2.
Proposal succeeds only with two fully verified collection-v2 parents and remains
unapproved, without keys or executable rules.

Deepen the collection verifier to return private verified facts and the parent
manifest digest from the same pinned handles; retain its released public safe
summary interface. Reopening source metadata paths after verification is not an
authorized evidence boundary. Derive exact artifact bytes from these observations
and the explicit bounded plan. Verification must replay against both bound local
parents, not merely accept internally consistent output digests.

The gate requires exact frozen proposal and ACCEPT assessment bytes, runtime
rejection of the semantic-negative corpus, actual evaluator coverage of all rule
and precedence cases, full-inventory lineage/key and unknown-state checks,
legacy-parent fallback, 32-entry disjoint union handling, bounded publication,
symlink/mutation/interrupt/no-overwrite defenses and compact safe CLI output.
Known DENY outranks unknown facts. Allowed widening still emits findings. A
selection membership change has no implicit exclusion permission; it is a known
field membership change. Column selection order alone does not change logical
identity; ordered primary-key roles remain exact.

Live 16→18 and 17→18 pairs must qualify explicit equality/widening/denial,
unknown PG18 guarantees, provider drift and offline replay after shutdown.
Equal metadata with different rows can establish only representation compatibility,
never parity PASS. All features remain subject to the fixed not_assessed scope.
Independent Standards and Spec review, full local checks and exact-head quality/
full built-wheel CI are required before feature 2 is declared integrated. All ten
features must qualify before a 2.4 candidate.

## Implementation checkpoint

The frozen proposal/ACCEPT artifact bytes match actual generated output. All31
rule cases run through the real comparator/evaluator. The runtime rejects the
schema-valid negative obligations, checks full lineage and unknown semantics,
keeps legacy inventories unavailable, and replays every expected member byte
against both verified parents. Proposal numbering is generated deterministically;
proposals are never accepted as assessment plans. Safe unresolved-field counts
sum the explicit unmatched column lists under suggested table pairs; unmatched
table IDs are counted separately.

Publication uses private staging, exclusive file creation and atomic no-overwrite
rename; assessment staging is replay-verified before publication. The verifier
returns source facts from its pinned handles rather than re-reading paths. Safe
CLI tests cover0/1/2/3/130, frozen help/errors and summary-only stdout.

Initial `make check` passed635 tests. The disposable live pair script passed18
gates with10 cases across16→18 and17→18; final frozen-source rerun and independent
reviews remain before qualification. The helper starts only fresh clusters and
stops all of them before deriving or replaying any evidence. Its source records
are synthetic; no confidential values or user credentials are published.

Review corrections preserve unknown nullability/collation for optional added or
removed fields; their allowed membership does not resolve native uncertainty.
Fully known provider drift emits its DENY reasons without an unknown label.
Recorded and actual observations retain their distinct meanings: corresponding
cross-parent changes differ from an identical intrinsic mismatch in both inputs.
The contract clarifies that distinction, with reason-specific regressions. Returned
not_assessed lists are independent copies, preserving deterministic later runs.

## Qualified source evidence

Corrected source `04a2ded3eb822f5ac191797c5d5847b2a70788be` passed639 local
tests, independent Standards and Spec review, and the exact-source disposable
pair rerun. The [raw pair report](../../benchmarks/results-2026-10-31-representation-assessment-pairs.json)
records PostgreSQL16.15/17.11/18.6, Python/driver/platform,18 gates and10 pair cases.
Every server stopped before assessment, proposal creation or replay.

| Scenario for both16→18 and17→18 | Expected compatibility |
| --- | --- |
| Equal native metadata, deliberately different CSV rows | ACCEPT, no row parity claim |
| Widened native bounds under exact rules | DENY |
| Same changes under explicit widen rules | ACCEPT with all change findings |
| PG18 unvalidated native guarantee | INCONCLUSIVE |
| Observed provider drift plus unknown native guarantee | DENY |

Both pairs also produce visibly unapproved proposals that cannot execute as
plans. All prior capture gates and source profiles remain qualified separately;
this pair gate adds no future PostgreSQL version to either live allowlist.
Final PR-head built-wheel/quality CI is still required before integration and
before recording feature2 as the second of ten integrated features.

## Graceful handoff at 95% usage

PR [#127](https://github.com/raghavkandpal/parison/pull/127) remains unmerged.
Head `a55d99090a4fecf813364a2fd307d21f89605e8c` passed independent final-head
reviews and [quality CI](https://github.com/raghavkandpal/parison/actions/runs/41176713818).
The manually dispatched [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/41176711494)
failed `test_cli_help_errors_and_safe_stdout` on Python3.11 and3.12. The confirmed
difference is argparse usage line wrapping for `representation propose`:
older Python places `--candidate` at the end of the first usage line, while the
frozen Python3.14 fixture puts that complete option on the next line. No merge
is authorized by these failed results. The existing source-head qualification
and44 clean-archive tests remain evidence, not an overall cross-version pass.

Next make usage formatting deterministic across supported Python versions,
preferably explicit stable usage text rather than weakening the byte fixture.
Run the focused help/error tests on3.11–3.14, `make check`, independent review of
the correction and fresh quality/full built-wheel CI on the exact updated head.
Merge only when qualified. Then update the changing handoff on a scoped docs
branch from current develop and record feature2 as2/10. Feature3 is exact
discovery for composite/text keys; research/freeze its bounded hash-routing
contract and collision/adversarial gate before implementation. No2.4 candidate
until all ten features integrate and qualify.

Useful local environment: `/private/tmp/parison24-feature2-venv/bin/python`
(Python3.14 with test/dev/parquet/postgres extras). The older
`/private/tmp/parison-goal-venv` lacks venv metadata and must not be used to install
packages into system Python. Local CI failure output is
`/private/tmp/parison24-assessment-ci-failed.log`; all public qualification evidence
is committed in this version folder and benchmarks. No reset was consumed.
