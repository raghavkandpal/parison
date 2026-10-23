# Parison 2.1.0 release checklist

Date: 23 October 2026
Status: three substantial capabilities integrated; 2.1.0 candidate in qualification

## Completed suite workflow

- [x] Workbench validates and displays explicit local suite plans and member
  bindings through the released suite loader. Contract: [suite plan review](221-workbench-suite-plan-contract.md).
- [x] Workbench rehearses one selected suite locally with bounded progress,
  cancellation, verified publication and History registration. Contract:
  [bounded rehearsal](222-workbench-suite-rehearsal-contract.md).
- [x] Workbench verifies a suite before previewing and exporting the existing
  unsigned Statement and cutover report. Contract: [verified handoff](223-workbench-handoff-contract.md).
- [x] Independent Standards and Spec reviews found one released-format gap:
  partitioned input directories. [PR #69](https://github.com/raghavkandpal/parison/pull/69)
  corrected it with a mutation regression test.
- [x] The Handoff view was rendered and inspected in the local Workbench at a
  narrow browser viewport. Its verification, export and non-authorization
  labels remained visible and legible.
- [x] Feature [PR #68](https://github.com/raghavkandpal/parison/pull/68)
  merged to `develop` at `40288e4`; that merge passed
  [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39737204435)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39737204420)
  on Python 3.11–3.14 across Linux, macOS and Windows.
- [x] Fix PR #69 merged to `develop` at `b3c5c69`. Its exact head `52e6744`
  passed the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39780279353).

## Train scope gate

- [x] Complete at least two more substantial, separately reviewable
  capabilities. The three Workbench suite slices above form one integrated
  workflow for this gate; defects, UI polish and release records do not count.
- [x] Qualify [repeated suite comparison](227-suite-comparison-contract.md)
  on a green pushed checkpoint after independent review. PR #72 merged to
  `develop` at `074c512`; exact head `2cc485a` passed the
  [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39783092724).
- [x] Qualify [failed-member investigation](228-suite-investigation-contract.md)
  on a green pushed checkpoint after independent review. PR #73 merged to
  `develop` at `a9e387b`; exact head `c7c13dd` passed the
  [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39914308237)
  and independent Standards and Spec review.
- [x] Update the train research, contracts, changelog and guide for the full
  set of capabilities before restoring 2.1.0 candidate status.

## Candidate qualification

The earlier `1bdef8b` checkpoint passed clean-archive wheel smoke and full CI.
It is engineering evidence for the suite workflow, not the final 2.1 release
candidate. Repeat candidate gates on the complete train.

- [x] Local `make check` on the integrated source passed 430 tests, with 11
  optional skips, plus Ruff, generated documentation and diff checks on
  Python 3.12.
- [ ] Review `origin/main...develop` against the 2.1 contracts and repository
  invariants after the candidate documentation and version are integrated.
- [ ] Record exact candidate commit and successful quality and full built-wheel
  CI on Python 3.11–3.14 across Linux, macOS and Windows.
- [x] A clean `git archive` of integrated candidate `fe9be1d` built and
  inspected `parison-2.1.0-py3-none-any.whl` (SHA-256
  `50c43c7ed7dd17372942698cad04705cf8519660327938a935a3d134a0ef5f81`)
  and `parison-2.1.0.tar.gz` (SHA-256
  `bb41ded1ab8502bf6db2dee6fbc7552181550dc1b3ad87a7ab30771943216013`).
  Wheel metadata reports 2.1.0 and Python >=3.11; its five relevant runtime
  modules and the source archive's tests were present.
- [x] A fresh Python 3.14 environment installed that exact wheel and passed
  synthetic Workbench plan/run, recursive suite verification, History,
  PASS-to-FAIL suite comparison, failed-member investigation, bounded raw
  export, Statement byte parity with CLI and report export. No source checkout
  was used by the smoke environment.

## Publication

- [ ] Open the release PR from `develop` to `main`; review, merge and require
  quality and full built-wheel CI on the exact merge commit.
- [ ] Rebuild wheel and source archive from the exact merge's clean archive,
  inspect metadata and hashes, and complete any release-specific external gate.
- [ ] Tag that tested merge with annotated `2.1.0` and publish the wheel,
  source archive and `SHA256SUMS` in a GitHub release. PyPI is opt-in.
- [ ] Re-download public assets, verify checksums, install the public wheel
  fresh and repeat the primary Workbench suite-to-handoff smoke.
- [ ] Reconcile this checklist, changelog, documentation index and current
  state against the exact tested release commit.

Internal qualification does not establish extraction truth, policy approval,
signer identity, migration approval or cutover authorization.
