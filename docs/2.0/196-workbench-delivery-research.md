# Workbench delivery architecture research

Date: 20 October 2026

Status: **2.0 architecture recommendation; implementation input, not a released contract**

Sources were accessed on 20 October 2026. External claims below use primary
sources: official project documentation, standards and first-party security
guidance. Repository documents are the authority for Parison's own boundaries.

## Question

What application architecture should Parison Workbench use so that a user can
launch it and run the existing Python engine without separately installing or
managing Python, while preserving local-first execution, deterministic evidence,
strict JSON, zero custody and CLI compatibility?

This narrows the product direction already established by the
[workbench product research](194-verification-workbench-product-research.md) and
[development direction](195-verification-workbench-development-direction.md).
It decides the runtime host and packaging seam. It does not approve new
verification semantics or replace the feature gates in those documents.

## Recommendation

Use a two-stage browser delivery architecture owned entirely by the installed
Python package:

1. **First slice: generated static navigator.** A Parison command verifies an
   explicitly selected bundle, writes a self-contained deterministic HTML view
   containing only its summary-safe projection, and opens that file in the
   system browser. It has no server, JavaScript-to-Python bridge or execution
   control.
2. **Execution slice: Python-hosted loopback application.** When interactive
   execution is added, the same installed package starts a narrowly routed
   ephemeral loopback server, opens the browser and invokes shared application
   services in-process.

Do not begin with Tauri or Electron. Package the interactive stage initially as
a PyInstaller **one-folder** application per supported desktop platform only
after the static navigator validates the information architecture and disclosure
boundary.

The installed launch path should be:

```text
installed `parison` command (first slice)
        |
        +-- verify bundle -> summary-safe projection -> deterministic HTML file
                                                        |
                                                        +-> system browser

later signed/packaged launcher
        |
        v
bundled Python + Parison package
        |
        +-- workbench adapter -> shared application services -> verification core
        |                              ^
        +-- CLI adapter ---------------+
        |
        +-- 127.0.0.1:<ephemeral-port> -> vendored HTML/CSS/JS in system browser
```

In the first slice, the generated document is a portable view, not the
application's authority: it can only render the verified projection embedded at
generation time. In the later interactive slice, the Python process is the
application, not a sidecar owned by a second runtime.
It starts a narrowly routed local HTTP server, opens the system browser, calls
the same Python application services as the CLI, and shuts down explicitly.
The UI never invokes shell command strings, imports CLI presentation code,
scrapes terminal output or reimplements outcome semantics.

The first slice should be an ordinary installed CLI subcommand and use Python's
standard browser launcher. For later interactive development, expose an explicit
module entry point such as `python -m parison.workbench`. For end users, the
packaged launcher includes the interpreter and required modules. PyInstaller
documents that its bundle includes
the active Python interpreter and lets users run without installing Python or
modules; it also documents that bundles are OS-, architecture- and Python-specific
and therefore must be built on each target platform
([PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html)).

