# Discrepancy analysis guide

Date: 17 October 2026

Use discrepancy analysis after comparison bundles have already been published and verified. It groups released keyed, aggregate and multiset counters without reopening source inputs.

## Analyze one run

```console
parison analyze run-01 --output analysis-01
parison verify-analysis analysis-01
```

`analysis-01/analysis.json` contains every supported reason group, including zero-count groups. Group identifiers are stable for the same comparison mode, kind, classification and logical field or measure name. The output is summary-safe: it contains bundle and policy digests, counts and policy pointers, but no local paths, keys, values or samples.

## Analyze an ordered series

```console
parison analyze run-01 run-02 run-03 --output rehearsal-series
```

The command treats the supplied order as authoritative. Every run must be distinct and use the exact same nonempty `policy_sha256` and comparison mode. Adjacent counts are classified as `introduced`, `resolved`, `increased`, `decreased` or `unchanged`. Parison does not infer timestamps or align runs across different policies.

Runs already recorded in the local catalog can be selected in insertion order:

```console
parison analyze --catalog .parison/catalog.sqlite --policy-sha256 POLICY_SHA256 --output rehearsal-series
```

Catalog selection rejects stale, missing, symlinked or multiply indexed bundle identities instead of analyzing stored metadata.

## Drill into already-published raw evidence

First obtain the exact `group_id` from an analysis, then select from raw-sensitivity bundles:

```console
parison drilldown run-01 run-02 \
  --group-id GROUP_SHA256 \
  --limit 100 \
  --per-run-limit 25 \
  --output drilldown.json
parison verify-drilldown drilldown.json
```

Drill-down never rereads comparison inputs. It selects only matching entries already present in each bundle's bounded `discrepancy_sample`, preserving run and sample order. Its per-run coverage distinguishes the full discrepancy population from the published sample, matched sample and returned subset. Summary-sensitivity bundles are rejected.

The strict canonical drill-down artifact contains raw keys or values and must be handled as sensitive data. It is intentionally separate from the summary-safe analysis bundle, is written atomically without overwrite, and can be checked independently with `verify-drilldown`.

## Interpretation boundary

Reason groups explain which verified counter and declared policy location produced a discrepancy class. They do not establish upstream cause, extraction truth, an approved tolerance, a repair, or cutover authorization. A changed policy requires a new series rather than implicit cross-policy comparison.
