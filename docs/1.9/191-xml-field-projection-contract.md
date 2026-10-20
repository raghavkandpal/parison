# XML field-projection contract

Status: **implementation contract**

## Versioned recipe policy

Recipe versions 4--6 add one `xml-field-v1` side kind to the frozen
`field_projection` declaration:

```json
{
  "field_projection": {
    "version": 1,
    "baseline": {
      "kind": "xml-field-v1",
      "namespaces": {"o": "https://example.com/orders/v1"},
      "fields": {"id": "@id", "amount": "o:totals/o:net"}
    },
    "candidate": {
      "kind": "direct-v1",
      "fields": {"id": "id", "amount": "amount"}
    }
  }
}
```

An XML document side must use `xml-field-v1`; that kind is invalid for every
other input format. The side contains exactly `kind`, `namespaces` and
`fields`. The namespace map is policy-owned and fingerprinted; prefixes and
URIs are nonempty, unique and used by at least one selector. It is independent
of the locator's record-path bindings, even when the same prefix spellings are
chosen. An empty map is required for wholly unqualified selectors.

The field map covers exactly the configured logical columns, with at most 256
unique selector strings. Selectors are no more than 1,024 UTF-8 bytes. Recipe
versions 1--3 and the released direct-child XML projection remain unchanged.

## Selector grammar and namespace identity

A selector is exactly one of:

- `@QName`, selecting one attribute on the record element; or
- `QName/QName/...`, selecting a child-element path relative to the record.

Each path contains 1--32 portable ASCII QName segments. The QName grammar is
the released locator grammar: an optional declared prefix followed by one
portable XML name. There is no default prefix. An unprefixed element or
attribute therefore selects the no-namespace expanded name; the XML default
namespace never applies implicitly to policy selectors. Attribute selection
is available only on the record element, not on nested elements.

The grammar has no wildcard, descendant axis, current or parent step,
predicate, position, function, text node, union, Clark notation or namespace
discovery. Prefix spellings are policy aliases; matching uses the expanded
namespace-URI/local-name pair.

## Closed record shape and values

Every configured selector must resolve exactly once in every selected record.
A missing attribute or element, or repeated element at any selected path
segment, is a controlled input error. Attribute values project as text. An
element leaf must have no attributes or child elements; its text may be empty.
Non-whitespace mixed text or tail content is rejected.

The admitted record shape is closed around the policy:

- the record's attributes are exactly the selected record attributes;
- every direct or nested child is a prefix of at least one configured element
  path;
- intermediate elements have no attributes, non-whitespace text or mixed
  tails; and
- leaf elements are exactly the selected element leaves.

Consequently, unselected attributes, branches and leaves fail closed rather
than being silently ignored. Shared intermediate paths are allowed. Distinct
logical fields may not use the same selector.

## Streaming, limits and evidence

Selection operates only on each completed record subtree while preserving the
released streaming removal of processed elements. The 64 MiB document,
depth-100, 1,000,000-element, 1 MiB-per-text-node and selected-row limits stay
authoritative. UTF-8-only input, DTD/entity rejection, non-symlink local files
and the absence of XInclude or network processing remain unchanged.

All three comparison modes and their memory/SQLite engines use the released
`semantic-scalar-v1` boundary. Portable suite-v2 cases preserve the XML
locator while selectors remain in the recipe. Preflight v16--v18 records the
full reviewed projection; summary comparison results exclude selector paths,
attribute names, namespaces and source field names. Raw effective recipes
retain the declaration as policy.

`draft-recipe` does not invent attribute or nested-element selectors. Strict
recipe schemas v4--v6 are extended in place because they are the active 1.9
policy boundary; no released schema is changed.

## Compatibility and non-goals

Comparison semantics, canonical scalar and row bytes, outcome reduction,
result schemas, historical bundle readers, CLI JSON and exit codes remain
unchanged. XML Schema validation, XPath, XQuery, DTD defaults, XInclude,
attribute normalization beyond the XML parser, mixed-content extraction,
container serialization, missing-value defaults, selector suggestions, repair
and approval are out of scope. PASS means only that the declared projections
agree under the explicit recipe policy.
