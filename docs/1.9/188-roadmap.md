# Parison 1.9 roadmap

Status: **released**

Theme: explicit structured field selection

## Release train

1. JSON per-field projection: select each logical field with an RFC 6901
   pointer relative to the explicitly selected record. Gate: new versioned
   policy, strict schemas, mixed direct/JSON inputs, all comparison modes,
   drafting, suites, preflight/evidence, hostile traversal cases, blind review
   and exact-commit CI. **Qualified at `c657fb2`; one of three required
   features complete.**
2. XML per-field projection: select each logical field from one exact record
   attribute or bounded unique child-element path. Gate: QName/namespace and
   attribute rules, structural ambiguity, streaming/resource limits, mixed
   inputs, all modes and engines, blind security review and exact-commit CI.
   **Qualified at `94078a4`; two of three required features complete.**
3. XLSX defined-name projection: resolve one exact static workbook-scoped name
   to one local bounded rectangle. Gate: scope, reference grammar, hostile
   definitions, headers, formulas/errors, ZIP limits, all modes and engines,
   suites/evidence, blind review and exact-commit CI.
   **Qualified at `5a0f800`; all three required features complete.**

Each feature earns a coherent pushed checkpoint. Do not open a candidate, tag
or release any subset; all three features plus combined Standards/Spec review
and exact built-wheel qualification are required for one 1.9.0 candidate.

All three feature checkpoints and the combined review gate completed. The
train advanced and was released as one 1.9.0 unit; no individual feature was
released separately.

Release 1.9.0 is complete at exact merge
`703e5b9daa39e9165f7bced933354061af0d5f89`. Exact-merge CI, tagged artifacts,
checksums and fresh public-wheel workflow verification passed.

## Versioned policy boundary

Recipe versions 1--3 and their installed schemas remain byte-for-byte
unchanged. Field selection introduces recipe versions 4--6 for keyed,
aggregate and multiset modes respectively. These versions require one
`field_projection` declaration with an explicit entry for each side:

- `direct-v1` maps every configured logical field to one exact flat source
  field, replacing rather than combining with `column_mappings`;
- `json-pointer-v1` maps every configured logical field to one nonempty RFC
  6901 pointer relative to each selected JSON record; and
- `xml-field-v1` maps every configured logical field to one exact record
  attribute or bounded unique child-element path.

The side maps must cover exactly the configured logical columns so projection
cannot silently fall back to a source name. Selectors enter the effective
policy fingerprint. Selection failure is invalid input, never inferred null,
exclusion, repair or tolerance policy. Existing locators still own record or
range selection; the projection declaration owns logical-field selection.

The XLSX defined-name locator remains compatible with released recipes because
it selects a rectangle, as named-table and explicit-rectangle locators already
do. Recipe versions 4--6 may also use it through `direct-v1`, but the locator
does not alter policy identity by itself.

## Compatibility and evidence

All features feed the released `semantic-scalar-v1` boundary. Comparison
contracts, canonical scalar and row bytes, outcome reduction, result schemas,
historical bundle readers, CLI JSON and exit codes remain unchanged. New
strict recipe and preflight schemas must not modify any released schema.

Full evidence may record declared selectors and resolved ranges when required
for reproducibility. Summary-safe projections exclude selectors, field and
attribute names, defined names, worksheets, ranges, source paths, keys, values
and discrepancy samples. Internal tests and reviews qualify development only;
they do not establish extraction truth, policy approval, migration approval or
cutover authorization.
