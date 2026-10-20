"""Hardened local host for the unified Parison Workbench."""

from __future__ import annotations

import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .core import ParisonError
from .workbench import workbench_projection

_MAX_REQUEST_BYTES = 4096
_PAGE = b"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Parison Workbench</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18202a}nav{word-spacing:1rem}form{display:flex;gap:.5rem;margin:2rem 0}label{display:grid;gap:.25rem}input,button{font:inherit;padding:.35rem}input{flex:1}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ccd3da;padding:.5rem;text-align:left;vertical-align:top}th{width:34%;background:#f3f5f7}code{overflow-wrap:anywhere}.notice{padding:1rem;border:1px solid #ccd3da}</style></head><body><header><p>Parison Workbench</p><h1 id="heading">Results</h1><nav>Plans Run <strong>Results</strong> History Investigate Compare</nav></header><p id="status" role="status" class="notice">Connecting to local Python host...</p><form id="open"><label for="bundle">Bundle within workspace</label><input id="bundle" required placeholder="runs/example"><button>Verify and open</button></form><table><tbody id="evidence"></tbody></table><footer><p>PASS means agreement under the displayed policy; it is not extraction truth, approval, or cutover authorization.</p><p>No source paths, keys, values, or discrepancy samples are returned.</p></footer><script>const token=location.hash.slice(1);history.replaceState(null,'',location.pathname);const status=document.getElementById('status'),body=document.getElementById('evidence'),heading=document.getElementById('heading');const post=(path,data)=>fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Parison-Session':token},body:JSON.stringify(data)});post('/api/session',{}).then(r=>r.ok?r.json():Promise.reject()).then(()=>status.textContent='Local workspace ready.').catch(()=>status.textContent='Session rejected.');document.getElementById('open').addEventListener('submit',async event=>{event.preventDefault();status.textContent='Verifying bundle...';body.replaceChildren();const response=await post('/api/evidence',{bundle:document.getElementById('bundle').value});if(!response.ok){status.textContent='Bundle could not be verified.';return}const evidence=await response.json();heading.textContent=evidence.outcome||'Results';heading.style.color=evidence.outcome==='PASS'?'#14733b':'#a22';const rows=(value,prefix='')=>{if(value&&typeof value==='object'&&!Array.isArray(value)){Object.keys(value).sort().forEach(key=>rows(value[key],prefix?prefix+'.'+key:key));return}const row=document.createElement('tr'),name=document.createElement('th'),cell=document.createElement('td'),code=document.createElement('code');name.scope='row';name.textContent=prefix;code.textContent=Array.isArray(value)?value.join(', '):JSON.stringify(value);cell.append(code);row.append(name,cell);body.append(row)};rows(evidence);status.textContent='Verified summary-safe evidence.'});</script></body></html>"""


def create_workbench_server(workspace: str | Path, token: str | None = None) -> tuple[ThreadingHTTPServer, str]:
    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise ParisonError("workbench workspace must be an existing non-symlink directory")
    root = root.resolve()
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
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
            )
            self.end_headers()

        def _api_authorized(self) -> bool:
            origin = f"http://127.0.0.1:{self.server.server_port}"
            return (
                self.headers.get("Host") == origin.removeprefix("http://")
                and self.headers.get("Origin") == origin
                and self.headers.get("X-Parison-Session") == capability
            )

        def _request_json(self) -> dict[str, object] | None:
            if self.headers.get("Content-Type") != "application/json":
                return None
            try:
                size = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return None
            if not 0 <= size <= _MAX_REQUEST_BYTES:
                return None
            try:
                value = json.loads(self.rfile.read(size))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            return value if isinstance(value, dict) else None

        def _bundle(self, value: object) -> Path | None:
            if not isinstance(value, str) or not value or Path(value).is_absolute():
                return None
            parts = Path(value).parts
            if any(part in {"", ".", ".."} for part in parts):
                return None
            candidate = root.joinpath(*parts)
            current = root
            for part in parts:
                current /= part
                if current.is_symlink():
                    return None
            return candidate

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
            self._headers(404, "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            if not self._api_authorized():
                self._headers(404, "text/plain; charset=utf-8")
                return
            request = self._request_json()
            if request is None:
                self._headers(415, "application/json")
                return
            path = urlsplit(self.path).path
            if path == "/api/session" and not request:
                payload = {"activities": ["plans", "run", "results", "history", "investigate", "compare"]}
            elif path == "/api/evidence":
                bundle = self._bundle(request.get("bundle"))
                if bundle is None:
                    self._headers(422, "application/json")
                    return
                try:
                    payload = workbench_projection(bundle)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            else:
                self._headers(404, "text/plain; charset=utf-8")
                return
            self._headers(200, "application/json")
            self.wfile.write(json.dumps(payload, sort_keys=True).encode())

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
