# Structured field-selection research

Date: 19 October 2026

Status: **research recommendation for the 1.9 release train**

## Question and repository boundary

What is the next coherent three-feature train after 1.8's explicit record
selectors that materially expands local deterministic verification without
adding another comparison model, implicit extraction or external custody?

Parison 1.8 can select a JSON array by RFC 6901 pointer, repeated XML records
by a bounded QName path and an XLSX named table or explicit rectangle. The
selected JSON records must still be flat; XML fields must still be direct,
attribute-free text children; and XLSX named ranges remain unsupported. These
are now the narrowest adjacent limitations in the released projection seam.
They prevent common, explicitly addressable exports from reaching the existing
typed-row engine even though their record or range boundary is already known.

The recommendation is one **explicit structured field-selection** train with
exactly three separately reviewable substantial features:

1. **JSON per-field pointers** evaluated from each selected record;
2. **XML per-field selectors** for an exact record attribute or bounded nested
   leaf element; and
3. **XLSX defined-name range projection** for one exact static workbook-scoped
   name.

Each feature deepens a released reader and feeds `semantic-scalar-v1`. None
changes keyed, aggregate or multiset comparison semantics. All three must be
complete before a 1.9 candidate; fixes, refactors and test hardening do not
count toward the three-feature minimum.

## Primary-source findings

Sources in this section were accessed **19 October 2026**.

### JSON Pointer is sufficient for explicit field selection

RFC 6901 defines a JSON Pointer as zero or more `/`-prefixed reference tokens,
with `~0` and `~1` escaping. Evaluation starts at a supplied root value and
processes tokens sequentially. Object member matching is code-point exact,
without Unicode normalization; array indices are canonical non-negative
decimal tokens without leading zeros. A nonexistent value, ambiguous duplicate
member or invalid traversal is an error, and applications must define the
effect of failure. These rules already underpin Parison's document-level
record pointer and can be reused with each selected record as the evaluation
root.

Source: [RFC 6901, JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901).

RFC 8259 permits arrays and objects as JSON values, warns that duplicate object
names make behavior unpredictable and permits number magnitudes or precision
that implementations may not represent interoperably. Therefore a field
pointer must resolve to one scalar admitted by `semantic-scalar-v1`; it must
not flatten a subtree, serialize a container or pass numbers through binary
floating point.

Source: [RFC 8259, The JavaScript Object Notation (JSON) Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259).

### XML has exact attributes and hierarchy, but no implicit field meaning

XML 1.0 defines elements as named tree nodes with an unordered set of uniquely
named attributes. The Namespaces in XML recommendation defines expanded names
as namespace-URI/local-name pairs, requires expanded attribute names to be
unique and specifies that a default namespace applies to element names but
not to unprefixed attribute names. A safe selector therefore has to distinguish
an attribute from an element path and resolve both through the caller's
explicit prefix map; comparing prefixes from the source document would be the
wrong identity rule.

Sources:

