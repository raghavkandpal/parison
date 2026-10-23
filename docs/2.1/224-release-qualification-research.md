# 2.1 release qualification research

Date and repository-source access: 22–23 October 2026
Status: updated for the complete three-capability train; candidate qualification active

## Finding

The 2.1 train has three separately reviewable capabilities: the integrated
suite plan/rehearsal/unsigned-handoff workflow, repeated suite comparison,
and failed-member investigation. The initial research treated the three steps
of the first workflow as separate features; the [expansion research](226-release-train-expansion-research.md)
corrected that count. All three capabilities now have green pushed checkpoints
and independent review. Candidate artifact, exact-head CI and publication
gates remain separate; fixes or documentation alone do not count toward the
three-feature minimum.
[Train plan](220-workbench-release-train-research-and-plan.md),
[plan contract](221-workbench-suite-plan-contract.md),
[rehearsal contract](222-workbench-suite-rehearsal-contract.md),
[handoff contract](223-workbench-handoff-contract.md),
[comparison contract](227-suite-comparison-contract.md),
[investigation contract](228-suite-investigation-contract.md),
[release procedure](../../RELEASING.md).

## Exact gates

1. Qualify each feature against its contract: focused behavioral and hostile
   input tests, full `make check`, independent Standards and Spec review,
   a green pushed checkpoint, and the required built-wheel matrix on the exact
   pull-request head before integration. The handoff contract additionally
   requires rendered UI review. Feature pull requests target `develop`.
   [Agent contract](../../AGENTS.md), [train plan](220-workbench-release-train-research-and-plan.md),
   [handoff contract](223-workbench-handoff-contract.md).
2. Before a candidate, reconcile the version, changelog, three feature
   checkpoints and a new 2.1 checklist. Run `make check`; review
   `origin/main...develop` against contracts and invariants; correct release
   blockers. Export the exact candidate with `git archive`, build wheel and
   source archive in a clean directory, inspect metadata and hashes, install
   the wheel in a fresh supported-Python environment, and smoke-test the
   primary suite-to-handoff workflow. Record commit, CI run, hashes and smoke
   result. [Release procedure](../../RELEASING.md),
   [2.0 checklist example](../2.0/219-release-checklist.md).
3. Require built-wheel CI on Python 3.11–3.14 across Linux, macOS and Windows
   for the exact candidate head. Pull-request CI runs Linux only; the macOS
   and Windows job excludes `pull_request`, so manually dispatch `test` on
   that head and verify its commit SHA and all lanes. Quality CI is separate.
   [Test workflow](../../.github/workflows/test.yml),
   [quality workflow](../../.github/workflows/quality.yml),
   [agent contract](../../AGENTS.md).
4. Open the release pull request from `develop` to `main`, review and merge,
   then require CI on the exact merge commit. Rebuild artifacts from that
   merge's clean archive, complete any release-specific external gate, tag
   that commit with annotated `2.1.0`, and publish wheel, source archive and
   `SHA256SUMS` in a GitHub release. PyPI publication is opt-in. Re-download
   public assets, verify checksums, install the public wheel fresh, repeat
   the primary smoke, and reconcile the checklist, changelog and current
   release records. [Release procedure](../../RELEASING.md),
   [2.0 checklist example](../2.0/219-release-checklist.md).

## Design consequences, threats and non-goals

- Candidate smoke should cover one explicit local suite selection through
  execution, recursive bundle verification, History, Statement export and
  report export, plus repeated suite comparison and failed-member
  investigation with bounded raw export. Compare exported bytes with the CLI
  where the contracts require parity. This follows the three 2.1 completion
  gates. [Train plan](220-workbench-release-train-research-and-plan.md),
  [rehearsal contract](222-workbench-suite-rehearsal-contract.md),
  [handoff contract](223-workbench-handoff-contract.md).
- A changed member after preview, interrupted execution, tampered child
  bundle, stale handoff digest or destination collision could invalidate the
  claim or leave partial evidence. Keep the existing revalidation, recursive
  verification, atomic no-overwrite publication and cleanup gates in the
  review and smoke evidence. [Train plan](220-workbench-release-train-research-and-plan.md),
  [agent contract](../../AGENTS.md).
- Passing internal checks means agreement under explicit policy. It does not
  establish extraction truth, policy approval, signer identity, migration
  approval or cutover authorization. No credentials, signing, remote
  orchestration, automatic repair or new evidence format belong to this
  train. [Agent contract](../../AGENTS.md),
  [train plan](220-workbench-release-train-research-and-plan.md),
  [handoff contract](223-workbench-handoff-contract.md).

## Historical blocker

At the original research checkpoint, the suite workflow still needed
qualification and there was no 2.1 release checklist recording exact CI,
candidate, merge or public-asset evidence. The [active checklist](225-release-checklist.md)
now tracks the complete train and those gates. [Contracts](221-workbench-suite-plan-contract.md),
[rehearsal](222-workbench-suite-rehearsal-contract.md),
[handoff](223-workbench-handoff-contract.md),
[documentation index](../README.md).
