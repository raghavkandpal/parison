# 2.1 release-train expansion research

Date and repository-source access: 22 October 2026  
Status: research proposal; no new contract or release approval

## Finding

The three current 2.1 slices—suite plan review, bounded suite run, and unsigned handoff—form **one integrated user capability**: rehearse a local multi-dataset gate and carry its evidence away. They share one plan, run, bundle and workflow. Counting its UI steps as three substantial additions is a weak reading of the accepted requirement for at least three separately reviewable features per minor release. The current release checklist should therefore pause before candidate or publication. [Accepted direction](../0.15/104-product-direction-and-release-arc.md), [train plan](220-workbench-release-train-research-and-plan.md), [current contracts](221-workbench-suite-plan-contract.md), [rehearsal](222-workbench-suite-rehearsal-contract.md), [handoff](223-workbench-handoff-contract.md).

The strongest coherent three-feature train is: **(1) the integrated suite rehearsal and handoff already built, (2) policy-locked comparison of repeated suite rehearsals, and (3) explicit bounded investigation of failed suite members.** These deepen successive rungs of the accepted verification ladder. The latter two need their own versioned contracts, implementation, tests, review and green pushed checkpoints before 2.1 qualification.

## Candidate 2: compare repeated suite rehearsals

**Capability.** Select two verified local suite bundles and see a summary-safe, case-by-case change in outcome, counts, completeness and input digest identity under the same effective suite and member policies. This answers whether a repeated migration rehearsal improved, regressed or merely read different inputs. Existing History/Compare handles ordinary runs, while the released catalog diff explicitly rejects suites. A suite comparison is thus a new user capability, not a restyled screen. [Workbench run/history contract](../2.0/209-workbench-run-history-contract.md), [catalog contract](../0.15/101-catalog-history-contract.md), [catalog implementation](../../src/parison/catalog.py).

**Completion gate.** A new shared local service and CLI/Workbench projection compare two recursively verified suites with the same selected case IDs, order, effective suite policy and each member's effective policy. The output is deterministic and summary-safe; changed case outcome/count/completeness/input digests are explicit. Missing, added or reordered cases, changed policies, tampered children and incomplete shards fail closed or receive an explicit incompatibility result. Tests cover PASS-to-FAIL, unchanged results with changed inputs, policy mismatch, tampering and CLI/Workbench parity. Freeze a versioned schema only if publishing a new artifact; otherwise return a strict projection without changing released bytes.

**Threats.** A green delta could be mistaken for migration safety; a changed case set could be silently compared as equivalent; a catalog entry could outlive tampered evidence. Verify both bundles fresh, label the comparison as policy-bound evidence, and reject ambiguous scope. **Non-goals:** trend forecasts, automatic policy migration, statistical drift, cutover approval or new source connectors.

## Candidate 3: bounded suite failure investigation

**Capability.** From a verified failed suite, select one failed member and inspect its existing discrepancy reason groups, then explicitly request a bounded raw sample when needed. The released analysis and drill-down services already support verified ordinary run bundles, while 2.0 Workbench Investigate only renders safe groups for a selected run; 2.1 suite Results currently gives the suite summary. This is a material workflow from broad failure to a specific reason and optional controlled raw evidence. [Analysis implementation](../../src/parison/analysis.py), [verified navigator contract](../2.0/197-verified-navigator-contract.md), [Workbench host](../../src/parison/workbench_host.py).

**Completion gate.** Recursively verify the suite and selected child before presenting a closed summary-safe reason projection. Member selection uses exact case identity, not an arbitrary nested path. An explicit second action invokes the released bounded drill-down for that child, enforces its limits and no-overwrite atomic export, and clearly marks raw values as sensitive. Tests cover multiple failed members, empty groups, unknown member, tampered child, traversal/symlink attempts, limit enforcement and cancellation/failure cleanup. The existing CLI analysis/drill-down bytes and schemas remain unchanged.

**Threats.** Raw values or keys might leak into the default browser view or logs; stale selection might target a changed child; failure messages might expose source paths. Keep the default projection summary-safe, reverify at every entry point, require explicit raw action and keep sensitive content out of URL/query strings and routine errors. **Non-goals:** automatic repair, fuzzy matching, unlimited sample browsing, or interpreting discrepancies as extraction truth.

## Optional fourth feature, only after the three gates

An explicit local **reconciliation gate in Workbench** could expose the released schema-evolution, time-alignment, conservation and relationship checks as one reviewed plan/run workflow. CLI already has `validate-reconciliation`, `explain-reconciliation`, `reconcile` and verified reconciliation inspection. This would be substantial, but it has a larger policy surface and should not delay the tighter three-feature train without a separate feasibility spike and contract. [CLI command surface](../../src/parison/cli.py), [accepted direction](../0.15/104-product-direction-and-release-arc.md).

## Compatibility and sequencing

Preserve old recipes, suite versions, bundles, exit codes, canonical bytes and CLI JSON. Keep policy choices explicit; neither comparison nor investigation approves keys, tolerances, scope, exclusions or repairs. Derive every view from fresh verification and retain local-only, symlink-safe, atomic publication boundaries. [Agent contract](../../AGENTS.md).

First revise the 2.1 train plan and checklist to count integrated rehearsal/handoff as one feature and to remove candidate-ready language. Then freeze a small contract for each added capability, build each on a scoped branch from current `develop`, qualify it independently, and integrate to `develop`. Only after three substantive capabilities have green pushed checkpoints should the release candidate receive exact-head full-matrix qualification. This research proposes scope; it does not claim either new capability is implemented or qualified.