- [XML 1.0, Fifth Edition](https://www.w3.org/TR/xml/)
- [Namespaces in XML 1.0, Third Edition](https://www.w3.org/TR/xml-names/)

Python's `xml.etree.ElementTree` exposes attributes at the `start` event but
only guarantees complete text and children at `end`. It also documents that
incremental parsing does not itself free parsed nodes and recommends clearing
or removing processed elements to retain low memory use. The existing 1.8
streaming removal, declaration rejection and depth/node/text limits must
therefore remain authoritative while a bounded field selector walks only the
completed record subtree.

Python also warns that XML parsers can be exposed to entity-expansion and
large-token denial of service depending on the linked Expat version. Extending
field reach must not relax the released UTF-8, DTD/entity, depth, node and text
controls or invoke XInclude.

Sources:

- [Python `xml.etree.ElementTree` documentation](https://docs.python.org/3.14/library/xml.etree.elementtree.html)
- [Python XML security guidance](https://docs.python.org/3.14/library/xml.html#xml-security)

### XLSX defined names require a deliberately smaller contract than Excel

Office Open XML defined names are not inherently ranges. A name can denote a
constant, formula, single cell, one range or multiple ranges, and can be
workbook-scoped or worksheet-scoped. Microsoft's conformance notes require
uniqueness only within the applicable global or local scope and identify
reserved built-in names. openpyxl likewise documents that definitions may be
constants, formulas or multi-destination ranges, and that it cannot resolve
dynamic definitions in general.

Sources:

- [Microsoft Office implementation note for `definedName`](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/16c3c118-f358-493d-a99f-4c85ca834c00)
- [openpyxl defined names](https://openpyxl.readthedocs.io/en/3.1.2/defined_names.html)

Consequently, Parison can safely support only an exact, non-reserved,
workbook-scoped name whose definition resolves to exactly one local worksheet
and one bounded rectangular cell range. Dynamic formulas, constants, unions,
external workbook references, sheet-local names and implicit active-sheet
resolution must fail closed. The first row remains the header and every value,
formula, error, ZIP and resource-limit rule from the released rectangle
contract remains unchanged.

## Recommended feature contracts

### Feature 1: JSON per-field pointers

Add a versioned, recipe-owned mapping from each logical field to an RFC 6901
pointer evaluated relative to every object selected by the released document
pointer. The empty field pointer may select the record only if that record is a
scalar; because the released record selector requires objects, the practical
v1 field vocabulary should require a nonempty pointer. Every pointer must
resolve exactly once for every record to a JSON scalar. Missing paths,
containers, non-finite or otherwise inadmissible values fail preflight and
comparison rather than becoming null or serialized JSON.

This is substantial because it changes schema discovery, recipe drafting,
portable-suite path rewriting, preflight metadata and all three comparison
modes while preserving the canonical scalar boundary. Existing flat JSON
records and `column_mappings` retain their released meaning; field pointers
must be a new explicit projection policy rather than an overloaded physical
column name.

Feature gate: strict new schemas, all comparison modes, drafting, portable
suites, duplicate-member and pointer-escaping fixtures, missing/container
failures, summary-safety checks, full `make check`, blind review and exact
built-wheel CI.

### Feature 2: XML per-field selectors

Add a versioned mapping from each logical field to either:

- one exact record attribute QName; or
- one bounded, root-relative sequence of child-element QNames ending in a
  text-only leaf.

The grammar must be smaller than XPath: no wildcard, descendant axis,
predicate, parent step, function, text concatenation or namespace discovery.
Every intermediate child and final leaf must be unique within the record;
missing or repeated matches fail. An element leaf remains attribute-free,
child-free text. An attribute selector reads exactly one attribute and does not
apply DTD defaults because declarations remain forbidden. Record-level
attributes not selected by policy and branches not selected as fields need an
explicit closed rule in the contract; the safest v1 rule is to reject them so
that ignored source content cannot silently widen.

This is substantial because bounded nested traversal interacts with streaming
element lifetime, namespace identity, structural ambiguity, resource limits,
schema discovery, drafting, suites and each comparison engine. The released
direct-child projection remains unchanged when no field-selector policy is
present.

Feature gate: strict new schemas, qualified and unqualified attribute cases,
default-namespace distinction, nested-leaf uniqueness, mixed-content and
unselected-content failures, depth/node/text enforcement, streaming-removal
regressions, all comparison modes and engines, full `make check`, blind
security review and exact built-wheel CI.

### Feature 3: XLSX defined-name range projection

Add an exact locator for one workbook-scoped defined name. Resolve the name
without case folding and accept it only when its definition has one destination
consisting of one existing local worksheet plus one bounded rectangle with a
header and at least one data row. Normalize absolute references to the same
canonical worksheet/range evidence used by explicit rectangles.

Reject sheet-local names, reserved built-ins, constants, formulas, dynamic
references, multiple destinations, whole-row/whole-column references, external
links and ambiguous or malformed definitions. Reuse the released ZIP audit,
read-only cell streaming, scalar rules and formula/error rejection; a defined
name selects cells but does not calculate or validate workbook meaning.

This is substantial because defined names introduce separate package metadata,
scope and reference grammars and must be carried safely through drafting,
portable suites, exact evidence and every comparison mode. Released explicit
rectangles and named tables remain unchanged.

Feature gate: strict new schemas; exact-scope, quoting, absolute-reference and
normalization fixtures; hostile duplicate, external, dynamic, union and
reserved-name cases; formula/error/ZIP/resource-limit regressions; all
comparison modes and engines; summary-safe metadata; full `make check`, fresh
blind review and exact built-wheel CI.

## Train-wide design consequences

- Freeze a separate contract before each implementation. Do not encode all
  selectors into a generic query language or shared mini-AST.
- Deepen `inputs.py` and the existing locator/preflight/suite seams. Reuse the
  current RFC 6901 evaluator, QName expansion, XLSX archive audit, normalized
  range logic and typed-row readers before adding modules or dependencies.
- Make field selection part of the effective policy and its fingerprint. Two
  recipes that select different source values must never share policy identity.
- Preserve recipe versions 1--3 and every released schema byte. New strict
  schema versions must prove that the corresponding selector is actually in
  use rather than merely admitting optional metadata.
- Full evidence may identify declared selectors and resolved ranges as required
  for reproducibility. Summary-safe results must omit field paths, attribute
  names, defined names, worksheets, ranges, source paths, keys and values.
- Selection failure is invalid input, never an inferred null, exclusion,
  tolerance change or repair suggestion.
- Qualify both memory and SQLite engines wherever the mode offers both. The
  projected typed rows and canonical comparison evidence must be identical.
- Each feature earns a coherent pushed checkpoint. Candidate and release work
  begins only after all three checkpoints and a fresh combined Standards/Spec
  review pass.

## Threats

- **Policy ambiguity:** overloading existing column mappings could make a
  physical field name indistinguishable from a selector. Use a new versioned
  projection member with one closed selector grammar per format.
- **Silent omission:** nested objects, XML branches or workbook definitions can
  contain data outside selected fields. Require an explicit closed record
  shape for JSON/XML and exact one-rectangle resolution for XLSX; do not imply
  completeness beyond the declared projection.
- **Resource amplification:** many JSON pointers can repeatedly traverse large
  records, nested XML can retain subtrees and defined-name resolution reads ZIP
  metadata. Bound selector count and depth, retain existing input/node/text/ZIP
  limits and benchmark machine-specific time and memory before claiming scale.
- **Namespace confusion:** XML default namespaces do not apply to unprefixed
  attributes. Test element and attribute QName expansion separately and never
  compare source prefixes as identity.
- **Spreadsheet indirection:** a defined name may conceal a formula, union,
  external reference or local scope. Accept one static workbook-scoped local
  rectangle only; reject anything openpyxl cannot resolve exactly.
- **Disclosure:** selectors often reveal business field and sheet names. Keep
  them out of summary-safe projections even when they appear in raw effective
  policy or evidence.
- **Compatibility drift:** parser or openpyxl upgrades can change malformed
  input handling. Pin byte fixtures for canonical policy/evidence and hostile
  format fixtures across Python 3.11--3.14, macOS, Windows and Linux.

## Non-goals

- JSONPath, Relative JSON Pointer, wildcards, recursive descent, inferred
  flattening, container serialization or missing-value defaults.
- XPath, XQuery, XML Schema validation, DTD defaults, entity processing,
  XInclude, mixed-content extraction or XML canonical equality.
- Dynamic XLSX names, formulas, unions, external workbooks, sheet-local names,
  whole-row/column ranges, recalculation, macros, editing or repair.
- A cross-format selector language, schema inference, automatic mapping,
  generated approval, migration approval or cutover authorization.
- Changes to comparison modes, scalar encodings, outcome reduction, released
  result schemas, historical bundle readers or CLI exit codes.

## Recommendation and uncertainty

Adopt these three features as the 1.9 train, in JSON, XML, XLSX order. The first
two establish the format-specific policy model for logical fields; the third
completes the same explicit-selection theme at workbook range level without
pretending a defined name is always a range.

The main design uncertainty is where the new field-selector mapping belongs in
the strict recipe while recipe versions 1--3 remain frozen. The contract phase
should compare a new versioned top-level projection declaration with a
format-specific locator suffix, choosing the representation that enters the
effective-policy fingerprint and portable suites without changing existing
locator interpretation. A locator-only encoding is compact but risks exposing
field policy in path-like source strings; a recipe declaration is clearer and
more reviewable. This research recommends the recipe declaration, but does not
freeze its JSON shape.

There is a second, narrower uncertainty around openpyxl read-only exposure of
defined names. Implementation should inspect the workbook package metadata
directly if necessary, as 1.8 did for named tables, while still using
openpyxl's reference tokenizer/range utilities where their exact behavior can
be pinned. That is an implementation question, not a reason to broaden the
accepted defined-name subset.
