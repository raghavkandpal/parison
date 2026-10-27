# Complete reconciliation workflow and typed handoff

Date: 27 October 2026  
Status: contract frozen before feature 6 implementation

The existing reconciliation count verifier is the authority for preserved
evidence. The Workbench accepts explicit local alignment and reconciliation
declarations, dataset recipes and baseline/candidate inputs. Review displays
normalized policy fingerprints, receipt identity and summary-safe input
identities. Execution rechecks reviewed bytes and source identities. A stale
review fails closed. One local job supports cooperative cancellation before
publication; a verified published bundle remains reported as published if later
catalog registration fails. Results/history use verified bundles, and diagnosis
derives fixed reason codes from preserved alignment, parity, reference and
conservation counts without reading source data. No names, paths, values or
tokens appear in summary-safe diagnosis.

## Typed unsigned Statement

Existing run/suite Statement v1 bytes and report bytes remain unchanged.
Reconciliation and dataset-evidence bundles use the existing in-toto Statement
envelope with `predicateType` `https://parison.dev/attestations/evidence/v2`.
The subject is exactly one `manifest.json` SHA-256 digest of the verified outer
bundle. The canonical UTF-8 sorted-key compact JSON ends in one newline.

The v2 predicate has exactly `bundleKind`, `complete`, `outcome`,
`parisonVersion`, `schemaVersion` and `policy`. Reconciliation additionally has
`alignmentSha256`, `receiptSha256`, `coordinationMode`, `coordinationOutcome`,
and `reconciliationSha256`. Its policy is exactly `{kind: reconciliation,
sha256: reconciliationSha256}`. `coordinationOutcome` is the verified alignment
outcome, so a relationship FAIL is never described as ordinary parity.
Dataset evidence has `manifestSha256` and `semanticResult`; its policy is the
verified outer policy `{kind, sha256}`. The semantic result is the verified
outer semantic-result metadata, with no source paths or raw values. V1 and v2
dataset-evidence bundles retain their own schemaVersion.

The verifier reconstructs the expected Statement from the verified local
bundle, compares all fields and binds the subject digest. A Statement is
unsigned; authentication and issuer authorization remain external. Report
cover sheets identify the verified kind, policy, scope/coordination and outcome,
and avoid declaring approval, source truth or cutover readiness. Existing
`statement`, `verify-statement` and `report-cutover` CLI commands accept the
new kinds without altering their prior outputs.

The installed `statement-v2` schema and
`tests/fixtures/statement-reconciliation-v2.canonical.json` pin the typed wire
shape. The fixture demonstrates a reconciliation FAIL with coordination PASS;
the subject and policy digests are illustrative.

Acceptance: parity PASS with orphan/reference and conservation FAIL;
ambiguous parent, forbidden null, parent without children, zero counts and
heuristic INCONCLUSIVE; malformed counts and forged outcomes with recomputed
file digests; stale receipt/input; cancellation and post-publication catalog
failure; source-free diagnosis; typed handoff roundtrip and mismatched subject;
unchanged old Statement byte fixtures; summary disclosure assertions.

Implementation checkpoint: typed reconciliation and dataset-evidence
Statements, source-free local matching, metadata reports, schema registration
and focused roundtrip/forgery tests are present on the feature branch. The
Workbench reconciliation flow and remaining acceptance fixtures are pending.
