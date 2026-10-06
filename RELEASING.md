# Release checklist

## Hard blockers

- [ ] Clear the `Parison` and `parison` names for the intended distribution channels.
- [x] Choose a distribution license, add its `LICENSE` file, and declare it in `pyproject.toml` (MIT).
- [x] Complete an unfamiliar workflow end to end: two blinded unfamiliar-agent executions completed, followed by human acceptance of the second trial's evidence and recommendation; no blocking usability finding was reported.

Do not publish while any hard blocker remains open.

## Candidate verification

- [ ] Confirm the version in `src/parison/__init__.py` and heading in `CHANGELOG.md`.
- [ ] Start from a clean checkout with no generated inputs or prior run directories.
- [ ] Remove prior `build`, `dist` and `src/*.egg-info` outputs before building release archives.
- [ ] Run `python -m unittest discover -s tests -v` on Python 3.11 through 3.14.
- [ ] Run the optional Polars suite on every supported Python version, plus macOS and Windows smoke jobs.
- [ ] Build wheel and source archive with `python -m build`.
- [ ] Install the wheel into an empty virtual environment.
- [ ] Run `parison --version`, `validate-recipe`, example `compare`, and `verify` from the installed wheel.
- [ ] Inspect the wheel and source archive for only intended package, README and metadata files.
- [ ] Confirm the tested support envelope still matches the committed benchmark evidence.
- [ ] Confirm CI passes from the release commit.

## Publish

- [ ] Tag the verified commit with the exact package version.
- [ ] Publish the immutable wheel and source archive from that tag.
- [ ] Install once from the distribution channel and repeat the CLI smoke test.
- [ ] Record the release date and move the changelog entries out of `Unreleased`.
