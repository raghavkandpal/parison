# Current development state

- Version: **0.19 implementation**
- Branch: `develop`
- Theme: 1.0 readiness and compatibility
- Released: 0.18.0 explicit SQLite-backed keyed execution with bounded temporary storage and unchanged keyed-v1 semantics
- Verified: exact merge `1f43d1724625b508e9c81cae01f454d659b3925a` passed the full CI matrix; public assets were checksum-verified and the wheel passed fresh direct and suite SQLite-keyed smoke workflows
- Next gate: run and record a direct-human migration workflow rehearsal, then close only demonstrated usability gaps

Authoritative detail: [0.19 roadmap](0.19/125-roadmap.md), [compatibility contract](0.19/126-compatibility-contract.md), [performance envelope](0.19/127-performance-envelope.md) and deferred [non-CSV input research](0.19/124-non-csv-input-research.md).

Update this page when the active version, completion state, or next gate changes. Keep historical evidence in the version folder.
