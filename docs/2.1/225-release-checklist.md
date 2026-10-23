# Parison 2.1.0 release checklist

Date: 23 October 2026
Status: **released** at exact tested merge `9a6e9e9`

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

The earlier `1bdef8b` checkpoint was engineering evidence for the first suite
workflow only. Complete-train qualification follows.

- [x] Local `make check` on the integrated source passed 430 tests, with 11
  optional skips, plus Ruff, generated documentation and diff checks on
  Python 3.12.
- [x] Independent Standards and Spec reviews of `origin/main...develop` at
  integrated candidate `fe9be1d` found no release blocker against the 2.1
  contracts and repository invariants. The last candidate change after initial
  review corrected only qualification documentation; both axes rechecked it.
- [x] Exact integrated candidate `fe9be1d` passed
  [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39915435312)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39915435281)
  on Python 3.11–3.14 across Linux, macOS and Windows. Qualification-record
  changes after this checkpoint also require exact-head CI before the release PR.
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

- [x] [Release PR #76](https://github.com/raghavkandpal/parison/pull/76)
  merged `develop` to `main` at exact commit
  `9a6e9e93b709331bb6bf1503b78f26d9fd5e6ac5`. It passed
  [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39916541177)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39916541313)
  on Python 3.11–3.14 across Linux, macOS and Windows.
- [x] A clean `git archive` of that exact merge built and inspected
  `parison-2.1.0-py3-none-any.whl` (SHA-256
  `4173b75e605c5c3d7cffe112db72ff229d1b48ab4be7f3d525ccd10aba69ef71`)
  and `parison-2.1.0.tar.gz` (SHA-256
  `d21f31d906209d23459a98175c854dae469990a34699106ad3ad2b433598edad`).
  A fresh Python 3.14 wheel install passed the complete three-capability smoke.
  No release-specific external gate was required.
- [x] Annotated tag [`2.1.0`](https://github.com/raghavkandpal/parison/releases/tag/2.1.0)
  peels to that tested merge. The public GitHub release contains the wheel,
  source archive and `SHA256SUMS`. PyPI was not requested.
- [x] All three public assets were re-downloaded; both archives matched the
  published checksum file. A fresh Python 3.14 install of the public wheel
  passed plan/run, recursive verification, History, repeated suite comparison,
  failed-member investigation, bounded raw export, Statement byte parity with
  CLI and report export.
- [ ] Reconcile this checklist, changelog, documentation index and current
  state against the exact tested release commit.

Internal qualification does not establish extraction truth, policy approval,
signer identity, migration approval or cutover authorization.
