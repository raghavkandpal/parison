# Workbench bounded suite rehearsal

Date: 22 October 2026  
Status: implemented on the 2.1 feature branch; qualification pending

After validating a suite in Plans, the operator can bring that exact selection
to Run and choose a new workspace-relative output folder. The host checks the
plan source digest and the bytes of every referenced recipe and input at submission. It
executes one suite locally with one job, bounded by the released suite limits.
The UI reports the number of selected cases completed, can request cooperative
cancellation during input scans, and does not publish a partial suite on that
cancellation path. The released suite runner publishes the immutable bundle;
the Workbench then verifies it before registering a summary-safe catalog entry.
Partitioned input directories use the released source selection and digest
rules, so changed partition contents invalidate a reviewed plan before Run.

History includes verified run, suite and suite-shard bundles in insertion order.
Results verifies any completed suite bundle before showing its closed
summary-safe projection. The Workbench uses the released runner, so equivalent
CLI and Workbench invocations produce byte-identical suite artifacts. A failure
after publication is reported as an error with direction to verify the output
in Results before reusing its path.

This slice does not add scheduling, remote workers, automatic resume, approval,
or a new suite format. Parallel jobs remain a CLI choice; Workbench uses one
job so cooperative cancellation has one bounded path.

Completion gate: focused tests cover stale plan and member rejection, local PASS suite
publication, byte parity with CLI, verified history, and cancellation cleanup.
The full `make check` gate and exact-head CI must pass before integration.
