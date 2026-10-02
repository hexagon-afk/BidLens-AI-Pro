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
        """Verify fallback defaults when file_info is empty dict and risk_score is None."""
        empty_audit = {
            "rejection_risk_analysis": {"risk_score": None}
        }
        result_path = generate_certified_audit_pdf(empty_audit, self.output_pdf)
        self.assertTrue(os.path.exists(result_path))
        self.assertGreater(os.path.getsize(result_path), 500)

    def test_generate_pdf_full_dossier_with_overrides_and_evidence(self):
        """Verify full dossier with clauses, contradictions, and officer overrides."""
        full_audit = {
            "file_info": {
                "vendor_name": "MegaTech Systems & Solutions Ltd",
                "filename": "Bid_MegaTech_BigBrand.pdf"
            },
            "compliance_summary": {
                "overall_status": "COMPLIANT",
                "risk_tier": "LOW",
                "total_clauses_checked": 4,
                "passed": 3,
                "exempt": 0,
                "failed": 1
            },
            "rejection_risk_analysis": {
                "risk_score": 0.08
            },
            "value_spotlight": {
                "is_spotlight_candidate": True,
                "value_highlights": ["Meets 65% Local Content baseline", "3-Year Comprehensive Warranty"]
            },
            "government_verification": {
                "overall_govt_verification": "VERIFIED",
                "gateways": [
                    {"name": "GSTN Portal", "status": "VERIFIED", "details": {"gstin": "27AAACG0561F1Z1"}},
                    {"name": "ITD PAN Registry", "status": "VERIFIED", "details": {"pan": "AAACG0561F"}}
                ]
            },
            "clause_level_decisions": [
                {
                    "clause_id": "GFR-149",
                    "clause_name": "GSTIN Tax Registration",
                    "status": "PASS",
                    "regulation_ref": "Rule 149 GFR 2017 & GeM Guidelines",
                    "evidence": "Active GSTIN found with turnover > 10 Cr & valid filing."
                }
            ],
            "contradictions_detected": [
                {
                    "title": "Minor formatting discrepancy",
                    "severity": "LOW",
                    "description": "Declaration date precedes tender issuance by 2 days",
                    "remedy": "Obtain clarification letter from bidder."
                }
            ]
        }

        overrides = {
            "GFR-149": {
                "clause_name": "GSTIN Tax Registration",
                "original_status": "FAIL",
                "status": "PASS",
                "justification": "Verified on live GST portal manually under Rule 149 delegation.",
                "timestamp": "02-Oct-2026 23:25"
            }
        }

        nested_pdf_path = os.path.join(self.temp_dir, "nested", "subfolder", "dossier.pdf")
        result_path = generate_certified_audit_pdf(
            full_audit,
            nested_pdf_path,
            officer_name="Shri A. K. Sharma",
            officer_designation="Director of Procurement",
            officer_overrides=overrides
        )
        self.assertTrue(os.path.exists(result_path))
        self.assertGreater(os.path.getsize(result_path), 1500)


if __name__ == '__main__':
    unittest.main()
