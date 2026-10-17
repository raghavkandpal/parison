# Parison 1.5 roadmap

Date: 17 October 2026

Status: **active**

## Objective

Deliver one coherent `discrepancy-analysis-v1` capability that turns verified keyed, aggregate and multiset results into deterministic reason groups, compares those groups across explicitly ordered same-policy rehearsals, and permits bounded drill-down only over raw samples already present in verified bundles.

## Work order

1. Freeze the strict analysis contract, closed reason/group vocabulary, canonical group identity and policy-reference rules.
2. Implement exhaustive per-run adapters for result schemas 1–3 with canonical fixtures and consistency checks against released counters.
3. Implement explicitly ordered same-policy series with introduced, resolved, increased, decreased and unchanged transitions.
4. Add bounded raw drill-down with explicit population/sample coverage and no source rereads.
5. Add strict installed schemas, CLI commands, atomic analysis bundles, standard verification/inspection and a realistic three-run rehearsal.
6. Qualify exact bytes and built wheels on Python 3.11–3.14, macOS and Windows before release.

## Compatibility boundary

Existing recipes, results, bundles, catalog databases, canonical bytes, CLI JSON and exit codes remain unchanged. Analysis is derived evidence: it does not affect comparison outcomes, infer chronology, diagnose upstream causes, recommend repairs or approve policy/cutover decisions.

## Completion gate

The ten-point promotion and completion gate in [the research note](159-discrepancy-analysis-research.md) is normative. Version 1.5 is not releasable until every point passes from built wheels.
