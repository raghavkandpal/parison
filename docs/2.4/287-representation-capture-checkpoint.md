# Feature 2 same-snapshot collection-v2 capture

Date: 31 October 2026
Status: source-head tests, live gates and independent reviews passed; exact PR-head CI pending

The offline verifier [286](286-representation-offline-verification.md) merged
through PR #125 at `9b71e64`. Exact source head
`5c314b50c0f4a81fc6b4dddf808fd72f0bb971bf` passed 615 tests, independent
Standards and Spec clearance, [quality](https://github.com/raghavkandpal/parison/actions/runs/41173039673)
and the [full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/41173037237).

This slice enables explicit collection-plan-v2 on the existing
`parison postgres collection --plan FILE --output DIRECTORY` command under
[contract 284](284-representation-assessment-contract.md). No new command,
project script or dependency is added. Existing help/error fixtures still apply.
Collection-plan-v1 keeps its existing source-v2 ONLY output and never executes
representation queries. Source children retain their four source limits; the
fifth representation limit belongs only to the collection-v2 parent.

A separate representation capability allowlist pins PostgreSQL 16.15, 17.11 and
18.6, independently of future CSV-profile promotions. The writer locks and
qualifies all members first, then captures physical/catalog and accessible
information-schema inventories in the same read-only repeatable-read transaction
before COPY. Missing/extra rows, unsupported selected types, non-UTF8 databases,
physical column overflow and impossible normalized observations abort capture.
Unsupported unselected domain identity is retained without inferring semantics.

Every metadata query checks the shared deadline before and after execution,
and its statement timeout is capped by remaining wall time. This prevents a
one-shot cancellation fired during Python processing from allowing a later
long catalog query. A live idle-between-statements expiry gate rejects before
COPY. Each query bounds rows; potentially large catalog locale/version/rule strings
are truncated to one character beyond their scalar cap on the server, then
rejected by byte validation rather than silently accepted as shortened facts.
Native constraints, identity/generated/default flags, default/explicit collation
facts and recorded/actual provider versions retain typed meanings. PG16 versus
PG17/18 catalog differences use fixed profile branches; no dynamic user SQL or
expression evaluation is introduced. Server SELECT/COPY semantics still govern
any selected generated column.

The complete metadata document is validated and checked against its exact byte
budget before any COPY, using fixed-length child digest placeholders. Actual
child manifest digests replace those placeholders after child publication in
private staging. The final metadata digest/byte count is bound into version2
receipt, summary and manifest; the full pinned verifier runs before atomic
no-overwrite publication. Shared row/CSV/deadline limits and cleanup remain.

The existing disposable qualification script gains `--representation`; no
existing cluster or service is used. It retains the full feature 1 adversarial
set and adds inventory mismatch/byte caps before COPY, full native type replay,
signed and excess numeric scale, bounded text/time precision, unsupported
unselected domains, identity/stored/default flags, ICU definitions and observed
provider-version mismatch, PG17/18 builtin observations, PG18 virtual generation
and unvalidated native not-null, plus the physical 100-column cap.
Primary-source review on 31 October corrected contract 284's ambiguous
not-enforced not-null gate: [PG18 CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html)
permits NOT ENFORCED only for CHECK/foreign-key constraints. The live gate
therefore requires PostgreSQL to reject native NOT NULL NOT ENFORCED, rather
than inventing such a source observation. This does not broaden capture or
interpret the explicitly unassessed CHECK/foreign-key semantics. Repeated
100k/250k measurements remain machine-specific evidence, never capacity promises.

Narrow gate: `make test TEST='tests.test_representation_capture tests.test_representation tests.test_postgres_collection_acquisition'`.
Before integration require `make check`, independent Standards/Spec review,
source-head live runs for all three exact targets, and exact PR-head quality plus
full Python 3.11–3.14 Linux/macOS/Windows built-wheel CI. An inherited CSV
qualification or preliminary prototype does not qualify the new profile.

Feature 2 remains incomplete until private proposals, explicit offline assessment,
replay, CLI execution fixtures and both 16→18/17→18 assessment live/adversarial
qualification pass. All ten 2.4 features must integrate and qualify before a
candidate. Capture evidence establishes neither data parity nor approval/cutover
authority.

## Qualified source evidence

Exact source head `0edccd231d948d7eba8ab62762128791a265690b` passed 621 local
tests, independent Standards and Spec clearance, and all disposable live gates:
40 on PostgreSQL16.15, 42 on17.11, 43 on18.6. Raw reports:
[16](../../benchmarks/results-2026-10-31-postgresql16-representation-capture.json),
[17](../../benchmarks/results-2026-10-31-postgresql17-representation-capture.json),
[18](../../benchmarks/results-2026-10-31-postgresql18-representation-capture.json).

The reviewed deadline finding is fixed and the unsupported native constraint
probe returns FeatureNotSupported. Both review axes cleared the corrected head.

Three repeats per row count/version ran sequentially on this machine; database
server memory is excluded from worker RSS. These observations are not universal
capacity or latency promises. Every report records Python, driver, server and
platform. Each run uses six tables; published bytes include metadata and children.

| PostgreSQL version | Rows | Median seconds | Median worker RSS MiB | Published MiB |
| --- | ---: | ---: | ---: | ---: |
| 160015 | 100,000 | 0.249 | 48.2 | 1.61 |
| 160015 | 250,000 | 0.544 | 49.1 | 4.19 |
| 170011 | 100,000 | 0.244 | 48.3 | 1.61 |
| 170011 | 250,000 | 0.548 | 49.2 | 4.19 |
| 180006 | 100,000 | 0.248 | 48.4 | 1.61 |
| 180006 | 250,000 | 0.540 | 49.2 | 4.19 |
