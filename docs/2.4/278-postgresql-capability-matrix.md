# PostgreSQL collection version and capability matrix

Date and primary-source access: 30 October 2026
Status: exact local live lanes qualified at `461b2d5`; feature 1 integrated through PR #121

This matrix is normative for the live adapter in [contract 277](277-postgresql-collection-contract.md).
It separates a target from successful qualification. The current official
[versioning table](https://www.postgresql.org/support/versioning/) lists 16.15,
17.11 and 18.6 as current minors. Local binaries independently report 16.15
and 18.6 (Homebrew); 17.11 was installed for the disposable qualification.
An installed binary is not an executed collection qualification.

## Live server targets

| Exact server / `server_version_num` | Profile | Required fixture | Status / evidence |
| --- | --- | --- | --- |
| 16.15 / `160015` | `postgresql-base-table-only-csv-v1` | six-table full adversarial corpus and 16-table structural probe | qualified local candidate; [33 gates](../../benchmarks/results-2026-10-30-postgresql-collection-16.json) |
| 17.11 / `170011` | same profile | same corpus and probe, without version-specific evaluator branches | qualified local candidate; [35 gates](../../benchmarks/results-2026-10-30-postgresql-collection-17.json) |
| 18.6 / `180006` | same profile | same corpus and probe | qualified local candidate; [35 gates + measurements](../../benchmarks/results-2026-10-30-postgresql-collection-18.json) |

All three rows must pass before feature 1 integrates. Their source acquisition
roles are independent single-server lanes; this does not qualify every ordered
source/target migration pair. New collection support is advertised only after
recording live evidence for these exact targets. Runtime promotion of the live
allowlist is part of the feature's reviewed implementation commit, after those
tests. A private test harness may exercise pending rows; public CLI must have
no bypass flag, wildcard version range or implicit experimental fallback.

A later minor/major requires a scoped matrix change, primary-source release-note
review, all capability checks and applicable live corpus before promotion.
Changing support metadata does not change an evidence schema unless wire meaning
changes. Future released majors and prerelease builds are rejected by this
live profile until explicitly qualified. Do not promote a version just because
its major sorts between known versions. The live qualification source commit is `461b2d5ec153f016c6ee3c46adcbff101c9f59b7`
on MacBookPro17,1/macOS27.0.1, Python3.14.7 and Psycopg3.3.6.
[Checkpoint 282](282-collection-budget-and-qualification.md) records commands,
reports and machine-specific measurements. Final platform CI remains separate.

## Mandatory capability checks, independent of version

| Capability | Required observation / fail-closed behavior |
| --- | --- |
| Transaction | one connection; repeatable-read read-only settings; all relation locks before the first snapshot query; identical recorded snapshot for every child |
| Relation/role | permanent ordinary base table, no observed partition/inheritance membership; ONLY selection prevents later attachment expanding scope; pinned pg_catalog search path; exact schema/name; dedicated SELECT-only role; no owner membership, superuser, `BYPASSRLS` or inherited write access; row security off fails rather than silently filtering |
| Key | declared ordered primary key exactly equals valid, ready, immediate nondeferrable server primary key; all key columns selected |
| Representation | built-in supported scalar types only; UTF-8 client, ISO/YMD dates, UTC timestamps, explicit CSV/null marker; collision scan and count/COPY agreement |
| Bounds | reviewed per-child and collection rows/bytes; metadata/staging caps; lock/statement/shared deadline enforcement and all-or-nothing cleanup |
| Offline replay | complete collection verifies with server stopped and Psycopg absent; frozen source/pair/dossier readers and canonical bytes remain unchanged |

No extension-specific types, custom collation semantics, arbitrary transformations
or extension compatibility are inferred from the version row. Exact server
version and observed type/session facts are private receipt fields. Schema,
precision/scale and collation assessment expands in feature 2 under its own
contract; feature 1 may acquire text without approving application collation
or later comparison policy.

## Evidence record required for each promotion

Record source `postgres --version` and actual SQL `server_version_num`, Python
and Psycopg versions, OS/architecture, database encoding and fixture collation,
role setup, table/column/type/PK fixture coverage, fixture seed/version,
qualification commit, command and local report path, live corpus outcomes,
cleanup checks and offline replay result. Retain synthetic reproducible reports
without credentials or production source data. Platform evidence applies to the
actual tested environment only. Local live PostgreSQL tests and the installed-wheel
Python 3.11–3.14 Linux/macOS/Windows matrix are separate claims; both are required.

## Migration project lanes and durable evidence

| Lane | Feature 1 meaning | Later 2.4 combined gate |
| --- | --- | --- |
| 16.15→18.6 | independently qualified collections on both ends | retain 16→18 regression; six-table rehearsal, graph, coverage and project dossier at 100k/250k total rows per side |
| 17.11→18.6 | independently qualified collections on both ends | same six-table project contract and adversarial corpus; no pair-specific evaluator code |

The later transfer fixture must record exact `pg_dump`/restore tool versions,
transfer method and upstream coordination claim. Feature 1 neither transfers
nor compares databases. Existing 2.3 live rehearsal evidence at 16.15→18.6 is
historical evidence for that released contract, not a substitute for these new
collection/project gates. No future pair is supported by implication.

Offline validation does not consult a changing installed-version allowlist or
connect to the source. It checks the recorded profile, exact wire facts and
internal consistency. Old evidence remains readable after live support removal
or upstream end-of-life. Preserve 2.3's fixed 16→18 rehearsal contract rather
than relaxing it to admit 17→18; new pairs use new 2.4 project formats.

PostgreSQL's major versions have a five-year upstream support lifecycle;
that lifecycle is separate from Parison's offline format compatibility.
Review live rows at each Parison release and retain immutable historical
qualification records when rows are retired. A valid locally forged receipt
cannot be treated as proof a listed server was actually used.
[Versioning policy](https://www.postgresql.org/support/versioning/),
[pg_upgrade](https://www.postgresql.org/docs/18/pgupgrade.html),
[pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html).

Feature 1 final head `591f24db806ad445b3a0576eacfea87773471659` passed
quality CI and the [full installed-wheel Python 3.11–3.14 Linux/macOS/Windows matrix](https://github.com/raghavkandpal/parison/actions/runs/41050332917)
before [PR #121](https://github.com/raghavkandpal/parison/pull/121) merged at
`2f4ff188392aa53b4344b3639c4b3db689300e19`. Live-server platform claims remain
limited to the named macOS fixture; portable offline/unit CI is a separate gate.
