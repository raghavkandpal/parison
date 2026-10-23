# Parison 2.0.0 release checklist

Date: 22 October 2026

Status: **released**

## Capability gate

- [x] Verified Results and Investigate present summary-safe evidence only after
  verifying a complete local bundle.
- [x] Plans loads strict recipes, exposes schema-derived controls and effective
  policy, validates edits and downloads explicitly unapproved JSON drafts.
- [x] Bounded Run handles explicit local inputs and output publication; History
  and Compare inspect current verified evidence under exact policy.
- [x] Independent combined Standards and Spec findings were corrected and
  cleared on re-review; an informed participant completed the synthetic Plans
  trial with no reported usability issues. See the [combined review](218-workbench-combined-review.md).
- [x] Released recipes, schemas, canonical bytes, bundle readers, CLI JSON and
  exit codes retain their meanings.

## Candidate qualification

- [x] Full `make check` passes on the candidate source: 424 tests, Ruff,
  documentation reference and diff checks on Python 3.14.
- [x] `origin/main...develop` review found no release blocker after the
  independent combined Standards and Spec findings were corrected and cleared.
  The existing-core changes were limited to CLI routing, explicit catalog
  insertion ordering, in-memory recipe validation and cooperative input-scan
  cancellation. The remaining diff is the bounded Workbench and its tests.
- [x] Exact candidate merge `bdc3ce75fd52ec6ed179c2d8be882b14ec83c654`
  passed [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39616403567)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39616403537)
  on Python 3.11--3.14 across Linux, macOS and Windows. Its tree is identical
  to reviewed PR #64 head `b39fa3f`, which also passed the
  [full matrix](https://github.com/raghavkandpal/parison/actions/runs/39615550659).
- [x] A clean `git archive` of `b39fa3f` built an inspected 2.0.0 wheel and
  source archive. The wheel contains all four Workbench modules and reports
  version 2.0.0. Wheel SHA-256:
  `134b2fbdc9f4333758c8f7e343615f7607bd78fc528c85e0dd0d87d63bfcfb89`.
  Source SHA-256:
  `1c6fbdc81431227dd88db4fa50b7e891cca63a27de2fcb1ec083ca53d0131c8f`.
- [x] A fresh Python 3.14 environment installed that wheel, reported version
  2.0.0 and passed a synthetic Workbench smoke through Plans, Run, Results and
  History with local PASS evidence. No external data or approval was involved.

## Publication

- [x] [Release PR #66](https://github.com/raghavkandpal/parison/pull/66)
  merged `develop` to `main` at exact commit
  `9f4846a45bac5f0c5e8e20e8cb4d56d7de725edc`. Its head `a326ec4` passed
  the manually dispatched [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39732962036).
  The merge passed [quality CI](https://github.com/raghavkandpal/parison/actions/runs/39733155869)
  and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39733155795).
- [x] A clean `git archive` of that merge commit rebuilt and inspected the
  2.0.0 wheel and source archive. The wheel contains all four Workbench modules.
  Wheel SHA-256: `215d7e4e22ecc4d75b7e0faa9f900d0b64ec0ca89ffb89db7893a6ff249d82ea`.
  Source SHA-256: `cfc256e6256332e5059a0689bd502ec5fde16e508dfbb38992dc62a3fdafce18`.
- [x] No release-specific external gate was required.
- [x] Annotated tag `2.0.0` points to the tested merge. The
  [GitHub release](https://github.com/raghavkandpal/parison/releases/tag/2.0.0)
  publishes the wheel, source archive and `SHA256SUMS`.
- [x] All public assets were re-downloaded; both archives passed the published
  checksum file. A fresh Python 3.14 environment installed the public wheel,
  reported `parison 2.0.0`, and passed synthetic local Workbench Plans, Results
  and History smoke after a PASS comparison.
- [x] Release code, tag, public assets and records identify the same tested
  merge commit.

Internal qualification does not establish extraction truth, policy approval,
migration approval or cutover authorization.
