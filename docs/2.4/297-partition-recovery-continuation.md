# Recovery contract integration and continuation

Date: 31 October 2026
Status: contract frozen; feature4 execution not implemented

Feature3 integrated through [PR132](https://github.com/raghavkandpal/parison/pull/132)
at `95d434de117aed800aabbb775a33ef64f8fa97c2`. Its exact source head
`88997d50ae268a2d872d5f7653a2daae77449f58` passed683 local tests, independent
Standards/Spec clearance, [quality41219792891](https://github.com/raghavkandpal/parison/actions/runs/41219792891)
and [manual full built-wheel41219790371](https://github.com/raghavkandpal/parison/actions/runs/41219790371).
The full Python3.11–3.14 Linux/macOS/Windows matrix includes43 hash tests and
actual Windows stage/workspace/cleanup ownership tests. Earlier failed native
runs remain historical diagnostics in [checkpoint294](294-hash-discovery-execution-checkpoint.md).

Feature4 [research295](295-partition-recovery-research.md) and
[contract296](296-partition-recovery-contract.md) integrated through
[PR133](https://github.com/raghavkandpal/parison/pull/133) at
`1dcda1e5181d691e360e6cc39a9823231a5fdc33`. Exact docs head
`6382b74aad467a398015f41097d15f3b43a4a763` passed independent Standards/Spec
review and [quality41220917133](https://github.com/raghavkandpal/parison/actions/runs/41220917133).
Review clarified legitimate-cache byte equality, sole committed journal authority,
fixed-slot replacement discard and interruption-safe abandonment. This was a
documentation gate; it did not implement or qualify retained sessions.

## Bounded mechanical probe

A local one-shot probe used the existing hash engine with10,000 synthetic rows
per side and8 buckets on Darwin27.0.0 arm64,8 logical CPUs, CPython3.14.7.
Fresh execution made8 exact comparisons; reusing the first4 trusted in-memory
results and computing the last4 produced an identical canonical receipt.
Routing was repeated in both runs. Each run staged694,657 file-content bytes;
elapsed times were0.299s and0.236s respectively. These are single local diagnostic
observations, not a capacity or performance promise, and not retained-session
qualification. The ignored local probe is `local-research/partition-session-seam-probe.py`;
its temporary output was `/private/tmp/parison24-session-seam-probe.json`.
Neither probe nor output is needed to read the frozen public contract.

This establishes only that the existing comparison/aggregation seam can consume
legitimate prior results without changing the receipt. It does not implement
persisted children, authentication, kernel ownership, interruption recovery,
shared session budgeting or safe abandonment. A coherently forged cache remains
only integrity-checked prior evidence. Full source-backed verification must
always reconstruct the derivation and reject forged results.

## Exact next gate

Start with `make context`, AGENTS.md, ignored AGENTS.local.md and CURRENT.
Create the next scoped branch from clean current develop. Read295/296 before
editing code. Implement only the structural session gate first:

- Standalone closed schemas for session-v1 journal, partition-checkpoint-v1 child
  and session-result-v1 invocation response; expose through the existing schema
  command, with no new project script or session execution flags yet.
- Canonical synthetic fixtures for range-v1 and hash-v2 in initializing/routed/
  comparing/ready/published/abandoning states, plus preview/abandon/publication
  responses and ordinary final four-file byte references.
- Negative cases for wrong plan/profile/layout/runtime/engine/source binding,
  arithmetic/token substitution, malformed primary journals, incomplete next
  files, committed versus uncommitted children and coherent forgery's weaker
  assurance. Structural schemas do not prove semantic bindings or authenticate
  prior comparison; distinguish those future reader/replay obligations.
- Tests on all four Python minors, independent Standards/Spec review, quality
  and exact-head manual full built-wheel/platform qualification before integration.
  Do not enable retained execution merely because structures validate.

After that gate, deepen pinned session reading/ownership and transitions, then
implement retained execution with full contract296 adversarial qualification.
Keep normal range-v1/hash-v2 JSON, bytes, aliases and cleanup unchanged. Reuse the
corrected native ownership and compatible handle-stamp helpers from discovery;
do not repeat attribute-only Windows pinning or path/handle ctime comparisons.

Feature4 remains incomplete; features1–3 are integrated (3/10). Feature5 workers
follow recovery, not this checkpoint. All ten must integrate and qualify before
any2.4 candidate. Preserve local-first boundaries and the through-v5.0 direction.
No release or rate-limit reset is authorized by this handoff. Check usage and
stop near95%, leaving a scoped pushed checkpoint or clean develop.
