# Signing and evidence-handoff research

Date: 12 October 2026

Status: **design input for Parison 0.17**

## Recommendation

Parison should export one deterministic, unsigned in-toto Statement for a bundle that has already passed `parison verify`. The Statement should bind the SHA-256 digest of the bundle's top-level `manifest.json` and carry a small, safe Parison predicate. Parison should neither create an unsigned DSSE envelope nor implement signing, certificate validation, transparency-log validation, key storage or OIDC.

An external tool should authenticate the exported Statement. The preferred documented integration is Cosign's attestation flow (`attest-blob --statement` and `verify-blob-attestation`) because it produces a DSSE-wrapped in-toto Statement. A simpler `sign-blob`/`verify-blob` example may be provided as a detached-signature interoperability path, but it signs the Statement file as an opaque blob and should not be described as a DSSE attestation.

This boundary gives Parison one responsibility: produce and later validate stable evidence semantics. Existing identity systems retain responsibility for who signed those bytes.

## Standards findings

### DSSE v1

DSSE signs `PAE(UTF8(payloadType), payload)`, not a parsed or reserialized object. Its pre-authentication encoding is the ASCII sequence `DSSEv1`, the byte lengths and the two byte strings separated by spaces. Both the payload type and exact payload bytes are therefore authenticated. `keyid` is only an unauthenticated selection hint and must not drive a security decision. The verifier must pass the same verified payload bytes to the application rather than reparsing the envelope to retrieve another representation. [DSSE protocol v1.0.2](https://github.com/secure-systems-lab/dsse/blob/master/protocol.md)

The recommended JSON envelope contains a base64 payload, a payload type and an array of signatures. It permits multiple signatures, requires consumers to ignore unknown fields, and repeats the exact-byte verification requirement. [DSSE envelope v1.0.2](https://github.com/secure-systems-lab/dsse/blob/master/envelope.md)

Implications for Parison:

- Export exact UTF-8 bytes once and treat the file as immutable signing input. Never ask a signer to reconstruct JSON from a parsed object.
- Define deterministic serialization for reproducibility, but do not claim JSON canonicalization is part of DSSE. DSSE deliberately authenticates bytes and avoids depending on canonicalization.
- Do not emit a DSSE-shaped object with an empty signature list. That is neither authenticated evidence nor a useful handoff artifact.
- Do not expose `keyid` as trusted signer identity.

### in-toto Statement v1

An in-toto Statement v1 has `_type`, `subject`, `predicateType` and an optional `predicate`. Every subject must have a digest. A subject name is contextual, while artifact matching is purely by digest; names and URIs, when present, should be unique. The predicate type is a URI identifying how the predicate is interpreted. [in-toto Statement v1 specification](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md)

The in-toto envelope specification recommends DSSE. For a JSON Statement, its DSSE payload type may be the generic `application/vnd.in-toto+json`; consumers must use the authenticated Statement's `predicateType`, not a media-type hint, to determine predicate semantics. [in-toto envelope specification](https://github.com/in-toto/attestation/blob/main/spec/v1/envelope.md)

The framework requires consumers to ignore unknown fields under its monotonic parsing model, so Parison's predicate should be versioned by its type URI and additions must not make an older consumer turn a denial into an allowance. [in-toto v1 parsing rules](https://github.com/in-toto/attestation/blob/main/spec/v1/README.md)

Implications for Parison:

- Use `_type: "https://in-toto.io/Statement/v1"`.
- Use one subject named `manifest.json` with `digest.sha256` equal to the exact top-level manifest bytes. The existing recursive suite manifest relationship then anchors every covered child manifest without enumerating a second, potentially divergent subject set.
- Use an owned, versioned predicate URI such as `https://parison.dev/attestations/evidence/v1`. Do not publish the URI until Parison can keep it stable and serve or permanently document its schema.
- Make verification two-stage: authenticate the DSSE envelope and signer identity first, then run Parison's semantic checks on the authenticated Statement and the local evidence bundle.

## Proposed canonical export

Suggested filename: `parison-statement.json`.

Suggested logical shape:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {
      "name": "manifest.json",
      "digest": {
        "sha256": "<sha256 of exact top-level manifest.json bytes>"
      }
    }
  ],
  "predicateType": "https://parison.dev/attestations/evidence/v1",
  "predicate": {
    "bundleKind": "run-or-suite",
    "complete": true,
    "outcome": "PASS",
    "parisonVersion": "<producer version>",
    "policy": {
      "sha256": "<effective policy or suite-policy digest>"
    },
    "sensitivity": "summary"
  }
}
```

The final predicate schema should use fields already recovered by verified bundle inspection, never raw discrepancy values. Ordinary and suite bundles need an explicit discriminator and separately specified policy fields rather than overloading one digest. `outcome` is a signed report of the verified bundle's recorded result; it is not an authorization decision. A consumer must still apply its own rule, for example requiring `complete == true`, `outcome == "PASS"`, an approved policy digest and an approved signer identity.

Canonical byte contract:

1. Reject an unsafe, incomplete or integrity-invalid bundle before export.
2. Hash the exact top-level `manifest.json` bytes with SHA-256.
3. Construct only schema-defined Statement and predicate fields; do not include local paths or timestamps.
4. Serialize UTF-8 JSON with lexicographically sorted object keys, compact separators, no ASCII escaping where UTF-8 is valid, and exactly one trailing LF.
5. Refuse to overwrite an existing output and write atomically.
6. On later Parison verification, compare the authenticated subject digest to the local manifest bytes, recursively verify the bundle, and ensure the signed predicate projection equals the projection recomputed from that bundle.

This is a Parison reproducibility contract, not a replacement for DSSE PAE. Tests should include byte fixtures and demonstrate that key order, whitespace, newline, subject digest, predicate type and any signed semantic field changes are detected at the appropriate layer.

## Cosign interoperability

Cosign currently supports `attest-blob --statement`, writes verification material to a bundle, and supports keyless, local-key, KMS and hardware-key signing. Its corresponding verifier accepts a bundle, exact certificate identity or identity regex, OIDC issuer, predicate type, and by default checks that the supplied blob's SHA-256 digest exists in the in-toto subject. [Cosign `attest-blob` CLI](https://github.com/sigstore/cosign/blob/main/doc/cosign_attest-blob.md) [Cosign `verify-blob-attestation` CLI](https://github.com/sigstore/cosign/blob/main/doc/cosign_verify-blob-attestation.md)

The intended external flow is therefore:

```sh
parison statement BUNDLE --output parison-statement.json
cosign attest-blob \
  --statement parison-statement.json \
  --bundle parison-statement.sigstore.json \
  --yes \
  BUNDLE/manifest.json

