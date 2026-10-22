# Parison 2.1.0 release checklist

Date: 22 October 2026  
Status: candidate deferred; the suite workflow is one integrated capability
and the train needs further substantial features before publication

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

- [ ] Complete at least two more substantial, separately reviewable
  capabilities. The three Workbench suite slices above form one integrated
  workflow for this gate; defects, UI polish and release records do not count.
- [ ] Qualify [repeated suite comparison](227-suite-comparison-contract.md)
  on a green pushed checkpoint after independent review.
- [ ] Qualify [failed-member investigation](228-suite-investigation-contract.md)
  on a green pushed checkpoint after independent review.
- [ ] Update the train research, contracts, changelog and guide for the full
  set of capabilities before restoring 2.1.0 candidate status.

## Candidate qualification

The earlier `1bdef8b` checkpoint passed clean-archive wheel smoke and full CI.
It is engineering evidence for the suite workflow, not the final 2.1 release
candidate. Repeat candidate gates on the complete train.

- [x] Local `make check` on the corrected source passed 427 tests, with 11
  optional skips, plus Ruff, generated documentation and diff checks on
  Python 3.12.
- [ ] Review `origin/main...develop` against the 2.1 contracts and repository
  invariants after the candidate documentation and version are integrated.
- [ ] Record exact candidate commit and successful quality and full built-wheel
  CI on Python 3.11–3.14 across Linux, macOS and Windows.
- [ ] Build wheel and source archive from a clean `git archive` of that exact
  candidate. Inspect contents, metadata and SHA-256 hashes.
- [ ] Install the candidate wheel in a fresh supported-Python environment and
  smoke-test suite plan review, run, recursive verification, History, Statement
  export and report export against synthetic local inputs.

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
