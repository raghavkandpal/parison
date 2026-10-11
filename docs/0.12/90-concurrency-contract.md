# Bounded local concurrency contract

Date: 11 October 2026

Status: **development contract**

## Invocation

```text
parison run-suite --plan PLAN --output DIRECTORY --jobs N
```

`N` is an integer from 1 through 16. The default is 1 and preserves sequential execution. The option changes scheduling only: it does not alter plan selection, comparison policy, outcome precedence, bundle schemas, or external shard membership.

## Execution

For `N > 1`, Parison starts at most `N` standard-library worker processes using the cross-platform `spawn` start method. Each worker receives one resolved case and publishes one ordinary child bundle to a case-owned destination. Workers do not write the parent result or another case's workspace.

Cases are submitted in selected plan order. They may start and finish in another order. The parent verifies or digests each published child and reduces all case metadata back into selected plan order before it creates the suite result, report, and manifest.

FAIL, INCONCLUSIVE, and ordinary comparison ERROR outcomes do not cancel other cases. An unexpected worker failure becomes a generic summary-safe case ERROR while unrelated cases continue; the original exception text is not published. Parison does not retry a case automatically.

## Resource meaning

Recipe and suite limits remain per case. `--jobs N` bounds active case count; it is not a total CPU, memory, disk, byte, or row limit. Peak resource consumption can approach `N` times the cost of one case. Parison does not infer a safe job count from machine capacity.

External sharding remains the cross-machine mechanism. Local jobs operate only within the cases already assigned by selection and optional shard arguments.

## Workspaces and resume

Every case owns `cases/ID` and `checkpoints/ID.json` within an explicit suite-v2 workspace. Before worker submission, the parent applies the released 0.11 verification, version, policy, limit, sample-limit, and input-digest checks. A reusable case is copied into staging and is not submitted. A stale case is removed and recomputed in its own worker destination.

Checkpoint publication remains a parent operation after the worker has published its ordinary child bundle. Final parent publication remains atomic and no-overwrite.

## Determinism

Given the same current inputs, plan, policy, limits, Parison version, and selected scope:

- case outcomes and child verification are independent of `--jobs`;
- suite case entries and outcome reduction use selected plan order;
- completion timing is not stored in result identity; and
- `--jobs 1`, `2`, and higher values must have equivalent semantic result content.

Runtime metadata may still contain already documented platform and version fields.

## Interruption and failure isolation

The parent owns a private coordinator made only from public `multiprocessing` processes and one-way pipes. On interruption it stops admission, terminates the active set, waits against one pool-wide two-second deadline, kills survivors, and waits against a second two-second deadline. It never publishes the partial parent suite. Valid atomically published workspace children are checkpointed for explicit resume; incomplete children and publication scratch are removed.

An unexpected exception or abrupt `os._exit` becomes a generic summary-safe ERROR child without cancelling unrelated cases. Exception values are not sent across the worker boundary or published. A worker that ignores termination is killed, and a waiting case is never admitted after interruption.

