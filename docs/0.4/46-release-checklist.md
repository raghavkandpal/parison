# Parison 0.4.0 release checklist

Date: 8 October 2026

- [x] Complete the 0.4 roadmap without changing keyed-v1 comparison outcomes or weakening summary privacy.
- [x] Pass 101 local tests with optional Parquet and JSON Schema validation support.
- [x] Pass Python 3.11–3.14 plus macOS and Windows CI on the frozen development head.
- [x] Exercise policy-locked preflight, comparison, machine-readable verification and all four schemas end to end.
- [x] Build wheel and source archives and discover all installed schemas from the wheel.
- [x] Set the package version to `0.4.0` and move changelog entries out of Unreleased.
- [ ] Pass CI on the release commit and merge it to `main`.
- [ ] Build and checksum release archives from the merged commit.
- [ ] Install the release wheel and repeat the policy-locked CLI smoke test.
- [ ] Tag the merged commit `0.4.0` and publish a GitHub prerelease with wheel, source archive and checksums.
