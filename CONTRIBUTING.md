# Contributing to Parison

Parison is a local-first, deterministic verification layer. Contributions must preserve its zero-custody boundary and its meaning of PASS: agreement under an explicit policy, not extraction truth, approval or cutover authorization.

## Setup and checks

Parison supports Python 3.11 through 3.14. Select an installed supported interpreter explicitly; an unqualified `python` may resolve to an older system or Conda environment. For example, with Python 3.14 installed:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,test,parquet,postgres]' build
.venv/bin/python --version
make check PYTHON=.venv/bin/python
```

On Windows, use `.venv\Scripts\python.exe` for both pip and the Make `PYTHON` override. The `test` extra includes the pinned XLSX reader; `parquet` and `postgres` install the optional adapter dependencies used in CI. Installing the PostgreSQL adapter does not configure credentials or start a database. `build` supplies `make build`.

Make defaults to `PYTHON=python`; pass the virtual environment interpreter to each invocation, or activate the environment first. Confirm `python --version` after activation. Keep `.venv` local and ignored. See the [Codex development harness](docs/2.4/319-codex-development-harness.md) for agent workflows, evidence and rollback.

Use the Make targets as the public development interface:

- `make context` shows the branch, worktree state, latest tag and active gate.
- `make lint` runs the pinned Ruff rules.
- `make format` formats tracked Python source.
- `make format-check` verifies formatting without changing files.
- `make test` runs the complete unit suite.
- `make test TEST=tests.test_<area>` runs a focused module.
- `make docs-check` verifies that the generated command reference matches the parser.
- `make check` is the required local gate: lint, format verification, generated-reference validation, tests and whitespace checks.
- `make build` creates wheel and source archives.

Do not use Ruff unsafe fixes. Review warnings whose fixes could change runtime behavior.

## Compatibility and evidence

Released recipes, schemas, bundles, imports, exit codes, canonical bytes and CLI JSON remain readable and stable. Semantic changes require a new versioned contract. Keep policy choices explicit: generated output must not approve keys, tolerances, scope, exclusions or repairs.

Canonical JSON or byte serialization changes need a committed byte fixture. Defect fixes need a focused regression test. Preserve deterministic ordering and exact bytes across supported platforms.

Summary-safe output must exclude source paths, keys, values and discrepancy samples. Core execution must not add network access, credential handling, signing, repair or remote orchestration. Publication must remain atomic, no-overwrite, symlink-safe and clean sensitive staging after failure or interruption.

Names imported from `parison.core` or documented elsewhere are public compatibility surfaces. Leading-underscore names and internal modules are private, but moving implementation must not break released re-exports.

## Commits and releases

Keep commits coherent and use conventional prefixes such as `feat:`, `fix:`, `docs:`, `style:`, `refactor:` or `chore:`. Separate formatting and mechanical moves from semantic changes.

Create each change branch from current `develop`, using a purpose prefix such as `feature/`, `fix/`, `docs/` or `ci/`. Keep the branch scoped to one coherent change, then submit its pull request to `develop`. Direct development on `main` or `develop` is not the project workflow. Pull requests to `main` are reserved for reviewed releases from `develop`.

Before a feature commit, run `make check`. Packaging, schema, CLI or platform changes also require a manual full-matrix workflow dispatch on the exact pull-request head, covering built-wheel CI on Python 3.11–3.14, macOS and Windows. Use `make check` as local preflight and `make test TEST=tests.ci_native_preflight` for focused host regressions. CI runs complete Linux3.14 tests and tight macOS/Windows preflight first; manual `test.yml` dispatch defaults to full qualification. Add feature coverage to the discoverable suites instead of extending workflow command lists. See [CI gates](docs/2.4/305-tiered-ci-qualification.md). Follow [RELEASING.md](RELEASING.md) and the active release checklist for a release; internal formatting or module moves alone do not warrant one.
