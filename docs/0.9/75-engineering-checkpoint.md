# Parison 0.9 engineering checkpoint

Date: 9 October 2026

Candidate commit: `b2f742446e40a4a074e462e26128f9f16e2e0fcf`

## Verification

- 155 local tests pass with six optional dependency skips.
- The candidate [GitHub Actions run](https://github.com/raghavkandpal/parison/actions/runs/37946034446) passes Python 3.11, 3.12, 3.13 and 3.14 on Linux plus Python 3.14 smoke tests on macOS and Windows.
- A clean Python 3.12 environment installed the candidate wheel and passed `--version`, intentional-difference comparison, `verify`, `inspect` and filtered `export-evidence` smoke commands.
- Inspection reported the expected two discrepancies and complete two-item published sample without exposing evidence values.
- Filtered multiset export selected exactly one `baseline_surplus` row and recorded the bundle, schema, policy and filter provenance.
- Wheel and source archive contents contain the intended package, schemas, metadata, license, README and tests.

## Candidate artifacts

- Wheel SHA-256: `c0ba9b91ad671e68bbdaee36c46f016bbec5989c9e2bb5562f161f53f7d29d16`
- Source archive SHA-256: `842d7392ccc18aa144671d253f8732a6d43f202e95ba6aa753c2d0466c9f2606`

These hashes identify the candidate rehearsal artifacts. Release assets must be rebuilt from the tagged commit and published with their own checksums.

## Published release

The final commit [passed the full matrix](https://github.com/raghavkandpal/parison/actions/runs/37946214304), was tagged `0.9.0`, and was published with these verified assets:

- Wheel SHA-256: `d4ad1137157aa395919d1e3a83abb6a2f02350c8063b20846cfd4fbbebbc6d35`
- Source archive SHA-256: `6bac239285060212f5c29ee78ee73127589f118e01106a210eb49c40abe8737b`

Both assets were downloaded from the GitHub release, checked against the published checksum file, and the downloaded wheel repeated the Python 3.12 investigation smoke workflow.

## Scope decision

0.9 freezes verified inspection and bounded JSON Lines evidence export across keyed-v1, aggregate-v1 and multiset-v1 results. CSV export, source rereads, executable static-report actions and remote investigation remain deferred.
