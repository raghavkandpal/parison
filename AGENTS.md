# Parison agent contract

## Invariants

- Parison is a local-first, deterministic verification layer. PASS means agreement under an explicit policy—not extraction truth, approval, or cutover authorization.
- Core execution is zero-custody: local inputs, strict JSON, no network, credentials, signing, repair, or remote orchestration.
- Preserve released recipes, schemas, bundles, exit codes, canonical bytes, and CLI JSON. Version semantic changes and keep old bundles readable.
- Policies stay explicit; generated suggestions never approve keys, tolerances, scope, exclusions, or repairs.
- Derived evidence starts from verification. Summary-safe output excludes source paths, keys, values, and discrepancy samples.
- Publication is deterministic, atomic, no-overwrite, symlink-safe, and cleans sensitive staging on failure or interruption.
- Prefer stdlib and deepen existing modules before adding dependencies or seams.

Start with `make context`. Read [product direction](docs/0.15/104-product-direction-and-release-arc.md) only when changing scope or boundaries; use [the documentation index](docs/README.md) to locate feature contracts.

## Workflow

1. Preserve unrelated work reported by `make context`.
2. Start each change branch from current `develop`, using a purpose prefix such as `feature/`, `fix/`, `docs/`, or `ci/`; reserve `develop` for reviewed integration and `main` for releases.
3. Define the smallest coherent slice and a checkable completion gate.
4. Read/search only files needed for that gate. Keep command output bounded; expand it only to diagnose failure.
5. Test narrowly with `make test TEST=tests.test_<area>`. Add a regression test for each defect and a byte fixture for canonical serialization.
6. Before a feature commit, pass `make check`.
7. Document user-visible behavior in the active version folder; update `docs/README.md` and `CHANGELOG.md`.
8. Build each branch as a coherent chunk of roughly 3–4 conventional commits, then push it and open or update its pull request to `develop`. Verify the exact head commit in CI before integration.

Packaging, schema, CLI, or platform changes require a manual full-matrix dispatch on the exact pull-request head before integration: built-wheel CI on Python 3.11–3.14, macOS, and Windows. Optional-Polars skips are valid only when Polars is absent.

Targeted tests: core semantics `test_parison`/`test_semantics`; formats `test_jsonl`/`test_parquet`/`test_sqlite`; suites `test_suite`; catalog `test_catalog`; schemas `test_json_schemas`; integrations `test_github_actions`/`test_integrations`; evidence handoff `test_statement`.

## Conditional rules

- Research: use primary sources; record design consequences, threats, non-goals, and access date. Keep confidential work only in ignored `local-research/`.
- Benchmarks: report machine-specific evidence, never universal capacity.
- Releases: follow the active checklist and [RELEASING.md](RELEASING.md). Open pull requests to `main` only for releases from `develop`; tag the exact merge, publish wheel/source/checksums, re-download and smoke-test public assets, then reconcile every release record.
- Handoffs: replace changing state in `docs/CURRENT.md`; keep session history in version documents.
