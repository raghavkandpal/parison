# Effective-policy fingerprint

Date: 8 October 2026

Parison records two distinct SHA-256 values:

- `recipe_sha256` identifies the exact recipe file bytes used by a comparison.
- `policy_sha256` identifies the fully expanded comparison policy, including defaults and physical mappings.

The policy fingerprint is calculated from canonical UTF-8 JSON with sorted object keys and no insignificant whitespace. Reformatting or reordering a recipe therefore changes `recipe_sha256` but not `policy_sha256`; changing an effective policy decision changes both.

`parison explain` emits the fingerprint, and new result-v1 bundles record it in `result.json` and the HTML provenance section. The field is additive and optional in the result-v1 JSON Schema so released older bundles remain valid.

The fingerprint is evidence of policy equality, not approval of the policy and not a signature. It contains no secret key and provides no authenticity guarantee.
