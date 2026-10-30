# Parison 2.2.0 release checklist

Date: 27 October 2026  
Status: **released** at exact tested merge `bfb17a6baf26cde2930f12f4dfe4ff5f8c8c93c4`

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
- [x] Qualification-record head `e0b8e083e03966dabb51267ac6887f2b46336371`
  passed [the full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/40641683700)
  and PR quality CI before [PR #87](https://github.com/raghavkandpal/parison/pull/87)
  merged to `develop` at `f5dc3e4f153522fc525e2a13944a801f91d339af`.

The first manual matrix attempt at this candidate head ended with a cancelled
queued macOS 3.12 job; the successful rerun above completed every required
lane. The smoke used the installed wheel, not the source checkout.

## Publication

- [x] The user approved the release on 28 October 2026, superseding the
  [accepted contract's](233-contracts-and-acceptance.md) earlier publication
  hold without changing product policy or evidence semantics.
- [x] [Release PR #89](https://github.com/raghavkandpal/parison/pull/89)
  merged `develop` to `main` at exact commit
  `bfb17a6baf26cde2930f12f4dfe4ff5f8c8c93c4`. It passed
  [quality CI](https://github.com/raghavkandpal/parison/actions/runs/40643582338)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/40643616772)
  on Python 3.11–3.14 across Linux, macOS and Windows.
- [x] A clean `git archive` of that exact merge built and inspected
  `parison-2.2.0-py3-none-any.whl` (SHA-256
  `672547462348be9faf1c52b00f353ace8f725ce935ea47040e72da5aa9087dc9`)
  and `parison-2.2.0.tar.gz` (SHA-256
  `85a23fb2ef75a2a2b085d63f29662c8fe7884b589d40d41001a9382dec413f50`).
  Wheel metadata reports 2.2.0 and Python >=3.11; it contains 23 Python
  modules and 64 schemas. The source archive contains 49 test files. A fresh
  Python 3.14 wheel install passed 88 focused synthetic tests across all six
  capabilities. No release-specific external gate was required.
- [x] Annotated tag [`2.2.0`](https://github.com/raghavkandpal/parison/releases/tag/2.2.0)
  peels to that tested merge. The public GitHub release contains the wheel,
  source archive and `SHA256SUMS`; PyPI was not requested.
- [x] All three public assets were re-downloaded. Both archives matched the
  published checksum file. A fresh Python 3.14 install of the public wheel
  imported from site-packages and passed the same 88 focused synthetic tests.
- [x] Reconcile this checklist, changelog, documentation index, user guide,
  README and current state in a post-release records pull request to `develop`.

Internal qualification and public release do not establish extraction truth,
policy approval, signer identity, migration approval or cutover authorization.
