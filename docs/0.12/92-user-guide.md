# Bounded local concurrency user guide

## Run cases concurrently

Start with the released suite-v2 example:

```sh
parison run-suite --plan examples/0.11/scalable-suite.json \
  --jobs 2 --output runs/local-concurrent
parison verify runs/local-concurrent
```

`--jobs` accepts 1 through 16 and defaults to 1. It controls the maximum number of local case processes, not the number of threads within a comparison. Parison may finish cases in any order but always records them in the selected plan order.

Use more than one job only when cases perform enough parsing and comparison work to recover process-startup cost. The first tiny-fixture benchmark found jobs 2 and 4 slower than jobs 1. Measure your suite instead of assuming that the largest value is fastest.

## Understand resource limits

Existing byte, decoded-byte, row, group, and distinct-row limits apply independently to every active case. With `--jobs 4`, peak memory and I/O demand can approach four simultaneous cases. Parison does not inspect the machine and choose a safe value automatically.

Start with 2, observe the complete process tree, and increase only when elapsed time improves without unacceptable memory or storage pressure.

## Combine with selection and external shards

Local jobs run after case/tag selection and optional external shard assignment:

```sh
parison run-suite --plan examples/0.11/scalable-suite.json \
  --tag critical --jobs 2 --output runs/critical

parison run-suite --plan examples/0.11/scalable-suite.json \
  --shard-index 0 --shard-count 2 --jobs 2 \
  --output runs/shard-0
```

External shards remain the cross-machine mechanism. `--jobs` only adds concurrency inside one runner and does not change shard membership or assembly rules.

## Resume a concurrent workspace

```sh
parison run-suite --plan examples/0.11/scalable-suite.json \
  --jobs 2 --workspace .parison-work/scalable \
  --output runs/first

parison run-suite --plan examples/0.11/scalable-suite.json \
  --jobs 2 --workspace .parison-work/scalable --resume \
  --output runs/resumed
```

Before starting workers, Parison verifies each reusable child and checks its version, policy, limits, sample limit, and current input digests. Stale cases are removed and recomputed independently. The final destination remains atomic and no-overwrite.

## Interpret failures

Ordinary PASS, FAIL, INCONCLUSIVE, and ERROR results retain their existing meanings. One non-passing case does not cancel unrelated work. If a worker process exits unexpectedly, Parison publishes generic ERROR evidence for each affected case without copying arbitrary exception text into the summary.

The checked-in [GitHub Actions workflow](../../examples/github-actions/parison-suite-v2.yml) demonstrates both local `--jobs 2` execution and external matrix sharding. Prefer external shards when runners already provide the required parallel capacity or when one machine cannot safely hold multiple active comparisons.

