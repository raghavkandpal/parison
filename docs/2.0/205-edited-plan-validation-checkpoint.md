# Workbench edited-plan validation checkpoint

Date: 20 October 2026

Status: **implemented locally; qualification pending**

The unified Plans activity now treats every edit as unvalidated. Editing recipe
source immediately removes the previously computed policy identity and disables
draft download. **Validate changes** sends the exact current source to one
closed endpoint, where the authoritative Python recipe loader validates it in
memory and computes the effective policy identity. A successful response
restores the recipe version, comparison mode and policy SHA-256 and enables
download of the still-unapproved draft.

The browser's JSON parser remains syntax feedback only. A syntactically valid
but semantically invalid recipe cannot be downloaded after editing. Failed
validation returns no source, key, value or detailed validation content. If the
editor changes while a request is in flight, the response cannot validate or
enable download for the newer text.

The host accepts a bounded request of at most 256 KiB and adds no persistence,
temporary recipe, filesystem access or execution. `load_recipe_text` feeds the
existing version-specific recipe loaders, so file-backed CLI validation and
Workbench text validation share the same semantic implementation.

Focused tests cover policy-identity changes, invalid edited recipes and the
closed HTTP response. Browser verification covers dirty, disabled-download and
authoritatively validated states. The next gate is bounded host lifecycle and
shutdown behavior before any Run activity is exposed.
