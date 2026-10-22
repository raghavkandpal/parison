# Unified Workbench interface decision

Date: 20 October 2026

Status: **accepted 2.0 product and interface direction**

## Decision

Parison 2.0 presents one human application:

```sh
parison workbench
```

The application owns one local workspace and organizes the released
verification lifecycle as internal activities:

```text
Plans -> Run -> Results -> History -> Investigate -> Compare
```

Users do not launch separate generated applications for evidence and plans.
The current `parison workbench evidence` and `parison workbench plan` commands
are implementation prototypes that proved verification-before-rendering,
summary-safe disclosure, policy-byte preservation and unapproved draft export.
They are not the intended 2.0 release interface and may change or disappear
before release.

## Visual continuity

The canonical generated HTML result is the Workbench's visual baseline. The
application keeps its outcome-first hierarchy, system typography, restrained
color, bordered evidence tables, compact controls and plain-language notices.
Workbench navigation extends that document rather than replacing it with
generic dashboard chrome. Plans and Run may add task-specific controls, but the
result should still feel like the same Parison evidence surface.

## Application model

The installed Parison Python process is the application host. It invokes shared
Parison modules directly; it does not scrape terminal output or expose a generic
command runner. A browser provides the user interface through one hardened,
ephemeral numeric-loopback session. The CLI remains a peer adapter for exact
automation and reproducibility.

Opening Workbench must not itself run a comparison. Execution begins only from
an explicit local action inside the application. Each run creates new immutable
evidence and preserves the existing exit-code, canonical-byte, verification,
atomic-publication and interruption contracts.

## Required host controls

Before the unified host can replace the prototypes, it must have:

- numeric `127.0.0.1` binding on an OS-assigned port;
- a high-entropy per-launch capability required by every application request;
- strict Host, Origin, method, route, content-type and body-size checks;
- no permissive CORS, general filesystem route, URL fetcher or shell route;
- vendored deterministic assets and restrictive response headers;
- explicit workspace roots and user-selected paths rather than broad discovery;
- bounded concurrency, execution and shutdown behavior; and
- adversarial tests for request forgery, traversal, disclosure, cancellation
  and staging cleanup.

## Compatibility and migration

No released 1.x interface changes. The prototype Workbench commands are
unreleased and therefore do not create a compatibility obligation. Their tested
Python modules and rendering rules should be reused behind the unified host
where they deepen the final interface; implementation shaped solely around
generating separate applications should be removed.

## Release consequence

Do not release 2.0 with separate activity commands as the primary human
interface. Release consideration begins only after the unified application
contains a substantial verified navigator, schema-driven plan builder and
bounded local runner/history flow, with combined cross-platform qualification.
