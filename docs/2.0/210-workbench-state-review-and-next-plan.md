# Workbench state review and next plan

Date: 21 October 2026

Status: **development review; open 2.0 completion gates**

This review records the state of the unreleased Workbench. It does not change
the [unified interface decision](201-unified-workbench-interface-decision.md),
released 1.x contracts, operational policy, or release approval.

## Verified state

- Release 1.9.0 is published. The reviewed checkout was clean at `develop`
  commit `a37a15d01dc6f33930f8a7657f53d8b9ee7a33d7`.
- The unified Workbench contains Plans, Run, Results, History, Investigate and
  Compare activities. Run performs record preflight, in-process comparison,
  atomic publication, bundle verification and catalog registration for one
  explicit recipe and input pair. Its cancellation is cooperative before
  publication; see the [run and history contract](209-workbench-run-history-contract.md).
- The latest code checkpoint, `d1ba0a4a7ec7062e4b6a7206b806f3944624a9a0`,
  passed the complete [built-wheel test workflow](https://github.com/raghavkandpal/parison/actions/runs/39440174683):
  Python 3.11--3.14 on Linux and macOS/Windows platform smoke. The changes
  between that checkpoint and the reviewed head are documentation and workflow
  files, not Workbench implementation files. The reviewed head passed its
  [quality workflow](https://github.com/raghavkandpal/parison/actions/runs/39440995964).
- GitHub showed no open pull requests or issues at review time.
- The local command-reference check and seven focused `test_workbench.py`
  tests passed with Python 3.14. A complete local `make check` was not obtained:
  the default `python` is 3.9, and the available 3.14 installation lacks
  `ruff`, `jsonschema` and optional format dependencies. The local sandbox also
  rejects loopback socket binding used by host tests. These are limits of this
  review environment, not evidence of a product failure or a local full pass.

## Findings and recommendations

### 1. Run does not preserve structured input locators

The Workbench host passes recipe, baseline, candidate and output through the
same workspace-path conversion before execution. A released CLI locator such
as `json:input.json#/rows`, `xml:input.xml#root/item`,
`xlsx:input.xlsx#Sheet1!A1:B2` or `sqlite:input.db#items` becomes an ordinary
absolute workspace path. The input reader then no longer recognizes its
format selector. This was confirmed by calling the host path conversion and
the four locator parsers directly. Existing Workbench run tests cover plain
CSV paths, so they do not catch this mismatch.

Resolve source locators through one explicit, workspace-constrained path,
while keeping recipe and output paths under the existing non-symlink rule.
Add end-to-end tests for each released locator family and a CLI/Workbench
semantic and canonical-artifact parity check. Treat this as a 2.0 Run gap; do
not alter the released locator syntax or permit unrestricted filesystem access.

### 2. Plans remains short of its recorded full-feature gate

Plans can load exact recipe JSON, show effective policy identity, validate
edits through the Python loader and export visibly unapproved drafts. The
[plan-builder contract](199-plan-builder-contract.md) still calls for
schema-derived policy controls, explicit local input locator selection,
round trips across recipe versions 1--6 and unfamiliar-user review. The
current JSON editor does not establish those remaining gates.

Complete the smallest set of controls that represents every policy-affecting
field without hiding defaults or adding a second recipe format. Keep the JSON
source and authoritative loader as the source of truth. Record round-trip,
hostile-input and unfamiliar-user evidence before counting Plans as a complete
2.0 feature.

### 3. Current guidance mixes released and unreleased interfaces

The root README's quickstart installs a 1.8.0 wheel and then invokes the
unreleased unified Workbench. Its Workbench status text still describes the
superseded generated evidence and plan applications. The active documentation
should give separate released-install and source-checkout instructions, and
describe the unified interface that the checkout actually contains. Historical
2.0 prototype contracts should retain their provenance and superseded labels.

## Next completion sequence

1. **Run compatibility fix:** start a scoped `fix/` branch from current
   `develop`; preserve workspace containment and reject traversal and
   symlinks; cover JSON, XML, XLSX and SQLite locators plus plain paths. Gate:
   focused regression tests and CLI/Workbench result and canonical-byte parity.
2. **Plans completion:** start a separate `feature/` branch from updated
   `develop`; finish the remaining [plan-builder gates](199-plan-builder-contract.md)
   using released schemas and the authoritative recipe loader. Gate: all
   policy-affecting controls are explicit, recipe versions 1--6 round trip,
   drafts remain unapproved, and unfamiliar users do not mistake validation
   for approval.
3. **Combined review and interface inspection:** inspect the complete flow in
   a fresh browser session, including rejected inputs, modified evidence,
   cancellation, shutdown and failures between publication and cataloging.
   Complete independent Standards and Spec review against the active 2.0
   contracts. Gate: findings corrected and re-reviewed, with no summary-safe
   disclosure or compatibility regression.
4. **Documentation reconciliation:** update the root quickstart and active
   2.0 guidance for the qualified interface, keeping released instructions
   separate from development-only behavior. Gate: a new user can follow each
   path without installing a wheel that lacks the documented command.
5. **Exact-head qualification:** pass local `make check` with supported Python
   and dependencies, then push each coherent branch and open a pull request
   to `develop`. Qualify packaging, CLI and platform changes with the required
   manual full built-wheel matrix on the exact pull-request head. Consider a
   2.0 candidate only after the three substantial Workbench features and
   combined review satisfy the [release cadence](../CURRENT.md).

No release candidate, tag, publication or cutover approval follows from the
existing CI runs or this review.
