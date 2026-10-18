# SQLite aggregate execution contract

Status: **implementation contract**

## Selection

`parison compare --engine sqlite` and suite-v2
`{"execution":{"engine":"sqlite","max_temp_bytes":...}}` opt an aggregate
recipe into disk-backed execution. Parison never selects the engine from input
size. `--temp-directory` names only an existing, non-symlink parent for a new
private disposable workspace.

## Semantic equivalence

Every scalar is parsed and normalized under the released recipe before it
enters SQLite. Group identity uses Parison's existing typed encoding. Count,
integer and scaled-decimal sum, min/max, null handling, tolerance and outcome
classification remain Python-owned aggregate-v1 behavior.

For identical inputs and limits, memory and SQLite result JSON must be
byte-identical after removing only:

- `runtime.execution_engine`;
- `runtime.temporary_bytes`; and
- `resource_limits.max_temp_bytes`.

Raw samples retain the released order: baseline-only groups, candidate-only
groups, then common-group measure differences; groups use the existing
tuple-of-string ordering and measures use recipe order.

## Storage and limits

The SQLite database stores normalized group keys and aggregate states and is
sensitive temporary material. Journaling and synchronization are disabled for
the disposable database, `PRAGMA max_page_count` enforces
`--max-temp-bytes`, and the connection closes before recursive cleanup.
Parison offers no temporary-file encryption or secure erasure.

Existing physical/decoded input, row and group limits still apply. A storage
ceiling too small to initialize SQLite, a full database, invalid parent or I/O
failure is a controlled ERROR and cannot publish a complete comparison.

Successful execution records `execution_engine: sqlite`, final
`temporary_bytes` and `max_temp_bytes`. No scratch path enters evidence.

## Non-goals

No automatic engine selection, resumable database, remote SQL service, new
aggregate operator, changed result schema or capacity guarantee is introduced.
