import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from evidence_risk.contradiction import detect_cross_document_contradictions

class TestContradictionDetector(unittest.TestCase):
    def test_detector_initialization(self):
        extracted = {"all_pans": [], "raw_text": "", "is_msme": False}
        govt = {"pan_gstin_consistent": True}
        res = detect_cross_document_contradictions(extracted, govt)
        self.assertIsInstance(res, list)


    def test_contra_pan_01_mismatch(self):
        """Verify CONTRA-PAN-01 flags multiple distinct PANs."""
        extracted = {
            "all_pans": ["ABCDE1234F", "XYZAB5678C"],
            "raw_text": "",
            "is_msme": False
        }
        contradictions = detect_cross_document_contradictions(extracted, {"pan_gstin_consistent": True})
        pan_flags = [c for c in contradictions if c["contradiction_id"] == "CONTRA-PAN-01"]
        self.assertEqual(len(pan_flags), 1)
        self.assertEqual(pan_flags[0]["severity"], "HIGH")


    def test_contra_gst_pan_02_and_tax_status_03(self):
        """Verify embedded PAN mismatch and expired tax status contradictions."""
        extracted = {
            "all_pans": ["ABCDE1234F"],
            "pan": "ABCDE1234F",
            "gstin": "27XYZAB5678C1Z5",
            "gstin_expired": True,
            "raw_text": "bid proposal text",
            "is_msme": False
        }
        govt = {
            "pan_gstin_consistent": False,
            "consistency_note": "PAN mismatch detected."
        }
        contradictions = detect_cross_document_contradictions(extracted, govt)
        c_ids = [c["contradiction_id"] for c in contradictions]
        self.assertIn("CONTRA-GST-PAN-02", c_ids)
        self.assertIn("CONTRA-TAX-STATUS-03", c_ids)


    def test_contra_eligibility_04_and_mii_05(self):
        """Verify non-MSME turnover shortfall and unsubstantiated Make in India self-declaration."""
        extracted = {
            "all_pans": ["ABCDE1234F"],
            "pan": "ABCDE1234F",
            "gstin": "27ABCDE1234F1Z5",
            "gstin_expired": False,
            "raw_text": "we hereby declare compliance with make in india class-1 local supplier criteria.",
            "is_msme": False,
            "turnover_cr": 0.8,
            "local_content_pct": 0
        }
        govt = {"pan_gstin_consistent": True}
        contradictions = detect_cross_document_contradictions(extracted, govt, tender_requirements={"min_turnover_cr": 1.5})
        c_ids = [c["contradiction_id"] for c in contradictions]
        self.assertIn("CONTRA-ELIGIBILITY-04", c_ids)
        self.assertIn("CONTRA-FRAUD-MII-05", c_ids)

if __name__ == '__main__':
    unittest.main()



