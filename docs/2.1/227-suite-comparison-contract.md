# Repeated suite comparison contract

Date: 22 October 2026  
Status: released in 2.1.0

Compare two explicit local suite bundles after recursively verifying both.
The comparison has a closed, deterministic, summary-safe projection and makes
no new evidence bundle. The selected case IDs and order, selection, suite
policy identity and each member's effective policy identity must match. A
suite shard is accepted only when both sides have the exact same explicit
partial scope; otherwise comparison rejects it. Changed or missing members,
tampered child evidence and mixed run/suite input reject before display.

For each case, show before and after outcome, completeness, bounded counts and
whether input digests agree. Also show aggregate transition counts. A changed
input digest is evidence that the runs read different bytes; it does not
explain cause. Do not expose source paths, record keys, field names, values
or discrepancy samples. PASS remains agreement under the shared explicit
policy, never cutover authorization.

Expose the same service through CLI and Workbench without altering released
`catalog diff` output, old bundle readers or canonical bytes. Tests cover
PASS-to-FAIL, unchanged outcomes with changed inputs, differing case order or
policy, tampered child, mismatched shard scope and CLI/Workbench parity.

No trend forecast, statistical drift, automatic policy migration, signature,
repair or approval is part of this capability. [Expansion research](226-release-train-expansion-research.md),
[suite contract](../0.11/84-scalable-suite-contract.md), [agent contract](../../AGENTS.md).
