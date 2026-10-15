# Parison 1.2.0 release checklist

Date: 15 October 2026

Status: **candidate**

## Capability gate

- [x] The [semantic scalar contract](../1.1/139-semantic-scalar-contract.md) preserves legacy recipes and closes opt-in representation semantics across supported formats and comparison modes.
- [x] The [schema evolution and policy-diff contract](143-schema-evolution-and-policy-diff-contract.md) is deterministic, data-free, summary-safe and does not infer mappings, apply transformations or grant approval.
- [x] Canonical fixtures, scalar-format corpus, evolution classification cases and complete effective-policy mutation coverage pass locally.
- [x] Independent Standards and Spec reviews of the implementation report no release blockers.
- [x] The 1.x compatibility boundary remains unchanged: released recipes, schemas, bundles, canonical bytes, exit codes and CLI JSON stay readable.

## Exact candidate

- [ ] Review `origin/main...develop` at the final candidate commit against repository invariants, the roadmap, contracts and this checklist; require both standards and specification axes to be clean.
- [ ] `make check` passes from the final candidate worktree.
- [ ] The exact candidate passes built-wheel CI on Python 3.11–3.14, macOS and Windows with optional Polars installed.
- [ ] A clean archive of the exact candidate builds an inspected 1.2.0 wheel and source archive.
- [ ] A fresh supported-Python environment installs the candidate wheel and exercises semantic projection plus validate, explain, compile and summary policy-diff commands.
- [ ] Candidate commit, CI run, smoke evidence and artifact SHA-256 digests are recorded here.

## Publication

- [ ] Merge the reviewed candidate to `main` and require CI on the exact merge commit.
- [ ] Build the publishable wheel, source archive and checksums from a clean archive of the exact merge.
- [ ] Create annotated tag `1.2.0` at the exact tested merge and publish the GitHub release; PyPI remains opt-in.
- [ ] Re-download public assets, verify checksums and repeat fresh-wheel semantic projection and policy-diff smoke workflows.
- [ ] Reconcile roadmap, checklist, changelog, README, documentation index and current-state record to the published release.

Do not mark 1.2.0 released until the code, tag, public assets and release records identify the same tested commit.
