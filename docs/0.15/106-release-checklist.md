# Parison 0.15.0 release checklist

Date: 12 October 2026

Status: **release candidate**

## Feature and safety gates

- [x] History is restricted to ordinary runs with one exact lowercase policy fingerprint and durable insertion order.
- [x] Schema-v1 catalogs migrate once to explicit schema-v2 order; update, deletion and `VACUUM` preserve surviving positions.
- [x] Diff rejects suites and policy mismatch and compares only one centralized safe stored projection.
- [x] Equivalent lexical paths normalize to one catalog entry without resolving symlinks.
- [x] Live state checks recursively hash manifest-covered files without opening source data or decoding result evidence.
- [x] Input digests disclose equality without storing source paths or values, and the documentation describes their dictionary-guessing risk.
- [x] Warehouse/backfill, payout-reconciliation and feature-pipeline examples state both their proof and upstream limitations.

## Review and candidate evidence

- [x] Two-axis review against `0.14.0` found three contract gaps and three maintainability concerns; all were fixed and re-reviewed.
- [x] Post-review local suite: **208 passed, 6 skipped** optional-Polars tests.
- [x] Candidate `8278071` passed [GitHub Actions run 38216124378](https://github.com/raghavkandpal/parison/actions/runs/38216124378) on Python 3.11–3.14, macOS and Windows.
- [x] A clean `git archive` build contained only intended package/source files. Candidate wheel SHA-256: `2af9a6f539958a9b03cde075d12a47f122144f2fb44e39bc8a9345ad4bd202a2`; source archive: `638acaac229162cedfbe0f6157f445cf3937392adb270aeb5b0b7ec131424906`.
- [x] A clean Python 3.12 environment installed the wheel, reported `parison 0.15.0`, ran two same-policy rehearsals, added them to a schema-v2 catalog, and exercised unchanged history and diff.
- [x] Payout and feature-pipeline suites ran to PASS and recursively verified from the installed wheel.

## Publication

- [ ] Merge the reviewed candidate to `main`.
- [ ] Create annotated tag `0.15.0` from the merge commit.
- [ ] Publish wheel, source archive and SHA-256 checksums on the GitHub release.
- [ ] Download the published artifacts, verify checksums and repeat the installed-wheel smoke workflow.
- [ ] Mark the roadmap, checklist, README and documentation index released.

PyPI publication remains intentionally deferred.
