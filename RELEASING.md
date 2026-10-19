# Release procedure

The active version checklist records evidence; this file defines the reusable procedure.

## Release train size

For every release after 1.7.0, accumulate at least three separately reviewable,
substantial feature additions before opening a release candidate. Each feature
must have its own checkable completion gate and green pushed checkpoint.
Documentation-only reconciliation, refactors, defect fixes and test hardening
do not count as one of the three features unless they independently add a
material user capability.

Do not tag or publish a completed individual feature. Keep it on `develop`,
record its checkpoint, and continue building the same release train. Patch
releases remain available only for urgent compatible fixes to an already
published release; they are not a way around the three-feature minimum.

This cadence remains the default through at least v5.0. Select each train from
documented research and reachable repository evidence; do not wait for
real-world approval or production adoption to continue building. Use fresh
blind implementation review and tests where an internal scope decision needs
independent evidence. That evidence may advance a candidate, but it must never
be described as approval of a user's policy, data, migration or cutover.

## Candidate

1. Confirm the active roadmap identifies at least three completed substantial
   features and that version, changelog, checkpoints and checklist agree.
2. Run `make check`; require built-wheel CI on every supported Python and operating-system lane.
3. Review `origin/main...develop` against its contracts and repository invariants; correct every release blocker.
4. Export the candidate with `git archive` into a clean directory; build wheel and source archive there.
5. Inspect contents, hashes and metadata. Install the wheel in a fresh supported-Python environment and exercise the release's primary workflow.
6. Record the exact candidate commit, CI run, artifact hashes and smoke result in the active checklist.

## Merge and publish

1. Merge the reviewed pull request to `main`; require CI on the exact merge commit.
2. Build again from an archive of that merge commit. Never publish pre-merge artifacts.
3. Complete release-specific external gates before tagging.
4. Create annotated tag `VERSION` on the merge commit and push it.
5. Create the GitHub release with wheel, source archive and `SHA256SUMS`. PyPI remains opt-in.
6. Download the public assets, verify checksums, install the wheel fresh and repeat the primary smoke workflow.
7. Record merge, tag, release URL, hashes and public smoke evidence; mark every release document released and merge that update.

A release is complete only when code, tag, public assets and release records identify the same tested commit.
