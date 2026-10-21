"""Hardened local host for the unified Parison Workbench."""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .core import ParisonError
from .inputs import _source_path, _source_paths
from .workbench import (
    compare_projection,
    execute_run,
    history_projection,
    investigate_projection,
    plan_projection,
    plan_text_projection,
    workbench_projection,
)
from .workbench_page import PAGE
from .workbench_plans import edit_plan, plan_controls

_MAX_REQUEST_BYTES = 262_144
_MAX_REQUEST_THREADS = 8
_MACOS_PICKER = 'POSIX path of (choose folder with prompt "Choose a Parison evidence bundle")'
_MACOS_RECIPE_PICKER = 'POSIX path of (choose file with prompt "Choose a Parison recipe")'
_WINDOWS_PICKER = (
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
    "$dialog.Description = 'Choose a Parison evidence bundle'; "
    "if ($dialog.ShowDialog() -eq 'OK') { $dialog.SelectedPath }"
)
_WINDOWS_RECIPE_PICKER = (
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$dialog = New-Object System.Windows.Forms.OpenFileDialog; "
    "$dialog.Title = 'Choose a Parison recipe'; "
    "$dialog.Filter = 'JSON files (*.json)|*.json|All files (*.*)|*.*'; "
    "if ($dialog.ShowDialog() -eq 'OK') { $dialog.FileName }"
)


def _workspace_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    parts = Path(value).parts
    if any(part in {"", ".."} for part in parts):
        return None
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            return None
    return candidate


def _workspace_source(root: Path, value: object) -> str | Path | None:
    if not isinstance(value, str):
        return None
    prefix, separator, locator = value.partition(":")
    if separator and prefix in {"sqlite", "xlsx", "json", "xml"}:
        try:
            source = _source_path(value)
        except ParisonError:
            return None
        path = _workspace_path(root, str(source))
        if path is None:
            return None
        split = locator.split if prefix == "json" else locator.rsplit
        return f"{prefix}:{path}#{split('#', 1)[1]}"
    return _workspace_path(root, value)


def _choose_bundle(root: Path) -> str | None:
    if sys.platform == "darwin":
        command = ["/usr/bin/osascript", "-e", _MACOS_PICKER]
    elif sys.platform == "win32":
        command = ["powershell.exe", "-NoProfile", "-STA", "-Command", _WINDOWS_PICKER]
    else:
        raise ParisonError("native folder selection is unavailable on this platform")
    try:
        selected = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ParisonError("native folder selection failed") from exc
    if selected.returncode or not selected.stdout.strip():
        return None
    try:
        relative = Path(selected.stdout.strip()).absolute().relative_to(root)
    except ValueError as exc:
        raise ParisonError("selected folder must be inside the workbench workspace") from exc
    candidate = _workspace_path(root, str(relative))
    if candidate is None or not candidate.is_dir():
        raise ParisonError("selected bundle folder is unsafe")
    return str(relative)


def _choose_recipe(root: Path) -> str | None:
    if sys.platform == "darwin":
        command = ["/usr/bin/osascript", "-e", _MACOS_RECIPE_PICKER]
    elif sys.platform == "win32":
        command = ["powershell.exe", "-NoProfile", "-STA", "-Command", _WINDOWS_RECIPE_PICKER]
    else:
        raise ParisonError("native file selection is unavailable on this platform")
    try:
        selected = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ParisonError("native file selection failed") from exc
    if selected.returncode or not selected.stdout.strip():
        return None
    try:
        relative = Path(selected.stdout.strip()).absolute().relative_to(root)
    except ValueError as exc:
        raise ParisonError("selected file must be inside the workbench workspace") from exc
    candidate = _workspace_path(root, str(relative))
    if candidate is None or not candidate.is_file():
        raise ParisonError("selected recipe file is unsafe")
    return str(relative)


class _WorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = _MAX_REQUEST_THREADS

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._request_slots = threading.BoundedSemaphore(_MAX_REQUEST_THREADS)
        super().__init__(*args, **kwargs)

    def process_request(self, request: object, client_address: object) -> None:
        self._request_slots.acquire()
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_slots.release()
            raise

    def process_request_thread(self, request: object, client_address: object) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


