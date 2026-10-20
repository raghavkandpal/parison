# Verified navigator contract

Date: 20 October 2026

Status: **active 2.0 feature contract**

## Purpose

The first Parison Workbench feature is a generated local application for one
existing evidence bundle. The installed Python package is the application
runtime: `parison workbench` invokes released verification and inspection,
then publishes a browser-readable view. It does not require Node.js, a native
shell, a server, or network access.

This is the first feature in the proposed Define → Run → Investigate → Compare
train. It establishes the verified display seam before plan editing or live
execution is added.

## Command

```sh
parison workbench evidence RUN_DIRECTORY --output APPLICATION_DIRECTORY [--open]
```

The command verifies the selected bundle, obtains the released summary-safe
inspection projection, narrows it to the closed workbench field set, renders
one deterministic script-free `index.html`, and atomically publishes a new
directory. It opens the local file only when `--open` is explicit.

Verification failure publishes nothing. Publication failure or interruption
removes private staging. An existing or symlink output is rejected.

## Display and disclosure

The page may contain outcome, completeness, schema and suite versions,
summary counters, resource limits, runtime identifiers, policy/input/bundle
digests, and manifest member names. It excludes source paths, policy keys,
source values, discrepancy samples, detailed problem strings, suite case
identifiers, and selection locators.

All rendered labels and values are HTML-escaped. The page contains no script,
remote asset, active request, or embedded source artifact. It prominently
states that PASS means agreement under the displayed policy, not extraction
truth, approval, or cutover authorization.

## Compatibility

The workbench consumes released bundle readers and schemas without changing
them. It does not alter recipe semantics, comparison results, canonical bytes,
bundle membership, exit codes, or existing CLI JSON. Its output is a derived
human view, not evidence and not a versioned interchange format.

The interface is deliberately one command and one generated page. A loopback
adapter is deferred until live plan editing or structured execution progress
requires it; a native wrapper is deferred until packaging evidence shows that
a browser-delivered local application is insufficient.

## Non-goals

- creating or editing plans;
- executing, scheduling, cancelling, or retrying comparisons;
- discovering bundles by scanning a filesystem;
- reading raw evidence or reopening source inputs;
- remote connections, credentials, telemetry, updates, or hosted custody;
- approval, repair, deployment, or cutover actions;
- replacing the CLI.

## Completion gate

- identical verified evidence produces byte-identical HTML;
- tampered evidence is rejected before rendering;
- secrets from raw inputs and policies do not enter the page;
- hostile text is escaped and no JavaScript is emitted;
- publication is atomic, no-overwrite, symlink-safe, and interruption-clean;
- the focused test and repository quality gate pass.
