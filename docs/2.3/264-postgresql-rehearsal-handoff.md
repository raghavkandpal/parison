# Feature 5 usage-limit handoff

29 October 2026. Stopped when the five-hour window reported 98% used; no reset
credit consumed. Four of six features are integrated. No release or merge of
feature 5 was performed.

Branch `feature/2.3-postgresql-rehearsal`, based on clean develop
`d057ee918b9eb2964a7138cd87f7d68baa5c7654`. Initial candidate `ecd9558` is pushed
in [PR #104](https://github.com/raghavkandpal/parison/pull/104). Read the latest
branch commit for corrections saved after this candidate; do not qualify the
initial head or infer review approval from this handoff.

Research 261, frozen contract 262 and operator notes 263 are present. New opt-in
CLI composes unchanged pair verification, partition discovery and SQLite
relationship/conservation evaluators. A separate relationship declaration
avoids reinterpreting released time-alignment fields. Schemas and canonical
fixtures are installed. Initial `make check` passed 553 tests with the Python
3.14 environment `/private/tmp/parison-goal-venv/bin/python` (default shell
Python is unsupported 3.9).

Independent Standards review found transient input substitution could publish
PASS: discovery results were not bound to acquired CSV digests, and phases read
mutable caller paths. Corrections now stage private verified pair and policy
copies, compare discovery input/policy identities, and reverify originals.
Independent Spec review found argparse could leak unknown argument values and
reference-corpus/version/digest-recomputed checks were incomplete. Corrections
add fixed parser errors and targeted tests. These changes still require fresh
independent Standards/Spec review; neither review has cleared the corrected
head. The final local check log is `/private/tmp/rehearsal-final-check.log`.

Real disposable PostgreSQL 16.15→18.6 dump/restore passed a small live gate,
including orphan lines, per-order offsetting sums, timestamp/Unicode drift,
partial backfill and verification after both servers stopped. Three cold
100k and 250k runs completed on the pre-review implementation. Raw measurement
reports are saved under `benchmarks/results-2026-10-29-postgresql-rehearsal-*-pre-review.json`.
They are **not final qualification**: private snapshot staging changes disk and
time costs. Repeat on the corrected code, sequentially on a named machine;
record hardware/storage, median/max elapsed, worker RSS (worker has no child
processes), sampled temporary/output disk and source row/byte/query observations.
Do not present sampled peaks as exhaustive bounds or universal capacity.
PostgreSQL 16 was installed via Homebrew beside existing 18; disposable clusters
were stopped and removed. No service or existing database was used.

## Exact next steps

1. Inspect latest commit/status and final local check log. Run narrow rehearsal
   tests then `make check` if needed; the final added reference-count assertions
   and private staging correction must pass. Use escalation for existing local
   socket tests; sandbox-only full checks fail on loopback binding.
2. Re-review corrected code independently against `d057ee9` and contract 262.
   Add a direct transient original-policy/relationship substitution regression
   if needed; verify all phases consume private snapshots. Resolve findings.
3. Rerun `scripts/check_postgres_rehearsal_live.py` sequentially with
   `--pg16-bin /opt/homebrew/opt/postgresql@16/bin --pg18-bin /opt/homebrew/opt/postgresql@18/bin`,
   rows 100000 then 250000, three repeats each, adversarial on at least one.
   PostgreSQL shared memory requires escalation. Write final measurement notes.
4. Update PR #104 with final evidence, push the exact head, dispatch `test.yml`
   manually for that branch, and require exact-head quality plus full built-wheel
   Python 3.11–3.14 Linux/macOS/Windows success. Inspect head SHA, not just branch
   labels. CI for the initial head may exist but does not qualify corrections.
5. Merge only qualifying feature 5 to develop, then record integration in
   docs/CURRENT.md and a scoped handoff PR. Feature 6 portable decision dossier
   follows; all six features stay together before any 2.3 release decision.

Preserve released contracts, canonical bytes, CLI JSON/exit codes and local-first
architecture. PASS means explicit-policy agreement under unauthenticated
source-owned claims, never extraction truth, approval or cutover authorization.
The through-v5.0 direction remains in docs/0.15/104-product-direction-and-release-arc.md;
this work advances only feature 5 of 2.3, not later release boundaries.