def create_workbench_server(workspace: str | Path, token: str | None = None) -> tuple[ThreadingHTTPServer, str]:
    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise ParisonError("workbench workspace must be an existing non-symlink directory")
    root = root.resolve()
    capability = token or secrets.token_urlsafe(32)
    session = {"capability": capability, "closing": False}
    run_lock = threading.Lock()
    run_cancel = threading.Event()
    run_state = {"phase": "idle"}

    def set_run_phase(phase: str) -> None:
        run_state["phase"] = phase

    class Handler(BaseHTTPRequestHandler):
        def _headers(self, status: int, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if status != 200:
                self.send_header("Content-Length", "0")
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
                not session["closing"]
                and self.headers.get("Host") == origin.removeprefix("http://")
                and self.headers.get("Origin") == origin
                and self.headers.get("X-Parison-Session") == session["capability"]
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

        def do_GET(self) -> None:
            expected_host = f"127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != expected_host:
                self._headers(400, "text/plain; charset=utf-8")
                return
            if urlsplit(self.path).path == "/":
                self._headers(200, "text/html; charset=utf-8")
                self.wfile.write(PAGE)
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
            elif path == "/api/shutdown" and not request:
                session["closing"] = True
                session["capability"] = None
                run_cancel.set()
                self._headers(200, "application/json")
                self.wfile.write(b'{"status":"stopping"}')

                def shutdown_when_run_stops() -> None:
                    with run_lock:
                        self.server.shutdown()

                threading.Thread(target=shutdown_when_run_stops, daemon=True).start()
                return
            elif path == "/api/choose-bundle" and not request:
                try:
                    selected = _choose_bundle(root)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
                if selected is None:
                    self._headers(204, "application/json")
                    return
                payload = {"bundle": selected}
            elif path == "/api/choose-recipe" and not request:
                try:
                    selected = _choose_recipe(root)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
                if selected is None:
                    self._headers(204, "application/json")
                    return
                payload = {"recipe": selected}
            elif path == "/api/plan" and set(request) == {"recipe"}:
                recipe = _workspace_path(root, request["recipe"])
                if recipe is None:
                    self._headers(422, "application/json")
                    return
                try:
                    payload = plan_projection(recipe)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/validate-plan" and set(request) == {"source"}:
                source = request["source"]
                if not isinstance(source, str):
                    self._headers(422, "application/json")
                    return
                try:
                    payload = plan_text_projection(source)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/plan-controls" and set(request) == {"source"}:
                try:
                    if not isinstance(request["source"], str):
                        raise ParisonError("source must be JSON text")
                    payload = {"controls": plan_controls(request["source"])}
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/edit-plan" and set(request) == {"source", "edits"}:
                try:
                    if not isinstance(request["source"], str):
                        raise ParisonError("source must be JSON text")
                    payload = edit_plan(**request)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/plan-inputs" and set(request) == {"baseline", "candidate"}:
                try:
                    for name in ("baseline", "candidate"):
                        source = _workspace_source(root, request[name])
                        if source is None or not all(item.is_file() for item in _source_paths(source)):
                            raise ParisonError("inputs must exist inside the workspace")
                    payload = dict(request)
                except (ParisonError, OSError, ValueError):
                    self._headers(422, "application/json")
                    return
            elif path == "/api/evidence" and set(request) == {"bundle"}:
                bundle = _workspace_path(root, request.get("bundle"))
                if bundle is None:
                    self._headers(422, "application/json")
                    return
                try:
                    payload = workbench_projection(bundle)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/run" and set(request) == {"recipe", "baseline", "candidate", "output"}:
                paths = [
                    _workspace_path(root, request["recipe"]),
                    _workspace_source(root, request["baseline"]),
                    _workspace_source(root, request["candidate"]),
                    _workspace_path(root, request["output"]),
                ]
                if any(item is None for item in paths):
                    self._headers(422, "application/json")
                    return
                if not run_lock.acquire(blocking=False):
                    self._headers(409, "application/json")
                    return
                try:
                    run_cancel.clear()
                    payload = execute_run(root, *paths, cancelled=run_cancel.is_set, progress=set_run_phase)
                except ParisonError:
                    set_run_phase("cancelled" if run_cancel.is_set() else "error")
                    self._headers(422, "application/json")
                    return
                finally:
                    run_lock.release()
            elif path == "/api/cancel-run" and not request:
                if not run_lock.locked():
                    self._headers(409, "application/json")
                    return
                run_cancel.set()
                set_run_phase("cancelling")
                payload = {"status": "cancellation-requested"}
            elif path == "/api/run-status" and not request:
                payload = dict(run_state)
            elif path == "/api/history" and not request:
                try:
                    payload = history_projection(root)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/compare" and set(request) == {"left", "right"}:
                left, right = (_workspace_path(root, request[name]) for name in ("left", "right"))
                if left is None or right is None:
                    self._headers(422, "application/json")
                    return
                try:
                    payload = compare_projection(root, left, right)
                except ParisonError:
                    self._headers(422, "application/json")
                    return
            elif path == "/api/investigate" and set(request) == {"bundle"}:
                bundle = _workspace_path(root, request["bundle"])
                if bundle is None:
                    self._headers(422, "application/json")
                    return
                try:
                    payload = investigate_projection(bundle)
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

    server = _WorkbenchServer(("127.0.0.1", 0), Handler)
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
