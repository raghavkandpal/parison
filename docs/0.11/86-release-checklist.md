# Parison 0.11.0 release checklist

Status: **released**

## Scalable suite contract and implementation

- [x] Suite-v2 research, roadmap and normative contract are checked in.
- [x] Strict plan, result and manifest schemas are installed without changing suite v1.
- [x] Listing, case/tag selection, plan fingerprints and effective per-case limits share one implementation.
- [x] Fixed-modulo external shards publish distinct recursively verifiable bundles.
- [x] Assembly rejects gaps, duplicates, mixed selections, stale plans and tampered children before atomic publication.
- [x] Resume workspaces verify children and current input digests before reuse.
- [x] Markdown and JUnit-style reports are bounded, summary-safe and derived only from verified bundles.
- [x] A checked-in GitHub Actions matrix example transports and assembles shards.

## Evidence and release gates

- [x] Suite-v1 mixed-mode behavior remains covered unchanged.
- [x] Adversarial unit coverage includes selection errors, unsafe references, shard gaps, duplicate indexes, tampering, stale inputs and unsafe workspaces.
- [x] Reproducible 10-, 25- and 100-case orchestration measurements verify clean, sharded, assembled and resumed paths.
- [x] Candidate CI passes Python 3.11–3.14 plus macOS and Windows from the release commit.
- [x] A clean wheel contains every v2 schema and passes the complete scalable-suite workflow.
- [x] Candidate wheel and source archive checksums are recorded.
- [x] The verified commit is merged to `main`, tagged `0.11.0` and published with checksums.
- [x] Published assets are downloaded, checksum-verified and smoke-tested in an empty environment.

Released as [0.11.0](https://github.com/raghavkandpal/parison/releases/tag/0.11.0) from merged `main` commit `0417aa954774d62cb8195444b184defb99b92297`.
