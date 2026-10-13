# Parison 0.19 engineering checkpoint

Date: 13 October 2026

Status: **automated gates passed; human gate pending**

## Qualified checkpoint

Commit `0028e7c2fc34c90e2bb19e2b1f8ae3c3915ca496` passed GitHub Actions run [38402331045](https://github.com/raghavkandpal/parison/actions/runs/38402331045):

- installed-wheel tests on Linux with Python 3.11, 3.12, 3.13 and 3.14;
- installed-wheel macOS and Windows smoke workflows;
- all 239 tests, including the historical upgrade corpus and complete migration evidence workflow;
- schema, example, suite, SQLite-engine and benchmark-accuracy smoke gates.

The same commit passed identity-constrained keyless signing run [38402546260](https://github.com/raghavkandpal/parison/actions/runs/38402546260). That run exported a Statement for the immutable 0.1.0 bundle, signed it with GitHub Actions OIDC through Cosign, constrained certificate identity and issuer during verification, rebound the authenticated Statement to the local bundle, generated a cutover report and uploaded the evidence artifacts.

Local `make check` also passed with 239 tests and six valid optional-Polars skips before the checkpoint was pushed.

## What this proves

- Current built wheels recursively verify the pinned keyed, aggregate, multiset, suite-v1 and suite-v2 historical bundles on the supported functional matrix.
- The connected initialization-to-cutover acceptance workflow is portable across that matrix.
- The documented external signing path still authenticates exact Statement bytes under an explicit workload identity.

It does not prove source extraction truth, policy approval, universal performance, usability by an unfamiliar human, or 1.0 release readiness.

## Remaining gate

Run the direct-human migration workflow rehearsal defined by the [1.0 readiness checklist](128-1.0-readiness-checklist.md). Record every undocumented assumption or point of confusion, fix only demonstrated problems, and rerun the exact candidate matrix before a release decision.