cosign verify-blob-attestation \
  --bundle parison-statement.sigstore.json \
  --certificate-identity 'EXPECTED_IDENTITY' \
  --certificate-oidc-issuer 'EXPECTED_ISSUER' \
  --type 'https://parison.dev/attestations/evidence/v1' \
  --check-claims=true \
  BUNDLE/manifest.json
```

Exact commands must be acceptance-tested against a pinned Cosign release before documentation ships. As of this research, the current release is v3.1.3. Cosign advisories fixed an attestation-verification false positive in v3.0.6/v2.6.3 and recommend `--check-claims=true`; another recent release fixed a legacy-bundle verification bypass. Parison examples should pin a reviewed v3 release, retain claim checking, and avoid legacy bundles. [Cosign v3.1.3 release](https://github.com/sigstore/cosign/releases/tag/v3.1.3) [CVE-2026-39395 advisory](https://github.com/sigstore/cosign/security/advisories/GHSA-w6c6-c85g-mmv6) [CVE-2026-22703 advisory](https://github.com/sigstore/cosign/security/advisories/GHSA-whqx-f9j3-ch6m)

For opaque detached signing, Cosign recommends storing a Sigstore bundle containing the signature, certificate and transparency-log inclusion proof, then verifying it with the original blob plus an expected identity and issuer. [Sigstore blob-signing guide](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/) [Cosign `verify-blob` CLI](https://github.com/sigstore/cosign/blob/main/doc/cosign_verify-blob.md)

## GitHub Actions keyless identity

A GitHub Actions job needs `permissions: id-token: write` to request an OIDC token; this permission only enables token retrieval and does not itself grant repository or external-resource write access. Reusable workflows outside the caller's organization or enterprise require the caller to grant that permission explicitly. [GitHub Actions OIDC reference](https://docs.github.com/en/actions/reference/security/oidc)

For Sigstore keyless signing in GitHub Actions, the certificate issuer is `https://token.actions.githubusercontent.com`. Sigstore's CI example uses a certificate identity shaped as the exact workflow URL and ref, such as `https://github.com/OWNER/REPOSITORY/.github/workflows/WORKFLOW@refs/heads/BRANCH`. [Sigstore CI quickstart](https://docs.sigstore.dev/quickstart/quickstart-ci/)

