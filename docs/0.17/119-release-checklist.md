# Parison 0.17.0 release checklist

Date: 13 October 2026

Status: **released**

## Feature and safety gates

- [x] Run, suite and suite-shard Statements bind exact manifest bytes and distinct safe policy projections.
- [x] Canonical Statement bytes are frozen by a checked-in cross-platform fixture and installed schema.
- [x] Export verifies first, publishes atomically and refuses overwrite.
- [x] Semantic verification rejects malformed, ambiguous, substituted, stale and concurrently changed evidence.
- [x] Cutover reports remain deterministic safe projections and name the independent approval boundaries.
- [x] Signing and extraction guidance separates identity, integrity, gate policy and upstream data truth.
- [x] Parison adds no runtime dependency, credential access, cryptography or network behavior.

## Candidate evidence

- [x] Local suite: **230 passed, 6 skipped** optional-Polars tests after release hardening.
- [x] Post-hardening [GitHub Actions run 38251780359](https://github.com/raghavkandpal/parison/actions/runs/38251780359) passed Python 3.11–3.14, macOS and Windows.
- [x] Checksum-verified Cosign v3.1.3 completed local-key sign, bundle verification and Parison semantic rebinding.
- [x] Exact-merge [CI run 38361610482](https://github.com/raghavkandpal/parison/actions/runs/38361610482) passes on `f13fa089f023aedf2b140acac31f2116a165dd7e`.
- [x] [GitHub OIDC run 38361652874](https://github.com/raghavkandpal/parison/actions/runs/38361652874) passes with exact workflow identity and issuer constraints.
- [x] Clean exact-merge artifacts install and complete Statement export, semantic verification and cutover reporting under Python 3.14.

## Publication

- [x] Reviewed candidate merged through [pull request #28](https://github.com/raghavkandpal/parison/pull/28).
- [x] Annotated tag `0.17.0` identifies exact merge `f13fa089f023aedf2b140acac31f2116a165dd7e`.
- [x] [GitHub release 0.17.0](https://github.com/raghavkandpal/parison/releases/tag/0.17.0) publishes the exact-merge wheel, source archive and SHA-256 checksums.
- [x] Public artifacts were re-downloaded, checksum-verified and smoke-tested from a fresh environment.
- [x] Roadmap, checkpoint, checklist, README and documentation index identify 0.17.0 as released.

Published SHA-256:

- `parison-0.17.0-py3-none-any.whl`: `58c3b24a34df1d63def9154b7dac49004dbc087d4cf5317bf652ddae4b01edc8`
- `parison-0.17.0.tar.gz`: `5dddc5a354e0859728850c060a6062d5f9ed86a8f9ffc72ebd3ce3d1d7588881`

PyPI publication remains intentionally deferred.
