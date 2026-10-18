# XML record projection contract

Status: **implementation contract**

## Locator and namespaces

```text
xml:path/to/export.xml#p:root/p:records/p:record?ns=p,https%3A%2F%2Fexample.com%2Fv1
```

The `xml:` prefix, local `.xml` regular file, `#` separator and bounded
root-to-record path are mandatory. Path segments use portable ASCII XML names
or qualified names whose prefix has exactly one repeated `ns=prefix,URI` binding.
Namespace values use ordinary URL percent encoding. Prefixes and namespace
URIs must be unique. Bindings may additionally name field-only namespaces.
Wildcards, descendant search, predicates, parent steps,
XPath functions, implicit namespace discovery, compression, symlinks and
partition directories are rejected.

## Records and values

Every element at the exact path is one record. Its direct child elements are
fields; unqualified child names remain local names and qualified children use
the declared `prefix:local` name. Each field must be unique, attribute-free and
contain text only—no nested elements or mixed content. Records themselves may
not contain attributes or non-whitespace text. Every record must have the same
field set. Empty field elements project as the empty string.

XML inputs require `input_projection: semantic-scalar-v1`. Existing recipe
column types remain authoritative; XML selection adds no coercion, inference,
comparison mode or approval semantics.

## Security, limits and evidence

Documents must use UTF-8. DTD and entity declarations are rejected before parsing; Parison performs no
XInclude, external-resource or network processing. XML documents are limited
to 64 MiB, depth 100, 1,000,000 elements and 1 MiB text per element in addition
to the existing combined physical-byte and selected-row limits.

Full evidence records `format: xml`, the declared `record_path`, sorted
`namespaces`, bytes and whole-file SHA-256 without the source path. Keyed,
aggregate and multiset preflight use new strict schema versions while every
released schema remains unchanged.

## Non-goals

This is not XPath, XML canonicalization, recursive document equality, schema
validation, attribute mapping, entity expansion, repair or extraction truth.
