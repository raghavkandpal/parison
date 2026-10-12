# Evidence handoff guide

Parison 0.17 can turn a verified comparison bundle into a deterministic unsigned in-toto Statement. An existing signing system can authenticate those bytes without receiving the source datasets or teaching Parison about keys, certificates or OIDC.

## Create the Statement

```sh
parison verify evidence/cutover
parison statement evidence/cutover --output parison-statement.json
parison schema statement > statement-v1.schema.json
```

The Statement binds the exact SHA-256 digest of `evidence/cutover/manifest.json`. It reports the bundle kind, outcome, completeness, producer version and policy identity. It contains no local paths or discrepancy samples, but these fields remain operational metadata and should receive appropriate access control.

Do not edit, format or recreate the Statement after export. A byte-oriented signer authenticates the exact file, including its trailing newline.

## Authenticate with Cosign

The smallest interoperable workflow treats the Statement as an opaque blob. Provision a reviewed, pinned Cosign release through your normal toolchain; the examples were designed against Cosign v3.1.3. Keyless signing needs network access and an ambient OIDC identity, while Parison itself remains offline.

Sign and retain the generated Sigstore bundle:

```sh
cosign sign-blob \
  --bundle parison-statement.sigstore.json \
  --yes \
  parison-statement.json
```

At the receiving boundary, authenticate the exact Statement file with an explicit identity and issuer before asking Parison to interpret it:

```sh
cosign verify-blob \
  --bundle parison-statement.sigstore.json \
  --certificate-identity 'EXPECTED_IDENTITY' \
  --certificate-oidc-issuer 'EXPECTED_ISSUER' \
  parison-statement.json

parison verify-statement evidence/cutover parison-statement.json
```

For GitHub Actions keyless signing, grant only `contents: read` and `id-token: write` unless the job demonstrably needs more. The standard issuer is `https://token.actions.githubusercontent.com`. Prefer an exact workflow identity such as:

```text
https://github.com/OWNER/REPOSITORY/.github/workflows/evidence.yml@refs/tags/TAG
```

Organizations can customize GitHub's OIDC subject. Record the identity your actual protected workflow emits; do not infer it from the repository name. Pin third-party actions by commit and protect the signing workflow and release environment.

Cosign also supports DSSE in-toto blob attestations. Use that route only when the receiving integration passes the authenticated Statement payload—not a separately reconstructed JSON object—to Parison's semantic check. The opaque-blob workflow above makes this exact-byte boundary explicit.

## Apply the gate

Successful commands establish different facts:

| Check | Establishes | Does not establish |
| --- | --- | --- |
| `cosign verify-blob` | Signature material is valid and matches the required signer identity, issuer and exact Statement bytes | The signer used an appropriate comparison policy |
| `parison verify-statement` | The authenticated Statement exactly describes this recursively integrity-valid bundle | The bundle should authorize a cutover |
| Consumer gate policy | Required outcome, completeness, policy digest and suite scope are present | Upstream extraction truth |
| Extraction controls | Source-owned snapshot or watermark assertions | Parison comparison semantics |

A production gate should normally require `outcome == PASS`, `complete == true`, the reviewed policy fingerprint and, for suites, the expected scope. A valid signature on a FAIL or on an unapproved policy is still valid evidence and still not approval.

## Extraction receipts

Keep a source-owned receipt beside each export when the extraction system can produce one. Useful receipt fields include the source system, immutable snapshot or transaction boundary, extraction query or job identity, row count, content digest and completion status. Protect it according to its metadata sensitivity.

Do not copy an unauthenticated receipt claim into a Parison recipe and treat that as proof. Parison currently records declared snapshot, cutoff, filters and completeness but cannot observe the upstream transaction boundary. A future predicate revision may bind a receipt digest only after the receipt's issuer and semantics are independently specified.

## Failure handling

- If bundle verification fails, quarantine the bundle and do not create or accept a Statement for it.
- If signature verification fails, do not run semantic verification as a substitute.
- If `verify-statement` fails, the authenticated claim and local bundle are not the same evidence.
- If the policy fingerprint, outcome or scope is unexpected, retain the evidence but deny the cutover.

The normative byte and field rules are in the [Evidence Statement contract](115-statement-contract.md). Standards choices and threat boundaries are in the [signing research](113-signing-research.md).
