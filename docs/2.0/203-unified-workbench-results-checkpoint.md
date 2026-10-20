# Unified Workbench verified Results checkpoint

Date: 20 October 2026

Status: **implemented locally; qualification pending**

The unified `parison workbench --workspace DIRECTORY` application now has its
first useful Results flow. The user enters one bundle path relative to the
selected workspace. Python rejects absolute paths, traversal and symlinks,
verifies the bundle through the released evidence reader, and returns only the
existing closed `workbench_projection` fields. The browser receives no source
path, key, value, discrepancy sample or verification error detail.

The screen deliberately follows the canonical generated HTML result's visual
language: system typography, outcome-first color, bordered tables, compact
controls and restrained notices. This is the baseline for later activities,
not a temporary dashboard theme.

The responsive application shell now distinguishes the live Results activity
from planned activities, exposes local-session state, guides users to select a
complete bundle folder, and gives empty, verification-failure and verified
evidence states distinct hierarchy. The shell adds no UI framework or runtime
dependency; it remains an embedded asset served by the hardened Python host.

All API calls are closed POST routes and require an exact numeric-loopback
Origin and Host, the per-launch capability, exact JSON content type and a body
no larger than 4096 bytes. The page clears the capability fragment before
making requests. Unexpected methods, routes, origins, capabilities and unsafe
bundle paths fail closed; no CORS, static filesystem, URL-fetch, shell,
mutation or execution route exists.

Focused tests cover origin and capability rejection, loopback binding, verified
summary-safe presentation, traversal and symlink rejection, tamper refusal and
unsafe workspace rejection. The next slice should reuse authoritative recipe
loading and policy explanation in a unified Plans activity. Execution remains
deferred until the host has bounded concurrency and shutdown plus an explicit
run contract and parity gate.
