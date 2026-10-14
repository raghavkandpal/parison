# Schema evolution and policy diff v1

Status: **implemented on `develop`**

## Boundary

`schema-evolution-v1` is local review metadata. It declares baseline-to-candidate field identity and lineage; it does not inspect records, infer renames, transform values, apply defaults or approve a migration. `policy-diff-v1` compares two fully expanded Parison policies under that declaration. Its `ACCEPT`, `DENY` and `INCONCLUSIVE` labels are mechanical compatibility assessments, never approval or cutover authorization.

Existing recipes, comparisons, result bundles, catalog history and policy fingerprints are unchanged. In particular, an accepted diff does not make evidence with unequal policy fingerprints trend-comparable.

## Declaration

A declaration contains exactly `evolution_version`, `direction` and a nonempty `changes` array. Version 1 fixes the direction to `baseline-to-candidate`.

Every side-specific field contains a nonempty stable `id`, a case-sensitive physical `name`, `presence` (`required` or `optional`), `nullability` (`non-null` or `nullable`) and optionally a finite JSON-scalar `default`. Defaults are review metadata only and are never applied.

Change cardinalities are closed:

| Change | Baseline | Candidate | Identity rule |
|---|---:|---:|---|
| `unchanged` | 1 | 1 | same ID and name |
| `renamed` | 1 | 1 | same ID, different name |
| `added` | 0 | 1 | fresh candidate ID |
| `removed` | 1 | 0 | retired baseline ID |
| `split` | 1 | 2 or more | all candidate IDs fresh |
| `merged` | 2 or more | 1 | candidate ID fresh |

Logical IDs and physical names must be unique on each side. An ID may occur on both sides only in one `unchanged` or `renamed` entry. Duplicate JSON members, unsupported members, identity conflicts and invalid cardinalities are input errors.

## Canonical identity

Parison sorts fields by logical ID and changes by the fixed order `unchanged`, `renamed`, `added`, `removed`, `split`, `merged`, then by participating IDs. Canonical bytes are UTF-8 compact JSON with recursively sorted object keys and no trailing newline. `evolution_sha256` is SHA-256 over exactly those bytes.

Authoring order and insignificant whitespace therefore do not affect identity. Names, field metadata, defaults and lineage do.

## Policy assessment

`parison diff-policy` expands and fingerprints both recipes without reading data. It compares all non-column policy fields through deterministic leaf paths, then accounts for every compared and excluded physical field through the declaration.

- An unchanged or renamed field is accepted only when its complete column policy, comparison role, presence, nullability and default metadata remain identical.
- An addition or removal is accepted only when it is required, non-null, has no default and is already explicitly excluded with a nonempty rationale on the side where it exists.
- A compared addition or removal, semantic-policy change, global-policy change or undeclared policy field is denied.
- A split or merge over non-compared fields is inconclusive and requires upstream materialization. If its fields participate directly in comparison, it is denied.

Overall compatibility is `DENY` if any change is denied, otherwise `INCONCLUSIVE` if any change is inconclusive, otherwise `ACCEPT`. The full artifact records both policy fingerprints, the evolution fingerprint, ordered change records and `policy_diff_sha256`. The diff fingerprint covers every field except itself.

## Disclosure modes

Full output contains policy paths, physical names and changed policy fragments and must be handled as schema-sensitive metadata. `--summary` emits only versions, fingerprints, compatibility, counts and stable reason codes. It omits source paths, keys, values, physical names, logical IDs and policy fragments.

## Commands

```console
parison validate-evolution examples/1.2/orders.schema-evolution.json
parison explain-evolution examples/1.2/orders.schema-evolution.json
parison compile-evolution examples/1.2/orders.schema-evolution.json
parison diff-policy \
  --baseline-recipe baseline.recipe.json \
  --candidate-recipe candidate.recipe.json \
  --evolution examples/1.2/orders.schema-evolution.json
parison diff-policy \
  --baseline-recipe baseline.recipe.json \
  --candidate-recipe candidate.recipe.json \
  --evolution examples/1.2/orders.schema-evolution.json \
  --summary
```

`diff-policy` exits `0` for `ACCEPT`, `1` for `DENY`, `3` for `INCONCLUSIVE` and `2` for invalid input. Installed JSON Schemas are available as `parison schema schema-evolution` and `parison schema policy-diff`.

`compile-evolution` emits an existing `column_mappings` fragment keyed by logical field ID for unchanged and renamed fields. Added and removed fields produce no value mapping. Any split or merge makes compilation fail because those values must be materialized upstream. Generated mappings are suggestions for review; the command never edits or approves a recipe.
