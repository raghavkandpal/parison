# Current development state

- Version: **0.17.0 release candidate**
- Branch: `develop`
- Theme: authenticated evidence handoff
- Implemented: canonical Statements, semantic rebinding, cutover reports, installed schema, Cosign guidance, cross-platform fixture and keyless acceptance workflow
- Verified: 228 local tests passed; six optional-Polars tests skipped; built-wheel CI passed Python 3.11–3.14, macOS and Windows
- Next gate: merge the reviewed candidate to `main`, run `.github/workflows/evidence-signing.yml`, then complete exact-merge artifact and public-release verification

Authoritative detail: [roadmap](0.17/114-roadmap.md), [engineering checkpoint](0.17/118-engineering-checkpoint.md), [release checklist](0.17/119-release-checklist.md).

Update this page when the active version, completion state, or next gate changes. Keep historical evidence in the version folder.
