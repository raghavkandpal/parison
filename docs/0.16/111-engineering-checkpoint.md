# Parison 0.16 engineering checkpoint

Date: 12 October 2026

Status: **release-candidate implementation complete on `develop`**

## Implemented

- `parison init DIRECTORY` creates a deterministic, runnable keyed migration starter in a missing or empty directory and refuses overwrite and symlink destinations.
- The starter contains a valid summary-only recipe, synthetic smoke inputs and explicit validate, preflight, compare and verify commands.
- Failed ordinary comparisons print platform-native verification and inspection commands. Raw-sensitivity failures additionally offer bounded evidence export; summary-only failures do not.
- Non-passing suite and assembled-suite results point to verification, safe inspection and bounded Markdown CI reporting.
- Installed-wheel CI executes the complete generated-project quickstart on Linux, macOS and Windows.
- Tested generic CI, dbt, Airflow and Dagster references preserve the comparison exit code, verify evidence before restoring that code, and keep extraction credentials outside Parison.
- The public GitHub Actions example now pins the 0.15.0 release rather than the obsolete 0.2.0 asset.

## Verification

- Local suite: **218 passed, 6 skipped** optional-Polars tests in the non-Parquet environment.
- Final GitHub Actions run [38218894935](https://github.com/raghavkandpal/parison/actions/runs/38218894935) passed Python 3.11–3.14 plus macOS and Windows after the platform-native command-rendering and symlink-destination corrections.
- The 3.14 Linux lane and both platform lanes created, validated, compared and recursively verified an initialized project from the installed package.
- Integration references are syntax-compiled or structurally checked without adding orchestrator packages to Parison's dependency graph.

## Remaining release gates

1. Build candidate archives from the reviewed commit and repeat the initialized-project workflow in a fresh environment.
2. Require candidate CI to pass every supported Python and operating-system lane.
3. Merge, build from the exact merge commit, tag and publish only after those checks pass.

Do not release from this checkpoint alone.

The subsequent release review found and corrected two acceptance gaps: the generic CI reference now verifies evidence before upload and outcome restoration, and macOS/Windows build and install the wheel before executing the quickstart. Post-review GitHub Actions run [38247890734](https://github.com/raghavkandpal/parison/actions/runs/38247890734) passed all supported lanes.
