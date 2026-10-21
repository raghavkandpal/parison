# Workbench schema controls and input handoff

Date: 21 October 2026

Status: **implemented locally; interface review and qualification in progress**

Plans derives controls from the installed recipe schemas for versions 1--6.
Objects, named policy maps, ordered arrays, booleans, constrained choices,
strings and exact JSON numbers remain explicit. Conditional column and measure
fields follow the schema's declared type, comparison and operator choices.
Adding a field starts an incomplete draft rather than supplying policy choices.
Required constants are displayed; optional settings may be added or removed.

The exact imported JSON remains untouched until an explicit field edit. Each
edit is applied in Python to the current source and returns a reformatted
CLI-native JSON draft. Existing integers and numeric literals never pass
through JavaScript serialization. The source editor remains available for
every recipe version. Refreshing controls only reads its current text.
Controls stop at 4,096 fields or 32 path segments; larger validated recipes
retain source editing and draft export.

Every edit invalidates the displayed policy identity and effective policy,
and disables download until the authoritative Python loader accepts the current
draft. The effective policy view includes loader defaults without inserting
them into source JSON. Asynchronous edits, import, validation and clear actions
are revision-checked. Controls use text DOM APIs for policy names and values.

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
- Full local `make check` passes 418 tests with Python 3.14, Ruff, jsonschema,
  openpyxl and Polars installed.

Fresh rendered inspection, an explicitly labeled unfamiliar-agent proxy trial,
independent Standards/Spec review and exact-commit built-wheel CI complete the
remaining qualification evidence. Proxy trials do not substitute for a real
human usability study or establish policy approval.
