# Combined Workbench review and usability qualification

Date: 21 October 2026

Status: **implementation and review gates complete; candidate-head qualification remains**

The integrated 2.0 Workbench has verified Results and Investigate, schema-driven
Plans, and bounded Run with History and exact-policy Compare. The
[integration checkpoint](215-workbench-integration-checkpoint.md) records the
combined implementation and local checks.

The [synthetic Plans usability trial](../../studies/workbench-plans-01/human-trial-01-report.md)
was completed by an informed participant. They reported no confusing or
misleading steps, gave a go verdict and confirmed the unapproved-policy and
non-executing input-handoff boundaries. This is self-reported usability evidence,
not a claim that every task action was independently observed.

Two independent reviewers assessed the combined code against repository
Standards and the Workbench Spec. The Spec reviewer found that Compare could
show a stored catalog diff after either bundle was modified or missing. PR #61
made Compare require two current verified bundles and added regressions; the
reviewer cleared the fix on re-review. The Standards reviewer found that eight
stalled clients could occupy all request handlers and block the host accept
loop. PR #62 added nonblocking admission, bounded reads and regression tests;
the reviewer cleared the fix on re-review.

The Compare fix merged at `caf1e6d` and passed its exact-merge
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39610651284)
and [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39610651251).
The stalled-client fix merged at `5bcedf7` after exact PR head `2d4b788`
passed the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39611398493)
on Linux Python 3.11--3.14 and macOS/Windows Python 3.11--3.14. Local
`make check` passed 424 tests on the corrected code. The exact `5bcedf7`
merge-head CI is recorded in [CURRENT.md](../CURRENT.md) when complete.

Before treating 2.0 as a candidate, qualify the exact candidate head and
follow the active release checklist. None of these reviews approves a policy,
an extraction, a migration or a cutover.
