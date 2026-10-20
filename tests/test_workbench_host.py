from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from parison.core import ParisonError, compare, load_recipe, publish
from parison.workbench_host import _choose_bundle, _choose_recipe, create_workbench_server


class WorkbenchHostTests(unittest.TestCase):
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
