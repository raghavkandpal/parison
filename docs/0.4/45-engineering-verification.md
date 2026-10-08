# Parison 0.4 engineering verification

Date: 8 October 2026

## Current evidence

- The full local suite passes 101 tests on Python 3.14 with Polars 1.44.2 and jsonschema 4.26.0.
- The GitHub Actions matrix passed on commit `eec5b7a` in [run 37735611150](https://github.com/raghavkandpal/parison/actions/runs/37735611150): Python 3.11–3.14 with optional Parquet support plus Python 3.14 macOS and Windows smoke jobs.
- A policy-locked preflight and comparison of the checked-in orders example used effective-policy SHA-256 `f1033e05bf3abd6e5e57041a2b46772cc3811ce2e4a3e2f10ece32947121eb54`. Preflight returned `valid`; comparison returned PASS with one exact and one within-tolerance match.
- Machine-readable bundle verification returned a complete summary manifest whose result, effective recipe and report matched their recorded SHA-256 digests.
- The effective recipe, comparison result, manifest and structured preflight output all passed their installed Draft 2020-12 JSON Schemas.
- A clean isolated build produced the `0.4.0.dev0` wheel and source archive. Installing that wheel into an isolated target exposed all four packaged schemas through `parison schema recipe|result|manifest|preflight`.

## Release boundary

The release commit must set version `0.4.0`, move the changelog entries out of Unreleased, and pass the complete CI matrix again. Release archives must then be built from the merged commit, checksummed and smoke-tested before publication.
