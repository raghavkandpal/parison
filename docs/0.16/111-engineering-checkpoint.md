# Parison 0.16 engineering checkpoint

Date: 12 October 2026

Status: **released in 0.16.0 on 12 October 2026**

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

## Release evidence

- Pull request [#26](https://github.com/raghavkandpal/parison/pull/26) merged the reviewed candidate as `09628e8bc56dae38b2f859cf0e1acfdd477fa919`.
- Annotated tag `0.16.0` identifies that merge commit.
- Exact-merge artifacts were published with checksums and re-downloaded; the public wheel passed the complete initialized-project workflow in a fresh Python 3.12 environment.

The release review found and corrected two acceptance gaps: the generic CI reference now verifies evidence before upload and outcome restoration, and macOS/Windows build and install the wheel before executing the quickstart. Post-review GitHub Actions run [38247890734](https://github.com/raghavkandpal/parison/actions/runs/38247890734) passed all supported lanes.
