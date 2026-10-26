# Recoverable suites continuation

26 October 2026. Session stopped at 7% remaining five-hour usage, as requested.

## Copy-ready next-session goal

Create a goal to continue the accepted Parison 2.2 six-feature train. Start with
`make context`. Current branch is `feature/recoverable-suites-v2`, PR
https://github.com/raghavkandpal/parison/pull/83 to `develop`; base is
`71a54adc4d8be570c3d3c3d9358d4759bac0795d`. Implementation checkpoint `4a44187`
is followed by the final safety-fix commit containing this handoff; resolve its
exact SHA with `git rev-parse HEAD`, and verify it matches the PR head.

Dataset evidence v2 and suite authoring are integrated (PRs #81/#82).
Recoverable suites now implement the complete frozen contract in document 238.
Independent Standards and Spec reviews cleared all findings after correcting
published-output deletion, checkpoint symlink following, malformed UTF-8 and
incomplete-child reuse. Final local `make check` passed 484 tests with Python
3.14 and Polars installed. No known open review findings remain. Exact-head
full built-wheel CI and quality CI were dispatched at session close; their
results are not yet claimed green. Inspect the exact PR head runs, fix any
failures, rerun qualification and merge only after green required checks.

Use `/tmp/parison-goal-venv/bin/python` if still available, otherwise recreate a
supported environment using CONTRIBUTING.md. Continue with policy-change review,
suite rehearsal series, then complete reconciliation workflow/typed handoff.
Freeze each small contract and acceptance fixtures before coding. Use existing
modules and architecture; preserve recipes, schemas, canonical bytes, bundles,
CLI JSON/exit codes, local zero-custody execution, explicit policies,
verification-first summary-safe evidence and atomic no-overwrite publication.

All six accepted capabilities must be independently qualified before candidate
preparation; general releases require at least three substantial features.
No release/tag/publication is authorized by this session. Follow RELEASING.md
and the researched direction through v5.0; future scopes require explicit
contracts. Commit, push, PR and merge reviewed feature work as required, and
stop gracefully near 5% remaining usage with an updated handoff.
