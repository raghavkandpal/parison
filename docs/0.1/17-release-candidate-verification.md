# Release candidate verification: 0.1.0

**Date:** 6 October 2026

**Release commit:** `8b3448f7a0b5789f8f82b72923d2653f9f833229`

**Result:** **PASS and published as the verified [0.1.0 GitHub prerelease](https://github.com/raghavkandpal/parison/releases/tag/0.1.0).**

## Clean local rehearsal

The repository was exported with `git archive` into a fresh temporary directory. Build and installation used separate new Python 3.14 virtual environments; no prior `build`, `dist` or egg-info output was present in the exported source.

`python -m build` produced:

- `parison-0.1.0-py3-none-any.whl` — 15,730 bytes, SHA-256 `91bf3dc9ec8497ffbb0c819f88dbaf92b902da570d4f0467322b300d790ed117`;
- `parison-0.1.0.tar.gz` — 24,719 bytes, SHA-256 `86afcad5c7c9919b0cfab45c4f53169ed15a0cb8f346c1c411bf3b6e6a07e99f`.

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

The merged `main` workflow passed at the tagged release commit on 6 October 2026: [GitHub Actions run 37438338132](https://github.com/raghavkandpal/parison/actions/runs/37438338132).

That workflow builds and tests the wheel with Polars on Ubuntu for Python 3.11, 3.12, 3.13 and 3.14, and runs Python 3.14 optional-Polars smoke tests on macOS and Windows. The local rehearsal independently covered Python 3.14 on arm64 macOS. This remains functional compatibility evidence, not cross-platform performance evidence.

The code and benchmark evidence underlying `docs/0.1/13-tested-support-envelope.md` did not change after the recorded benchmark runs; only documentation and synthetic usability-study fixtures changed before this verification. The documented performance envelope therefore remains the claimed measured envelope.

## Version and changelog

`src/parison/__init__.py` declares `0.1.0`. `CHANGELOG.md` retains the `Unreleased` heading until publication, consistent with the publish step in `RELEASING.md`; its entries describe the candidate contents.

## Published-asset verification

After publication, both archives were downloaded from the GitHub Release and matched `SHA256SUMS.txt`. The published wheel was installed with its Parquet extra into another empty Python 3.14 environment. `parison --version`, recipe validation, the documented example comparison and bundle verification all passed. The release is marked as a prerelease, and no PyPI package was published.

The preliminary name screen supports bounded alpha use but is not a legal opinion or formal trademark clearance. Qualified counsel remains appropriate before material commercial investment or a trademark filing.
