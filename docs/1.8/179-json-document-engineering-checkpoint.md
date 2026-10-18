# JSON document engineering checkpoint

Status: **feature gate complete locally**

The first feature in the 1.8 release train is implemented. Explicit `json:`
locators resolve RFC 6901 pointers to arrays of flat objects and feed the
released typed-row boundary across keyed, aggregate and multiset comparison.
Drafting, portable suite resolution, summary-safe source metadata and strict
preflight schemas v7--v9 cover the new locator without changing schemas v1--v6.

The negative corpus rejects implicit selection, duplicate members, non-finite
numbers, nested record values, inconsistent fields, invalid or unresolved
pointers, empty schemas, non-object records, symlinks and missing
`semantic-scalar-v1` policy. Whole-file digests and physical byte/row limits
remain authoritative.

Fresh blind review found and corrected schema-only row-limit enforcement,
non-ASCII and oversized pointer indices, recursion error translation, and a
loose nested multiset preflight shape. Regression coverage pins every
correction.

Local completion gate: `make check` passes 369 tests on Python 3.14. The exact
corrected commit and built-wheel CI link are recorded after the checkpoint is
pushed.

This completes one of three required 1.8 features. It is not a release
candidate and must not be tagged or published independently.
