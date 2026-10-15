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

- [x] Review `origin/main...develop` at the final candidate commit against repository invariants, the roadmap, contracts and this checklist; both Standards and Spec axes are clean.
- [x] `make check` passes **276 tests with 11 documented optional-Polars skips** from the final candidate worktree.
- [x] Exact candidate `eb0566899278e337f0818e30d11486ad66fa83b4` passes [built-wheel CI run 38694867223](https://github.com/raghavkandpal/parison/actions/runs/38694867223) on Python 3.11–3.14, macOS and Windows with pinned Polars 1.44.2.
- [x] A clean archive of `eb05668` builds an inspected 1.2.0 wheel and source archive.
- [x] A fresh Python 3.14 environment installs the candidate wheel with pinned Polars 1.44.2; version/schema inspection, semantic CSV-to-JSON-Lines comparison and recursive verification pass, as do evolution validation/explanation/compilation, full policy diff and summary-safe diff assertions.
- [x] Candidate commit, CI run, smoke evidence and artifact SHA-256 digests are recorded here.

Candidate SHA-256:

- `parison-1.2.0-py3-none-any.whl`: `769ff7281760138b3ff7d6f1e42cf1cff803e6070e72c55291136974ce9c480f`
- `parison-1.2.0.tar.gz`: `6ae67f53b0a84a7f9d181963e4b4b9803a946cb42ddedb05bf32324f3aed2518`

## Publication

- [ ] Merge the reviewed candidate to `main` and require CI on the exact merge commit.
- [ ] Build the publishable wheel, source archive and checksums from a clean archive of the exact merge.
- [ ] Create annotated tag `1.2.0` at the exact tested merge and publish the GitHub release; PyPI remains opt-in.
- [ ] Re-download public assets, verify checksums and repeat fresh-wheel semantic projection and policy-diff smoke workflows.
- [ ] Reconcile roadmap, checklist, changelog, README, documentation index and current-state record to the published release.

Do not mark 1.2.0 released until the code, tag, public assets and release records identify the same tested commit.
