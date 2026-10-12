# Parison working agreement

## Product invariant

Build Parison as a local-first, deterministic verification layer for migrations, backfills and pipeline rewrites. A PASS reports agreement under an explicit reviewed policy; it never proves extraction truth, policy approval or cutover authorization.

Preserve the zero-custody boundary: core execution reads user-supplied local inputs and performs no network access, credential discovery, signing, data repair or remote orchestration. Keep recipes strict JSON. Read [the accepted product direction](docs/0.15/104-product-direction-and-release-arc.md) before changing these boundaries.

## Start every change

1. Inspect `git status` and preserve unrelated user work.
2. Read [the documentation index](docs/README.md), then the active-version roadmap and the contract governing the touched behavior.
3. State the smallest coherent slice and its observable completion gate.

## Implementation rules

- Prefer the Python standard library and deepen existing modules before adding dependencies or abstractions.
- Treat published recipes, schemas, result bundles, exit codes, canonical encodings and CLI JSON as compatibility contracts. Version semantic changes; keep released bundles readable.
- Keep comparison policy explicit. Suggestions may draft policy, but may not silently approve keys, tolerances, scope, exclusions or repairs.
- Verify before deriving evidence. Safe projections exclude source paths, keys and values unless the user explicitly selected raw sensitivity.
- Publish files and bundles atomically, refuse overwrite, reject unsafe symlinks and clean staging or sensitive temporary state on failure and interruption.
- Keep output deterministic: stable ordering, explicit encodings and no path, clock, hostname or process-dependent semantic fields.
- Keep optional integrations outside the runtime dependency graph and pass arguments without shell interpolation where practical.

## Verification gates

Run the narrowest relevant tests while iterating, then before a feature commit run:

```sh
PYTHONPATH=src python -m unittest discover -s tests -q
git diff --check
```

The complete local suite must pass; optional-Polars skips are acceptable only when Polars is absent. Changes to packaging, schemas, CLI workflows or platform behavior also require built-wheel GitHub Actions evidence on Python 3.11–3.14, macOS and Windows. Add a regression test for every corrected defect and a byte fixture for every canonical serialization contract.

## Documentation and research

- Record each feature in the active version folder with a normative contract or guide, update `docs/README.md`, and keep `CHANGELOG.md` user-facing.
- Number new version documents after the highest existing document number.
- Use primary specifications and maintainer documentation for unstable or security-sensitive claims; record access date, design implications, threats and non-goals.
- Keep confidential or commercial research under ignored `local-research/`. Never commit that directory or quote it into public documentation.
- Treat benchmark results as machine-specific evidence, never universal capacity claims.

## Git and releases

- Work on `develop`; merge reviewed release candidates to `main` through a pull request.
- Make small conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `release:`) only after their stated gate passes. Do not rewrite shared history.
- Push coherent checkpoints so GitHub Actions validates the exact commit.
- For a release, follow the active version checklist and [RELEASING.md](RELEASING.md): build from a clean archive, test the installed wheel in a fresh environment, merge the reviewed candidate, tag the exact merge commit, publish wheel/source/checksums, then re-download and verify public assets.
- A release is complete only when code, tag, GitHub release, public-asset smoke evidence, changelog, roadmap, checkpoint and checklist agree.
