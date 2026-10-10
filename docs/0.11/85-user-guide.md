# Scalable suite user guide

## Inspect and select

Start with the checked-in suite-v2 example:

```sh
parison validate-suite examples/0.11/scalable-suite.json
parison list-suite examples/0.11/scalable-suite.json
parison list-suite examples/0.11/scalable-suite.json --tag critical --json
```

Repeated `--case` values select explicit IDs. Repeated `--tag` values require every tag. Both filters together are conjunctive. Listing validates references and policy locks but does not scan input records.

## Run locally and resume

```sh
parison run-suite --plan examples/0.11/scalable-suite.json \
  --workspace .parison-work/scalable \
  --output runs/scalable

parison run-suite --plan examples/0.11/scalable-suite.json \
  --workspace .parison-work/scalable --resume \
  --output runs/scalable-resumed
```

The second command verifies completed children and recomputes current input digests before reuse. Keep workspaces private: raw-sensitive child bundles remain raw-sensitive there. Output and workspace paths must differ, and neither command overwrites its destination.

## Run external shards

```sh
parison run-suite --plan examples/0.11/scalable-suite.json \
  --shard-index 0 --shard-count 2 --output runs/shard-0
parison run-suite --plan examples/0.11/scalable-suite.json \
  --shard-index 1 --shard-count 2 --output runs/shard-1

parison assemble-suite --plan examples/0.11/scalable-suite.json \
  --input runs/shard-0 --input runs/shard-1 \
  --output runs/assembled
parison verify runs/assembled
```

Shard order on the assembly command does not matter. Missing, duplicate, stale, tampered or mixed-selection shards are rejected. The [GitHub Actions reference](../../examples/github-actions/parison-suite-v2.yml) shows artifact transport; Parison itself remains runner-neutral.

## Export CI summaries

```sh
parison report-ci runs/assembled --format markdown --output summary.md
parison report-ci runs/assembled --format junit --output junit.xml
```

These exports contain case IDs and outcomes, not discrepancy samples. They are convenient CI views, not replacements for the verified bundle.
