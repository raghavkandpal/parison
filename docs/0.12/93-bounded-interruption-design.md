# Bounded concurrent interruption design

Date: 10 October 2026

Status: **implementation-ready; final 0.12 release gate**

## Observed behavior

An eight-case, 100,000-row keyed suite was interrupted 0.4 seconds after starting with two workers. The parent returned exit 130 only after roughly 6.8 seconds because `ProcessPoolExecutor` waits for active workers during context exit. No requested output was published. After the recovery fix, all eight completed workspace children were verified and checkpointed, and `--resume` produced a verified suite in 0.20 seconds.

This is safe but not bounded early termination: a very long case can delay Ctrl-C for its full remaining runtime.

## Decision

Replace `ProcessPoolExecutor` with a small private spawn-process coordinator built from public `multiprocessing` primitives. Do not expose a scheduler interface and do not add a dependency.

The coordinator owns at most `jobs` `Process` objects and one result queue. Each process still calls the existing `_execute_suite_case` seam and owns one destination. The parent remains the only writer of checkpoints and parent-suite artifacts.

## State machine

Each selected non-reused case has exactly one parent state:

```text
waiting -> running -> published
                   -> crashed
        -> omitted-on-interrupt
running -> terminated-on-interrupt
```

- `published`: the worker returned and its ordinary child bundle verifies.
- `crashed`: the process exited without a valid child; publish generic ERROR evidence and continue admission.
- `terminated-on-interrupt`: terminate and join the process, then preserve a valid atomically published workspace child if one exists; otherwise remove incomplete scratch state.
- `omitted-on-interrupt`: never start the case and do not manufacture evidence for work that did not run.

After interruption, no parent suite bundle is published. Every valid completed workspace child receives its normal checkpoint before exit 130. The next explicit `--resume` decides reuse through the unchanged 0.11 validation contract.

## Bounds

On first KeyboardInterrupt:

1. stop admitting cases;
2. call `terminate()` for every live worker;
3. call `join()` with a short fixed per-pool deadline;
4. call `kill()` only for workers still alive where the supported Python platform exposes it;
5. join again and fail closed if any worker remains alive;
6. verify/checkpoint atomically published workspace children;
7. delete the unpublished parent staging tree; and
8. return exit 130.

The deadline controls process shutdown only. Filesystem verification and checkpoint writes remain bounded by the number of active/completed cases and existing bundle-size limits.

## Acceptance tests

1. A real slow worker receives SIGINT and the parent returns 130 within the documented deadline on Linux, macOS, and Windows.
2. No output directory or parent staging directory survives.
3. A child that published before interruption is reusable; a child terminated before publication is absent.
4. Waiting cases never start.
5. A process that ignores terminate is killed or causes a fail-closed diagnostic without parent publication.
6. Abrupt worker death still becomes generic ERROR evidence during ordinary non-interrupted execution.
7. Jobs 1 retains the released sequential interruption behavior.

## Non-goals

- Cooperative cancellation inside comparison loops.
- Checkpointing partially parsed inputs.
- Retrying terminated or crashed cases automatically.
- Platform-specific signal semantics in the public interface.
- Dynamic worker replacement after parent interruption.

