import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestrator.orchestrator import run_full_audit

class TestAuditOrchestrator(unittest.TestCase):
    def test_missing_file_raises_not_found(self):
        """Verify non-existent document path raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            asyncio.run(run_full_audit("non_existent_tender_proposal.pdf"))

    def test_orchestrator_payload_structure(self):
        """Verify 3-branch audit payload contains all Layer 3 and Layer 4 branches."""
        sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/sample_bids/Bid_ApexLabs_MSME.pdf'))
        if os.path.exists(sample_path):
            res = asyncio.run(run_full_audit(sample_path))
            self.assertIn("branch_a_extracted_data", res)
            self.assertIn("branch_b_clause_results", res)
            self.assertIn("branch_c_govt_verification", res)
            self.assertIn("knowledge_graph", res)
            self.assertIn("claim_integrity", res)
            self.assertIn("filename", res["file_info"])
            self.assertIn("overall_status", res["compliance_summary"])
            self.assertIsInstance(res["is_compliant"], bool)

    def test_async_parallel_fanout_execution(self):
        """Verify asyncio.gather executes Rule Engine and Govt Verification concurrently."""
        sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/sample_bids/Bid_ApexLabs_MSME.pdf'))
        if os.path.exists(sample_path):
            res = asyncio.run(run_full_audit(sample_path))
            self.assertEqual(res["file_info"]["vendor_name"], "Apex Labs Micro Devices LLP")
            self.assertGreater(len(res["branch_b_clause_results"]), 0)
            self.assertIn("overall_govt_verification", res["branch_c_govt_verification"])

if __name__ == '__main__':
    unittest.main()
