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
- [ ] Exact candidate passes installed-wheel CI on Python 3.11–3.14, macOS and Windows.
- [ ] Clean archive build contains only intended files and produces reproducible wheel/source checksums.
- [ ] A clean environment installs the wheel, reports `parison 0.15.0`, runs two same-policy rehearsals, adds them to a catalog, and exercises history and diff.
- [ ] Payout and feature-pipeline suites run and recursively verify from the installed wheel.

## Publication

- [ ] Merge the reviewed candidate to `main`.
- [ ] Create annotated tag `0.15.0` from the merge commit.
- [ ] Publish wheel, source archive and SHA-256 checksums on the GitHub release.
- [ ] Download the published artifacts, verify checksums and repeat the installed-wheel smoke workflow.
- [ ] Mark the roadmap, checklist, README and documentation index released.

PyPI publication remains intentionally deferred.
