# Contributing to Parison

Parison is a local-first, deterministic verification layer. Contributions must preserve its zero-custody boundary and its meaning of PASS: agreement under an explicit policy, not extraction truth, approval or cutover authorization.

## Setup and checks

Parison supports Python 3.11 through 3.14. Create a virtual environment with a supported interpreter, then install the development and optional format dependencies:

```sh
python -m pip install -e '.[dev,test,parquet]'
```

Use the Make targets as the public development interface:

- `make context` shows the branch, worktree state, latest tag and active gate.
- `make lint` runs the pinned Ruff rules.
- `make format` formats tracked Python source.
- `make format-check` verifies formatting without changing files.
- `make test` runs the complete unit suite.
- `make test TEST=tests.test_<area>` runs a focused module.
- `make check` is the required local gate: lint, format verification, tests and whitespace checks.
- `make build` creates wheel and source archives.

Do not use Ruff unsafe fixes. Review warnings whose fixes could change runtime behavior.

## Compatibility and evidence

Released recipes, schemas, bundles, imports, exit codes, canonical bytes and CLI JSON remain readable and stable. Semantic changes require a new versioned contract. Keep policy choices explicit: generated output must not approve keys, tolerances, scope, exclusions or repairs.

Canonical JSON or byte serialization changes need a committed byte fixture. Defect fixes need a focused regression test. Preserve deterministic ordering and exact bytes across supported platforms.

Summary-safe output must exclude source paths, keys, values and discrepancy samples. Core execution must not add network access, credential handling, signing, repair or remote orchestration. Publication must remain atomic, no-overwrite, symlink-safe and clean sensitive staging after failure or interruption.

Names imported from `parison.core` or documented elsewhere are public compatibility surfaces. Leading-underscore names and internal modules are private, but moving implementation must not break released re-exports.

## Commits and releases

Keep commits coherent and use conventional prefixes such as `feat:`, `fix:`, `docs:`, `style:`, `refactor:` or `chore:`. Separate formatting and mechanical moves from semantic changes.

Before a feature commit, run `make check`. Packaging, schema, CLI or platform changes also require built-wheel CI on Python 3.11–3.14, macOS and Windows. Follow [RELEASING.md](RELEASING.md) and the active release checklist for a release; internal formatting or module moves alone do not warrant one.
