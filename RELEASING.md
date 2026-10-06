# Release checklist

## Hard blockers

- [ ] Clear the `Parity` and `parity-compare` names for the intended distribution channels.
- [ ] Choose a distribution license, add its `LICENSE` file, and declare it in `pyproject.toml`.
- [ ] Complete at least one unfamiliar-user comparison session and record blocking usability findings.

Do not publish while any hard blocker remains open.

## Candidate verification

- [ ] Confirm the version in `src/parity/__init__.py` and heading in `CHANGELOG.md`.
- [ ] Start from a clean checkout with no generated inputs or prior run directories.
- [ ] Run `python -m unittest discover -s tests -v` on Python 3.11 through 3.14.
- [ ] Run the optional Polars suite on every supported Python version, plus macOS and Windows smoke jobs.
- [ ] Build wheel and source archive with `python -m build`.
- [ ] Install the wheel into an empty virtual environment.
- [ ] Run `parity --version`, `validate-recipe`, example `compare`, and `verify` from the installed wheel.
- [ ] Inspect the wheel and source archive for only intended package, README and metadata files.
- [ ] Confirm the tested support envelope still matches the committed benchmark evidence.
- [ ] Confirm CI passes from the release commit.

## Publish

- [ ] Tag the verified commit with the exact package version.
- [ ] Publish the immutable wheel and source archive from that tag.
- [ ] Install once from the distribution channel and repeat the CLI smoke test.
- [ ] Record the release date and move the changelog entries out of `Unreleased`.
