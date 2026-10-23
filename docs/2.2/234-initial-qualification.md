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

## Follow-up qualification

Independent Standards and Spec reviews found no actionable findings at
`1b4cb73d959141cf284d037f3b466aadc3b1954d`. Its manually dispatched
[full built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39956126851)
passed Linux Python 3.11–3.14 and all macOS/Windows Python 3.11–3.14 lanes.
This evidence applies to that exact checkpoint, not later edits.

Additional synthetic probes reproduced acceptance of an unknown extra count,
`distinct_keys > rows`, and a PASS identity with `duplicate_keys = 1`.
These probes use a generated valid result with modified counts and publication
through the released publisher; all three verified PASS. The frozen mutation
inputs in `tests/fixtures/2.2/reconciliation-count-mutations.json` specify rejection
cases for the forthcoming verifier regression, including missing, boolean,
negative and inconsistent reference counts. They are acceptance inputs, not
passing rejection tests yet. The baseline identity/reference outcomes are PASS;
mutations must leave those outcomes unchanged to test independent derivation.

A fourth dataset feasibility test pins ordered partition hashing independently
of file creation order, and detects changed member contents and added members.
The branch must contain multiple substantive commits before integration, per the
updated user instruction. No checkpoint authorizes publication.
