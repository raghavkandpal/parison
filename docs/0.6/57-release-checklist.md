# Parison 0.6.0 release checklist

Date: 8 October 2026

Status: **release candidate**. Product and development verification are complete; the versioned commit still requires CI, merge and final archive verification before publication.

- [x] Keep schema-only preflight backward-compatible and make full record validation opt-in.
- [x] Apply the reviewed parsing, mapping, normalization and typed-key policy during record validation.
- [x] Report aggregate row, invalid-field, null-key and duplicate-key diagnostics without source values.
- [x] Preserve byte, decoded-byte, row, policy-fingerprint and input-mutation trust boundaries.
- [x] Continue scanning after configured type failures while retaining malformed-source operational errors.
- [x] Pass 122 tests with optional Parquet and JSON Schema support on Python 3.11–3.14, macOS and Windows.
- [x] Set the package version to `0.6.0` and move changelog entries out of Unreleased.
- [ ] Pass CI on the release commit and merge it to `main`.
- [ ] Build, inspect and checksum release archives from the merged commit.
- [ ] Install the release wheel with Polars and repeat schema, record-validation and comparison smoke tests.
- [ ] Tag the verified merge commit as `0.6.0` and publish the GitHub prerelease with wheel, source archive and checksums.
