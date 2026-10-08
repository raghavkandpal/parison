# Parison 0.5 engineering verification

Date: 8 October 2026

## Current evidence

- The full suite passes 116 tests with Polars 1.44.2 and JSON Schema validation.
- Commit `86f94ad` passed Python 3.11–3.14 plus macOS and Windows in [run 37777909652](https://github.com/raghavkandpal/parison/actions/runs/37777909652).
- CI smoke-tested the combined 0.5 example through preflight and comparison on every supported Python version.
- Tests cover plain and gzip CSV, TSV and JSON Lines; files and partitions; delimiter and null-token policy; drafting; preflight and comparison evidence; malformed streams; decoded overruns; and source mutation.
- A clean archive of commit `86f94ad` produced `parison-0.5.0.dev0-py3-none-any.whl` and `parison-0.5.0.dev0.tar.gz`. Their development-verification SHA-256 values are `230c54ae851581016c7ae25660c022900aaf4dacc9bcd1c4d9e63a45293303ce` and `723c094cc286ee86e8845dd8bb6290687e1002b9b9e816f6b8cb8abebcfd2d6f` respectively.
- Archive inspection found only the intended package, four schemas, metadata, license, README and tests.
- Installing the wheel with Polars into an empty environment exposed all schemas, returned `valid` preflight for the combined 0.5 example, produced a two-row PASS comparison and verified its summary-only bundle.
- The combined example's effective-policy SHA-256 is `9725d4ebb0afecce570958814dfa0499b71ed15b36a55ba05aa22dcb78045fc0`.

## Boundary

This evidence covers the complete planned 0.5 product boundary. ZIP archives, other compression codecs, recursive discovery, arbitrary encodings, content sniffing and remote objects remain explicitly unsupported.

The release commit must set version `0.5.0`, move changelog entries out of Unreleased and pass the complete matrix again. Final archives must be built from the merged release commit, so the development hashes above are evidence rather than release checksums.

## Merged release candidate

- Release commit `66f9b34` passed the complete matrix in [run 37778372061](https://github.com/raghavkandpal/parison/actions/runs/37778372061) and all [PR #9](https://github.com/raghavkandpal/parison/pull/9) checks before merging to `main` as `8573954d1c060680f2d5ece4fe4834337f93b326`.
- A clean archive of the merge commit produced `parison-0.5.0-py3-none-any.whl` with SHA-256 `42c2ad5a7dc7d32cff575af312a6341375c8f405d100fdee3d63805a1697e7df` and `parison-0.5.0.tar.gz` with SHA-256 `374b7e7c8eab12b4ba344b732a2ef0dad291c1b4f03a81a954779093da4c7bbe`.
- Archive inspection confirmed the same intended package, schemas, metadata, license, README and tests as the development build.
- Installing the final wheel with Polars 1.44.2 into an empty environment reported version `0.5.0`, exposed all four schemas, returned valid combined-example preflight, produced a two-row PASS and verified the summary-only bundle.
