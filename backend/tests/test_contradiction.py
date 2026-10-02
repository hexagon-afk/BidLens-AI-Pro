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
        self.assertEqual(pan_flags[0]["severity"], "CRITICAL")

if __name__ == '__main__':
    unittest.main()

