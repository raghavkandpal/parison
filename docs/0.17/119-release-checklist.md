# Parison 0.17.0 release checklist

Date: 12 October 2026

Status: **candidate**

## Feature and safety gates

- [x] Run, suite and suite-shard Statements bind exact manifest bytes and distinct safe policy projections.
- [x] Canonical Statement bytes are frozen by a checked-in cross-platform fixture and installed schema.
- [x] Export verifies first, publishes atomically and refuses overwrite.
- [x] Semantic verification rejects malformed, ambiguous, substituted, stale and concurrently changed evidence.
- [x] Cutover reports remain deterministic safe projections and name the independent approval boundaries.
- [x] Signing and extraction guidance separates identity, integrity, gate policy and upstream data truth.
- [x] Parison adds no runtime dependency, credential access, cryptography or network behavior.

## Candidate evidence

- [x] Local suite: **228 passed, 6 skipped** optional-Polars tests.
- [x] Post-hardening [GitHub Actions run 38251780359](https://github.com/raghavkandpal/parison/actions/runs/38251780359) passed Python 3.11–3.14, macOS and Windows.
- [x] Checksum-verified Cosign v3.1.3 completed local-key sign, bundle verification and Parison semantic rebinding.
- [ ] Candidate merge CI passes on the exact `main` commit.
- [ ] GitHub OIDC keyless acceptance passes with exact workflow identity and issuer constraints.
- [ ] Clean candidate artifacts install and complete Statement export, semantic verification and cutover reporting in a fresh environment.

## Publication

- [ ] Reviewed candidate is merged to `main`.
- [ ] Annotated tag `0.17.0` identifies the exact merge commit.
- [ ] GitHub release publishes exact-merge wheel, source archive and SHA-256 checksums.
- [ ] Public artifacts are re-downloaded, checksum-verified and smoke-tested.
- [ ] Roadmap, checkpoint, checklist, README and documentation index identify 0.17.0 as released.

PyPI publication remains intentionally deferred.
