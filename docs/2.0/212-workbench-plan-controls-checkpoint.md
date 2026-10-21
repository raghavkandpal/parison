# Workbench schema controls and input handoff

Date: 21 October 2026

Status: **implementation qualified at `77b05ab`; human and combined release reviews remain**

Plans derives controls from the installed recipe schemas for versions 1--6.
Objects, named policy maps, ordered arrays, booleans, constrained choices,
strings and exact JSON numbers remain explicit. Conditional column and measure
fields follow the schema's declared type, comparison and operator choices.
Adding a field starts an incomplete draft rather than supplying policy choices.
Required constants are displayed; optional settings may be added or removed.

The exact imported JSON remains untouched until field edits are explicitly
applied. Text and choice changes stay pending until Apply field edits; adding
or removing a field applies pending changes first. Batches of up to 128 edits
are applied atomically in Python to the current source and return a reformatted
CLI-native JSON draft. Existing integers and numeric literals never pass
through JavaScript serialization. The source editor remains available for
every recipe version. Refreshing controls only reads its current text.
Controls stop at 4,096 fields or 32 path segments; larger validated recipes
retain source editing and draft export.

Every edit invalidates the displayed policy identity and effective policy,
and disables download until the authoritative Python loader accepts the current
draft. The effective policy view includes loader defaults without inserting
them into source JSON. Asynchronous edits, import, validation and clear actions
are revision-checked, including native picker responses that arrive after a
clear or newer import. Source import validates one exact read. Controls use
text DOM APIs for policy names and values.

Local input locations are separate from policy JSON. The closed input-location
route checks explicit workspace-relative paths or released JSON, XML, XLSX and
SQLite locators, existing files or supported partitions, and symlink rejection.
Copying these locations to Run does not select a recipe or begin preflight or
execution. Users save the reviewed draft and choose its recipe path in Run.

New control and edit routes retain the host's capability, Origin, Host,
content-type and request-size guards. They do not persist drafts or execute
commands. The control description and field-edit requests are transient UI
messages; downloaded recipes use only the released recipe language.

## Verification

- All six recipe versions retain their policy identity after field edits are
  reversed, with omitted settings still omitted.
- Regression coverage includes conditional schema branches, every control
  family, hostile strings and property names, integers beyond JavaScript's safe
  range, malformed edits, non-finite numbers and bounded control generation.
- Host tests cover closed control/edit/input routes, unchanged source files,
  rejected input locations and explicit input copying.
- Full local `make check` passes 421 tests with Python 3.14, Ruff, jsonschema,
  openpyxl and Polars installed.

Fresh rendered inspection at desktop and narrow-window sizes found no
horizontal overflow. An explicitly labeled
[unfamiliar-agent proxy trial](../../studies/workbench-plans-01/agent-trial-01-report.md)
completed the task and identified picker, wording and interaction corrections.
Independent Standards/Spec review cleared the implementation after those
corrections. Exact implementation commit
`77b05abbe16e87ef55d114f272f4b9906883a01b` passed the complete
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39570203040)
on Python 3.11--3.14 with macOS and Windows smoke, and the
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39570191438).
Integration is tracked in [PR #57](https://github.com/raghavkandpal/parison/pull/57).
Proxy evidence does not establish human usability or policy approval; a human
review of the full Plans workflow remains part of the release gate.
