# Parison 0.9 investigation guide

The first 0.9 workflow operates only on completed local bundles. It never rereads source datasets and cannot turn summary evidence into raw evidence.

## Inspect a verified bundle

```sh
parison inspect run/
```

`inspect` verifies the manifest and returns safe metadata: outcome, completeness, result schema, counts, discrepancy count, published sample size and limit, resource limits, policy fingerprint, runtime, bundle digest and covered bundle files. It does not print discrepancy samples. Compare `discrepancy_sample_size` with `discrepancy_count` to see whether the published evidence is truncated.

## Export raw evidence

Raw evidence must have been explicitly requested when the comparison ran:

```sh
parison export-evidence run/ \
  --classification baseline_surplus \
  --kind row \
  --limit 50 \
  --output baseline-surplus.jsonl
```

Exports are bounded, deterministic JSON Lines projections of the already-published sample. The first line is a `_parison_export` provenance record containing the verified bundle digest, result schema, policy fingerprint, filter and limit. They are written atomically and refuse to overwrite an existing file. Summary-sensitivity bundles are rejected. Treat exported files as sensitive because they may contain source values or keys.

Supported classifications include keyed and aggregate evidence (`baseline_only`, `candidate_only`, `within_tolerance`, `different`) and multiset evidence (`baseline_surplus`, `candidate_surplus`). Use `--kind` to select `record`, `field`, `group`, `measure` or multiset `row` evidence. `--name` further selects an exact keyed field or aggregate measure name. All applied filters are recorded in the provenance line.

The export is not a completeness claim about the source dataset: it cannot contain more evidence than the original bounded result sample.
