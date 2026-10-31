# Feature 3 hash evidence integrity reader

Date: 31 October 2026
Status: implemented; independent review and exact-head CI pending

The [wire gate292](292-key-discovery-wire-checkpoint.md) integrated through
PR [#130](https://github.com/raghavkandpal/parison/pull/130) at `d68e1bb`, after
646 tests, six wire tests on all four Python versions including clean archives,
independent review, [quality](https://github.com/raghavkandpal/parison/actions/runs/41194824995)
and the [full matrix](https://github.com/raghavkandpal/parison/actions/runs/41194822612)
on exact head `2d0c33e52897dfd386be54603d5444d53a4cb5f7`.

This slice admits existing partition-plan-v2 evidence to integrity-only reading
under [contract291](291-composite-key-discovery-contract.md). It does not create
hash evidence, read source CSVs, approve keys or perform exact source-backed
replay. Both new execution paths explicitly fail before source work until the
producer/replay gate is implemented and qualified. Feature3 remains incomplete;
features1 and2 are the two integrated features of the all-ten release train.

The reader opens the root and all four members through existing pinned-read
primitives, enforces regular files and byte caps before parsing, requires exact
canonical LF bytes, validates version/profile/context shapes and all bindings,
then rechecks descriptor stamps and membership. An initial manifest version sniff
is dispatch only: no sniffed data becomes authoritative; the new reader captures
and validates its own pinned manifest and members. Nonblocking regular-file opens
also protect against a raced FIFO. No database driver or network is involved.

Version2 validation reuses the existing arithmetic machinery with explicit
version-dependent fields, bucket labels and copied-source/derived-recipe staged
bytes. Exact JSON token checks apply to counts, limits, versions and indexes.
Summary bytes must reproduce the private receipt's safe projection, so float
substitution cannot exploit Python numeric equality. Foreign well-formed numeric
runtime versions remain integrity-readable without granting execution permission.

Released range-v1 shapes and result bytes are unchanged. Existing single-integer
investigation-v1 explicitly rejects hash-v2 discovery before interpreting upper
bounds or emitting raw evidence. New-version integrity interruption uses a
value-free message and exit130; legacy behavior remains intact.

Narrow gate: `make test TEST='tests.test_partition_hash_reader tests.test_partition_hash_wire tests.test_partition_discovery tests.test_partition_investigation'`.
Tests cover canonical example/CLI aliases, every semantic-negative record after
rehashing its manifest, strict fields/tokens, unfamiliar context, disabled
execution before source I/O, malformed/oversize members, symlinks, interrupted
reads and post-parse mutation. Full tests, independent Standards/Spec review and
exact-head quality/full built-wheel CI are required before integration.

Next implement the private pinned CSV snapshot/recipe admission and sequential
hash producer, then exact-source-backed replay, the complete collision/Unicode/
NULL/duplicate/skew/publication gate and qualification. The existing hash plan
validator must not implicitly enable creation by falling into the range router.
Only after all those gates pass may feature3 be recorded as3/10. No release or
candidate is proposed here.

Local gate:655 repository tests pass under `make check` on Python3.14.7;
all15 reader/wire tests pass on3.11.18,3.12.5,3.13.18 and3.14.7. Path-mode
replacement is checked against pinned file identities when directory descriptors
are unavailable; interruption coverage runs on every platform. These are reader
checks only and do not qualify hash creation or source-backed replay.
