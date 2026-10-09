# Parison 0.9 roadmap

Date: 9 October 2026

Status: **release candidate**

## Focus: discrepancy investigation

0.9 should make a completed comparison easier to investigate without changing the three proof modes or moving source data off the customer's machine. The release focus is a bounded, deterministic discrepancy workspace built on existing result bundles: filter and export already-published evidence, inspect conservation and policy context, and preserve the summary/raw privacy boundary.

This is deliberately narrower than adding remote inputs, a server or a UI. The static report and CLI remain the interfaces.

## Candidate surface

- `inspect` reads a verified local bundle and prints schema-aware counts, policy and limit evidence.
- `export-evidence` writes a bounded, deterministic JSON Lines or CSV projection of raw discrepancy samples.
- Filters select classification, field/group/row kind and a stable limit; they never reread source inputs or invent missing evidence.
- Summary bundles remain value-free and cannot be upgraded to raw output after publication.
- Every export records the source bundle digest, result schema, policy fingerprint and applied filter.

## Compatibility and safety

- Preserve keyed-v1, aggregate-v2 and multiset-v3 result meanings.
- Read only verified bundles; reject incomplete manifests and unsupported schemas.
- Keep exports customer-side, bounded and atomic.
- Sort by the result's existing deterministic evidence order, never filesystem or hash order.
- Add no runtime dependency and no remote access.

## Ordered implementation

1. Freeze an inspect/export contract with examples for keyed, aggregate and multiset evidence. **Implemented for the initial JSONL slice.**
2. Add schema-aware bundle readers and one shared filter model. **Bundle inspection implemented.**
3. Add deterministic bounded JSONL export; add CSV only if it does not duplicate semantics. **JSONL export implemented.**
4. Add terminal summaries and static-report links without exposing summary values. **Terminal commands and guide implemented; executable links are omitted from static local reports.**
5. Add adversarial tests for tampered manifests, unsupported schemas, limits, ordering and sensitive output. **Implemented.**
6. Add cross-version wheel smoke and a release checkpoint. **Implemented.**

## Deferred

Tolerant row assignment, subset comparison, spill-backed comparison, nested values, expressions, remote inputs, a server and an interactive UI remain separate product decisions.
