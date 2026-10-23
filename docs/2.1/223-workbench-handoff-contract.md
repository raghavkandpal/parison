# Workbench verified suite handoff

Date: 22 October 2026  
Status: implemented on `develop`; release qualification pending

Handoff opens a workspace-relative suite or suite-shard bundle only after
recursive integrity verification. It shows the released unsigned Statement's
manifest digest and closed predicate: outcome, completeness, scope, suite policy
identity and producer version. The view does not claim that a signer has been
authenticated or that the policy or cutover is approved.

The operator explicitly chooses a new workspace-relative path for an unsigned
Statement or Markdown cutover report. Each export verifies the bundle again,
requires the manifest digest seen at preview, and uses the released deterministic,
atomic, no-overwrite writer. The Workbench returns only the relative output
path and bound digest. Output paths inside an existing bundle are rejected so
handoff cannot modify verified evidence. The two exports are separate actions so each published
file has an unambiguous result. The receiver must authenticate any detached
signature and decide whether policy, outcome, completeness and scope meet its
own gate.

Completion gate: focused tests cover verified suite preview, byte identity
with CLI Statement and report exports, rejection of a stale preview digest,
and rejection of tampered child evidence. Full `make check`, rendered UI review,
and exact-head CI remain required before integration.

No signing keys, credentials, network calls, approval, cutover action or new
evidence format are added.
