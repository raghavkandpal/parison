# Workbench plan-builder engineering checkpoint

Date: 20 October 2026

Status: **first slice implemented locally; qualification pending**

## Implemented

- `parison workbench` now has explicit `evidence` and `plan` activities.
- The plan activity accepts every recipe supported by the authoritative loader,
  computes the effective policy fingerprint, and publishes no output for an
  invalid recipe.
- The generated local application embeds the exact input JSON bytes in an
  escaped editor, provides local syntax feedback and downloads an explicitly
  unapproved CLI-native draft.
- The page displays equivalent `validate-recipe` and `compare` commands and
  never presents browser parsing as authoritative policy validation.
- Publication reuses the navigator's atomic, no-overwrite, interruption-clean
  implementation and adds no dependency, server, credential, or network path.

## Verification

Focused tests cover byte-preserving import, hostile HTML escaping, absence of
the source path, authoritative rejection before publication, CLI behavior and
the existing evidence-navigator guarantees.

## Next gate

Pass the full quality and built-wheel matrix, then add schema-derived controls
and an in-process validation seam. Do not introduce the loopback execution host
until the bounded-runner cancellation and request-security contracts are
frozen.
