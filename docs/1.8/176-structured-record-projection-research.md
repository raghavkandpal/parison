# Structured record projection research

Date: 18 October 2026

Status: **accepted release-train boundary**

## Decision

Parison 1.8 will add three explicit local record selectors that feed the
released typed-row boundary:

1. a JSON Pointer selecting one array of flat JSON objects;
2. a bounded XML element path with an explicit namespace map; and
3. a named XLSX table selection alongside the released worksheet rectangle.

These are parser features, not new comparison modes. They require
`semantic-scalar-v1`, retain existing keyed, aggregate and multiset semantics,
and never infer a record collection.

## Primary-source consequences

RFC 8259 permits JSON object names that are not unique but warns that their
handling is unpredictable. Parison therefore rejects duplicate members at
every level. RFC 6901 defines JSON Pointer escaping and failed evaluation;
Parison accepts the string form only, implements `~0` and `~1`, and rejects
missing, ambiguous or invalid traversal rather than guessing.

Python's XML security guidance documents denial-of-service risks around
entities and large inputs. The XML feature must reject declarations and
entities, avoid network access, and impose explicit depth, element and text
limits in addition to Parison's byte and row limits. Element selection and
namespace bindings must be declared, not inferred.

openpyxl documents worksheet tables as named objects with a rectangular
reference and requires string column headings. The XLSX feature will select an
exact table name and reuse the released values-only, no-formula projection.

Sources accessed 18 October 2026:

- [RFC 8259: JSON](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 6901: JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901)
- [Python XML security](https://docs.python.org/3/library/xml.html#xml-security)
- [ElementTree](https://docs.python.org/3/library/xml.etree.elementtree.html)
- [openpyxl worksheet tables](https://openpyxl.readthedocs.io/en/stable/worksheet_tables.html)

## Threats and non-goals

- No recursive document diff, JSONPath, XPath, schema inference or repair.
- No DTD, entity, XInclude, external-resource or network processing.
- No workbook calculation, implicit active-sheet selection or table discovery.
- No change to recipes, scalar encodings, result outcomes or evidence meaning.

Each selector is separately reviewable, but all three ship together. The
release candidate gate remains closed until every feature has its own contract,
tests, green full check and pushed exact-commit CI checkpoint.
