# Warehouse backfill gate

This synthetic suite models a historical orders backfill. The aggregate case checks row-count and exact scaled-decimal conservation by region. The multiset case then proves that every normalized output row occurs the same number of times, using the opt-in SQLite engine.

```sh
parison run-suite --plan examples/0.14/backfill-suite.json --output runs/backfill-gate
parison verify runs/backfill-gate
```

A PASS proves equality only for these supplied exports under the reviewed recipes. The extractor must still guarantee a common cutoff, the declared full scope and stable settlement or source state. The data is synthetic and this is not a certified migration or accounting control.
