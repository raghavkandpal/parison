# XML record engineering checkpoint

Status: **feature gate complete locally**

The second feature in the 1.8 train is implemented. Explicit `xml:` locators
bind a bounded QName record path to a unique namespace map and project flat
direct-child text elements into the released typed-row boundary across keyed,
aggregate and multiset comparison. Drafting, suite portability, summary-safe
metadata and strict preflight schemas v10--v12 cover the new source.

The fail-closed boundary rejects DTD/entity declarations, XPath-like or
unbound paths, attributes, nested or mixed-content fields, duplicate or
inconsistent fields, symlinks, absent selection, missing projection policy,
excess rows, files over 64 MiB, depth over 100, more than 1,000,000 elements
and per-element text over 1 MiB. Parsing stays local and performs no inclusion,
external-resource or network work.

Local completion gate: `make check` passes 372 tests on Python 3.14. Exact
commit CI and fresh blind review remain before final checkpoint status.

This completes two of three required 1.8 features. It is not a release
candidate and must not be tagged or published independently.
