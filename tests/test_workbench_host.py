from __future__ import annotations

import http.client
import tempfile
import threading
import unittest
from pathlib import Path

from parison.core import ParisonError
from parison.workbench_host import create_workbench_server


class WorkbenchHostTests(unittest.TestCase):
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
            connection.request("GET", "/api/session")
            self.assertEqual(connection.getresponse().status, 404)
            connection.request("GET", "/api/session", headers={"X-Parison-Session": "test-capability"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn(b'"plans"', response.read())

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
