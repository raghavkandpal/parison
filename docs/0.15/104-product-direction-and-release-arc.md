# Product direction and release arc

Date: 11 October 2026

Status: **accepted direction**

## Position

Parison should become the trustworthy verification layer for data changes:

> Before a migration, backfill, rewrite, or cutover ships, Parison produces portable evidence that the old and new outputs agree under an explicit policy.

This is more specific than a general data-diff tool. The primary applications are database and warehouse migrations, pipeline rewrites, historical backfills, financial reconciliation, feature-pipeline parity, and dual-run cutover gates.

## Verification ladder

Product work should strengthen this sequence:

```text
schema and input preflight
    -> aggregate conservation
    -> keyed or multiset parity
    -> repeated rehearsal history
    -> signed cutover evidence
```

Users should be able to start with cheap broad checks and progressively increase confidence without changing tools or surrendering local control.

## Priorities

1. **Own migration and backfill verification.** Optimize the complete workflow from reviewed policy through portable evidence.
2. **Reduce adoption effort.** Provide excellent starter suites, `parison init`, integration guides, actionable failure summaries, and stable automation output.
3. **Make evidence travel.** Add a canonical signing payload, extraction-receipt guidance, verified bundle comparison, and a concise cutover report.
4. **Extend scale carefully.** Prove explicit disk-backed keyed execution before considering aggregate spill or automatic engine selection. Keep distributed orchestration external.

## Intentional boundaries

Do not prioritize a hosted dashboard, embedded database credentials, continuous CDC monitoring, automatic data repair, statistical drift detection, YAML, a desktop UI, a plugin architecture, or fuzzy record matching. These features broaden Parison into other product categories before the core verification workflow demonstrates adoption.

Reconsider a boundary only when repeated user evidence identifies it as an adoption blocker and its correctness and trust implications can be made explicit.

## Suggested release arc

### v0.15 — rehearsal history

- Policy-locked catalog history.
- Safe same-policy run diff.
- Input digest comparison.
- Payout-reconciliation starter suite.
- Optional feature-pipeline parity example if it does not delay contract review.

### v0.16 — fast project adoption

- `parison init` for a minimal migration or backfill project.
- Tested migration, dbt, Airflow, Dagster, and generic CI examples.
- Better terminal summaries with exact next investigation commands.
- A clean-environment quickstart acceptance test.

### v0.17 — evidence handoff

- Canonical domain-separated signing statement.
- Detached-signature workflow using existing CI identity systems.
- Extraction-receipt guidance.
- Concise verified cutover evidence report.

### v0.18 — larger keyed comparisons

- Explicit SQLite-backed keyed engine.
- Semantic equivalence with memory execution.
- Bounded temporary storage and interruption cleanup.
- Honest cross-platform performance and memory evidence.

### v1.0 — stable verification standard

Release 1.0 only when Parison has frozen compatibility guarantees, a polished migration/backfill workflow, stable CI integration, trustworthy signing guidance, proven upgrade compatibility, multiple realistic starter suites, and documented performance envelopes.

## Decision test

Evaluate every proposed feature with one question:

> Does this help a team define, execute, investigate, or independently verify a high-stakes data-change gate?

If yes, it belongs near Parison's center. If it mainly turns Parison into an orchestrator, connector platform, dashboard, or data-cleaning system, it stays outside the core until user evidence proves otherwise.
