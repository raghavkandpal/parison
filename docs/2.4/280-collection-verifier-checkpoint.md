# Collection offline verifier checkpoint

Date: 30 October 2026
Status: implementation slice; acquisition and live qualification pending

`parison verify-postgres-collection DIR` now verifies local contract-277
collections without importing Psycopg or connecting to a server. Plan validation
reuses released selection/limit validation and adds bounded private IDs and
unique relations. The verifier pins regular members, bounds enumeration and
metadata/content before hashing, verifies unchanged source-v1 children through
the same handles, reconstructs the plan, checks shared facts/elapsed/totals and
derives the exact compact summary. Regular-file and pinned-directory mutations observed during verification fail.
The evolving live support matrix is not an offline reader dependency.

Tests enforce all seven schema-valid semantic-negative fixtures, exact integer
types, digest-valid false totals/plan/summary, snapshots, shared limits,
noncanonical/extra files, FIFO/symlink rejection, mutation and value-free CLI
errors/interruption. Source-v1 regular-file opening now uses POSIX NONBLOCK to
reject FIFOs without hanging, and enumeration stops after excess membership;
released ordinary bundles and bytes remain unchanged. Full local gate: 587 tests.

No acquisition command or collection live-support claim is introduced. Next:
review/integrate this verifier slice, then implement bounded collection acquisition
through existing ingress/pair helpers and materialize acquisition help/error
fixtures. Prequalify every table before COPY, enforce shared deadlines/budgets,
and run all pending PostgreSQL16.15/17.11/18.6 rows in matrix278. All ten features
remain required before a 2.4 candidate. Never reset account usage automatically.
