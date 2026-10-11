# Large local multiset comparison guide

Date: 11 October 2026

Status: **released guide**

Use the SQLite engine when distinct multiset rows are too numerous for the default in-memory counter and local disk is an acceptable sensitive workspace.

```sh
mkdir -m 700 .parison-tmp
parison compare \
  --recipe multiset.recipe.json \
  --baseline old-export.csv \
  --candidate new-export.csv \
  --engine sqlite \
  --max-temp-bytes 10000000000 \
  --temp-directory .parison-tmp \
  --output runs/backfill-check
```

The parent directory must already exist and must not be a symlink. Parison creates and removes a private child inside it. Keep the parent on an encrypted volume when the inputs are sensitive.

For a suite-v2 plan, put execution policy on the multiset case:

```json
{
  "id": "all-rows-exactly-once",
  "recipe": "multiset.recipe.json",
  "baseline": "old-export.csv",
  "candidate": "new-export.csv",
  "tags": ["backfill", "critical"],
  "execution": {
    "engine": "sqlite",
    "max_temp_bytes": 10000000000
  }
}
```

The engine does not coordinate snapshots. Export both inputs at a reviewed cutoff, record intentional filters in the recipe and use aggregate cases first for cheap count and sum coverage. A passing multiset case proves equality only for the supplied normalized rows.

Inspect `result.json` after the run. `runtime.execution_engine` identifies the engine, `runtime.temporary_bytes` records the peak database size and `resource_limits.max_temp_bytes` records the selected ceiling. The published bundle never includes the spill database.
