# XML field-projection engineering checkpoint

Status: **qualified feature checkpoint**

The second feature in the 1.9 release train is implemented. Recipe versions
4--6 accept `xml-field-v1` sides whose policy-owned namespace map and exact
selectors project record attributes or bounded unique child-element paths.
The existing record locator continues to select records independently; field
selection feeds the released semantic-scalar boundary in keyed, aggregate and
multiset modes under both memory and SQLite execution.

The admitted record tree is closed. Record attributes must equal the selected
attribute set, every child must be a prefix or leaf of a selected element
path, intermediate nodes contain only selected children, and leaf nodes are
attribute-free text elements. Missing, repeated, unselected and mixed-content
shapes fail. Policy and locator namespace aliases resolve independently to
expanded names; unprefixed selectors always mean no namespace.

The implementation deepens the released streaming XML reader. Completed
record subtrees remain attached only until projection and are then removed;
UTF-8, DTD/entity, depth, element, text, physical-byte and row limits stay
authoritative. Strict recipe schemas v4--v6 and preflight schemas v16--v18 are
extended without modifying any released schema.

Fresh blind Spec review found no contract defect. Fresh Standards/security
review found one closed-shape gap: non-whitespace text after a selected record
element was accepted. The correction rejects record tails only for
`xml-field-v1`, preserving released recipes, and regression coverage now pins
record, intermediate and leaf tails. Standards re-review cleared the corrected
gate with no remaining security or compatibility finding.

The focused XML/JSON/schema/suite gate passes 53 tests. Full `make check`
passes 392 tests on Python 3.14 with 11 optional dependency skips. Exact
checkpoint `94078a4ffb6bcc68127f663359f7346e97870b86` passed the full
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39272848506)
on Python 3.11--3.14 across Linux, macOS and Windows, plus the independent
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39272848633).

This is the second of three required 1.9 features. It is not a release
candidate and must not be tagged or published independently. Review and test
evidence qualifies repository development only; it does not establish
extraction truth, policy approval, migration approval or cutover authorization.
