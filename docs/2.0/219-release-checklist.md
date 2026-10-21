# Parison 2.0.0 release checklist

Date: 21 October 2026

Status: **candidate preparation**

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
- [ ] `origin/main...develop` review finds no release blocker.
- [ ] Exact candidate commit passes quality CI and the full built-wheel matrix
  on Python 3.11--3.14 across Linux, macOS and Windows.
- [ ] Clean `git archive` builds inspected 2.0.0 wheel and source archive;
  record their SHA-256 digests.
- [ ] A fresh supported-Python environment installs the archive wheel and
  exercises the Workbench primary workflow.

## Publication

- [ ] Release PR from `develop` to `main` merges after review, and CI passes
  on the exact merge commit.
- [ ] Build and inspect new artifacts from an archive of that merge commit.
- [ ] Complete any release-specific external gates.
- [ ] Push annotated `2.0.0` tag on the tested merge commit and publish the
  wheel, source archive and `SHA256SUMS` as a GitHub release.
- [ ] Re-download public assets, verify checksums, install the wheel fresh and
  repeat the Workbench smoke workflow.
- [ ] Reconcile release records to the exact tested commit and assets.

Internal qualification does not establish extraction truth, policy approval,
migration approval or cutover authorization.
