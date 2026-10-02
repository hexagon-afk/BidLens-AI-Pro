"""
Tests for PDF Dossier Generator and Official B&W Canvas - Layer 5
"""
import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.pdf_generator import generate_certified_audit_pdf, OfficialReportCanvas


class TestPdfGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_pdf = os.path.join(self.temp_dir, "test_report.pdf")

    def tearDown(self):
        if os.path.exists(self.output_pdf):
            try:
                os.remove(self.output_pdf)
            except OSError:
                pass
        if os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except OSError:
                pass

    def test_generate_pdf_with_sample_data(self):
        """Verify certified PDF generates successfully and is non-empty."""
        sample_audit = {
            "file_info": {
                "vendor_name": "Apex Laboratories Pvt Ltd",
                "filename": "Bid_ApexLabs_MSME.pdf"
            },
            "compliance_summary": {
                "overall_status": "COMPLIANT",
                "risk_tier": "LOW",
                "total_clauses_checked": 5,
                "passed": 4,
                "exempt": 1,
                "failed": 0
            },
            "rejection_risk_analysis": {
                "risk_score": 0.12
            },
            "government_verification": {
                "overall_govt_verification": "VERIFIED"
            }
        }

        result_path = generate_certified_audit_pdf(sample_audit, self.output_pdf)
        self.assertEqual(result_path, self.output_pdf)
        self.assertTrue(os.path.exists(self.output_pdf))
        self.assertGreater(os.path.getsize(self.output_pdf), 500)

    def test_generate_pdf_missing_metadata_fallback(self):
        """Verify fallback defaults when file_info is empty dict."""
        empty_audit = {}
        result_path = generate_certified_audit_pdf(empty_audit, self.output_pdf)
        self.assertTrue(os.path.exists(result_path))
        self.assertGreater(os.path.getsize(result_path), 500)


if __name__ == '__main__':
    unittest.main()
