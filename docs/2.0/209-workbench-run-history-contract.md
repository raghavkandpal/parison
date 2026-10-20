# Workbench run, history and investigation contract

Date: 20 October 2026

Status: **implemented locally; exact-commit qualification pending**

## User capability

The unified Workbench now closes its first complete local rehearsal loop:

```text
review plan -> preflight -> run -> publish -> verify -> catalog
            -> Results / History / Investigate / Compare
```

Run accepts one existing CLI-native recipe, two explicit inputs and one new
workspace-relative output bundle. It performs authoritative record preflight,
locks the effective policy identity into comparison, invokes the existing
in-process comparison and publication services, verifies the resulting bundle,
then registers only the existing safe catalog projection. The output remains an
ordinary immutable Parison bundle accepted unchanged by the CLI.

History lists Workbench-registered runs in insertion order with only a
workspace-relative bundle locator, outcome, live integrity state and bundle
digest. Compare invokes the existing catalog same-policy gate and returns its
closed safe projection with relative bundle locators. Investigate starts from a
verified run and exposes exhaustive discrepancy classifications as opaque group
IDs, counts, reason codes and top-level policy sections. Its Workbench projection
removes logical field names, source paths, policy values, record keys and
discrepancy samples even though the lower-level analysis artifact supports
broader reviewed policy references.

## Execution and cancellation

One session permits exactly one active run. A second Run request fails rather
than queues or schedules work. The browser receives a closed phase vocabulary:
`preflight`, `comparing`, `publishing`, `verifying`, `cataloging`, `complete`,
`cancelling`, `cancelled` or `error`.

Cancellation is cooperative at the shared input-row boundary used by every
supported format and is checked between comparison and publication. A cancelled
preflight or comparison publishes and catalogs nothing. Once atomic publication
has begun, the run is allowed to finish and the verified bundle is registered;
the interface does not relabel completed evidence as cancelled. Host shutdown
requests cancellation before stopping its listener.

## Boundaries

- No background scheduling, arbitrary command execution or CLI subprocess.
- No automatic workspace scan or general filesystem endpoint.
- No source paths, record keys, field names, values or samples in default
  investigation output.
- No approval, repair, deployment or cutover action.
- No changes to released recipes, schemas, canonical bytes, bundle readers,
  exit codes or CLI JSON.

The completion gate is full local `make check`, hostile route and cancellation
coverage, fresh interface inspection, then exact-commit built-wheel and quality
CI across the supported matrix.

Fresh rendered inspection covered the Run activity at 1280 x 900 and the
documented 390 x 844 narrow-window stress size. The desktop composition retained
its established navigation, field grouping and outcome hierarchy; the narrow
composition had no horizontal overflow and kept primary Run controls above 44
pixels. Navigation remains a desktop control and its 33-pixel narrow-state rows
do not establish mobile support. The Impeccable 4.7.0 source detector reported
no findings, and explicit shutdown left every application control disabled.
