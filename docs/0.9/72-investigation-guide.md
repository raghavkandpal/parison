# Parison 0.9 investigation guide

The first 0.9 workflow operates only on completed local bundles. It never rereads source datasets and cannot turn summary evidence into raw evidence.

## Inspect a verified bundle

```sh
parison inspect run/
```

`inspect` verifies the manifest and returns safe metadata: outcome, completeness, result schema, counts, resource limits, policy fingerprint, runtime and covered bundle files. It does not print discrepancy samples.

## Export raw evidence

Raw evidence must have been explicitly requested when the comparison ran:

```sh
parison export-evidence run/ \
  --classification baseline_surplus \
  --limit 50 \
  --output baseline-surplus.jsonl
```

Exports are bounded, deterministic JSON Lines projections of the already-published sample. They are written atomically and refuse to overwrite an existing file. Summary-sensitivity bundles are rejected. Treat exported files as sensitive because they may contain source values or keys.

Supported classifications include keyed and aggregate evidence (`baseline_only`, `candidate_only`, `within_tolerance`, `different`) and multiset evidence (`baseline_surplus`, `candidate_surplus`).

The export is not a completeness claim about the source dataset: it cannot contain more evidence than the original bounded result sample.
