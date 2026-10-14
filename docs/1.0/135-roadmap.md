# Parison 1.0 roadmap

Status: **candidate**

## Theme: name the qualified contract stable

Version 0.19 completed the accepted 1.0 readiness gate: historical artifacts remain readable, the complete workflow passes from built wheels across the supported matrix, a direct human completed the workflow without reported confusion, and the compatibility and performance boundaries are explicit. Version 1.0 promotes that surface unchanged.

## Release slice

1. [x] Reconfirm every pre-candidate product and compatibility prerequisite in the [1.0 readiness checklist](../0.19/128-1.0-readiness-checklist.md).
2. [x] Set the package and release records to 1.0.0 without changing runtime behavior.
3. [ ] Pass local checks, exact-candidate CI and fresh-wheel smoke workflows.
4. [ ] Merge the reviewed candidate, pass CI on the exact merge, and publish exact-merge artifacts.
5. [ ] Re-download and verify the public artifacts, repeat fresh-wheel smoke workflows, and reconcile the release records.

## Compatibility boundary

The [0.19 compatibility contract](../0.19/126-compatibility-contract.md) is the 1.x contract. The [consolidated command guide](../0.19/131-user-guide.md) remains authoritative because 1.0 adds no command or behavior to document. The version designation is the only package-level change.

## Non-goals

- New input formats, comparison semantics, execution engines or dependencies.
- Reinterpreting PASS as extraction truth, approval, signer authentication or cutover authorization.
- Treating the major version as permission to break released artifacts or automation.
- Starting `.xlsx` or receipt-binding work before the adoption gates in the [post-1.0 direction research](../0.20/134-post-1.0-direction-research.md) are met.
