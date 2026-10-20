# Unified Workbench Plans checkpoint

Date: 20 October 2026

Status: **qualified at exact implementation commit `462eeac`**

The unified `parison workbench --workspace DIRECTORY` application now exposes
Plans as its second live activity. A user can enter a workspace-relative recipe
path or use a fixed native file chooser on macOS and Windows. Python rejects
absolute paths, traversal, symlinks, non-files and selections outside the
configured workspace before using the existing recipe loader and policy
explanation service.

The browser receives the recipe's exact UTF-8 source, recipe version,
comparison mode and effective policy SHA-256. It exposes the source in a local
JSON editor and shows equivalent CLI commands. Edits remain browser-local and
can only be downloaded as `plan.json`; the interface labels the download an
unapproved draft and directs the user to `parison validate-recipe`. Clearing a
plan removes its path, source and derived metadata from the page without
changing the original recipe.

This slice adds no recipe language, schema, persistence, execution, filesystem
listing or generic file-access endpoint. Browser JSON parsing is only immediate
syntax feedback and is never presented as authoritative Parison validation.
The Python service validates only the recipe opened from the workspace.

The implementation reuses one `plan_projection` application seam from both the
generated plan prototype and unified host, preserving exact source text and a
single policy implementation. Focused tests cover the projection, native picker
confinement, closed API route, traversal rejection and absence of source paths
from the response. Browser verification covers activity navigation, a real
recipe load and explicit clear behavior.

The next slice should validate edited plan text through a closed, non-persisting
Python route. Local execution remains deferred until bounded concurrency,
shutdown and an explicit parity-tested run contract exist.

Exact commit `462eeac3b9e21b641df2070a4cdff8bfbde91c94` passed the complete
[built-wheel matrix](https://github.com/raghavkandpal/parison/actions/runs/39398735075)
on Python 3.11--3.14 with macOS and Windows platform smoke, plus the
[quality gate](https://github.com/raghavkandpal/parison/actions/runs/39398735044).
