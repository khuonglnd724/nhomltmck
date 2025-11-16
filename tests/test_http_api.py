import os
import unittest

# Ensure DB is disabled for tests to avoid MySQL dependency
os.environ["ENABLE_DB"] = "false"

from fastapi.testclient import TestClient
from server.http_app import app


class TestHTTPAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("status"), "ok")
        # When DB disabled via env, db_enabled should be False
        self.assertIn("db_enabled", data)
        self.assertFalse(data["db_enabled"])  # EXPECT DB off in tests

    def test_upload_without_db(self):
        # Simulate a small file upload
        files = {
            "file": ("hello.txt", b"hello world", "text/plain"),
        }
        data = {"user_id": 1}
        r = self.client.post("/api/upload", files=files, data=data)
        self.assertEqual(r.status_code, 200)
        res = r.json()
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("filename"), "hello.txt")
        self.assertEqual(res.get("bytes"), 11)
        # With DB disabled, endpoint indicates not stored to DB
        self.assertFalse(res.get("stored"))

    def test_files_requires_db(self):
        # /api/files should be unavailable when DB disabled
        r = self.client.get("/api/files", params={"user_id": 1})
        self.assertEqual(r.status_code, 503)

    def test_stats_without_db(self):
        r = self.client.get("/api/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("total_files"), 0)
        self.assertEqual(data.get("total_bytes"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
