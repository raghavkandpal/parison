# Release checklist

## Hard blockers

- [x] Complete a preliminary `Parison` / `parison` name screen for a bounded open-source alpha; PyPI and npm exact names were unclaimed and no obvious software conflict was identified. This is not formal legal clearance; obtain counsel before material commercial investment or a trademark filing.
- [x] Choose a distribution license, add its `LICENSE` file, and declare it in `pyproject.toml` (MIT).
- [x] Complete an unfamiliar workflow end to end: two blinded unfamiliar-agent executions completed, followed by human acceptance of the second trial's evidence and recommendation; no blocking usability finding was reported.

Do not publish while any hard blocker remains open.

## Candidate verification

- [x] Confirm the version in `src/parison/__init__.py` is `0.1.0`; retain the `Unreleased` changelog heading until publication.
- [x] Start from a clean `git archive` export with no generated inputs or prior run directories.
- [x] Build outside the working tree with no prior `build`, `dist` or `src/*.egg-info` outputs.
- [x] Run tests on Python 3.11 through 3.14 in the merged CI matrix.
- [x] Run the optional Polars suite on every supported Python version, plus macOS and Windows smoke jobs.
- [x] Build wheel and source archive with `python -m build`.
- [x] Install the wheel with its Parquet extra into an empty virtual environment.
- [x] Run `parison --version`, `validate-recipe`, example `compare`, and `verify` from the installed wheel.
- [x] Inspect the wheel and source archive for only intended package, tests, README, license and metadata files.
- [x] Confirm the tested support envelope still matches the committed benchmark evidence.
- [x] Confirm CI passes from source commit `db6397035561fd33e02cf55ece7249990f058995` ([run 37436739580](https://github.com/raghavkandpal/parison/actions/runs/37436739580)).

## GitHub release

- [ ] Tag the verified commit with the exact package version.
- [ ] Create a GitHub Release from that tag and attach the immutable wheel, source archive and SHA-256 checksums. Do not publish to PyPI for this alpha.
- [ ] Download the wheel from the GitHub Release into an empty environment and repeat the CLI smoke test.
- [ ] Record the release date and move the changelog entries out of `Unreleased`.
