# Parison 0.19.0 release checklist

Date: 13 October 2026

Status: **candidate validation**

## Compatibility and product gates

- [x] The compatibility contract freezes released recipe semantics, schemas, exit codes, canonical encodings, CLI JSON and summary-safety boundaries through 1.x.
- [x] Immutable original-release fixtures cover keyed result schema 1, aggregate result schema 2, multiset result schema 3, suite-v1 and suite-v2.
- [x] Current code recursively verifies, safely inspects and derives supported Statement and cutover evidence from the historical corpus without rewriting it.
- [x] The installed-wheel acceptance suite invokes the complete CLI command path in-process, covering initialization, record preflight, repeated rehearsals, catalog history and diff, suites, verification, Statement rebinding and cutover reporting with checked-in synthetic suite inputs.
- [x] An unfamiliar human completed the workflow without reported confusion or undocumented repository knowledge.
- [x] The consolidated user guide documents the complete supported workflow, limits, security boundary and input surface.
- [x] The changelog records every frozen 1.x guarantee and explicitly records that 0.19 introduces no incompatibility.
- [x] Native workbook and unstructured-document inputs remain deferred and do not expand the 0.19 runtime or dependency surface.

## Performance and safety gates

- [x] Accuracy-checked machine-qualified evidence covers keyed, aggregate and multiset memory execution, keyed and multiset SQLite execution, raw high-mismatch evidence and mixed-mode concurrency.
- [x] Raw 10,000/100,000-row profiles quantify time, peak RSS and serialized result size at sample limits 10, 100 and 1,000.
- [x] Mixed-mode 100,000-row suites record three timed runs after warm-up for one, two and four workers; earlier evidence records sampled process-tree RSS.
- [x] Cross-platform throughput is deployment-specific; CI proves installed-wheel semantics on supported platforms, not equal host performance.
- [x] No network, credential, signing, repair, remote orchestration or automatic policy/engine selection was added.

## Pre-candidate evidence

- [x] Compatibility checkpoint `0028e7c` passed built-wheel CI on Python 3.11–3.14, macOS and Windows plus identity-constrained signing acceptance.
- [x] Performance-evidence checkpoint `96f2f66` passed [GitHub Actions run 38406588110](https://github.com/raghavkandpal/parison/actions/runs/38406588110) on Python 3.11–3.14, macOS and Windows.
- [x] Local pre-candidate suite after performance hardening: **240 passed, 6 skipped** optional-Polars tests.

## Exact candidate

- [x] Review `origin/main...develop` against repository invariants, the roadmap, compatibility contract and this checklist; the standards axis was clean and two spec gaps were corrected and re-reviewed clean.
- [x] Set `src/parison/__init__.py` to `0.19.0` only after the review was clean.
- [x] `make check` passed **240 tests with 6 optional-Polars skips** before exact candidate `7527ca652cce0a4f28f5faa8eecbfa2c8c1db0dc` was committed.
- [x] Exact candidate `7527ca6` passed [GitHub Actions run 38520230521](https://github.com/raghavkandpal/parison/actions/runs/38520230521) with built wheels on Python 3.11–3.14, macOS and Windows.
- [x] A clean `git archive` of `7527ca6` built an inspected wheel and source archive with 0.19.0 metadata.
- [x] A fresh Python 3.14 environment installed the candidate wheel and completed initialization, record preflight, direct comparison, catalog indexing, suite execution, recursive verification, Statement rebinding and cutover reporting.
- [x] Candidate artifact SHA-256 digests are recorded below.

Candidate SHA-256:

- `parison-0.19.0-py3-none-any.whl`: `4c7a6fa94c8894d7e295117e20a948716b10456c842e371e683116ff50c115e6`
- `parison-0.19.0.tar.gz`: `1f6ee4818d8c08f6603dbf0e89b1131ab662d8cf455dd85878aa26191cb63dc0`

## Publication

- [ ] Merge the reviewed candidate to `main` and require CI on the exact merge commit.
- [ ] Build from a clean archive of the merge commit and complete any release-specific external gates before tagging.
- [ ] Create and push annotated tag `0.19.0` on the exact tested merge.
- [ ] Publish the wheel, source archive and `SHA256SUMS` in the GitHub release; PyPI remains opt-in.
- [ ] Re-download public assets, verify checksums, install the wheel fresh and repeat the primary workflow.
- [ ] Reconcile the roadmap, checkpoint, checklist, changelog, README, documentation index and current-state record with the published artifacts.

Do not mark 0.19.0 released until the code, tag, public assets and release records identify the same tested commit.
