# Aggregate SQLite execution research

Date: 18 October 2026

Status: **accepted direction**

## Decision

Add explicit SQLite-backed execution for the released `aggregate-v1`
contract. Keyed and multiset comparisons already offer bounded disk-backed
execution; aggregate conservation is the remaining comparison mode whose
group state must stay in Python memory.

This strengthens the verification ladder without adding a new truth claim,
policy language or automatic engine choice. The memory engine remains the
semantic oracle and default.

## Design consequences

- Parse and normalize every input value in Parison before storage.
- Encode group identity with the existing typed length-prefixed encoding;
  SQLite collation and affinity never define equality.
- Store only disposable aggregate state and stream the symmetric group join.
- Preserve released group and measure ordering, classifications, counts,
  samples, policy fingerprints and canonical evidence bytes after removing
  documented operational telemetry.
- Reuse the private spill directory, hard page ceiling, input-change guard and
  cleanup behavior already qualified for keyed and multiset execution.
- Support direct comparison and suite-v2 cases with the same explicit
  `engine: sqlite` selection.

## Threats and non-goals

The spill database contains normalized group values and is sensitive even for
summary output. Parison does not encrypt or preserve it. Disk exhaustion,
invalid temporary parents and database failures must be controlled errors;
handled completion, failure and interruption must clean the workspace.

Automatic engine selection, resume, remote databases, changed aggregate
semantics, new measures and universal capacity claims are out of scope.

## Completion gate

- PASS, FAIL, INCONCLUSIVE, empty, raw and summary cases match memory output
  after removing only engine, temporary-byte and temporary-limit telemetry.
- Direct and suite execution enforce group, row and temporary-byte limits and
  publish verifiable existing result-v2 bundles.
- Deterministic benchmark cases cover low and high cardinality with explicit
  accuracy oracles and machine-specific memory/time/storage measurements.
- `make check` and built-wheel CI pass on Python 3.11--3.14, macOS and Windows.
