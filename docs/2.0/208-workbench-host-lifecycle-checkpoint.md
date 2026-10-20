# Workbench host lifecycle checkpoint

Date: 20 October 2026

Status: **implemented locally; exact-commit qualification pending**

The unified Workbench host now owns an explicit, bounded session lifecycle.
At most eight request handlers run concurrently; excess local connections wait
behind the equally bounded listener queue rather than creating unbounded
threads. Handler threads are daemonized so an abandoned browser connection
cannot keep the application process alive after shutdown, while the shutdown
controller waits for the single cooperative Run operation to stop safely.

The authenticated, origin-checked `POST /api/shutdown` route is the only remote
lifecycle mutation. It accepts only an empty JSON object, immediately clears
the in-memory launch capability, returns one closed `stopping` response and
then stops the server loop from a separate thread. Requests without the exact
session capability and origin still fail closed. The browser exposes this as
an explicit **Stop workbench** action and disables its local controls once the
host accepts shutdown. Ctrl-C remains an equivalent host-owned stop path.

Closing a browser tab does not stop the host and shutdown does not infer a
verification outcome. This checkpoint adds no execution, cancellation,
filesystem, persistence or discovery endpoint. It changes no recipe, schema,
bundle, canonical-byte, exit-code or CLI JSON contract.

The next gate is one bounded local recipe execution path using existing Python
services, followed by atomic catalog registration and summary-safe history.
