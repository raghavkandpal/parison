# Release procedure

The active version checklist records evidence; this file defines the reusable procedure.

## Candidate

1. Confirm version, changelog, roadmap, checkpoint and checklist agree.
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
