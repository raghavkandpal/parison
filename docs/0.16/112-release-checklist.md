# Parison 0.16.0 release checklist

Date: 12 October 2026

Status: **release candidate**

## Feature and safety gates

- [x] `parison init` produces a runnable summary-only keyed project without overwriting files or following a destination symlink.
- [x] Ordinary and suite failures provide platform-appropriate commands only for evidence operations their bundles support.
- [x] Generic CI, dbt, Airflow and Dagster references keep extraction and credentials outside Parison.
- [x] Integration references verify published evidence before restoring a nonzero comparison outcome.
- [x] The feature adds no runtime dependency, network access, credential handling or new evidence format.

## Review and candidate evidence

- [x] Two-axis review against `origin/main` found one maintainability concern and two specification gaps; all were corrected.
- [x] Manual review corrected the integration filename, Airflow timezone and Dagster two-input dependency examples.
- [x] Post-review local suite: **218 passed, 6 skipped** optional-Polars tests.
- [x] Post-review [GitHub Actions run 38247890734](https://github.com/raghavkandpal/parison/actions/runs/38247890734) passed Python 3.11–3.14, macOS and Windows using built-wheel quickstarts.
- [x] Clean `git archive` candidate `66bec21` produced an inspected wheel and source archive with no repository or local-research state. Wheel SHA-256: `d443429e7f98f67a4507a01bd277e29bf492916edd6f5d980b450b09bdbb9f4f`; source archive: `493ee9b1d2007165a54fdd5ea6fabe8f7c0551d5216a4144265a680f9b251121`.
- [x] A fresh Python 3.12 environment installed the candidate wheel, reported `parison 0.16.0`, and completed init, recipe validation, record preflight, PASS comparison and recursive verification.
- [x] Candidate [GitHub Actions run 38248176578](https://github.com/raghavkandpal/parison/actions/runs/38248176578) passed every supported Python and operating-system lane.

## Publication

- [ ] Merge the reviewed candidate to `main`.
- [ ] Create annotated tag `0.16.0` from the merge commit.
- [ ] Publish wheel, source archive and SHA-256 checksums on the GitHub release.
- [ ] Download the public artifacts, verify checksums and repeat the installed-wheel quickstart.
- [ ] Mark the roadmap, checklist, README and documentation index released.

PyPI publication remains intentionally deferred.
