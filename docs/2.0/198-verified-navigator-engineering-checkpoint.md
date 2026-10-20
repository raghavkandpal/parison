# Verified navigator engineering checkpoint

Date: 20 October 2026

Status: **implemented and exact-commit CI qualified**

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
- Exact checkpoint `fbb6ea5675fee8bd5ed787aafe4291e6349d441c` passed the
  [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39370931604)
  and the complete
  [built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39370931644)
  on Python 3.11--3.14, including direct Workbench generation and page checks
  on macOS and Windows for every supported Python version.

## Preserved

Released recipes, schemas, bundles, canonical bytes, comparison semantics,
exit codes, and CLI JSON are unchanged. The generated page is derived output,
not a new evidence artifact.

## Next gate

Complete independent Standards/Spec review, then continue the 2.0 train with
the schema-driven plan builder. Add a loopback runner only after the shared
execution interface and cancellation contract are frozen.
