# Parison 0.19.0 release checklist

Date: 13 October 2026

Status: **candidate preparation**

## Compatibility and product gates

- [x] The compatibility contract freezes released recipe semantics, schemas, exit codes, canonical encodings, CLI JSON and summary-safety boundaries through 1.x.
- [x] Immutable original-release fixtures cover keyed result schema 1, aggregate result schema 2, multiset result schema 3, suite-v1 and suite-v2.
- [x] Current code recursively verifies, safely inspects and derives supported Statement and cutover evidence from the historical corpus without rewriting it.
- [x] A clean installed-wheel workflow covers initialization, record preflight, repeated rehearsals, catalog history and diff, suites, verification, Statement rebinding and cutover reporting.
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

- [ ] Review `origin/main...develop` against repository invariants, the roadmap, compatibility contract and this checklist; resolve every blocker.
- [ ] Set `src/parison/__init__.py` to `0.19.0` only after the review is clean.
- [ ] Run `make check` from a clean checkout and record the exact candidate commit.
- [ ] Require built-wheel CI on Python 3.11–3.14, macOS and Windows for that exact commit.
- [ ] Export the exact commit with `git archive`; build and inspect its wheel and source archive.
- [ ] Install the wheel in a fresh supported-Python environment and complete the primary workflow from initialization through verified cutover evidence.
- [ ] Record candidate wheel and source-archive SHA-256 digests here.

## Publication

- [ ] Merge the reviewed candidate to `main` and require CI on the exact merge commit.
- [ ] Build from a clean archive of the merge commit and complete any release-specific external gates before tagging.
- [ ] Create and push annotated tag `0.19.0` on the exact tested merge.
- [ ] Publish the wheel, source archive and `SHA256SUMS` in the GitHub release; PyPI remains opt-in.
- [ ] Re-download public assets, verify checksums, install the wheel fresh and repeat the primary workflow.
- [ ] Reconcile the roadmap, checkpoint, checklist, changelog, README, documentation index and current-state record with the published artifacts.

Do not mark 0.19.0 released until the code, tag, public assets and release records identify the same tested commit.
