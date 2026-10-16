# Parison 1.4 engineering checkpoint

Date: 16 October 2026

Status: **candidate qualified**

## Delivered capability

- `dataset-manifest-v1` binds a reviewed local collection to canonical policy identity, exact regular-file bytes and optional closed directory membership.
- Creation and verification reject traversal, links, aliases, live SQLite sidecars, mutation and undeclared closed-scope members without taking custody of inputs.
- `reproducibility-diagnostic-v1` records a closed runtime vocabulary and compares it informationally; diagnostic differences never change verification outcomes.
- Atomic `dataset-evidence` publication binds the canonical manifest, full verification result, effective policy, diagnostic and a complete verified suite or reconciliation result.
- Standard verification recursively checks semantic evidence; inspection derives its summary-safe projection from the same locked verified snapshot.

## Qualification

- `make check` passes 318 tests with 11 expected optional-Polars skips.
- Independent Standards and Spec reviews report no release blockers.
- Exact implementation checkpoint `e81e92b27cc6823b8a511e41cfda733fd95648da` passed [built-wheel CI run 38895998570](https://github.com/raghavkandpal/parison/actions/runs/38895998570) on Python 3.11–3.14, Linux, macOS and Windows, including dataset-evidence publication, verification and inspection.

## Preserved boundaries

PASS remains agreement under an explicit policy. Manifests do not prove extraction completeness, diagnostics do not approve environments, and dataset evidence does not authorize cutover. Inputs remain local; Parison adds no connectors, credentials, signing, repair or remote orchestration.
