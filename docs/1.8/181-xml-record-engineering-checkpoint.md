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

Local completion gate: `make check` passed 372 tests on Python 3.14 at
`f7d919453a84d79024bbc23f299f7afd4f53557b`; its
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39142255693)
and [quality gate](https://github.com/raghavkandpal/parison/actions/runs/39142255664)
also passed.

Fresh blind review then found that UTF-16 could bypass the declaration scan,
resource limits were enforced only after full tree construction, and
field-only namespace bindings were rejected. The follow-up requires UTF-8,
scans declarations independent of a byte encoding trick, enforces depth/node/
text bounds during event parsing, releases completed elements, and permits
additional unique field namespace bindings. Its focused 17-test parser/schema
gate and Ruff pass; a full `make check`, commit, push and exact-commit CI remain
for the next session.

This completes two of three required 1.8 features. It is not a release
candidate and must not be tagged or published independently.
