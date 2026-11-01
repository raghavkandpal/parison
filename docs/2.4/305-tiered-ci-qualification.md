# Tiered CI before continuing 2.4

Date: 1 November 2026
Status: scoped CI change; product features1–3 integrated, feature4 incomplete

The owner requested this maintenance change after qualified preview PR140 and
before further 2.4 implementation. Preserve released product contracts, all ten
features before a candidate, and existing exact-head/native qualification rules.
This changes CI organization and frequency, not comparison or evidence semantics.

## Fixed gates

| Event/profile | Coverage |
| --- | --- |
| Code PR to develop, push to develop, manual preflight | Quality/docs checks, one built wheel, complete Linux3.14 unit suite and installed smoke, tight native3.14 regression/smoke on macOS and Windows. |
| Manual full (default), source push to main | All preflight gates first; then Linux3.11–3.13 complete unit/installed smoke, macOS/Windows3.11–3.14 full native suites, plus historical Linux scenarios and small benchmark checks once on3.14. |
| Docs-only change | Existing quality workflow; runtime workflow keeps its existing documentation path exclusions. |

Linux3.14 is already fully tested in preflight and is not repeated in expansion.
Native3.14 preflight is deliberately small; its full qualification suite runs
later. Expansion depends on successful Linux AND native preflight. Failed
preflight leaves the remaining matrix skipped, never qualified. Full native
coverage spans all12 supported OS/Python pairs, using one shared wheel.

Manual commands on the exact PR head branch:

```sh
gh workflow run test.yml --ref BRANCH                 # full, default
gh workflow run test.yml --ref BRANCH -f profile=preflight
```

Preflight-only success does not satisfy full integration/candidate/release gates.
Packaging, schema, CLI and platform changes still require manual full exact-head
qualification before integration. Candidate and exact release-merge requirements
in RELEASING.md remain. Main source pushes expand fully; develop pushes no longer
repeat every native/version lane after the required pre-integration qualification.
PR synthetic-merge wheels and manual exact-head wheels are intentionally rebuilt
separately: their commit identities can differ. Existing quality check stays.

## Coverage and maintenance

Local preflight remains `make check`; use focused `make test TEST=...` first.
`make test TEST=tests.ci_native_preflight` runs the tight native regressions on
the local host. Actual Windows/macOS runner evidence remains necessary.

The workflow invokes stable unittest suites. Normal unit discovery automatically
finds new feature tests. Full native coverage discovers test_partition_*.py and
includes XLSX plus installed workflows; other platform-sensitive areas belong in
tests/ci_platform.py. Tight early regression selection lives in
ci_native_preflight.py. Defects found late should gain deterministic local
regressions where possible and appropriate early native cases. Feature work adds
coverage in tests, rather than a new YAML command block for each feature.

Installed smoke checks every registered schema and installed console entry point
against pyproject metadata, canonical command help and quickstart. Historical
native CLI scenarios execute in-process through the same CLI functions, with
separate real installed entry-point help checks. This preserves application
paths while reducing repeated interpreter and shell-step startup. The Linux
historical scenarios and1000-row benchmark accuracy checks retain their original
commands/expected exits in tests/ci/linux-smoke.sh, run only in the full3.14 lane.
Outputs use an explicit new private directory, including the existing summary
smoke artifact. No live PostgreSQL, new product script or runtime dependency.

The historical benchmark cases remain machine-specific correctness/budget gates,
not universal capacity claims. Larger benchmarks/stress/live-server gates remain
separate local/manual work. No granular changed-file-only unit selection was
introduced; broad shared-module regressions still get a complete Linux suite.

## Validation and evidence

Completion requires full local checks, installed-wheel smoke/native suites,
independent Standards/Spec review, ordinary PR preflight and manual full matrix
on one final exact head. Confirm all preflight jobs succeed before expansion and
all required lanes complete. Preserve optional/native skip meanings; no failure
is converted to success or rerun away. Record exact head/run evidence in the PR.
The previous baseline in checkpoint303 was one measured run, not a savings
promise. Compare new job/step durations after qualification.

Primary platform reference, accessed1 November2026: GitHub's
[workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
defines choice/default inputs, conditional jobs and needs-dependent skipping.
The workflow uses those built-in mechanisms rather than adding an orchestrator.

After qualification, resume feature4's separate mutating ownership/abandonment
and retained execution gates. All ten 2.4 features must integrate and qualify
before any candidate. No release or usage reset is part of this change.

## Qualified checkpoint

PR143 integrated at `b82f50a4caea5b0c6fb1d36c109edb87651d14b3` from exact
head `19d725b2424719a67a93e487cba22436fd6a8e3d`, independently cleared by
Standards and Spec reviews. Full local checks passed736 tests (five native
Windows skips on macOS); a fresh-wheel full native suite passed138 tests.
All preserved historical scenarios and small benchmark checks passed locally,
then in the actual Linux full-profile job. Review found and corrected a shared
shell errexit leak; its regression failed before the fix and now verifies both
wrong expected exits and unexpected later failures terminate the script.

Exact-head [quality](https://github.com/raghavkandpal/parison/actions/runs/41308725570),
[ordinary PR preflight](https://github.com/raghavkandpal/parison/actions/runs/41308725566)
and [manual full qualification](https://github.com/raghavkandpal/parison/actions/runs/41308724072)
all passed. PR jobs skipped full expansion; manual full completed every required
OS/Python pair and historical scenarios. Job timestamps prove expansion began
only after every early gate completed.

One-run measurements: PR preflight80 wall seconds/117 summed job seconds;
full267 wall seconds/1,240 summed job seconds. The earlier full baseline was
241/1,418. Full wall time increased with the serial preflight gate, while summed
runner time fell and native discovery gained cases. These runs differ in test
counts and runner conditions; this is evidence of observed behavior, not an
isolated benchmark or promised speedup. Routine develop pushes now take the
preflight path instead of repeating full qualification. No native/version
qualification was silently removed.

Next resume feature4's mutating ownership/abandonment gate under contract296,
then retained execution and its full adversarial gate. Features1–3 remain
integrated (3/10); all ten precede a2.4 candidate. The owner's existing doc297
spacing edit remains uncommitted and unchanged. No reset/release/candidate.
