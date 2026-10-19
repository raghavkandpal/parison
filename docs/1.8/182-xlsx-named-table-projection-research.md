# XLSX named-table projection research

Date: 19 October 2026

Status: **contract input**

## Question

How can Parison select one named XLSX table without weakening the released
explicit-rectangle values contract or turning workbook metadata into inferred
policy?

## Primary-source findings

An OOXML workbook is a package of related parts rather than a single worksheet
document. ECMA-376 defines both the document vocabularies and their packaging,
so table identity has to be resolved through the workbook package rather than
guessed from populated cells ([ECMA-376, 5th edition](https://ecma-international.org/publications-and-standards/standards/ecma-376/)).

openpyxl represents each worksheet's tables with the dictionary-like
`ws.tables` collection. Its documented lookup returns a table by name, and the
selected object's `ref` is the cell range that the table currently covers
([openpyxl worksheet tables](https://openpyxl.readthedocs.io/en/stable/worksheet_tables.html#get-table-by-name-or-range)).
The implementation stores tables under `table.name`; `TableList.get(name=...)`
delegates to the ordinary dictionary lookup, while range lookup is a separate
branch. Name selection is therefore exact and does not require case folding,
prefix matching, or range discovery
([openpyxl `TableList` source](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/worksheet/table.html#TableList)).

openpyxl documents table names as workbook-unique and table headings as
strings. It also warns that the table-column headings and corresponding
worksheet cells must agree or Excel may treat the file as invalid
([openpyxl worksheet tables](https://openpyxl.readthedocs.io/en/stable/worksheet_tables.html#creating-a-table)).
Its table model separately exposes the bounded `ref`, `headerRowCount`,
`totalsRowCount`, `totalsRowShown`, table-column names, calculated-column
formulas and totals-row formulas
([openpyxl table source](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/worksheet/table.html#Table)).
Those fields are structural input metadata; filters and styles are presentation
metadata and do not define which stored values Parison compares.

There is an important implementation constraint. In read-only mode openpyxl
constructs `ReadOnlyWorksheet` objects and skips the normal worksheet binding
path that loads table definitions; normal mode binds table parts after loading
the worksheet
([openpyxl reader source](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/reader/excel.html#ExcelReader.read_worksheets)).
Switching the whole adapter to normal mode merely to discover a table would be
a material resource regression: openpyxl says ordinary memory use can be about
50 times the input file size, while read-only mode significantly reduces
memory use
([openpyxl performance documentation](https://openpyxl.readthedocs.io/en/stable/performance.html)).

Formula handling must remain based on cell content, not cached results.
`load_workbook(data_only=False)` exposes formulas, whereas `data_only=True`
returns the value last stored when Excel read the sheet; `keep_links=False`
also avoids preserving cached external-workbook data
([openpyxl `load_workbook` API](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html#openpyxl.reader.excel.load_workbook)).

## Recommended contract consequences

- Add one locator form that is syntactically disjoint from the released
  `xlsx:path#worksheet!range` form, for example
  `xlsx:path/to/export.xlsx#table=Orders`. The selector is one non-empty exact
  table name; it never accepts a worksheet hint, case-insensitive fallback,
  table-number fallback, wildcard, named range, used range, or active sheet.
- Resolve the exact name across worksheet tables, require exactly one match,
  and take the selected openpyxl `Table.ref` as the sole rectangle. Record the
  resolved worksheet and normalized range; never expand or shrink the range
  from populated cells.
- Require the table to have exactly one header row and at least one data row.
  Continue the released checks that header cells are non-empty unique strings.
  Also require the table column-name sequence to match those header cell values
  exactly, so corrupt or stale table metadata fails closed instead of choosing
  an implicit schema.
- Reject a declared totals row. A totals row is structurally distinct from a
  record row, and silently including or excluding it would add inference. Reject
  calculated-column and totals-row formulas in table metadata, and retain the
  released formula/error-cell rejection over every cell in the resolved
  rectangle with `data_only=False`.
- Keep the released `semantic-scalar-v1` conversion, date handling, all-blank
  row behavior, physical/decoded ZIP limits, member-count and encryption checks,
  whole-file digest, row limit, symlink rejection, and explicit workbook close.
  The table selector changes only how the rectangle is obtained.
- Preserve streaming value extraction. Because openpyxl read-only worksheets do
  not expose bound tables, isolate a bounded, pinned-version metadata resolver
  that parses only workbook/worksheet relationship and table parts into
  openpyxl table objects and uses openpyxl's exact `TableList` lookup and
  `Table.ref`; then reopen or retain the workbook in read-only mode for cells.
  Do not load every workbook cell in normal mode as an undocumented side effect
  of table discovery.
- Full evidence may add the exact table name together with the resolved
  worksheet and range. Summary-safe output must continue to exclude source
  paths and physical selection names. Keyed, aggregate and multiset preflight
  need new strict schema versions; schemas v1--v12 remain byte-for-byte
  unchanged.
- Drafting, portable suites and all three comparison modes should preserve the
  table selector verbatim except for the existing suite-relative workbook-path
  resolution. The table name is workbook metadata, not a policy suggestion or
  approval.

## Threats

- A small compressed package can expand into large XML, and ordinary openpyxl
  loading can amplify memory further. Existing physical/decoded/member limits
  must run before metadata parsing, and table discovery must remain bounded.
- Duplicate ZIP names, malformed relationships, missing table parts, duplicate
  table identities, invalid refs, headerless tables, totals rows and metadata/
  cell heading disagreement can make selection ambiguous. Every such condition
  should fail closed.
- Formula caches, calculated columns, totals formulas and external-link caches
  can represent stale or externally derived state. They must not enter the
  values projection.
- Hidden rows or columns, filters, styles and the table's displayed extent can
  make the workbook look different from its stored rectangle. Parison compares
  the stored cells in `Table.ref` only and makes no display-equivalence claim.
- openpyxl's table-binding helpers are partly internal and can change. The
  dependency remains exactly pinned, and built-wheel tests must exercise table
  discovery on every supported Python and platform.

## Non-goals

- Table discovery, fuzzy naming, worksheet inference, named ranges or dynamic
  print areas;
- applying filters, hidden-state rules, styles, sort state or display behavior;
- totals-row interpretation, calculated columns, formula evaluation, cached
  formula acceptance, query refresh or external connections;
- `.xls`, `.xlsb`, `.xlsm`, macros, workbook editing or repair;
- changing comparison modes, recipe semantics, canonical scalar/row bytes,
  exit codes, evidence meaning or historical bundle readers;
- treating a successful projection as extraction truth, policy approval,
  migration approval or cutover authorization.

## Checkable implementation gate

The feature gate should cover exact-name success and wrong-case failure,
multiple worksheets, absent and malformed table metadata, invalid or unbounded
refs, header/table-column mismatch, headerless and totals-row tables, cell and
table-metadata formulas, errors, blank rows, date/scalar boundaries, row and ZIP
limits, suite relocation, drafting, full versus summary-safe evidence, and all
three comparison modes. New installed preflight schemas must be strict without
modifying v1--v12. Completion requires a fresh blind review, full `make check`,
exact-commit built-wheel CI on Python 3.11--3.14 across Linux, macOS and Windows,
and a fresh-wheel XLSX named-table smoke.

All sources above were accessed 19 October 2026.
