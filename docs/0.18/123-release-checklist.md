# Parison 0.18.0 release checklist

Date: 13 October 2026

Status: **candidate hardening**

## Feature and safety gates

- [x] SQLite execution is explicit for keyed-v1 and multiset-v1; memory remains the default and aggregate-v1 remains memory-only.
- [x] Parison-owned typed encodings and comparison code define identity, equality, tolerance and evidence order; SQLite coercion and collation do not.
- [x] Memory and SQLite produce byte-identical keyed result JSON after removing only documented SQLite operational metadata.
- [x] Cross-engine coverage includes PASS, FAIL, tolerance, null values, normalization, mappings, raw and summary sensitivity, empty inputs, null keys and duplicate keys.
- [x] Temporary storage has an explicit byte ceiling and private workspaces clean up after success, handled failure and interruption.
- [x] Direct and suite ERROR and INTERRUPTED evidence retains SQLite engine and temporary-limit metadata.
- [x] Released keyed memory output retains its existing runtime and terminal-result shape.
- [x] No runtime dependency, credential access, network behavior, automatic engine selection or changed keyed-v1 policy was added.

## Candidate evidence

- [x] Local suite after candidate-review hardening: **236 passed, 6 skipped** optional-Polars tests.
- [x] The two-axis `origin/main...develop` review found raw pre-normalization evidence loss and missing suite failure metadata; both blockers have regression coverage and are corrected.
- [x] The 10k/100k arm64 macOS benchmark preserved exact PASS counts. At 100k rows SQLite reduced measured process peak RSS from 166.7 MiB to 25.7 MiB while taking 3.4 times as long and using 77.2 MiB of scratch storage.
- [x] Pre-review implementation commit `12610d5` passed [GitHub Actions run 38363720890](https://github.com/raghavkandpal/parison/actions/runs/38363720890) on Python 3.11–3.14, macOS and Windows.
- [x] Exact candidate `62390ae` passed [GitHub Actions run 38364667632](https://github.com/raghavkandpal/parison/actions/runs/38364667632) with built wheels on Python 3.11–3.14, macOS and Windows.
- [x] A clean `git archive` of `62390ae` built wheel and source artifacts with inspected contents and 0.18.0 metadata.
- [x] A fresh Python 3.12 environment installed the candidate wheel and completed direct and suite SQLite-keyed PASS workflows with recursive bundle verification.

Candidate SHA-256:

- `parison-0.18.0-py3-none-any.whl`: `ca1db393fa6414daf641627eaf3fb09158e9f475015d39f1dd899464d4a97182`
- `parison-0.18.0.tar.gz`: `2a205e2765d75a1290deea70141c03838e7cd3c3a31d7866d8af5bfbb4a85da9`

## Publication

- [ ] Reviewed candidate is merged to `main` through a pull request.
- [ ] Exact merge commit passes the full CI matrix.
- [ ] Annotated tag `0.18.0` identifies the exact tested merge commit.
- [ ] GitHub release 0.18.0 publishes the exact-merge wheel, source archive and `SHA256SUMS`.
- [ ] Public assets are downloaded again, checksum-verified and smoke-tested from a fresh environment.
- [ ] Roadmap, checkpoint, checklist, changelog, README and current-state documents identify 0.18.0 as released.

PyPI publication remains intentionally deferred.
