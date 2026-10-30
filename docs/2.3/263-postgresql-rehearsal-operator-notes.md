# PostgreSQL 16→18 rehearsal operator notes

Date: 29 October 2026
Status: feature 5 integrated through PR #104

This offline workflow evaluates two reviewed acquisition pairs under explicit
scope, policy and upstream coordination claims. A PASS is agreement under those
claims; it authenticates neither extraction nor the external claim and does not
approve a migration or authorize cutover. Indexes, sequences, application
behavior and live replication readiness are outside this two-table scope.

Start with independently reviewed feature 2 acquisition plans and acquire the
PostgreSQL 16 baseline and PostgreSQL 18 candidate outside the verifier. Retain
both private pair directories. Review expected counts independently of the
exports, pin their exact manifests, source-local snapshots, selection digests
and ordered types in the new plan, and explicitly review both recipe policies.
Do not manufacture scope review by copying observed counts into expectations.
The [frozen contract](262-postgresql-rehearsal-contract.md) defines each field.

The two recipes use one integer key, all selected columns, comma CSV and only
`\\N` as the null token (JSON string `"\\N"`). String, decimal and timestamp
semantics remain explicit; database collation does not become local equality.
A new relationship declaration requires identities for both tables, a non-null
order-line reference and exact per-order amount conservation. Its separate
version reuses released relationship evaluation without repurposing released
time-alignment semantics. Inspect installed schemas with `parison schema
postgres-rehearsal-plan`, `postgres-rehearsal-relationships`,
`postgres-rehearsal-receipt`, `postgres-rehearsal-summary` and
`postgres-rehearsal-manifest`.

```sh
parison-rehearsal run --plan rehearsal.json --baseline pg16-pair --candidate pg18-pair --orders-recipe orders.json --lines-recipe order_lines.json --reconciliation relationships.json --claim operator-claim.txt --output rehearsal
parison-rehearsal verify rehearsal --baseline pg16-pair --candidate pg18-pair --orders-recipe orders.json --lines-recipe order_lines.json --reconciliation relationships.json --claim operator-claim.txt
```

The opaque local claim file must match the reviewed SHA-256 when coordination
is `source-owned`. When coordination is `unestablished`, omit `--claim`; local
agreement remains INCONCLUSIVE. Matching omissions against reviewed counts
also remain INCONCLUSIVE, and an established discrepancy takes precedence as
FAIL. Invalid/substituted bindings or malformed data fail closed without a
published result. Exit codes are PASS 0, FAIL 1, invalid input 2, INCONCLUSIVE 3.
The command and verifier print only the closed summary-safe projection.

Treat the output directory as private: it binds source snapshots and policies,
even though its summary excludes names, paths, tokens, keys and values. It
contains the reviewed plan, receipt, summary, manifest and two unchanged
partition discovery children. Use `parison-partitions investigate` with
`rehearsal/discovery/orders` or `rehearsal/discovery/order_lines` and the exact
original recipe and pair CSV files for bounded case evidence. Investigation
remains an explicit separate action; it cannot establish missing coordination.

Verification needs the original local pairs and policy/claim inputs, reruns
all checks and compares canonical bytes. It requires no server or PostgreSQL
driver, but this artifact is not a self-contained portable dossier; that is
feature 6. Publication is atomic and no-overwrite; interruptions remove the
sensitive stage. Keep all six 2.3 capabilities together before release.

The reproducible live gate is `scripts/check_postgres_rehearsal_live.py` with
explicit `--pg16-bin`, `--pg18-bin`, `--rows`, `--repeats`, `--report`, and optional
`--adversarial`. It creates disposable synthetic clusters with private sockets,
uses target-version dump/restore, independently acquires both pairs, reruns
verification after server shutdown, then removes the clusters. It never targets
an existing database. Run only in a suitable development environment with the
optional Psycopg dependency. Measurements and exact-head qualification are
recorded separately; synthetic byte fixtures alone do not qualify the live gate.
