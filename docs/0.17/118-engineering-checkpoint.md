# Parison 0.17 engineering checkpoint

Date: 12 October 2026

Status: **release candidate**

## Implemented

- `parison statement` exports a deterministic unsigned in-toto Statement only from a recursively verified run, suite or suite-shard bundle.
- Evidence-v1 binds the exact top-level manifest SHA-256 plus a minimal kind-specific projection of outcome, completeness, policy identity and producer contract.
- `parison verify-statement` rejects ambiguous JSON and recomputes every semantic field against a stable manifest-covered result. Signature and identity authentication remain external.
- `parison report-cutover` creates a deterministic safe Markdown cover sheet for human review without source paths, values, discrepancy samples or timestamps.
- The installed Statement schema, canonical checked-in byte fixture, extraction-receipt guidance and pinned Cosign/GitHub Actions reference complete the handoff workflow.
- No runtime dependency, cryptography, OIDC exchange, key handling or network access was added to Parison.

## Verification

- Local suite: **228 passed, 6 skipped** optional-Polars tests in the non-Parquet environment.
- GitHub Actions run [38251780359](https://github.com/raghavkandpal/parison/actions/runs/38251780359) passed Python 3.11–3.14 plus installed-wheel macOS and Windows lanes after Statement source-stability hardening.
- Every platform lane exports, semantically verifies and reports a Statement from an installed wheel. Tests regenerate the checked-in canonical Statement byte for byte.
- A temporary checksum-verified Cosign v3.1.3 binary signed the canonical Statement with a local key into a Sigstore bundle, verified that signature under the explicit no-transparency-log test policy, and then passed `parison verify-statement` against the checked-in bundle.
- The manual GitHub OIDC acceptance workflow pins the Cosign installer action by commit, pins Cosign v3.1.3, constrains verification to its exact `GITHUB_WORKFLOW_REF` and the GitHub issuer, and retains the complete handoff.

## Remaining release gate

Merge the candidate to `main`, dispatch the protected keyless acceptance workflow there, and record its successful run before tagging. Local-key verification proves cryptographic interoperability; only the GitHub run proves the documented OIDC identity path.
