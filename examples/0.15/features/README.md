# Feature-pipeline parity gate

This synthetic suite compares materialized outputs from two feature-pipeline implementations. The keyed case permits one explicitly reviewed decimal tolerance while requiring exact identifiers, counts and categories. The multiset case verifies duplicate-aware occurrence parity for a keyless batch.

```sh
parison run-suite --plan examples/0.15/features/feature-suite.json \
  --output runs/feature-parity
parison verify runs/feature-parity
```

A PASS proves parity only for these supplied feature rows under the reviewed policies. It does not measure statistical drift, training-serving skew across live populations, model quality, extraction-window consistency or upstream correctness. Parison intentionally leaves those responsibilities to the feature platform and purpose-built validation systems.
