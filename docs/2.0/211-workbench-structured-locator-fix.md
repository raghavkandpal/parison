# Workbench structured locator fix

Date: 21 October 2026

Status: **implemented locally; qualification pending**

Run now resolves the path component of released JSON, XML, XLSX and SQLite
input locators within the workspace, then passes the original selector to the
existing input reader. Plain paths remain supported. Recipe and output paths
retain the existing workspace rule. Traversal, absolute input paths and
symlinked path components are rejected before preflight.

The focused host test covers each locator family and a complete JSON Run with
byte-identical published artifacts against direct comparison and publication.
It also checks plain paths, traversal and symlinks. Full cross-format
execution and exact-head quality and platform qualification remain. No
released syntax, recipe, schema or evidence format changes.