Verification policy should therefore:

- Prefer an exact `--certificate-identity` for a pinned workflow file and protected tag or branch.
- If a regex is unavoidable, anchor and escape it; never use `.*` or similarly universal issuer/identity patterns.
- Pin third-party actions by commit and limit job permissions to `contents: read` and `id-token: write` unless another permission is demonstrably required.
- Treat workflow identity as authorization policy outside the Parison Statement. Do not copy ambient OIDC claims into the predicate and then trust those self-reported values.
- Protect the signing workflow and its release environment. An authentic signature from an attacker-modified authorized workflow is still authentic.

GitHub exposes repository, ref, workflow, actor, event and reusable-workflow claims, and permits organizations to customize `sub`; customized formats replace the default subject format. Consequently, consumers must document the expected certificate identity for their actual workflow configuration rather than infer it from repository name alone. [GitHub OIDC claims and subject customization](https://docs.github.com/en/actions/reference/security/oidc#oidc-token-claims)

## Threat model and non-goals

The design should detect:

- modification, removal or substitution of manifest-covered evidence after signing;
- substitution of an unsigned or differently signed Statement;
- a valid signature from a signer outside the consumer's explicit identity/issuer policy;
- predicate, outcome or policy-digest substitution between signing and consumption;
- confusion between Parison evidence and another in-toto predicate type.

It does not prove:

- that the baseline and candidate extracts were complete, contemporaneous or taken at the claimed transaction boundary;
- that a PASS policy was appropriate for the business decision;
- that an authorized workflow or signer was uncompromised;
- confidentiality, freshness, non-revocation or indefinite transparency-log availability;
- that a local path, report filename, wall-clock time or human-readable HTML is meaningful outside the bundle;
- trust merely because a signature is mathematically valid.

Extraction receipts should remain separate, source-owned attestations or manifest-covered inputs. Parison may document how to bind their digests into a future predicate revision, but it should not invent warehouse-specific receipt semantics, connect to source systems, or assert snapshot guarantees it cannot verify.

## Acceptance gates for v0.17

- A fixture proves byte-for-byte deterministic Statement export on every supported platform.
- Export verifies the source bundle first, includes no raw discrepancy evidence or absolute path, writes atomically and never overwrites.
- Run and suite Statements have explicit, schema-validated predicate projections and bind the top-level manifest digest.
- Parison can consume an already-authenticated Statement and reject wrong predicate type, subject cardinality, subject name, digest algorithm, manifest digest, policy projection, outcome projection and bundle integrity.
- CI exercises both a local cryptographic test fixture and a pinned Cosign keyless example where credentials are available; absence of network identity must not weaken local semantic tests.
- Documentation separates four independent checks: signature validity, signer authorization, bundle integrity and gate policy.
- No runtime cryptography, Sigstore, OIDC, certificate or network dependency is added to Parison.

