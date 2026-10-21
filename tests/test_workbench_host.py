from __future__ import annotations

import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from parison.core import ParisonError, compare, load_recipe, publish
from parison.workbench_host import _choose_bundle, _choose_recipe, _workspace_source, create_workbench_server

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None


class WorkbenchHostTests(unittest.TestCase):
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
                {"source": plan["source"], "path": ["scope", "snapshot"], "operation": "set", "value": '"field-edit"'},
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(json.loads(response.read())["source"])["scope"]["snapshot"], "field-edit")
            self.assertEqual(recipe.read_text(encoding="utf-8"), plan["source"])
            for path, request in (
                ("/api/plan-controls", {"source": []}),
                ("/api/plan-controls", {"source": "[]"}),
                ("/api/edit-plan", {"source": plan["source"], "path": [], "operation": [], "value": "null"}),
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
