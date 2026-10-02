import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from evidence_risk.graph_engine import build_compliance_knowledge_graph

class TestKnowledgeGraphEngine(unittest.TestCase):
    def test_graph_scaffold_initialization(self):
        file_info = {"filename": "test_bid.pdf", "vendor_name": "Apex Labs"}
        clause_results = [
            {
                "clause_id": "GFR-149-GST",
                "clause_name": "GSTIN Validity",
                "regulation_ref": "GFR 2017 Rule 149",
                "status": "PASS",
                "evidence": "Active GSTIN verified."
            }
        ]
        govt = {"overall_govt_verification": "PASS"}

        graph = build_compliance_knowledge_graph(file_info, clause_results, govt)
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertGreaterEqual(graph["summary"]["total_nodes"], 4)

    def test_semantic_compliance_chain_relations(self):
        """Verify Regulation -> Clause -> Evidence -> Decision directed relations."""
        file_info = {"filename": "proposal.pdf", "vendor_name": "MegaTech Systems"}
        clauses = [
            {
                "clause_id": "GFR-160-TO",
                "clause_name": "Turnover Threshold",
                "regulation_ref": "GFR 2017 Rule 160",
                "status": "PASS",
                "evidence": "CA audited turnover sheet."
            }
        ]
        govt = {"overall_govt_verification": "PASS"}
        graph = build_compliance_knowledge_graph(file_info, clauses, govt)
        relations = [e["relation"] for e in graph["edges"]]
        
        self.assertIn("governs", relations)
        self.assertIn("mandates_evidence", relations)
        self.assertIn("justifies_decision", relations)
        self.assertIn("cross_verified_with_portal", relations)

if __name__ == '__main__':
    unittest.main()
