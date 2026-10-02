"""
Tests for FastAPI Main Entry Point & Sovereign Health Telemetry - Layer 2
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from fastapi.testclient import TestClient


class TestMainApplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint_metadata(self):
        """Verify root endpoint returns operational status and offline edge mode."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("service"), "BidLens AI Sovereign Backend")
        self.assertEqual(data.get("version"), "1.0.0")
        self.assertEqual(data.get("status"), "OPERATIONAL")
        self.assertEqual(data.get("mode"), "OFFLINE_EDGE_READY")
        self.assertIn("docs", data)

    def test_system_health_telemetry(self):
        """Verify /system/health endpoint returns air-gapped readiness and security checks."""
        response = self.client.get("/system/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("system_status"), "OPERATIONAL")
        self.assertIn("SOVEREIGN_OFFLINE_EDGE", data.get("mode", ""))
        self.assertEqual(data.get("cloud_data_retention"), "DISABLED (AIR-GAPPED COMPATIBLE)")
        sec = data.get("security_integrity", {})
        self.assertIn("SHA-256", sec.get("cryptographic_fingerprinting", ""))
        self.assertEqual(sec.get("guidelines_alignment"), "PROTOTYPE_BASELINE")
        self.assertNotIn("tamper_proof_audit_log", sec)
        self.assertNotIn("cert_in_compliance", sec)

    def test_all_routers_mounted(self):
        """Verify document, audit, and review routers are mounted in OpenAPI schema."""
        openapi_paths = app.openapi()["paths"].keys()
        self.assertTrue(any(p.startswith("/document") for p in openapi_paths))
        self.assertTrue(any(p.startswith("/audit") for p in openapi_paths))
        self.assertTrue(any(p.startswith("/review") for p in openapi_paths))
        self.assertIn("/system/health", openapi_paths)
        self.assertIn("/", openapi_paths)


if __name__ == '__main__':
    unittest.main()
