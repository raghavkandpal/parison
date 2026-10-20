"""Hardened local host for the unified Parison Workbench."""

from __future__ import annotations

import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .core import ParisonError

_PAGE = b"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Parison Workbench</title></head><body><h1>Parison Workbench</h1><p>Plans | Run | Results | History | Investigate | Compare</p><p id="status">Connecting to local Python host...</p><script>const token=location.hash.slice(1);location.hash='';fetch('/api/session',{headers:{'X-Parison-Session':token}}).then(r=>r.ok?r.json():Promise.reject()).then(()=>document.getElementById('status').textContent='Local workspace ready.').catch(()=>document.getElementById('status').textContent='Session rejected.');</script></body></html>"""


def create_workbench_server(workspace: str | Path, token: str | None = None) -> tuple[ThreadingHTTPServer, str]:
    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise ParisonError("workbench workspace must be an existing non-symlink directory")
    capability = token or secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def _headers(self, status: int, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()

        def do_GET(self) -> None:
            expected_host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected_host:
                self._headers(400, "text/plain; charset=utf-8")
                return
            path = urlsplit(self.path).path
            if path == "/":
                self._headers(200, "text/html; charset=utf-8")
                self.wfile.write(_PAGE)
                return
            if path == "/api/session" and self.headers.get("X-Parison-Session") == capability:
                payload = json.dumps(
                    {"activities": ["plans", "run", "results", "history", "investigate", "compare"]}
                ).encode()
                self._headers(200, "application/json")
                self.wfile.write(payload)
                return
            self._headers(404, "text/plain; charset=utf-8")

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return server, f"http://127.0.0.1:{server.server_port}/#{capability}"


def serve_workbench(workspace: str | Path, open_browser: bool = True) -> None:
    server, url = create_workbench_server(workspace)
    if open_browser and not webbrowser.open(url):
        server.server_close()
        raise ParisonError("cannot open the workbench in a browser")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
