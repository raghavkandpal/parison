# Parison 1.1 roadmap

Status: **planned**

## Theme

Make Parison's existing mixed-format behavior an explicit, versioned semantic-scalar contract without changing released 1.x recipes or comparison semantics.

The governing research is [deterministic cross-format semantic projection](137-cross-format-semantic-projection-research.md). It finds that CSV, JSON Lines, SQLite and Parquet already converge at the recipe parser, but the accepted raw representations and Parquet dtype boundary are not yet a stable compatibility promise.

## Scope

1. Specify `semantic-scalar-v1`: the exact source representations admitted for null, string, integer, decimal, float, boolean, date and timezone-aware timestamp recipe domains.
2. Introduce the contract behind an explicit versioned policy boundary. Released recipe versions 1–3 keep their current behavior and canonical bytes.
3. Validate the complete Parquet schema before materialization. Reject nested, binary, time, duration, object/extension, unknown and lossy temporal representations with stable diagnostics.
4. Add a byte-fixture matrix proving equivalent admitted values converge across CSV, JSON Lines, SQLite and Parquet while ambiguous or lossy conversions fail closed.
5. Record projection identity in full evidence without weakening summary safety.
6. Qualify built wheels on Python 3.11–3.14 across Linux, macOS and Windows because the slice touches schema, packaging and optional Polars behavior.

## Non-goals

- schema or type inference;
- file conversion, repair or source extraction;
- nested JSON or Parquet comparison;
- implicit locale, timezone, boolean, epoch, binary or numeric-to-text coercion;
- a new comparison mode, generic value abstraction or dependency;
- reinterpretation of released recipes, bundles, schemas, CLI JSON, exit codes or canonical encodings.

## Delivery order

### 1. Contract

Write the normative projection contract and strict schema change. Define compatibility with legacy recipe versions, accepted raw representations, stable error classes, evidence identity and summary-safe disclosure.

Gate: every conversion is either explicitly admitted, explicitly policy-controlled or rejected; no source representation depends on incidental Python stringification.

### 2. Reader boundary

Deepen the existing parser seam rather than adding a parallel conversion layer. Validate Parquet dtypes before reading rows, preserve the standard-library CSV, JSON Lines and SQLite readers, and keep keyed, aggregate and multiset execution unchanged.

Gate: unsupported or lossy values fail before comparison and no input reader performs writes, network access, repair or orchestration.

### 3. Compatibility corpus

Add positive and negative fixtures for every semantic type and admitted format representation, including null/empty distinctions, numeric bounds and precision, signed zero/non-finite floats, Unicode normalization, timezone offsets, pre-epoch timestamps and sub-microsecond Parquet timestamps.

Gate: admitted equivalents produce identical canonical rows and semantic results; rejected representations produce stable diagnostics; all released compatibility fixtures remain byte-readable.

### 4. Platform qualification and guide

Run the built-wheel matrix, document authoring and upstream-materialization guidance, and record the exact qualified dependency/runtime envelope.

Gate: the complete promotion gate in the research note passes from built wheels and `make check` is green.

## Completion condition

Parison 1.1 is complete only when `semantic-scalar-v1` is narrow, versioned and independently reviewable; mixed-format equivalence is proven by byte fixtures across the supported matrix; ambiguous or lossy projections fail closed; and the stable 1.x compatibility and zero-custody boundaries remain unchanged.
