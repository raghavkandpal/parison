# Combined structured-selection qualification

Status: **qualified combined checkpoint**

The complete 1.9 train contains three separately reviewed capabilities: JSON
per-field RFC 6901 projection, XML attribute or bounded child-path projection,
and XLSX exact workbook-defined-name range projection. Each has an independent
contract, feature checkpoint, blind review and exact-commit built-wheel CI.

Fresh combined Standards/security review of `origin/main...develop` found no
release blocker. It covered compatibility, policy fingerprints, summary-safe
evidence, parser and package trust boundaries, resource limits, deterministic
artifacts and supported-platform packaging.

Fresh combined Spec review found one candidate blocker: structured preflight
schemas did not correlate each projection kind with its source format. The
correction makes all six schemas v16--v18 and v22--v24 require
`json-pointer-v1` with JSON documents, `xml-field-v1` with XML documents and
`direct-v1` with every other admitted format. Mutation regressions cover both
sides and all six schemas. Independent re-review exhaustively checked every
format/kind pairing and passed with no remaining finding.

Full `make check` passes 400 tests on Python 3.14 with 11 expected optional
dependency skips. Exact combined checkpoint
`75e5ea03b0fe6d837273379959a9c65dcf4a88d4` passed the
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39369155085)
and its complete
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39369155164)
on Python 3.11--3.14 across Linux, macOS and Windows.

The complete train may advance as one 1.9.0 candidate. This qualification is
internal development evidence only. It does not establish extraction truth,
policy approval, migration approval or cutover authorization.
