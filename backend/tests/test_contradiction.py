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

if __name__ == '__main__':
    unittest.main()
