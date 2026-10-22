from __future__ import annotations

import http.client
import json
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from parison.core import ParisonError, compare, load_recipe, publish
from parison.evidence import export_statement, report_cutover
from parison.project import init_project
from parison.suites import run_suite
from parison.workbench_host import _choose_bundle, _choose_recipe, _workspace_source, create_workbench_server

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None


class WorkbenchHostTests(unittest.TestCase):
    def test_failed_suite_member_investigation_exports_bounded_raw_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_project(root)
            recipe = json.loads((root / "recipe.json").read_text(encoding="utf-8"))
            recipe["output"]["sensitivity"] = "raw"
            (root / "recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
            (root / "candidate.csv").write_text("id,value\nexample,private-789\n", encoding="utf-8")
            (root / "suite.json").write_text(
                json.dumps(
                    {
                        "suite_version": 1,
                        "cases": [
                            {
                                "id": identifier,
                                "recipe": "recipe.json",
                                "baseline": "baseline.csv",
                                "candidate": "candidate.csv",
                            }
                            for identifier in ("first", "second")
                        ],
                    }
                ),
                encoding="utf-8",
            )
            run_suite(root / "suite.json", root / "suite-run")
            server, _ = create_workbench_server(root, "test-capability")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection(*server.server_address)
                select = {"bundle": "suite-run", "case_id": "second"}
                response = self._post(connection, server, "/api/investigate-suite", select)
                self.assertEqual(response.status, 200)
                view = json.loads(response.read())
                self.assertNotIn("private-789", json.dumps(view))
                self.assertTrue(any(group["count"] for group in view["groups"]))
                request = {
                    **select,
                    "suite_sha256": view["suite_sha256"],
                    "group_id": next(group["group_id"] for group in view["groups"] if group["count"]),
                    "limit": 1,
                    "per_run_limit": 1,
                    "output": "raw.json",
                }
                response = self._post(connection, server, "/api/investigate-export", request)
                self.assertEqual(response.status, 200)
                self.assertNotIn("private-789", response.read().decode())
                self.assertIn("private-789", (root / "raw.json").read_text(encoding="utf-8"))
                for bad in ({**select, "case_id": "missing"}, {**select, "bundle": "../outside"}):
                    response = self._post(connection, server, "/api/investigate-suite", bad)
                    self.assertEqual(response.status, 422)
                    response.read()
                for bad in (
                    {**request, "output": "raw.json"},
                    {**request, "limit": 101},
                    {**request, "output": "../escape.json"},
                    {
                        **request,
                        "group_id": next(group["group_id"] for group in view["groups"] if not group["count"]),
                        "output": "empty.json",
                    },
                    {**request, "group_id": "0" * 64, "output": "unknown.json"},
                    {**request, "suite_sha256": "0" * 64, "output": "stale.json"},
                ):
                    response = self._post(connection, server, "/api/investigate-export", bad)
                    self.assertEqual(response.status, 422)
                    response.read()
                self.assertFalse((root / "unknown.json").exists())
                self.assertFalse((root / "empty.json").exists())
                self.assertFalse((root / "stale.json").exists())
                (root / "linked.json").symlink_to(root / "raw.json")
                response = self._post(
                    connection, server, "/api/investigate-export", {**request, "output": "linked.json"}
                )
                self.assertEqual(response.status, 422)
                response.read()
                (root / "suite-run" / "cases" / "first" / "result.json").write_text("{}", encoding="utf-8")
                response = self._post(connection, server, "/api/investigate-suite", select)
                self.assertEqual(response.status, 422)
                response.read()
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_partitioned_suite_inputs_revalidate_member_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            init_project(root)
            for side in ("baseline", "candidate"):
                partition = root / side
                partition.mkdir()
                (root / f"{side}.csv").rename(partition / "part.csv")
            (root / "suite.json").write_text(
                json.dumps(
                    {
                        "suite_version": 1,
                        "cases": [
                            {"id": "orders", "recipe": "recipe.json", "baseline": "baseline", "candidate": "candidate"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            server, _ = create_workbench_server(root, "test-capability")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection(*server.server_address)
                request = {
                    "plan": "suite.json",
                    "case_ids": [],
                    "tags": [],
                    "shard_index": None,
                    "shard_count": None,
                    "output": "suite-run",
                }
                response = self._post(connection, server, "/api/suite-plan", request)
                self.assertEqual(response.status, 200)
                preview = json.loads(response.read())
                member = root / "candidate" / "part.csv"
                original = member.read_bytes()
                member.write_bytes(original + b"\n")
                run = {**request, "plan_sha256": preview["plan_sha256"], "members_sha256": preview["members_sha256"]}
                response = self._post(connection, server, "/api/suite-run", run)
                self.assertEqual(response.status, 422)
                response.read()
                self.assertFalse((root / "suite-run").exists())
                member.write_bytes(original)
                response = self._post(connection, server, "/api/suite-run", run)
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read())["evidence"]["outcome"], "PASS")
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_suite_rehearsal_verifies_and_registers_local_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            init_project(root)
            (root / "suite.json").write_text(
                json.dumps(
                    {
                        "suite_version": 2,
                        "cases": [
                            {
                                "id": "orders",
                                "recipe": "recipe.json",
                                "baseline": "baseline.csv",
                                "candidate": "candidate.csv",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            server, _ = create_workbench_server(root, "test-capability")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection(*server.server_address)
                request = {
                    "plan": "suite.json",
                    "case_ids": [],
                    "tags": [],
                    "shard_index": None,
                    "shard_count": None,
                    "output": "suite-run",
                }
                response = self._post(connection, server, "/api/suite-plan", request)
                self.assertEqual(response.status, 200)
                preview = json.loads(response.read())
                response = self._post(
                    connection,
                    server,
                    "/api/suite-run",
                    {
                        **request,
                        "plan_sha256": "0" * 64,
                        "members_sha256": preview["members_sha256"],
                    },
                )
                self.assertEqual(response.status, 422)
                response.read()
                self.assertFalse((root / "suite-run").exists())
                original_candidate = (root / "candidate.csv").read_bytes()
                (root / "candidate.csv").write_bytes(original_candidate + b"\n")
                response = self._post(
                    connection,
                    server,
                    "/api/suite-run",
                    {**request, "plan_sha256": preview["plan_sha256"], "members_sha256": preview["members_sha256"]},
                )
                self.assertEqual(response.status, 422)
                response.read()
                (root / "candidate.csv").write_bytes(original_candidate)
                response = self._post(
                    connection,
                    server,
                    "/api/suite-run",
                    {
                        **request,
                        "plan_sha256": preview["plan_sha256"],
                        "members_sha256": preview["members_sha256"],
                    },
                )
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read())["evidence"]["outcome"], "PASS")
                run_suite(root / "suite.json", root / "cli-suite")
                for file in (root / "suite-run").rglob("*"):
                    if file.is_file():
                        self.assertEqual(
                            file.read_bytes(), (root / "cli-suite" / file.relative_to(root / "suite-run")).read_bytes()
                        )
                response = self._post(connection, server, "/api/compare", {"left": "suite-run", "right": "cli-suite"})
                self.assertEqual(response.status, 200)
                comparison = json.loads(response.read())
                self.assertFalse(comparison["changed"])
                self.assertEqual(comparison["cases"][0]["id"], "orders")
                response = self._post(connection, server, "/api/handoff-preview", {"bundle": "suite-run"})
                self.assertEqual(response.status, 200)
                claim = json.loads(response.read())
                self.assertEqual(claim["predicate"]["bundleKind"], "suite")
                self.assertTrue(claim["predicate"]["scopeComplete"])
                for writer, name in ((export_statement, "changed.json"), (report_cutover, "changed.md")):
                    with self.assertRaisesRegex(ParisonError, "changed since handoff preview"):
                        writer(root / "suite-run", root / name, expected_manifest_sha256="0" * 64)
                    self.assertFalse((root / name).exists())
                for format_name, name, direct in (
                    ("statement", "statement.json", export_statement),
                    ("report", "report.md", report_cutover),
                ):
                    response = self._post(
                        connection,
                        server,
                        "/api/handoff-export",
                        {
                            "bundle": "suite-run",
                            "output": name,
                            "format": format_name,
                            "manifest_sha256": claim["manifest_sha256"],
                        },
                    )
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read())["output"], name)
                    direct(root / "suite-run", root / f"cli-{name}")
                    self.assertEqual((root / name).read_bytes(), (root / f"cli-{name}").read_bytes())
                response = self._post(
                    connection,
                    server,
                    "/api/handoff-export",
                    {
                        "bundle": "suite-run",
                        "output": "stale.json",
                        "format": "statement",
                        "manifest_sha256": "0" * 64,
                    },
                )
                self.assertEqual(response.status, 422)
                response.read()
                self.assertFalse((root / "stale.json").exists())
                response = self._post(
                    connection,
                    server,
                    "/api/handoff-export",
                    {
                        "bundle": "suite-run",
                        "output": "suite-run/statement.json",
                        "format": "statement",
                        "manifest_sha256": claim["manifest_sha256"],
                    },
                )
                self.assertEqual(response.status, 422)
                response.read()
                self.assertFalse((root / "suite-run" / "statement.json").exists())
                response = self._post(connection, server, "/api/history", {})
                self.assertEqual(response.status, 200)
                history = json.loads(response.read())
                self.assertEqual([(item["bundle"], item["kind"]) for item in history], [("suite-run", "suite")])
                response = self._post(connection, server, "/api/suite-run-status", {})
                self.assertEqual(
                    json.loads(response.read()), {"phase": "complete", "completed_cases": 1, "selected_cases": 1}
                )
                (root / "cli-suite" / "cases" / "orders" / "result.json").write_text("{}", encoding="utf-8")
                response = self._post(connection, server, "/api/handoff-preview", {"bundle": "cli-suite"})
                self.assertEqual(response.status, 422)
                response.read()
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_stalled_clients_cannot_hold_accept_loop_or_slots_forever(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("parison.workbench_host._REQUEST_READ_TIMEOUT_SECONDS", 1),
            patch("parison.workbench_host._REQUEST_INPUT_DEADLINE_SECONDS", 1),
        ):
            server, _ = create_workbench_server(directory, "test-capability")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            clients = []
            try:
                for _ in range(8):
                    client = socket.create_connection(server.server_address)
                    client.sendall(b"POST /api/session HTTP/1.1\r\n")
                    clients.append(client)
                deadline = time.monotonic() + 1
                while server._request_slots._value and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertEqual(server._request_slots._value, 0)

                extra = socket.create_connection(server.server_address, timeout=0.5)
                try:
                    extra.sendall(b"GET / HTTP/1.1\r\n\r\n")
                    try:
                        self.assertEqual(extra.recv(1), b"")
                    except ConnectionResetError:
                        pass
                finally:
                    extra.close()

                for _ in range(12):
                    for client in clients:
                        try:
                            client.sendall(b"x")
                        except OSError:
                            pass
                    time.sleep(0.12)
                deadline = time.monotonic() + 1
                while server._request_slots._value != 8 and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertEqual(server._request_slots._value, 8)
            finally:
                for client in clients:
                    client.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_input_deadline_does_not_interrupt_accepted_run(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("parison.workbench_host._REQUEST_INPUT_DEADLINE_SECONDS", 0.1),
        ):
            server, _ = create_workbench_server(directory, "test-capability")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch("parison.workbench_host.execute_run") as execute:

                    def complete_run(*args, **kwargs):
                        time.sleep(0.2)
                        return {"evidence": {"outcome": "PASS"}, "catalog_status": "added"}

                    execute.side_effect = complete_run
                    connection = http.client.HTTPConnection(*server.server_address)
                    response = self._post(
                        connection,
                        server,
                        "/api/run",
                        {"recipe": "recipe.json", "baseline": "left.csv", "candidate": "right.csv", "output": "run"},
                    )
                    self.assertEqual(response.status, 200)
                    response.read()
                    connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_structured_sources_preserve_selection_inside_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selections = (
                ("json:data.json#/rows", "json"),
                ("xml:data.xml#root/row?ns=p,urn%3Atest", "xml"),
                ("xlsx:data.xlsx#Sheet1!A1:B2", "xlsx"),
                ("sqlite:data.db#records", "sqlite"),
            )
            for locator, prefix in selections:
                with self.subTest(locator=locator):
                    self.assertEqual(
                        _workspace_source(root, locator),
                        f"{prefix}:{root / locator.split(':', 1)[1].split('#', 1)[0]}#{locator.split('#', 1)[1]}",
                    )
                    self.assertIsNone(_workspace_source(root, locator.replace("data.", "../data.")))
            self.assertEqual(_workspace_source(root, "data.csv"), root / "data.csv")
            self.assertIsNone(_workspace_source(root, "json:data.json#bad-pointer"))
            self.assertIsNone(_workspace_source(root, f"sqlite:{root / 'data.db'}#records"))
            (root / "link.json").symlink_to(root / "data.json")
            self.assertIsNone(_workspace_source(root, "json:link.json#/rows"))

    def _post(self, connection, server, path, body, **headers):
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Origin", f"http://127.0.0.1:{server.server_port}")
        headers.setdefault("X-Parison-Session", "test-capability")
        connection.request("POST", path, body=json.dumps(body), headers=headers)
        return connection.getresponse()

    def test_session_is_loopback_capability_guarded(self):
        with tempfile.TemporaryDirectory() as directory:
            server, url = create_workbench_server(directory, "test-capability")
            self.addCleanup(server.server_close)
            self.assertEqual(server.server_address[0], "127.0.0.1")
            self.assertTrue(url.endswith("/#test-capability"))
            connection = http.client.HTTPConnection(*server.server_address)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            connection.request("GET", "/")
            page = connection.getresponse()
            self.assertEqual(page.status, 200)
            self.assertIn("style-src 'unsafe-inline'", page.getheader("Content-Security-Policy"))
            page_body = page.read()
            self.assertIn(b"border:1px solid #ccd3da", page_body)
            self.assertIn(b"No result open", page_body)
            self.assertIn(b"Local only", page_body)
            self.assertIn(b"Choose folder...", page_body)
            self.assertIn(b"Clear result", page_body)
            self.assertIn(b"Choose file...", page_body)
            self.assertIn(b"Download unapproved draft", page_body)
            self.assertIn(b"Validate changes", page_body)
            self.assertIn(b"Stop workbench", page_body)
            response = self._post(connection, server, "/api/session", {}, Origin="http://attacker.invalid")
            self.assertEqual(response.status, 404)
            response.read()
            response = self._post(connection, server, "/api/session", {})
            self.assertEqual(response.status, 200)
            self.assertIn(b'"plans"', response.read())

            with patch("parison.workbench_host._choose_bundle", return_value="runs/one"):
                response = self._post(connection, server, "/api/choose-bundle", {})
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"bundle": "runs/one"})
            with patch("parison.workbench_host._choose_recipe", return_value="recipes/one.json"):
                response = self._post(connection, server, "/api/choose-recipe", {})
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"recipe": "recipes/one.json"})

            running = threading.Event()

            def wait_for_cancel(*args, cancelled, progress, **kwargs):
                progress("comparing")
                running.set()
                self.assertTrue(running.wait(1))
                while not cancelled():
                    running.wait(0.01)
                raise ParisonError("workbench run cancelled")

            run_status = []

            def start_run():
                run_connection = http.client.HTTPConnection(*server.server_address)
                response = self._post(
                    run_connection,
                    server,
                    "/api/run",
                    {"recipe": "recipe.json", "baseline": "left.csv", "candidate": "right.csv", "output": "run"},
                )
                run_status.append(response.status)
                response.read()
                run_connection.close()

            with patch("parison.workbench_host.execute_run", side_effect=wait_for_cancel):
                run_thread = threading.Thread(target=start_run)
                run_thread.start()
                self.assertTrue(running.wait(1))
                response = self._post(connection, server, "/api/run-status", {})
                self.assertEqual(json.loads(response.read()), {"phase": "comparing"})
                response = self._post(connection, server, "/api/cancel-run", {})
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"status": "cancellation-requested"})
                run_thread.join(timeout=2)
            self.assertEqual(run_status, [422])
            response = self._post(connection, server, "/api/run-status", {})
            self.assertEqual(json.loads(response.read()), {"phase": "cancelled"})

            running.clear()
            run_status.clear()

            def fail_catalog(*args, cancelled, progress, **kwargs):
                progress("cataloging")
                running.set()
                while not cancelled():
                    running.wait(0.01)
                raise ParisonError("catalog unavailable")

            with patch("parison.workbench_host.execute_run", side_effect=fail_catalog):
                run_thread = threading.Thread(target=start_run)
                run_thread.start()
                self.assertTrue(running.wait(1))
                response = self._post(connection, server, "/api/cancel-run", {})
                self.assertEqual(response.status, 200)
                response.read()
                run_thread.join(timeout=2)
            self.assertEqual(run_status, [422])
            response = self._post(connection, server, "/api/run-status", {})
            self.assertEqual(json.loads(response.read()), {"phase": "error"})

            response = self._post(connection, server, "/api/shutdown", {})
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"status": "stopping"})
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

    def test_native_picker_returns_only_workspace_relative_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            bundle = root / "runs" / "one"
            bundle.mkdir(parents=True)
            completed = SimpleNamespace(returncode=0, stdout=f"{bundle}\n")
            with patch("parison.workbench_host.sys.platform", "darwin"):
                with patch("parison.workbench_host.subprocess.run", return_value=completed) as run:
                    self.assertEqual(_choose_bundle(root), "runs/one")
            self.assertEqual(run.call_args.args[0][0], "/usr/bin/osascript")

            with tempfile.TemporaryDirectory() as outside_directory:
                completed.stdout = f"{outside_directory}\n"
                with patch("parison.workbench_host.sys.platform", "darwin"):
                    with patch("parison.workbench_host.subprocess.run", return_value=completed):
                        with self.assertRaisesRegex(ParisonError, "inside"):
                            _choose_bundle(root)

            recipe = root / "recipe.json"
            recipe.write_text("{}", encoding="utf-8")
            completed.stdout = f"{recipe}\n"
            with patch("parison.workbench_host.sys.platform", "darwin"):
                with patch("parison.workbench_host.subprocess.run", return_value=completed):
                    self.assertEqual(_choose_recipe(root), "recipe.json")

    def test_opens_only_verified_summary_safe_workspace_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root / "recipe.json"
            recipe.write_text(
                json.dumps(
                    {
                        "recipe_version": 1,
                        "comparison_mode": "keyed",
                        "keys": ["private_id"],
                        "scope": {
                            "snapshot": "test",
                            "cutoff": "2026-10-20T00:00:00Z",
                            "filters": [],
                            "completeness": "full",
                            "expected_empty": False,
                        },
                        "identity": {"null_keys": "reject", "duplicates": "reject"},
                        "nulls_equal": True,
                        "columns": {
                            "private_id": {"type": "string", "comparison": "exact"},
                            "secret": {"type": "string", "comparison": "exact"},
                        },
                        "output": {"sensitivity": "raw"},
                    }
                ),
                encoding="utf-8",
            )
            baseline, candidate = root / "baseline.csv", root / "candidate.csv"
            baseline.write_text("private_id,secret\n1,hidden\n", encoding="utf-8")
            candidate.write_text("private_id,secret\n1,hidden\n", encoding="utf-8")
            bundle = root / "runs" / "one"
            result, effective = compare(recipe, baseline, candidate), load_recipe(recipe)
            publish(bundle, result, effective)
            server, _ = create_workbench_server(root, "test-capability")
            self.addCleanup(server.server_close)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            connection = http.client.HTTPConnection(*server.server_address)
            response = self._post(connection, server, "/api/plan", {"recipe": "recipe.json"})
            self.assertEqual(response.status, 200)
            plan = json.loads(response.read())
            self.assertEqual(plan["source"], recipe.read_text(encoding="utf-8"))
            self.assertEqual(plan["comparison_mode"], "keyed")
            self.assertRegex(plan["policy_sha256"], r"^[0-9a-f]{64}$")
            suite = root / "suite.json"
            suite.write_text(
                json.dumps(
                    {
                        "suite_version": 2,
                        "cases": [
                            {
                                "id": "orders",
                                "recipe": "recipe.json",
                                "baseline": "baseline.csv",
                                "candidate": "candidate.csv",
                                "tags": ["migration"],
                                "description": "secret-value-must-not-leak",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            response = self._post(
                connection,
                server,
                "/api/suite-plan",
                {
                    "plan": "suite.json",
                    "case_ids": ["orders"],
                    "tags": ["migration"],
                    "shard_index": 0,
                    "shard_count": 1,
                    "output": "suite-run",
                },
            )
            self.assertEqual(response.status, 200)
            listed = json.loads(response.read())
            self.assertEqual(
                listed["cases"],
                [
                    {
                        "id": "orders",
                        "comparison_mode": "keyed",
                        "tags": ["migration"],
                        "recipe": "recipe.json",
                        "baseline": "baseline.csv",
                        "candidate": "candidate.csv",
                    }
                ],
            )
            self.assertEqual(listed["output"], "suite-run")
            self.assertNotIn("secret-value-must-not-leak", json.dumps(listed))
            self.assertRegex(listed["suite_policy_sha256"], r"^[0-9a-f]{64}$")
            (root / "suites").mkdir()
            nested = root / "suites" / "nested.json"
            nested.write_text(
                suite.read_text()
                .replace('"recipe.json"', '"../recipe.json"')
                .replace('"baseline.csv"', '"../baseline.csv"')
                .replace('"candidate.csv"', '"../candidate.csv"'),
                encoding="utf-8",
            )
            response = self._post(
                connection,
                server,
                "/api/suite-plan",
                {
                    "plan": "suites/nested.json",
                    "case_ids": [],
                    "tags": [],
                    "shard_index": None,
                    "shard_count": None,
                    "output": "",
                },
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["cases"][0]["recipe"], "../recipe.json")
            response = self._post(
                connection,
                server,
                "/api/suite-plan",
                {
                    "plan": "suite.json",
                    "case_ids": ["missing"],
                    "tags": [],
                    "shard_index": None,
                    "shard_count": None,
                    "output": "",
                },
            )
            self.assertEqual(response.status, 422)
            response.read()
            (root / "linked.csv").symlink_to(root / "baseline.csv")
            suite.write_text(suite.read_text().replace('"baseline.csv"', '"linked.csv"'), encoding="utf-8")
            response = self._post(
                connection,
                server,
                "/api/suite-plan",
                {
                    "plan": "suite.json",
                    "case_ids": [],
                    "tags": [],
                    "shard_index": None,
                    "shard_count": None,
                    "output": "",
                },
            )
            self.assertEqual(response.status, 422)
            response.read()
            suite.write_text(suite.read_text().replace('"linked.csv"', '"../outside.csv"'), encoding="utf-8")
            response = self._post(
                connection,
                server,
                "/api/suite-plan",
                {
                    "plan": "suite.json",
                    "case_ids": [],
                    "tags": [],
                    "shard_index": None,
                    "shard_count": None,
                    "output": "",
                },
            )
            self.assertEqual(response.status, 422)
            response.read()
            self.assertNotIn(str(recipe), json.dumps(plan))
            self.assertEqual(plan["controls"]["kind"], "object")
            self.assertIn('"null_tokens"', plan["effective_policy"])

            response = self._post(connection, server, "/api/plan-controls", {"source": plan["source"]})
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["controls"], plan["controls"])
            response = self._post(
                connection,
                server,
                "/api/edit-plan",
                {
                    "source": plan["source"],
                    "edits": [{"path": ["scope", "snapshot"], "operation": "set", "value": '"field-edit"'}],
                },
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(json.loads(response.read())["source"])["scope"]["snapshot"], "field-edit")
            self.assertEqual(recipe.read_text(encoding="utf-8"), plan["source"])
            for path, request in (
                ("/api/plan-controls", {"source": []}),
                ("/api/plan-controls", {"source": "[]"}),
                (
                    "/api/edit-plan",
                    {"source": plan["source"], "edits": [{"path": [], "operation": [], "value": "null"}]},
                ),
                ("/api/plan-inputs", {"baseline": "../outside.csv", "candidate": "candidate.csv"}),
                ("/api/plan-inputs", {"baseline": "missing.csv", "candidate": "candidate.csv"}),
            ):
                response = self._post(connection, server, path, request)
                self.assertEqual(response.status, 422)
                response.read()
            response = self._post(
                connection, server, "/api/plan-inputs", {"baseline": "baseline.csv", "candidate": "candidate.csv"}
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read()), {"baseline": "baseline.csv", "candidate": "candidate.csv"})

            edited = json.loads(plan["source"])
            edited["scope"]["snapshot"] = "edited"
            response = self._post(connection, server, "/api/validate-plan", {"source": json.dumps(edited)})
            self.assertEqual(response.status, 200)
            validated = json.loads(response.read())
            self.assertNotEqual(validated["policy_sha256"], plan["policy_sha256"])
            self.assertEqual(validated["recipe_version"], 1)

            response = self._post(connection, server, "/api/validate-plan", {"source": "{}"})
            self.assertEqual(response.status, 422)
            self.assertNotIn(b"recipe_version", response.read())

            response = self._post(connection, server, "/api/plan", {"recipe": "../recipe.json"})
            self.assertEqual(response.status, 422)
            response.read()
            response = self._post(connection, server, "/api/evidence", {"bundle": "runs/one"})
            self.assertEqual(response.status, 200)
            payload = response.read()
            self.assertIn(b'"outcome": "PASS"', payload)
            for secret in (b"private_id", b"hidden", b"baseline.csv"):
                self.assertNotIn(secret, payload)

            run_request = {
                "recipe": "recipe.json",
                "baseline": "baseline.csv",
                "candidate": "candidate.csv",
                "output": "runs/two",
            }
            response = self._post(connection, server, "/api/run", run_request)
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["evidence"]["outcome"], "PASS")
            run_request["output"] = "runs/three"
            response = self._post(connection, server, "/api/run", run_request)
            self.assertEqual(response.status, 200)
            response.read()
            for name in ("baseline", "candidate"):
                (root / f"{name}.json").write_text(
                    json.dumps({"rows": [{"private_id": "1", "secret": "hidden"}]}), encoding="utf-8"
                )
            json_recipe = json.loads(recipe.read_text(encoding="utf-8"))
            json_recipe["recipe_version"] = 4
            json_recipe["input_projection"] = "semantic-scalar-v1"
            json_recipe["field_projection"] = {"version": 1}
            for side in ("baseline", "candidate"):
                json_recipe["field_projection"][side] = {
                    "kind": "json-pointer-v1",
                    "fields": {"private_id": "/private_id", "secret": "/secret"},
                }
            (root / "json-recipe.json").write_text(json.dumps(json_recipe), encoding="utf-8")
            json_request = {
                "recipe": "json-recipe.json",
                "baseline": "json:baseline.json#/rows",
                "candidate": "json:candidate.json#/rows",
                "output": "runs/json",
            }
            response = self._post(connection, server, "/api/run", json_request)
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["evidence"]["outcome"], "PASS")
            direct = compare(
                root / "json-recipe.json",
                f"json:{root / 'baseline.json'}#/rows",
                f"json:{root / 'candidate.json'}#/rows",
            )
            self.assertEqual(direct["outcome"], "PASS")
            publish(root / "runs" / "cli-json", direct, load_recipe(root / "json-recipe.json"))
            for file in (root / "runs" / "json").iterdir():
                self.assertEqual(file.read_bytes(), (root / "runs" / "cli-json" / file.name).read_bytes())
            formats = [
                ("sqlite", "db", "records"),
                ("xml", "xml", "root/row"),
            ]
            if Workbook:
                formats.append(("xlsx", "xlsx", "Sheet1!A1:B2"))
            for kind, suffix, selector in formats:
                with self.subTest(kind=kind):
                    for side in ("baseline", "candidate"):
                        source = root / f"{side}-{kind}.{suffix}"
                        if kind == "sqlite":
                            with closing(sqlite3.connect(source)) as database:
                                database.execute("CREATE TABLE records (private_id TEXT, secret TEXT)")
                                database.execute("INSERT INTO records VALUES ('1', 'hidden')")
                                database.commit()
                        elif kind == "xml":
                            source.write_text('<root><row private_id="1"><secret>hidden</secret></row></root>')
                        else:
                            workbook = Workbook()
                            workbook.active.title = "Sheet1"
                            workbook.active.append(["private_id", "secret"])
                            workbook.active.append(["1", "hidden"])
                            workbook.save(source)
                            workbook.close()
                    format_recipe = json.loads(recipe.read_text(encoding="utf-8"))
                    if kind in {"xml", "xlsx"}:
                        format_recipe["input_projection"] = "semantic-scalar-v1"
                    if kind == "xml":
                        format_recipe["recipe_version"] = 4
                        format_recipe["field_projection"] = {"version": 1}
                        for side in ("baseline", "candidate"):
                            format_recipe["field_projection"][side] = {
                                "kind": "xml-field-v1",
                                "namespaces": {},
                                "fields": {"private_id": "@private_id", "secret": "secret"},
                            }
                    format_recipe_path = root / f"{kind}-recipe.json"
                    format_recipe_path.write_text(json.dumps(format_recipe), encoding="utf-8")
                    sources = {side: f"{kind}:{side}-{kind}.{suffix}#{selector}" for side in ("baseline", "candidate")}
                    direct = compare(
                        format_recipe_path,
                        *(
                            f"{kind}:{root / f'{side}-{kind}.{suffix}'}#{selector}"
                            for side in ("baseline", "candidate")
                        ),
                    )
                    response = self._post(
                        connection,
                        server,
                        "/api/run",
                        {"recipe": format_recipe_path.name, **sources, "output": f"runs/{kind}"},
                    )
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read())["evidence"]["outcome"], "PASS")
                    self.assertEqual(direct["outcome"], "PASS")
                    publish(root / "runs" / f"cli-{kind}", direct, load_recipe(format_recipe_path))
                    for file in (root / "runs" / kind).iterdir():
                        self.assertEqual(file.read_bytes(), (root / "runs" / f"cli-{kind}" / file.name).read_bytes())
            response = self._post(connection, server, "/api/history", {})
            self.assertEqual(response.status, 200)
            expected = ["runs/two", "runs/three", "runs/json", "runs/sqlite", "runs/xml"]
            if Workbook:
                expected.append("runs/xlsx")
            self.assertEqual([run["bundle"] for run in json.loads(response.read())], expected)
            response = self._post(connection, server, "/api/compare", {"left": "runs/two", "right": "runs/three"})
            self.assertEqual(response.status, 200)
            comparison = json.loads(response.read())
            self.assertFalse(comparison["changed"])
            self.assertNotIn(str(root), json.dumps(comparison))
            response = self._post(connection, server, "/api/investigate", {"bundle": "runs/two"})
            self.assertEqual(response.status, 200)
            investigation = json.loads(response.read())
            self.assertTrue(investigation["groups"])
            self.assertTrue(all(group["count"] == 0 for group in investigation["groups"]))
            self.assertNotIn(str(root), json.dumps(investigation))

            response = self._post(connection, server, "/api/evidence", {"bundle": "../outside"})
            self.assertEqual(response.status, 422)
            response.read()
            link = root / "linked-bundle"
            link.symlink_to(bundle)
            response = self._post(connection, server, "/api/evidence", {"bundle": "linked-bundle"})
            self.assertEqual(response.status, 422)

            (bundle / "result.json").write_text("{}", encoding="utf-8")
            response.read()
            response = self._post(connection, server, "/api/evidence", {"bundle": "runs/one"})
            self.assertEqual(response.status, 422)
            self.assertNotIn(b"result.json", response.read())

    def test_rejects_unsafe_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.mkdir()
            link = Path(directory) / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(ParisonError, "non-symlink"):
                create_workbench_server(link)


if __name__ == "__main__":
    unittest.main()
