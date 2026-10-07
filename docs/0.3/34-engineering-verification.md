# Parison 0.3 engineering verification

Date: 7 October 2026

## Current evidence

- The full local suite passes 86 tests on Python 3.14 with Polars 1.44.2, covering old recipes and the checked-in 0.2 bundle as well as 0.3 mappings, partitions, normalization and input preflight.
- The GitHub Actions matrix is configured for Python 3.11, 3.12, 3.13 and 3.14 with optional Parquet support on every version, plus Python 3.14 macOS and Windows smoke jobs.
- The full matrix passed on commit `f8c1f3a` in [GitHub Actions run 37589530326](https://github.com/raghavkandpal/parison/actions/runs/37589530326).
- CI smoke commands retain the released example and add schema preflight plus the combined 0.3 migration example.
- A clean `git archive` of commit `63091d3` built `parison-0.3.0.dev0` wheel and source archive on Python 3.14.
- The wheel was installed into an empty virtual environment with its pinned Parquet extra. Installed commands `--version`, `validate-recipe`, `validate-inputs`, `compare` and `verify` completed successfully; the example comparison produced a verified PASS bundle.

## Release boundary

The matrix must pass again on the eventual release commit after its final version and changelog changes. These checks establish engineering readiness only; they do not authorize a tag or publication.
