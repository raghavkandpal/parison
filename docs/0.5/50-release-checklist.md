# Parison 0.5.0 release checklist

Date: 8 October 2026

Status: **not release-ready**. The real-world export product slices are complete, but release verification and packaging have not been rerun against the full 0.5 boundary.

- [x] Complete the bounded gzip slice without adding archive containers or new dependencies.
- [x] Preserve keyed-v1 outcomes, summary privacy, policy locks and input-change detection.
- [x] Pass 116 tests with optional Parquet and JSON Schema support, including malformed, high-expansion and mutation cases.
- [x] Pass Python 3.11–3.14 plus macOS and Windows CI on the completed product boundary.
- [x] Build and inspect wheel and source archives from a clean Git archive.
- [x] Install the development wheel with Polars into an empty environment and smoke-test all schemas plus the combined 0.5 preflight, comparison and bundle verification.
- [x] Complete explicit TSV/custom-delimiter policy and evidence.
- [x] Complete reviewed null-token semantics without conflating null and empty strings.
- [x] Complete drafting, preflight and a combined migration example for the expanded input policy.
- [ ] Set the package version to `0.5.0` and move changelog entries out of Unreleased.
- [ ] Pass CI on the release commit and merge it to `main`.
- [ ] Build, inspect and checksum release archives from the merged commit.
- [ ] Install the release wheel and repeat the compressed-input CLI smoke test.
- [ ] Tag the merged commit `0.5.0` and publish a GitHub prerelease with wheel, source archive and checksums.