Start with one-folder rather than one-file packaging. PyInstaller recommends
getting one-folder operation working first because collected files and failures
are easier to inspect; it also notes that one-file startup is slower because of
its packaging model. One-folder avoids making temporary extraction part of the
first product security and interruption boundary
([PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html),
[one-file security validation](https://pyinstaller.org/en/latest/advanced-topics.html#security-validation-in-onefile-mode)).

## Why this is the smallest coherent architecture

### Static output is the right first delivery boundary

The navigator's first job is to prove verification-before-rendering,
summary-safe disclosure and useful information architecture. A generated file
can prove all three without introducing a live origin, session authentication,
process cancellation or writable API. It is portable and independently
inspectable, and identical verified inputs can be tested for byte-identical
HTML.

Static generation cannot run Python after the page has loaded. That is a useful
constraint for the read-only slice, not the final answer to local execution.
Do not simulate execution in browser code or add file-origin bridges. Graduate
to the loopback host only when the product adds an explicit Run operation.

### Python remains the semantic owner

The current engine is a Python package with a stable CLI and versioned JSON
schemas. A Python host can call extracted application services directly, retain
native Python types and exceptions inside the trusted boundary, and reuse the
existing verification, bundle, catalog and safe-publication modules. This makes
CLI and Workbench peer adapters as required by the existing direction.

A subprocess is useful only as a disposable workflow probe. Making CLI JSON the
permanent internal RPC protocol would add process lifecycle, cancellation,
stream framing and compatibility behavior while encouraging the UI to couple to
commands rather than tasks. If a subprocess is ever required for fault isolation,
Python recommends argument sequences with the default `shell=False`; shell use
requires separate security care
([Python `subprocess` documentation](https://docs.python.org/3/library/subprocess.html#security-considerations)).

### The system browser is sufficient for the first product

Python's standard `webbrowser` module is specifically a high-level interface for
displaying web documents and normally opens the configured browser appropriately
([Python `webbrowser` documentation](https://docs.python.org/3/library/webbrowser.html)).
Using it avoids shipping Chromium, Node.js, Rust, a native webview abstraction or
platform-specific UI bindings before evidence shows that a dedicated window is
valuable.

Loopback pages are treated as potentially trustworthy origins by the web platform,
so secure-context-only browser capabilities can remain available without local
TLS ([MDN secure contexts](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts)).
The browser is nevertheless a separate, potentially hostile client; “local” is
not an authentication decision.

### Packaging solves “Python runs automatically” without a second runtime

PyInstaller explicitly collects the script, imported modules, libraries and
Python interpreter into a distributable folder or executable. It is not a cross
compiler, so release CI must produce and smoke-test separate Windows, macOS and
Linux artifacts on their corresponding systems
([PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html)).
This matches Parison's existing built-wheel cross-platform discipline while
making interpreter installation invisible to users.

PyInstaller should be a release/build dependency, not a runtime dependency of
the `parison` wheel. The existing wheel and CLI remain independently installable;
the desktop bundle is another tested distribution of the same package.

## Alternatives considered

| Option | Fit | Decision |
| --- | --- | --- |
| Generated static HTML + system browser | No listener or bridge; deterministic and portable; cannot execute after generation | **Choose for the first navigator slice** |
| Python process + system browser + loopback UI | One runtime owns semantics; stdlib launch/server primitives; self-contained packaging; browser accessibility and developer tools | **Choose when interactive execution enters 2.0** |
| Tauri shell + packaged Python sidecar | Dedicated window and capability system, but adds Rust/JavaScript build surfaces and a second process protocol | Defer until a measured need for native windowing, tray integration or installer behavior |
| Electron shell + Python child | Mature desktop APIs, but ships Chromium and Node and adds preload/IPC/security surfaces while Python still owns semantics | Reject for the initial workbench |
| Native Python widget toolkit | Direct Python calls, but creates platform widget, accessibility, styling and packaging work with little reuse of existing HTML evidence views | Reject for the initial workbench |
| Browser-only/Pyodide engine | No local server, but moves Python and file handling into a constrained browser runtime and creates a new compatibility/performance target | Reject; it is not the existing installed engine |
| CLI subprocess behind any UI | Fast prototype and strong black-box parity | Prototype only; not the permanent semantic seam |

Tauri officially supports external “sidecar” binaries and names Python programs
packaged with PyInstaller as a use case. It requires target-specific binary names
and explicit execute/spawn capabilities
([Tauri sidecars](https://tauri.app/develop/sidecar/)). That is a credible future
shell, but it does not eliminate Python packaging and would add Rust, webview,
sidecar protocol and capability-policy maintenance now.

Electron's official process model gives each window a renderer and uses separate
utility processes for CPU-intensive or crash-prone work. Its security guidance
requires context isolation, sandboxing, restricted navigation/window creation,
validated IPC senders and no Node integration for remote content
([Electron process model](https://www.electronjs.org/docs/latest/tutorial/process-model),
[Electron security checklist](https://www.electronjs.org/docs/latest/tutorial/security)).
Those are useful controls if Electron is justified, but they are additional
product surfaces rather than solutions to Parison's Python-hosting requirement.

## Required delivery boundaries

### 1. Application-service boundary

Before enabling execution, extract or identify a narrow Python service for each
screen operation. Inputs and outputs must be typed domain objects or strict,
versioned JSON projections. Services own validation, effective policy,
verification, safe publication and outcome reduction. Adapters own only request
translation and presentation.

The first execution slice should support one already released recipe/run path,
not a generic command runner. Its parity gate is semantic identity between CLI
and Workbench results plus byte identity for every canonical artifact.

### 2. Static document boundary

The generated navigator must contain only the strict summary-safe projection
produced after successful verification. Assets must be local and deterministic;
there are no remote fonts, scripts, images, analytics or fetches. Prefer no
JavaScript for the first view; if progressive disclosure requires it, vendor a
fixed script and keep all data embedded and inert. Rendering must escape content
as text, never interpolate evidence into executable markup. The output is a new
no-overwrite artifact and never mutates the verified source bundle.

The file must visibly identify itself as a generated view, record the source
bundle identity and renderer version without exposing its path, and state that
PASS means agreement under the displayed policy rather than truth or approval.

### 3. Later loopback boundary

The server must:

- bind the numeric loopback address `127.0.0.1`, never `0.0.0.0`, and ask the OS
  for an ephemeral port;
- serve only embedded/vendored assets and closed, method-specific API routes;
- generate a high-entropy per-launch capability, put it in the initial URL
  fragment rather than query or logs, and require it on every API request;
- validate `Host` and `Origin`, emit no permissive CORS headers, reject unexpected
  content types, and use POST for mutations;
- set a restrictive Content Security Policy, `frame-ancestors 'none'`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and
  `Cache-Control: no-store` for sensitive responses;
- never expose a general filesystem route, command route, URL fetcher or static
  directory traversal surface;
- bound bodies, concurrency, execution time, response detail and shutdown; and
- clear the session capability and sensitive in-memory state at shutdown.

The IETF's native-app guidance recommends numeric loopback literals over
`localhost`, ephemeral ports, loopback-only listeners and short listener
lifetimes because name resolution and other local applications remain relevant
threats ([RFC 8252, sections 7.3 and 8.3](https://datatracker.ietf.org/doc/html/rfc8252#section-8.3)).
Although that standard addresses OAuth redirects rather than local workbenches,
the listener constraints transfer directly; this is an explicit design
inference, not a claim that RFC 8252 specifies Workbench authentication.

Python warns that `http.server` implements only basic security checks and is not
recommended for production use
([Python `http.server` documentation](https://docs.python.org/3/library/http.server.html)).
Therefore do not expose `SimpleHTTPRequestHandler` or treat loopback binding as
sufficient hardening. A small closed router built on the server primitives is
acceptable only after adversarial tests cover the controls above. If that router
stops being small, select a maintained server library through a separate
dependency and threat-model decision.

### 4. Filesystem and custody boundary

File selection grants access only to paths the user explicitly chooses for that
operation. The browser never receives arbitrary absolute paths; display names
and summary-safe identities are separate projections. The Python process opens
inputs and produces evidence using existing symlink-safe, atomic, no-overwrite
publication. Do not upload, sync, index broadly or retain source contents.

A Workbench workspace is a transparent local descriptor, not a database of
copied inputs. Recent-item convenience must store only reviewed, documented
metadata and must remain optional. Catalog internals do not become a UI API.

### 5. Evidence boundary

Every displayed bundle is verified before parsing members for presentation.
Summary-safe routes cannot return source paths, keys, values or discrepancy
samples. Sensitive drill-down is a separate explicit operation with its own
bounded response. Reruns create new immutable outputs; refresh never overwrites
the evidence under review.

### 6. Process and interruption boundary

The launcher owns exactly one server lifecycle. Closing a tab does not silently
kill an active publication. The UI can request cooperative cancellation, but the
Python service owns interruption cleanup and the final state. Crash recovery may
identify incomplete staging, but must not infer a verification outcome.

## Suggested implementation sequence

1. **Verified static navigator:** open an explicitly selected bundle, verify it,
   write deterministic self-contained summary-safe HTML, open it in the system
   browser, and cover tampered/unsupported failure paths.
2. **Information-architecture evaluation:** test the five tasks in the existing
   development direction before adding a live server.
3. **Interactive host skeleton:** Python entry point, loopback capability
   protocol, vendored static shell, explicit shutdown and no engine execution.
4. **One execution path:** invoke one released recipe service in-process, show
   bounded progress, publish through existing safe paths, then open the verified
   result. Prove CLI/Workbench semantic and canonical-byte parity.
5. **Self-contained distribution:** reproducible one-folder builds and installed
   smoke tests on Python 3.11--3.14 release CI hosts for Windows, macOS and Linux;
   document artifact composition and code-signing/notarization status honestly.
6. **Only then broaden:** schema-driven authoring and history views after their
   stable service/projection seams exist.

This sequence refines, rather than replaces, the existing three-feature train.
The host skeleton is enabling architecture, not a substantial user feature.

## Completion gates for the runtime decision

- The first installed-wheel command verifies before rendering and produces
  byte-identical HTML for identical safe inputs; the HTML makes no network
  requests and contains no sensitive fields.
- Later, launching the packaged application on each supported OS requires no
  separately installed Python, Node.js, Rust toolchain or network access.
- With network disabled, the UI loads only vendored assets and a released recipe
  can run to a verified local result.
- The same recipe and inputs through CLI and Workbench have the same outcome,
  effective policy and byte-identical canonical artifacts.
- Requests without the per-launch capability, with a foreign `Origin`, with an
  invalid `Host`, or to an undeclared route fail closed.
- Binding is observable only on numeric loopback and uses an OS-assigned port.
- Default views contain no source paths, keys, values or discrepancy samples.
- Tampered and unsupported bundles fail before member rendering.
- Cancellation and forced termination leave no published partial result and
  clean sensitive staging according to existing publication guarantees.
- The ordinary wheel, CLI JSON, schemas, exit codes and old bundles remain
  unchanged and readable.

## Threats and controls

### Browser-to-localhost request forgery

Threat: an attacker-controlled page probes the local port or submits a mutation.

Control: unguessable per-launch capability, numeric loopback, strict Host and
Origin checks, no CORS, JSON-only mutation requests and closed routes. Do not put
the capability in logs, query strings, local storage or persistent history.

### Semantic drift between adapters

Threat: forms or handlers acquire policy defaults and outcome logic.

Control: both adapters call the same application service; parity fixtures compare
effective policy and canonical output bytes. UI schemas describe presentation,
not alternative verification semantics.

### Packaged-runtime drift

Threat: hidden imports, optional format dependencies or platform libraries differ
from the wheel tested by core CI.

Control: build on every target OS; inspect bundle contents; smoke every supported
format from the packaged artifact; pin build tooling; re-download and smoke public
assets under the release checklist.

### Excess filesystem authority

Threat: a convenient workspace scan or file API discloses unrelated local data.

Control: explicit selected roots, canonical containment checks, existing symlink
rules, no browser-supplied unrestricted reads and no automatic home-directory
indexing.

### UI success implies approval

Threat: a green visual compresses policy agreement into extraction truth or
cutover authorization.

Control: render PASS with policy identity and the established disclaimer; provide
no approve, deploy, repair or cutover action.

### Runtime proliferation

Threat: a thin shell evolves into independent JavaScript/Rust orchestration and
duplicates security and release machinery.

Control: Python owns lifecycle and semantics for 2.0. Reconsider Tauri only
against measured requirements and an explicit migration decision.

## Non-goals

- hosted service, remote API, telemetry, update service or account system;
- database credentials, direct warehouse connections or embedded extraction;
- scheduling, continuous monitoring, background daemon or remote workers;
- repair, synchronization, deployment, approval or cutover controls;
- arbitrary command execution, plugin loading or user-authored Python;
- browser reimplementation of the engine or a Pyodide compatibility target;
- a generic filesystem browser or automatic indexing of user directories;
- changing released recipes, schemas, bundles, exit codes, canonical bytes or
  CLI JSON to accommodate presentation convenience; and
- choosing an installer framework, auto-update channel or commercial licensing
  mechanism before the packaged vertical slice proves the workflow.

## Decision consequence

Proceed first with the deterministic generated static navigator delivered by
the installed Python package. It is the minimum safe proof of the Workbench's
navigation and disclosure model. When execution is added, evolve the same
Python-owned adapter into a loopback application and treat PyInstaller one-folder
artifacts as a distribution experiment subject to the same exact-artifact
discipline as wheels. Keep Tauri as a documented escape hatch for a later
dedicated shell, not as the initial architecture. A CLI subprocess or generic
command bridge is not an acceptable shortcut into the permanent design.
