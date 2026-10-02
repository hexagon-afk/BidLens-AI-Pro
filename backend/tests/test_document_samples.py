"""
Integration tests for Pre-Packaged GeM Sample Document Loaders - Layer 2
"""
import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app
from fastapi.testclient import TestClient


class TestDocumentSamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_load_sample_tender_rfp(self):
        """Verify pre-packaged GeM computer tender RFP loads and parses successfully."""
        response = self.client.get("/document/tender/sample")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "SUCCESS")
        tender_data = data.get("tender_data", {})
        self.assertTrue(len(tender_data.get("sha256", "")) == 64)
        self.assertIn("tender_id", tender_data)

    def test_load_sample_vendor_bids(self):
        """Verify pre-packaged vendor bids load and extract across PDF, DOCX, XLSX, and PNG."""
        response = self.client.get("/document/sample/vendor-bids")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertGreaterEqual(data.get("count", 0), 1)

    def test_load_single_sample_bid_with_extension(self):
        """Verify loading specific sample by exact filename."""
        response = self.client.post("/document/sample/load/Bid_ApexLabs_MSME.pdf")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "uploaded")
        self.assertIn("extracted_summary", data)

    def test_load_single_sample_bid_extensionless(self):
        """Verify loading specific sample using extensionless name."""
        response = self.client.post("/document/sample/load/Bid_ApexLabs_MSME")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "uploaded")
        self.assertEqual(data.get("filename"), "Bid_ApexLabs_MSME.pdf")


if __name__ == '__main__':
    unittest.main()
