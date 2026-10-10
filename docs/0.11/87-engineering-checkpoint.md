# Parison 0.11 engineering checkpoint

Date: 10 October 2026

Release commit: `0417aa954774d62cb8195444b184defb99b92297`

## Verification

- 177 local tests passed on Python 3.12 with Polars 1.44.2.
- The release PR and merged `main` passed Linux Python 3.11–3.14 plus Python 3.14 smoke jobs on macOS and Windows. The final `main` evidence is [GitHub Actions run 38038709777](https://github.com/raghavkandpal/parison/actions/runs/38038709777).
- The matrix exercises every installed schema, the unchanged suite-v1 mixed-mode workflow, suite-v2 selection, two shards, exact assembly, recursive verification, safe reporting and the full test corpus.
- A clean Git archive built the universal wheel and source archive. The wheel contained all suite-v2 schemas and installed as Parison 0.11.0 in an empty Python 3.12 environment.
- The installed wheel passed listing, fixed-modulo shard execution, out-of-order verified assembly, recursive verification, Markdown and JUnit export, workspace seeding and digest-validated resume.
- Adversarial coverage includes duplicate and unknown filters, unsafe absolute references, limit propagation, shard gaps and duplicate indexes, mixed selection, child tampering, changed inputs, unsafe workspaces, output refusal and scope-aware outcome verification.

## Published release

The [0.11.0 GitHub release](https://github.com/raghavkandpal/parison/releases/tag/0.11.0) contains:

- wheel SHA-256: `d060cb63935a55dd251e93508561df5f75333e70c8298b6b932646f5abdb61ea`;
- source archive SHA-256: `4bc56adaeaff65a9baa9c897d7d96f4156ac68e540c0bdfaaf1ff9e930f85d18`; and
- `SHA256SUMS.txt` covering both archives.

All assets were downloaded from the public release. Both archive checksums matched, and the downloaded wheel repeated the sharded execution, assembly, verification and Markdown-report workflow in a fresh environment.

## Scale evidence

The recorded arm64 macOS Python 3.12 run verifies clean, four-shard sequential, assembly and resume paths at 10, 25 and 100 cases. These tiny-input measurements show orchestration and verification overhead; they do not claim local speedup. Parallel throughput remains the responsibility of the external runner. See [`benchmarks/results-2026-10-10-suite-v2.json`](../../benchmarks/results-2026-10-10-suite-v2.json).

## Scope decision

0.11 freezes suite-v2 selection and plan identity, fixed-modulo external sharding, exact verified assembly, conservative same-version resume workspaces, and bounded Markdown/JUnit-style projections. Internal worker pools, dynamic scheduling, remote transport, hosted coordination, retries and trend storage remain deferred.
