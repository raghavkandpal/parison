# Unified Workbench host checkpoint

Date: 20 October 2026

Status: **host foundation implemented locally; qualification pending**

`parison workbench --workspace DIRECTORY` now starts one Python-owned application
on numeric loopback and an OS-assigned port. A high-entropy launch capability is
placed in the URL fragment, removed by the page, and required on the closed
session route. The host validates the workspace, rejects symlinks, validates
Host, suppresses request logs, sends no-store and restrictive browser headers,
and exposes no filesystem, shell, execution or network-fetch route.

The shell names the six product activities but does not implement them yet.
The earlier `evidence` and `plan` commands have been removed from the active CLI;
their tested rendering modules remain implementation inputs for migration behind
the unified host.

Focused tests cover numeric-loopback binding, capability rejection and unsafe
workspace rejection. The next slice must add strict Origin checking and a
read-only verified-evidence route before any mutation or execution route exists.
