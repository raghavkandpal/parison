# Parison 2.2.0 release candidate checklist

Date: 27 October 2026  
Status: candidate qualification in progress; 2.1.0 remains the published release

## Completed train

Six substantial capabilities from the [accepted roadmap](232-accepted-roadmap.md)
are integrated on `develop`:

1. Dataset evidence v2: [PR #81](https://github.com/raghavkandpal/parison/pull/81).
2. Workbench suite-v2 authoring: [PR #82](https://github.com/raghavkandpal/parison/pull/82).
3. Recoverable suites: [PR #83](https://github.com/raghavkandpal/parison/pull/83).
4. Workbench policy-change review: [PR #84](https://github.com/raghavkandpal/parison/pull/84).
5. Verified suite rehearsal series: [PR #85](https://github.com/raghavkandpal/parison/pull/85).
6. Complete reconciliation workflow and typed handoff:
   [PR #86](https://github.com/raghavkandpal/parison/pull/86), merged at
   `71b075f60d27f7a6253a987088cba9724c1b18a0`. Its exact feature head
   `06d1346f7b0e869bd9b7e223cb22c10abce9196e` passed
   [the full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/40521983174)
   on Python 3.11–3.14 across Linux, macOS and Windows. Independent Standards
   and Spec reviews cleared the corrected staging cancellation boundary.

## Candidate qualification

- [x] `make check` on the integrated candidate preparation branch passed 503
  tests, Ruff, generated documentation and diff checks with Python 3.14.
- [x] Independent Standards and Spec review of `origin/main...develop` at
  `71b075f` found no actionable release blocker. A proposed suite-series
  `INCONCLUSIVE` gap was disproved by a focused regression attempt: all three
  ordinary comparison modes set `complete: false` when the outcome is
  `INCONCLUSIVE`, so no such parent meets the series contract's complete gate.
- [x] Candidate source commit `5ecff944b479628b284cb7a932bdc13cfccc3847`
  passed [the full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/40641209814)
  on Python 3.11–3.14 across Linux, macOS and Windows, plus PR quality CI.
- [x] A clean `git archive` of that commit built and inspected
  `parison-2.2.0-py3-none-any.whl` (SHA-256
  `440f90def82b14c6f7ce7330c0e2aaab0ad15bbe8bb7f6356f4bea44d21fe071`)
  and `parison-2.2.0.tar.gz` (SHA-256
  `d5928fd6b8bbfcae55e09622a44c998769cd44a1591fa1fe38789ff8b7132d05`).
  Wheel metadata reports version 2.2.0 and Python >=3.11; it contains 23
  Python modules and 64 schemas. The source archive contains 49 test files.
- [x] A fresh Python 3.14 environment installed that wheel, imported Parison
  from site-packages, passed an example comparison and bundle verification,
  and ran 88 focused synthetic tests from the clean archive across all six 2.2
  capabilities, including Workbench reconciliation and typed handoff.
- [ ] Require exact-head CI on the qualification-record commit before merging
  candidate preparation to `develop`.

The first manual matrix attempt at this candidate head ended with a cancelled
queued macOS 3.12 job; the successful rerun above completed every required
lane. The smoke used the installed wheel, not the source checkout.

## Publication boundary

The [accepted 2.2 contract](233-contracts-and-acceptance.md) does not authorize
a release merge, tag or publication. Candidate evidence does not approve a
user's policy, extraction, migration or cutover. Follow [RELEASING.md](../../RELEASING.md)
if release publication is later authorized.
