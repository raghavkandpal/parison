# Parison 0.5.0 release checklist

Date: 8 October 2026

Status: **not release-ready**. The completed gzip slice is engineering evidence, not the full 0.5 product boundary. Resume release preparation only after the remaining real-world export roadmap is complete.

- [x] Complete the bounded gzip slice without adding archive containers or new dependencies.
- [x] Preserve keyed-v1 outcomes, summary privacy, policy locks and input-change detection.
- [x] Pass 106 local tests, including malformed, high-expansion and mutation cases.
- [x] Pass Python 3.11–3.14 plus macOS and Windows CI.
- [x] Build wheel and source archives from a clean Git archive.
- [x] Install the development wheel into an empty environment and smoke-test gzip preflight, comparison and bundle verification.
- [x] Complete explicit TSV/custom-delimiter policy and evidence.
- [x] Complete reviewed null-token semantics without conflating null and empty strings.
- [ ] Complete drafting, preflight and a combined migration example for the expanded input policy.
- [ ] Set the package version to `0.5.0` and move changelog entries out of Unreleased.
- [ ] Pass CI on the release commit and merge it to `main`.
- [ ] Build, inspect and checksum release archives from the merged commit.
- [ ] Install the release wheel and repeat the compressed-input CLI smoke test.
- [ ] Tag the merged commit `0.5.0` and publish a GitHub prerelease with wheel, source archive and checksums.
