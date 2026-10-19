# XLSX defined-name projection contract

Status: **implementation contract**

## Locator and exact scope

```text
xlsx:path/to/export.xlsx#defined-name=OrdersExport
```

The `xlsx:` prefix, local `.xlsx` regular file, `#defined-name=` selector and
nonempty exact name are mandatory. The name is matched without case folding
against openpyxl's workbook-level defined-name collection. It must be globally
workbook-scoped. Worksheet-local definitions, implicit active-sheet lookup and
fallback between scopes are rejected.

The selected name must be non-reserved and no more than 255 UTF-8 bytes.
Names beginning with the reserved `_xlnm.` namespace are rejected
case-insensitively. Duplicate global names or conflicting global/local names
are invalid workbook metadata even if openpyxl would expose only one value.
The workbook package is audited before exact lookup so duplicate declarations
cannot be normalized away silently.
Defined-name metadata must use an ASCII-compatible XML encoding; DTD and
entity declarations are rejected before XML parsing or workbook loading.

Released explicit rectangle and exact named-table locators remain unchanged.

## Static range resolution

The definition must be one static range whose destination iterator yields
exactly one pair: one existing local worksheet and one cell reference. The
reference must resolve to one bounded rectangular range containing exactly one
header row and at least one data row. Absolute markers and quoted worksheet
names are accepted through openpyxl's defined-name parser; the resolved range
is normalized to the released `A1:F1000` evidence form.

Constants, formulas, dynamic or relative references, unions and multiple
destinations, external workbook references, whole-row or whole-column ranges,
3-D references, malformed destinations and missing worksheets fail closed.
Parison never evaluates, recalculates, repairs or expands a definition from
populated cells.

The first selected row is the header. Every remaining row is one record,
including an all-blank row. Existing requirements for nonempty unique string
headers, formulas, error cells, dates, scalar projection and timezones apply
unchanged.

## Package safety, workflows and evidence

The released physical-byte, decoded-ZIP-byte, member-count, duplicate-member,
encryption, symlink and selected-row limits apply before defined-name metadata
is trusted. Workbook loading remains read-only with external links disabled;
cell iteration stays bounded to the resolved rectangle.

Defined-name inputs require `semantic-scalar-v1` and work under keyed,
aggregate and multiset comparison with both memory and SQLite execution.
Portable suite-v2 locators preserve the exact name while resolving only the
plan-relative workbook path. Drafting may preserve an explicitly supplied
defined-name locator but never discovers or chooses one implicitly.

Full/raw evidence records exact `defined_name`, resolved `worksheet` and
normalized `range`, plus the released workbook digest, physical/decoded byte
counts and ZIP compression metadata. Summary comparison results omit the
defined name, worksheet and range. Strict preflight schemas v19--v21 cover
keyed, aggregate and multiset defined-name inputs for recipe versions 1--3.
Strict schemas v22--v24 carry the same input evidence with field projection
for recipe versions 4--6, without changing v1--v18.

## Compatibility and non-goals

Recipe versions 1--6, policy fingerprints, comparison semantics, canonical
scalar and row bytes, result schemas, historical bundle readers, CLI JSON and
exit codes remain unchanged. A defined name is an explicit record-range
locator, not logical-field policy.

Dynamic names, constants, formulas, unions, sheet-local names, reserved
built-ins, external references, tables by alias, macros, `.xls`, `.xlsb`,
`.xlsm`, workbook editing, formula evaluation, repair, extraction truth,
approval and cutover authorization are out of scope.
