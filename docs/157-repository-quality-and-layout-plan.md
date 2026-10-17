# Repository quality and layout plan

Date: 17 October 2026

Status: **planned for the next development session, before 1.5 product work**

## Objective

Establish one fast, deterministic Python quality gate; document contributor standards; and reduce the concentration in `src/parison/core.py` without changing released behavior, imports, schemas, canonical bytes, bundles, exit codes or CLI JSON.

## Baseline

- The branch is clean after the 1.4.0 release.
- Python source, tests and benchmarks total about 14,000 lines; `src/parison/core.py` contains about 3,900.
- Ruff 0.17.1 reports 82 findings with its defaults and 126 under the proposed initial rule set.
- At a 120-character line length, 38 of 46 Python files require formatting.
- Most findings are import ordering or safe modernization; unused-code findings require review.

## Work order

### 1. Add Ruff quality gates

- Pin Ruff 0.17.1 for reproducible local and CI behavior.
- Configure it in `pyproject.toml` for Python 3.11 and a 120-character line length.
- Begin with stable `E4`, `E7`, `E9`, `F`, `I`, `UP`, `B` and `RUF` lint families.
- Keep preview rules and unsafe fixes disabled.
- Add `make lint`, `make format`, and `make format-check`; extend `make check` with lint and format verification.
- Run lint once in a dedicated Ubuntu CI quality job rather than in every platform/Python lane.

### 2. Apply mechanical cleanup separately

Use isolated commits so formatting cannot conceal semantic changes:

1. `chore: configure ruff quality gates`
2. `style: apply ruff import and safe lint fixes`
3. `style: format source`
4. `style: format tests and benchmarks`
5. `fix: resolve remaining reviewed lint findings`

Never use `ruff check --unsafe-fixes`. Every commit must pass `make check`.

### 3. Document standards

Create a concise `CONTRIBUTING.md`, linked from `README.md`, covering supported Python versions, setup, Make targets, formatting, linting, targeted tests, deterministic JSON/byte fixtures, public versus private interfaces, compatibility obligations, summary safety, commits and releases.

Keep `AGENTS.md` focused on agent workflow. Do not duplicate the complete contract in contributor documentation.

### 4. Reshape implementation modules

Keep `core.py` as a compatibility facade while moving implementation behind existing seams:

```text
src/parison/
├── core.py             # compatibility facade and released re-exports
├── policies.py         # recipe/suite loading, normalization and fingerprints
├── inputs.py           # readers, source identity, validation and drafting
├── comparison.py       # keyed, aggregate and multiset execution
├── evidence.py         # publication, verification, inspection and reports
├── suites.py           # suite execution, assembly, resume and workers
├── reconciliation.py
├── manifesting.py
├── evolution.py
├── catalog.py
└── cli.py
```

Extract in this order: evidence, suites, inputs, comparison, policies. Each slice starts as a behavior-preserving move. Existing `parison.core` imports remain supported.

### 5. Consolidate filesystem safety

After module extraction, replace duplicated safe-file and publication implementations with one private deep module, `parison._safe_fs`. Its small interface should cover safe regular-file reads beneath an opened root, link/reparse rejection, stable identity checks, atomic no-overwrite directory publication and staging cleanup.

This is security-sensitive work. Require focused POSIX and Windows race tests before migrating each caller; replace old implementations rather than layering adapters over them.

### 6. Keep provenance layouts stable

Do not move versioned documentation, examples, schemas or compatibility fixtures. Keep the flat `tests/test_<area>.py` layout until source extraction is complete because it supports the documented targeted-test workflow.

## Completion gate

- Ruff lint and format checks are mandatory locally and in CI.
- `make check` remains the single local gate.
- Contributor standards have one authoritative document.
- `core.py` is a compatibility facade rather than the primary implementation module.
- Released imports and observable behavior remain compatible.
- The full built-wheel matrix passes on Python 3.11–3.14, macOS and Windows.
- Formatting and internal moves alone do not trigger a product release.

Only after this gate passes should 1.5 product research begin.
