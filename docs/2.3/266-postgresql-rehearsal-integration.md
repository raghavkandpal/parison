# Feature 5 integration checkpoint

Date: 29 October 2026
Status: historical feature 5 integration checkpoint; later released in 2.3.0

[PR #104](https://github.com/raghavkandpal/parison/pull/104) merged feature 5
at `4dd03eeabcfc81ac6aadb56cf03ebfa0ba794c68` from exact reviewed head
`8141b600586531fea4b12ea19361fb38bc5ffc3c`. Its final behavior is the
[frozen rehearsal contract](262-postgresql-rehearsal-contract.md) and
[operator notes](263-postgresql-rehearsal-operator-notes.md). The work combines
independently reviewed PostgreSQL 16/18 pair receipts, exact partition parity,
non-null identities/references and per-order exact amount conservation in one
local rehearsal. Missing coordination or reviewed-scope counts remain
INCONCLUSIVE unless an exact failure takes precedence. PASS does not authenticate
source extraction, approve migration or authorize cutover.

The corrected head passed 556 local tests and independent Standards and Spec
re-review after fixing transient input substitution and malformed CLI error
leakage. PR [quality CI](https://github.com/raghavkandpal/parison/actions/runs/40919931544)
and automatic [test CI](https://github.com/raghavkandpal/parison/actions/runs/40919931601)
passed at the exact head. The manually dispatched
[full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/40919945013)
passed Python 3.11–3.14 Linux tests plus macOS and Windows smoke jobs at the
same head. A disposable PostgreSQL 16.15→18.6 gate passed five adversarial
mutations and offline verification after source shutdown; the
[machine-specific budget](265-postgresql-rehearsal-budget-checkpoint.md)
records three sequential 100k/250k runs and limitations.

The next gate is feature 6, the portable decision dossier. Research and freeze
its end-to-end contract before implementation. It must compose verified
coverage, parity, reconciliation, exceptions and external human sign-off
references into a separately versioned unsigned local artifact, with the same
summary-safe result in Workbench and CI. Offline verification must reproduce
every derived status and fail closed on tampered or incomplete evidence. A PASS
or sign-off reference must never become automatic migration or cutover
approval. Keep all six 2.3 features together before a release decision.
