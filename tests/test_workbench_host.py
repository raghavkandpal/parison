from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from parison.core import ParisonError, compare, load_recipe, publish
from parison.workbench_host import create_workbench_server


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
            response = self._post(connection, server, "/api/session", {}, Origin="http://attacker.invalid")
            self.assertEqual(response.status, 404)
            response.read()
            response = self._post(connection, server, "/api/session", {})
            self.assertEqual(response.status, 200)
            self.assertIn(b'"plans"', response.read())

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
