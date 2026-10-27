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
- [ ] Exact candidate commit passes quality CI and the full built-wheel matrix
  on Python 3.11–3.14 across Linux, macOS and Windows.
- [ ] Clean `git archive` of that exact candidate builds wheel and source
  archive. Inspect contents, version metadata and SHA-256 hashes.
- [ ] Fresh supported-Python install of the built wheel passes a synthetic
  primary workflow covering the six 2.2 capabilities and verification-first
  evidence handling.
- [ ] Reconcile candidate commit, CI run, artifact hashes and smoke result here.

A clean archive of candidate-preparation commit `1ad33c7` built a 2.2.0 wheel
and source archive. Final candidate artifact qualification remains pending
exact-head CI and a fresh wheel smoke.

## Publication boundary

The [accepted 2.2 contract](233-contracts-and-acceptance.md) does not authorize
a release merge, tag or publication. Candidate evidence does not approve a
user's policy, extraction, migration or cutover. Follow [RELEASING.md](../../RELEASING.md)
if release publication is later authorized.
