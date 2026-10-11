# Parison 0.15 roadmap

Status: **active implementation**

## Theme: repeatable operational evidence

Parison 0.14 made exact high-cardinality local comparisons practical at lower peak memory. The next narrow adoption gap is interpretation across repeated migration rehearsals, backfills and dual-run pipeline checks.

0.15 will make the existing zero-custody catalog useful as a local run history without turning it into hosted observability:

1. return insertion-ordered summaries for one exact policy fingerprint;
2. make outcome and discrepancy-count transitions explicit;
3. compare two stored, verified safe projections only when their policies match;
4. expose input content digests—not paths or values—in safe run inspection;
5. document a copyable rehearsal workflow and its limits.

## Acceptance gates

- History is limited to ordinary run bundles with exactly one requested policy fingerprint.
- Ordering is catalog insertion order, not a claim about execution chronology.
- Diff rejects policy mismatch and suite bundles rather than producing misleading output.
- Neither command reads discrepancy evidence or source data.
- Modified and missing live bundle states remain visible; stored metadata is identified as the last verified projection.
- Output is deterministic JSON and adds no dependency or network access.

## Explicit non-goals

- No hosted history, scheduler, alerting or daemon.
- No trend comparison across different policies.
- No timestamps as ordering proof.
- No raw discrepancy diff.
- No claim that matching input digests prove coordinated extraction watermarks.

The direction follows the [real-world application research](../0.14/94-real-world-application-research.md): migration rehearsals and repeated backfills need safe interpretation across runs, while remote connectors and monitoring would expand Parison's trust boundary.
