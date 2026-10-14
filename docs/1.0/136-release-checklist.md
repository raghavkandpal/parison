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
- [x] Exact candidate `23d8b6ab67ed57c3f8fb05fe12dfd35ac98bd6e0` passes [built-wheel CI run 38521599332](https://github.com/raghavkandpal/parison/actions/runs/38521599332) on Python 3.11–3.14, macOS and Windows.
- [x] A clean archive of `23d8b6a` builds an inspected 1.0.0 wheel and source archive.
- [x] A fresh Python 3.14 environment installs the candidate wheel and completes direct comparison, suite execution, recursive verification, Statement rebinding and cutover reporting.
- [x] Candidate commit, CI run and artifact SHA-256 digests are recorded here.

Candidate SHA-256:

- `parison-1.0.0-py3-none-any.whl`: `ff32c7f39dd52f7d6d6636631e9d80e60f442766ec3b8d9db37a40b745751a14`
- `parison-1.0.0.tar.gz`: `1d83d5ab1ac79eea2b17a1ce24112bf35637176ef8a67ac64a3d39bfcb3378b8`

## Publication

- [ ] Merge the reviewed candidate to `main` and require CI on the exact merge commit.
- [ ] Build the publishable wheel, source archive and checksums from a clean archive of the exact merge.
- [ ] Create annotated tag `1.0.0` at the exact tested merge and publish the GitHub release; PyPI remains opt-in.
- [ ] Re-download public assets, verify checksums and repeat fresh-wheel smoke workflows.
- [ ] Reconcile roadmap, checklist, changelog, README, documentation index and current-state record to the published release.

Do not mark 1.0.0 released until the code, tag, public assets and release records identify the same tested commit.
