# Verified navigator engineering checkpoint

Date: 20 October 2026

Status: **implemented locally; exact-commit CI pending**

## Implemented

- `parison workbench BUNDLE --output DIRECTORY [--open]` runs from the same
  installed Python package as the verification engine.
- `parison.workbench` is a deep module with one publication interface. It
  verifies first, applies a closed summary-safe projection, renders one
  deterministic script-free page, and publishes atomically without replacing.
- The generated application has no dependency, server, remote asset, network
  operation, credential surface, or second interpretation of evidence.
- Focused tests cover deterministic bytes, disclosure exclusions, tamper
  rejection, no-overwrite publication, CLI output, and explicit browser open.

## Preserved

Released recipes, schemas, bundles, canonical bytes, comparison semantics,
exit codes, and CLI JSON are unchanged. The generated page is derived output,
not a new evidence artifact.

## Next gate

Run the complete quality gate and independent Standards/Spec review. After a
green pushed checkpoint, continue the 2.0 train with the schema-driven plan
builder; add a loopback runner only after the shared execution interface and
cancellation contract are frozen.
