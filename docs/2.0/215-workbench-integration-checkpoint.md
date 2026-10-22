# Workbench integration checkpoint

Date: 21 October 2026

Status: **combined implementation qualified; release reviews remain**

All three substantial 2.0 Workbench capabilities are integrated on `develop`:
verified Results and Investigate, schema-driven Plans, and bounded Run with
History and exact-policy Compare. The released 1.9 CLI quickstart is separate
from the unreleased 2.0 source-checkout path.

The combined local `make check` passed 422 tests on Python 3.14 with the
declared test, development, XLSX and Parquet dependencies. The Run status fix
head `57224cb` passed the complete [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39607547089)
on Linux Python 3.11--3.14 and macOS/Windows Python 3.11--3.14, as well as
the pull request quality gate. It merged through PR #59 at `8d9272e`.

A fresh local rendered inspection opened the unified Workbench, observed all
six activities, loaded and validated an example recipe, confirmed visible
schema controls and unapproved-draft wording, submitted missing Run inputs
and observed rejection without publication, then stopped the host and
confirmed application controls were disabled. Source and regression checks
also cover tampered evidence, symlink and traversal rejection, cancellation,
and a verified output that remains outside History when cataloging fails.

Before a 2.0 candidate, conduct an informed human usability review of the
full Plans workflow and fresh independent combined Standards and Spec review.
Correct any findings, then qualify the exact candidate head. This checkpoint
does not authorize a user's policy, extraction, migration or cutover.
