# Release candidate verification: 0.1.0

**Date:** 6 October 2026  
**Source commit:** `db6397035561fd33e02cf55ece7249990f058995`  
**Result:** **PASS for a bounded 0.1.0 release candidate. No tag or package publication was performed.**

## Clean local rehearsal

The repository was exported with `git archive` into a fresh temporary directory. Build and installation used separate new Python 3.14 virtual environments; no prior `build`, `dist` or egg-info output was present in the exported source.

`python -m build` produced:

- `parison-0.1.0-py3-none-any.whl` — 15,551 bytes;
- `parison-0.1.0.tar.gz` — 24,399 bytes.

The wheel was installed into an empty environment with the `parquet` extra. It installed Parison 0.1.0, Polars 1.44.2 and `polars-runtime-32` 1.44.2.

The installed wheel passed:

- `parison --version` (`parison 0.1.0`);
- `parison validate-recipe examples/orders.recipe.json`;
- the documented example comparison (`PASS`);
- `parison verify` on the generated bundle;
- all 48 unit tests, including all four optional Parquet tests.

## Archive inspection

The wheel contains only the four `parison` Python modules plus standard distribution metadata, entry-point metadata and the MIT license. The source archive contains the package, tests, README, license and build metadata. No generated benchmark inputs, study run bundles, credentials, caches or unrelated repository files were present.

## Supported matrix

The merged `main` workflow passed at the source commit on 6 October 2026: [GitHub Actions run 37436739580](https://github.com/raghavkandpal/parison/actions/runs/37436739580).

That workflow builds and tests the wheel with Polars on Ubuntu for Python 3.11, 3.12, 3.13 and 3.14, and runs Python 3.14 optional-Polars smoke tests on macOS and Windows. The local rehearsal independently covered Python 3.14 on arm64 macOS. This remains functional compatibility evidence, not cross-platform performance evidence.

The code and benchmark evidence underlying `docs/13-tested-support-envelope.md` did not change after the recorded benchmark runs; only documentation and synthetic usability-study fixtures changed before this verification. The documented performance envelope therefore remains the claimed measured envelope.

## Version and changelog

`src/parison/__init__.py` declares `0.1.0`. `CHANGELOG.md` retains the `Unreleased` heading until publication, consistent with the publish step in `RELEASING.md`; its entries describe the candidate contents.

## Remaining actions

- Review and merge the name-screen and verification documentation.
- Create the immutable `0.1.0` tag only from the final verified commit.
- Publish wheel and source archive from that tag.
- Install once from the distribution channel and repeat the smoke test.
- Add the release date and move changelog entries out of `Unreleased`.

The preliminary name screen supports bounded alpha use but is not a legal opinion or formal trademark clearance. Qualified counsel remains appropriate before material commercial investment or a trademark filing.
