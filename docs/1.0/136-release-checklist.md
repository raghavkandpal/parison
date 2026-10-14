# Parison 1.0.0 release checklist

Date: 14 October 2026

Status: **candidate**

## Stability gate

- [x] Every pre-candidate product and compatibility prerequisite in the [1.0 readiness checklist](../0.19/128-1.0-readiness-checklist.md) is complete; its release actions remain tracked below.
- [x] The candidate changes only the package version and release documentation; runtime semantics and dependencies are unchanged.
- [x] The [0.19 compatibility contract](../0.19/126-compatibility-contract.md) explicitly freezes the supported surface through 1.x.
- [x] The [consolidated user guide](../0.19/131-user-guide.md) documents every supported command and remains authoritative for 1.0.
- [x] Native workbook, document and receipt-binding work remains behind the adoption gates in the [post-1.0 research](../0.20/134-post-1.0-direction-research.md).

## Exact candidate

- [x] Review `origin/main...develop` against repository invariants, the roadmap, compatibility contract and this checklist; both standards and specification axes are clean.
- [x] `make check` passes **240 tests with 6 optional-Polars skips** from the candidate worktree.
- [ ] The exact candidate passes built-wheel CI on Python 3.11–3.14, macOS and Windows.
- [ ] A clean archive builds an inspected 1.0.0 wheel and source archive.
- [ ] A fresh supported-Python environment installs the candidate wheel and completes the primary direct, suite, recursive verification, Statement and cutover workflows.
- [ ] Candidate commit, CI run and artifact SHA-256 digests are recorded here.

## Publication

- [ ] Merge the reviewed candidate to `main` and require CI on the exact merge commit.
- [ ] Build the publishable wheel, source archive and checksums from a clean archive of the exact merge.
- [ ] Create annotated tag `1.0.0` at the exact tested merge and publish the GitHub release; PyPI remains opt-in.
- [ ] Re-download public assets, verify checksums and repeat fresh-wheel smoke workflows.
- [ ] Reconcile roadmap, checklist, changelog, README, documentation index and current-state record to the published release.

Do not mark 1.0.0 released until the code, tag, public assets and release records identify the same tested commit.
