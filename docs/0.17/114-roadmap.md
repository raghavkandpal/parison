# Parison 0.17 roadmap

Status: **in progress**

## Theme: evidence handoff

Parison 0.17 makes a verified comparison bundle portable across an organizational boundary. It defines stable evidence semantics that an existing identity system can authenticate, without turning Parison into a certificate authority, key manager or network client.

## Planned slices

1. Export a deterministic, schema-validated in-toto Statement from a verified run, suite or suite-shard bundle. **Implemented.**
2. Recompute and verify the semantics of an already-authenticated Statement against a local bundle. **Implemented.**
3. Document and test detached Sigstore Cosign workflows, including identity-constrained GitHub Actions keyless signing.
4. Document extraction receipts and produce a concise cutover evidence report from verified metadata. **Implemented.**

## Acceptance gates

- Statement bytes are identical across supported platforms and contain no local path, timestamp or raw discrepancy evidence.
- A Statement binds the exact top-level manifest bytes and an explicit Parison predicate type.
- Run and suite predicates expose distinct, minimal policy projections.
- Semantic verification rejects bundle substitution and every signed-field mismatch; it never claims to verify a signature.
- Export is atomic, refuses overwrite and verifies the bundle before creating output.
- External signing examples pin reviewed tooling and require explicit signer identity and issuer policy.
- Documentation separates signer authentication, bundle integrity, gate policy and upstream extraction truth.

## Non-goals

- Cryptography, key storage, OIDC exchange, certificate validation or transparency-log access in Parison.
- Treating a digest, signature or authenticated workflow as approval of a comparison policy.
- Calling comparison evidence SLSA provenance.
- Warehouse-specific extraction connectors or claims that Parison observed a shared transaction boundary.
- Embedding signatures inside a bundle after its manifest has been published.

The supporting standards and threat-model evidence is recorded in [the signing research](113-signing-research.md). The normative first slice is [the Statement contract](115-statement-contract.md).
