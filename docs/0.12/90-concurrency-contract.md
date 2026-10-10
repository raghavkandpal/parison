# Bounded local concurrency contract

Date: 10 October 2026

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

## Current hardening gate

The implementation covers bounded spawned workers, deterministic reduction, ordinary comparison errors, generic worker-failure evidence, verified child publication, selection/shard composition, and concurrent resume. A real `os._exit` worker-death test proves that the parent completes without hanging, preserves any already valid child, and publishes verifiable generic ERROR evidence for every affected case. The 0.12 release remains blocked until parent interruption during active work proves bounded cleanup and safe resume on Linux, macOS, and Windows.

