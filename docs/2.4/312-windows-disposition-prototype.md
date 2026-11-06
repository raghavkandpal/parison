# Windows handle disposition: isolated native experiment

Date: 6 November 2026
Status: prototype qualification pending; no product runtime change

## Scope and decision gate

This continues [assessment311](311-native-identity-removal-assessment.md),
which integrated through [PR150](https://github.com/raghavkandpal/parison/pull/150)
at `28070bc` from exact source head `379918d`, after independent Standards/Spec
clearance,752 local tests and
[exact-head quality](https://github.com/raghavkandpal/parison/actions/runs/42216025110).
That documentation checkpoint did not qualify a native deletion implementation.

The experiment uses only stdlib ctypes, temporary synthetic files and bounded
subprocesses. It lives in `tests/test_partition_disposition_native.py`, outside the product package. Its purpose is to
observe native handle disposition before choosing a private runtime helper.
It exposes no command or schema, reads no source inputs and changes no final
evidence, session metadata or execution authority. Non-Windows hosts skip the
native experiment explicitly. A local macOS skip is not Windows qualification.

## Candidate and required observations

Open an existing slot with read/attribute/DELETE access, permit read sharing only,
and open reparse objects rather than traversing them. Validate the handled type
and size before marking FileDispositionInfo. Pin the synthetic parent directory
throughout the worker's handle lifetime. Denying write sharing is deliberate:
namespace exclusion alone would not exclude same-size content substitution.
These choices narrow the [Microsoft documented candidate](311-native-identity-removal-assessment.md#primary-sources-and-consequences);
actual kernel behavior remains the experiment's subject.

Require an unpinned control where independent unlink, rename, replacement,
write and truncate operations succeed. With the candidate handle held, require
the independent operations to fail and preserve unrelated entries and committed
primary bytes. Exercise close and process kill before/after disposition and
retry after released ownership. Refuse oversized, directory and reparse slots.
A file-symlink creation privilege failure must be explicit; junction refusal
remains mandatory. Check existing conflicting handles and a compatible reader
held across disposition/close to observe delayed deletion.

## Limits and threats

This experiment is not session discard, atomic journal promotion, abandonment,
retained execution, or feature4 completion. It does not prove all identity,
byte-recognition, storage reservation, root/lock ownership, close-failure, preexisting writable mappings or
interruption obligations of contract296. A native failure blocks that conclusion;
never fall back to pathname removal or infer success from a mocked call.

The POSIX identity-removal gate remains unresolved. No platform exclusion,
fixed-layout change or threat-model relaxation is authorized here. After native
observations, independently review any proposed production helper as its own
scoped change. Before integrating this platform experiment, pass local preflight,
independent Standards/Spec review and exact-head manual full built-wheel
Python3.11–3.14 Linux/macOS/Windows qualification. Record actual observations and
run links rather than predicting qualification. Features1–3 remain integrated
(3/10); all ten and audit307 clarity gates precede2.4 release.

## Local checkpoint

Full local `make check` passes753 tests with six native skips on macOS using
CPython3.14.7 and declared dependencies including Polars. Focused native preflight
passes51 tests with four native skips. Both independent WIP reviews are clear.
These results establish local compatibility only; exact-head reviews and actual
Windows/full matrix results remain required before integration.
