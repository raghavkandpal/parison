# Repository maintenance checkpoint

Date: 17 October 2026

Status: **complete**

## Delivered

- Ruff 0.17.1 is pinned in the development extra and configured for Python 3.11, a 120-character line length and the planned stable lint families.
- `make lint`, `make format`, `make format-check` and the expanded `make check` provide one local quality gate; one dedicated Ubuntu CI job runs lint and format verification.
- Safe lint fixes and formatting were isolated from reviewed findings. `CONTRIBUTING.md` is the authoritative contributor setup, quality, compatibility and evidence-safety guide.
- `parison.core` is a 237-line compatibility facade. Implementations now live in `policies.py`, `inputs.py`, `comparison.py`, `evidence.py` and `suites.py`; released imports remain available from `parison.core`.
- `_safe_fs.py` owns output-parent validation and cross-platform atomic no-replace directory publication. Run, suite, editor-schema, reconciliation and dataset-evidence publishers use the shared primitive.
- Focused tests cover POSIX publication races, symlinked output parents and the Windows no-replace fallback contract.

## Verification

- `make check` passes 321 tests with 11 expected optional-Polars skips.
- Exact commit `35fe2d0578ac54956c58bd4501aba8ae03fb8de2` passed the complete built-wheel matrix on Python 3.11–3.14 across Linux, macOS and Windows, plus the dedicated Ruff quality job: [GitHub Actions run 39015498650](https://github.com/raghavkandpal/parison/actions/runs/39015498650).
- Formatting and internal moves did not change the package version, schemas, canonical bytes, bundle layouts, exit codes or CLI JSON and do not trigger a product release.

## Next gate

Research and specify one coherent 1.5 capability before implementation. Prefer a capability that strengthens investigation of high-stakes data-change gates without adding connectors, repair, implicit policy or remote custody.
