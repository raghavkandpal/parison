# Parison 0.5 engineering verification

Date: 8 October 2026

## Current evidence

- The full local suite passes 106 tests on Python 3.14 with Polars 1.44.2 and jsonschema 4.26.0.
- The complete Python 3.11–3.14, macOS and Windows matrix passed for the bounded gzip slice in [run 37736921864](https://github.com/raghavkandpal/parison/actions/runs/37736921864) and its mutation hardening in [run 37737099353](https://github.com/raghavkandpal/parison/actions/runs/37737099353).
- Tests cover mixed gzip CSV/JSON Lines, compressed partitions, recipe drafting, preflight metadata, comparison provenance, malformed streams, high-compression decoded overruns and source mutation during drafting.
- A clean archive of commit `f61c9d4` produced the `0.5.0.dev0` wheel and source archive.
- Installing that wheel without optional dependencies into an empty environment successfully ran version reporting, gzip schema preflight, a gzip-to-gzip PASS comparison and machine-readable bundle verification.

## Boundary

This evidence covers local gzip text inputs only. ZIP archives, other compression codecs, recursive discovery and remote objects remain explicitly unsupported.
