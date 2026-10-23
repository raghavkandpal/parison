# Initial qualification checkpoint

Date: 23 October 2026

`make context` reported a clean `develop` at
`cfefc1218d9240def982774e315e126e0c05bca3`. After fetching origin, local and remote
develop matched. GitHub confirmed PR #78 merged at that commit; its
[quality run](https://github.com/raghavkandpal/parison/actions/runs/39955246580)
passed. No full-matrix run for that planning commit was found in the inspected
recent develop runs. This is baseline verification, not feature qualification.

Created scoped branch `docs/2.2-contract-freeze`. Python 3.14 is available at
`/opt/homebrew/bin/python3.14`; an isolated temporary environment contains the
repository-declared test/dev extras and build tooling. Polars is absent.

## Reconciliation probe

A synthetic bundle produced using the existing `_preflight_files` test fixture
and `run_reconciliation` passed verification. Replaced the baseline identity
check's entire `counts` object with `{"invented_count": 999}`, rewrote the result
and updated its SHA-256 in the outer manifest. The current verifier still
returned PASS. Source data and summary were unchanged.

This reproduces the unknown-count-vocabulary gap identified by review 231. It
does not demonstrate upstream data falsification or bypass of issuer
authentication: bundle hashes do not authenticate issuers. Next gate: rejection
regressions for vocabulary, feasible arithmetic and outcome derivation, tested
against all valid released producer shapes before stronger diagnostics.

## Dataset feasibility boundary

Source inspection confirms `_source_digest` hashes only the underlying file for
structured selectors, while directories hash ordered basename/NUL/raw digest
triples, even with one member. Therefore manifest v2 must carry selectors and
policy separately from physical file identity, and retain the directory/file
distinction. Three executable feasibility fixtures pass in
`tests/test_dataset_binding_feasibility.py`: shared workbook ranges, distinct
JSON pointers and single-member/renamed/hidden partition membership. They pin
released identity behavior, not a v2 implementation. Complete wire contracts
and v2 acceptance fixtures remain pending. No capability is yet implemented or qualified.

## Local checks

Python 3.14 `make check` passed 433 tests with 11 optional-Polars skips
(Polars absent), lint, formatting, generated command-reference validation and
whitespace checks. The first sandboxed attempt could not bind loopback sockets;
the permitted rerun passed all Workbench host tests. This is local evidence only.
