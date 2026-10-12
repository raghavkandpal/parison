# Evidence Statement contract

Status: **implementation contract**

## Commands

```text
parison statement BUNDLE --output STATEMENT.json
parison verify-statement BUNDLE STATEMENT.json
```

`statement` verifies the complete bundle before producing a deterministic unsigned in-toto Statement. `verify-statement` accepts only a Statement whose bytes have already been authenticated by a trusted external verifier, then recomputes its Parison semantics from the supplied local bundle.

Neither command creates or verifies a cryptographic signature. Successful `verify-statement` means only that the authenticated Statement describes this integrity-valid bundle.

## Envelope and subject

The JSON object has exactly four top-level members:

- `_type` is `https://in-toto.io/Statement/v1`;
- `subject` contains exactly one subject named `manifest.json`;
- the subject contains exactly one digest, `sha256`, over the exact bytes of the bundle's top-level `manifest.json`;
- `predicateType` is `https://parison.dev/attestations/evidence/v1`;
- `predicate` is the evidence-v1 projection below.

The top-level manifest recursively binds children in suite bundles. Child subjects are deliberately not duplicated in the Statement.

## Evidence-v1 predicate

Every predicate has exactly these common fields:

- `bundleKind`: `run`, `suite` or `suite-shard`;
- `schemaVersion`: the result schema version;
- `outcome`: the recorded Parison outcome;
- `complete`: the recorded execution completeness;
- `parisonVersion`: the producing Parison version recorded in runtime provenance.

A run predicate additionally contains:

- `contract`: `keyed-v1`, `aggregate-v1` or `multiset-v1`;
- `policySha256`: the effective-policy fingerprint, or `null` for a terminal result that could not establish one;
- `sensitivity`: `summary` or `raw`.

A suite or suite-shard predicate additionally contains:

- `suiteVersion`;
- `suitePolicySha256` for suite-v2 evidence, or `null` for legacy suite-v1 evidence;
- `scopeComplete`, using the explicit suite-v2 field and the legacy `complete` meaning for suite-v1.

These are signed reports, not authorization decisions. Consumers decide which outcome, completeness, policy fingerprint, suite scope and signer identity are acceptable.

## Canonical bytes and publication

The Statement is encoded as UTF-8 JSON with object keys sorted lexicographically, compact `,` and `:` separators, non-ASCII characters encoded directly, and exactly one trailing LF. Arrays retain contract order.

Export creates missing parent directories, stages a regular file beside the target, atomically publishes it and refuses to overwrite any existing path. It includes no bundle path, execution time, source path, source value or discrepancy sample.

## Semantic verification

`verify-statement` reads a regular, non-symlink Statement file, validates the exact evidence-v1 shape, verifies the bundle recursively, recomputes the complete Statement, and requires semantic equality. It therefore rejects an incorrect type, predicate type, subject name or cardinality, digest algorithm or value, bundle kind, schema version, outcome, completeness, producer version or policy projection.

JSON whitespace and object-key order are not semantic inputs to this command. External DSSE or blob verification authenticates the exact Statement bytes before Parison parses them. A caller must never authenticate one file and pass different bytes to `verify-statement`.

## Trust boundary

The complete handoff has four independent checks:

1. an external verifier validates the signature and transparency material;
2. the consumer constrains the signer identity and issuer;
3. `parison verify-statement` binds the authenticated claim to an integrity-valid bundle;
4. the consumer applies its own gate policy to outcome, completeness and policy identity.

None of these proves that upstream extracts were complete, contemporaneous or taken at their claimed boundary. Extraction receipts remain source-owned evidence; guidance may bind their digests in a future predicate version only after their semantics are specified.
