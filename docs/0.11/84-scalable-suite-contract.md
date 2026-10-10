# Scalable suite v2 contract

Date: 10 October 2026

Status: **implemented contract candidate**

## Compatibility

Suite v1 remains unchanged. Suite v2 adds orchestration metadata above ordinary keyed-v1, aggregate-v1 and multiset-v1 child bundles; it does not change their recipes, results or outcomes.

## Plan and identity

A strict suite-v2 plan contains 1–100 explicitly enumerated cases. Every recipe, baseline and candidate reference is a nonempty plan-relative string. A case may add a bounded description, a sorted unique list of at most 20 portable tags, and positive resource-limit overrides. Suite defaults and case overrides layer over Parison's built-in limits.

`suite_policy_sha256` is SHA-256 over canonical compact JSON containing the ordered portable references, effective recipe-policy fingerprints, tags, descriptions and effective limits. Absolute resolved paths and current input bytes are excluded. Input digests remain child evidence.

## Selection and sharding

Repeated case filters form a union. Repeated tag filters are conjunctive. When both are present, a case must satisfy both. Selection retains plan order and zero matches are an error.

After selection, the case at zero-based position `p` belongs to shard `p mod N`. Shard indexes are zero based, shard count is 1–100, and empty shards are rejected. A shard result uses kind `suite-shard`, records the complete selection specification, and cannot claim full-plan scope.

`scope_complete` means the result covers every declared plan case. `execution_complete` means every selected or assigned case published a complete child. The legacy `complete` field equals execution completeness. Human output must name shard or selected scope rather than presenting it as an unqualified suite PASS.

## Assembly

Assembly accepts only recursively verified suite-v2 shard bundles. All inputs must share the current plan fingerprint, case/tag selection and shard count. Indexes must cover `0..N-1` exactly once, and child IDs must cover the selected plan exactly once.

Assembly copies only manifest-covered child files into a fresh staging directory, restores plan order, recomputes child digests and outcome counts, and atomically publishes an ordinary suite-v2 bundle. It does not open source inputs or rerun comparisons.

## Resume workspace

A workspace is explicitly mutable and is never a result bundle. A fresh run refuses an existing workspace; `--resume` requires one. Each completed child has an atomically replaced checkpoint binding case ID, suite and recipe-policy fingerprints, effective limits, sample limit, exact Parison version, current input digests and verified child-manifest digest.

Reuse requires the checkpoint to match exactly, the child to verify recursively, child resource limits to match, and freshly calculated source digests to equal the child evidence. Any mismatch reruns the case. Final output is always copied into a fresh atomic result bundle and retains the no-overwrite rule.

## CI projections

`report-ci` first verifies an ordinary suite or shard. Markdown and the documented JUnit-style XML subset contain only scope, outcomes, completeness and portable case IDs. They are derived, non-authoritative, limited to 1,000,000 UTF-8 bytes, written atomically and never overwrite an existing file.

JUnit maps `FAIL` to `failure`, `ERROR` and `INTERRUPTED` to `error`, `INCONCLUSIVE` to `skipped`, and records every exact Parison outcome as a testcase property. The canonical JSON and manifests remain authoritative.

## Security boundaries

- Plans cannot execute commands, interpolate environments, discover files recursively or use absolute references.
- Bundle verification rejects unsafe required files and assembly copies no unlisted content.
- Parent reports and CI projections never include raw child evidence.
- Digests prove integrity relative to the supplied manifest, not authorship or approval.
- Existing destinations are never overwritten.
