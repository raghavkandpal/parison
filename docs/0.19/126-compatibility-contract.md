# Parison compatibility contract

Status: **released 0.19 contract**

## Purpose

Parison evidence must remain independently useful after the producing release is replaced. This contract defines the compatibility surface that 0.19 will prove before a 1.0 release. Compatibility means that a current installation preserves the documented meaning of released inputs and can read released evidence; it does not mean old and new releases must emit identical runtime provenance or report presentation.

## Frozen semantic surface

The following released behavior cannot change in place:

- recipe versions 1, 2 and 3 and their keyed-v1, aggregate-v1 and multiset-v1 meanings;
- canonical typed equality, numeric tolerance formulas, normalization order, null policy, key identity and duplicate handling;
- released JSON Schema identifiers and the accepted fields of their matching runtime validators;
- outcome names and process exit codes: `PASS` 0, `FAIL` 1, `ERROR` 2, `INCONCLUSIVE` 3 and interruption 130;
- manifest-covered bundle integrity, deterministic evidence ordering, policy fingerprints and canonical encodings;
- summary-safety: summaries exclude source paths, keys, values and discrepancy samples;
- the v1 Evidence Statement predicate and its binding to exact manifest bytes.

A semantic change requires a new recipe, schema, comparison-contract, canonical-encoding or predicate version as appropriate. A new version must not make an older bundle unreadable.

## Artifact readability

Current Parison must continue to verify released run bundles with manifest schema 1 and result schemas 1–3, suite-v1 bundles, and suite-v2 suite or shard bundles. Safe inspection and derived evidence may expose fields unavailable in an old artifact as `null`, absent or empty according to the published derived-output contract; they must not invent provenance.

Verification authenticates manifest-covered bytes and checks their internal semantics. It never upgrades, rewrites or repairs the bundle. A derived Statement or cutover report identifies the producing Parison version recorded by that bundle, not the current reader version.

## CLI and JSON evolution

Existing commands, required arguments and exit meanings remain supported through 1.x unless a security defect makes that unsafe. Machine-readable output may gain optional fields, but released fields cannot be removed, renamed or assigned a new meaning without a versioned output contract. Human-readable terminal and Markdown wording may improve when machine-readable behavior and disclosure boundaries are unchanged.

Defaults that affect comparison meaning, evidence sensitivity, selected scope or resource behavior cannot change silently. New behavior must be explicit or introduced under a new versioned policy.

## Upgrade corpus

Compatibility is proved with immutable artifacts produced by their named historical releases. Each corpus entry records or asserts:

- producing Parison version and artifact kind;
- exact top-level manifest digest;
- expected outcome, semantic contract and schema version;
- successful recursive verification and summary-safe inspection;
- supported derived operations such as Statement or cutover-report projection.

The initial corpus is the checked-in 0.1.0 keyed run at `examples/output`. It is intentionally not copied or regenerated. Subsequent entries must cover aggregate-v1, multiset-v1, suite-v1 and suite-v2 at their introduction releases.

## Change policy

Before 1.0, an incompatible correction still requires a new semantic version and a documented migration; release numbering alone is not permission to reinterpret published evidence. Through 1.x, compatible additions use minor releases and fixes use patch releases. Removal of a supported released contract is reserved for a future major release and requires an explicit migration path.

Security hardening may newly reject an artifact that was always malformed, ambiguous or unsafe. Such a rejection must be documented as a fix, produce a stable controlled error and include a regression fixture. Valid artifacts within the declared support surface remain readable.

## Completion gate

This contract is qualified when the historical corpus covers every released artifact family, passes from built wheels on the supported CI matrix, and a clean upgrade rehearsal demonstrates the documented migration/backfill workflow without mutating historical evidence.
