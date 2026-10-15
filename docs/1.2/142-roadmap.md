# Parison 1.2 roadmap

Status: **released 15 October 2026**

Exact candidate `eb0566899278e337f0818e30d11486ad66fa83b4` passed dual-axis review, the complete local check, built-wheel CI across the supported matrix, clean-archive build and fresh-wheel smoke. [Release 1.2.0](https://github.com/raghavkandpal/parison/releases/tag/1.2.0) identifies tested merge `31eb265b64c01bfa6625364cc3c2e7f6240cb791`; its public assets were checksum-verified and passed the same fresh-wheel smoke workflow.

## Theme

Explain reviewed schema evolution and policy impact without inferring mappings, transforming data or treating compatibility as approval.

The governing research is [versioned schema evolution and meaningful policy diff](141-schema-evolution-and-policy-diff-research.md). The release is one paired capability: `schema-evolution-v1` declares field identity and lineage; `policy-diff-v1` explains how two effective policies differ under that declaration.

## Scope

1. [x] Strict local JSON declaration with baseline-to-candidate direction, immutable never-reused logical field IDs, side-specific physical names, presence/null/default review metadata and unchanged, renamed, added, removed, split or merged change kinds.
2. [x] Safe compilation of unchanged and one-to-one rename entries to the existing mapping model. Added/removed entries are structural review facts; split/merge remains upstream materialization.
3. [x] Deterministic diff of two fully expanded effective policies through a closed versioned path vocabulary.
4. [x] Per-change impact, stable reason codes and overall `ACCEPT`, `DENY` or `INCONCLUSIVE` compatibility assessment that never updates approval state.
5. [x] Exact baseline, candidate, evolution and diff fingerprints, plus full local and summary-safe renderings.
6. [x] Golden canonical fixtures, complete policy-field mutation coverage and task-oriented documentation; candidate qualification is tracked in the [release checklist](146-release-checklist.md).

## Non-goals

- schema discovery, rename guessing or sample-based identity;
- defaults, casts, backfills, splits, merges, repair or an expression language;
- business-equivalence, extraction-truth, approval or cutover claims;
- trend comparison between unequal policy fingerprints;
- registries, credentials, network access or remote orchestration;
- reinterpretation of released recipes, results, bundles, exit codes or catalog behavior.

## Delivery order

### 1. Declaration and canonical identity

Specify and validate the complete `schema-evolution-v1` shape, normalize authoring order, reject identity conflicts and pin canonical bytes plus `evolution_sha256` with golden fixtures.

### 2. Closed policy diff

Compare validated effective policies through explicit known fields; unknown semantic fields fail closed. Emit deterministic changes, impacts, reason codes and `policy_diff_sha256` without reading datasets.

### 3. Compatibility assessment and safe rendering

Implement the narrow classification table, prove that only identity-preserving mappings and already-excluded additions/removals can be accepted, and provide name-free summary output.

### 4. CLI, examples and qualification

Add local commands for full and summary-safe diff, document realistic rename/add/remove and split/merge workflows, then qualify built wheels on Python 3.11–3.14 across Linux, macOS and Windows.

## Completion condition

1.2 is complete only when every released effective-policy field is classified or fails closed, canonical identities are reproducible, unsafe transformations cannot be compiled, summary output discloses no schema details, historical evidence remains byte-compatible and the complete promotion gate in the research note passes.
