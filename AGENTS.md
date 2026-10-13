# Parison agent contract

## Invariants

- Parison is a local-first, deterministic verification layer. PASS means agreement under an explicit policy—not extraction truth, approval, or cutover authorization.
- Core execution is zero-custody: local inputs, strict JSON, no network, credentials, signing, repair, or remote orchestration.
- Preserve released recipes, schemas, bundles, exit codes, canonical bytes, and CLI JSON. Version semantic changes and keep old bundles readable.
- Policies stay explicit; generated suggestions never approve keys, tolerances, scope, exclusions, or repairs.
- Derived evidence starts from verification. Summary-safe output excludes source paths, keys, values, and discrepancy samples.
- Publication is deterministic, atomic, no-overwrite, symlink-safe, and cleans sensitive staging on failure or interruption.
- Prefer stdlib and deepen existing modules before adding dependencies or seams.

Read [current state](docs/CURRENT.md) first. Read [product direction](docs/0.15/104-product-direction-and-release-arc.md) only when changing scope or boundaries; use [the documentation index](docs/README.md) to locate feature contracts.

## Workflow

1. Inspect `git status`; preserve unrelated work.
2. Define the smallest coherent slice and a checkable completion gate.
3. Test narrowly while iterating. Add a regression test for each defect and a byte fixture for canonical serialization.
4. Before a feature commit, pass:

   ```sh
   PYTHONPATH=src python -m unittest discover -s tests -q
   git diff --check
   ```

5. Document user-visible behavior in the active version folder; update `docs/README.md` and `CHANGELOG.md`.
6. Commit coherent slices on `develop` with conventional prefixes; push checkpoints for exact-commit CI.

Packaging, schema, CLI, or platform changes require built-wheel CI on Python 3.11–3.14, macOS, and Windows. Optional-Polars skips are valid only when Polars is absent.

Targeted tests: core semantics `test_parison`/`test_semantics`; formats `test_jsonl`/`test_parquet`/`test_sqlite`; suites `test_suite`; catalog `test_catalog`; schemas `test_json_schemas`; integrations `test_github_actions`/`test_integrations`; evidence handoff `test_statement`.

## Conditional rules

- Research: use primary sources; record design consequences, threats, non-goals, and access date. Keep confidential work only in ignored `local-research/`.
- Benchmarks: report machine-specific evidence, never universal capacity.
- Releases: follow the active checklist and [RELEASING.md](RELEASING.md). Merge reviewed candidates to `main`, tag the exact merge, publish wheel/source/checksums, re-download and smoke-test public assets, then reconcile every release record.
