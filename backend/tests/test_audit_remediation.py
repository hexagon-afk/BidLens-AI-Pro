"""
BidLens AI - Correctness & Deployment Gates Acceptance Test Suite
Verifies all 7 deployment gates from the procurement audit:
1. Dynamic threshold response (2.0 Cr bidder passes 1.0 Cr tender, fails 3.0 Cr tender).
2. 1-Year warranty strictly fails 3-Year requirement.
3. Unreadable/unresolved turnover produces NEEDS_REVIEW (no fake defaults).
4. Negated MSME declaration ("We are not an MSME") does not grant exemption.
5. MegaTech BoQ Excel quote correctly resolves to INR 48,00,000 (not 1,00,000).
6. Officer override dynamically recalculates overall status, summary counts, and risk.
7. Modulus-36 checksum strictly validates GSTIN and rejects invalid check-digits.
8. Empty input returns NEUTRAL/NOT_EVALUATED, not false positive verifications.
"""
import unittest
import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator.rule_engine import evaluate_compliance
from orchestrator.ai_processing import extract_document_data
from orchestrator.govt_verify import verify_government_credentials, verify_gstin_checksum
from routers.audit import trigger_audit, record_clause_override, RunAuditPayload, ClauseOverridePayload


class TestAuditRemediationGates(unittest.TestCase):

    def test_gate_1_different_results_when_tender_threshold_changes(self):
        """Gate 1: The same bidder receives different results when tender threshold changes."""
        bidder = {"turnover_cr": 2.0, "is_msme": False}
        
        # Tender 1: Requires 1.0 Cr turnover
        res_lenient = evaluate_compliance(bidder, {"min_turnover_cr": 1.0, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000})
        t_lenient = [c for c in res_lenient if c["clause_id"] == "GFR-160-TO"][0]
        self.assertEqual(t_lenient["status"], "PASS")

        # Tender 2: Requires 3.0 Cr turnover
        res_strict = evaluate_compliance(bidder, {"min_turnover_cr": 3.0, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000})
        t_strict = [c for c in res_strict if c["clause_id"] == "GFR-160-TO"][0]
        self.assertEqual(t_strict["status"], "FAIL")

    def test_gate_2_one_year_warranty_fails_three_year_requirement(self):
        """Gate 2: 1-Year warranty fails an applicable 3-Year requirement."""
        bidder = {"warranty": "1-Year Standard OEM Warranty", "warranty_years": 1.0}
        res = evaluate_compliance(bidder, {"min_warranty_years": 3, "min_turnover_cr": 1.5, "min_local_content_pct": 50, "emd_required_inr": 100000})
        w = [c for c in res if c["clause_id"] == "SPEC-WARRANTY"][0]
        self.assertEqual(w["status"], "FAIL")
        self.assertIn("fails mandatory 3-Year", w["evidence"])

    def test_gate_3_unreadable_evidence_produces_needs_review(self):
        """Gate 3: Unreadable evidence produces NEEDS_REVIEW, not an invented pass or fail."""
        bidder = {"turnover_cr": None, "is_msme": False}
        res = evaluate_compliance(bidder, {"min_turnover_cr": 1.5, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000})
        t = [c for c in res if c["clause_id"] == "GFR-160-TO"][0]
        self.assertEqual(t["status"], "NEEDS_REVIEW")

    def test_gate_4_negated_msme_does_not_grant_exemption(self):
        """Gate 4: 'We are not an MSME' does not grant MSME turnover or EMD exemption."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as fp:
            fp.write("We are not an MSME. No bank guarantee submitted. Annual turnover is 0.50 Crore.")
            temp_path = fp.name

        try:
            extracted = extract_document_data(temp_path)
            self.assertFalse(extracted["is_msme"])
            self.assertEqual(extracted["emd_status"], "MISSING")
            
            res = evaluate_compliance(extracted, {"min_turnover_cr": 1.5, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000})
            statuses = {c["clause_id"]: c["status"] for c in res}
            # Turnover below 1.5 Cr without MSME exemption must be FAIL
            self.assertEqual(statuses.get("GFR-160-TO"), "FAIL")
            self.assertEqual(statuses.get("GFR-170-EMD"), "FAIL")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_5_megatech_excel_boq_quote_matches_48_lakh(self):
        """Gate 5: Displayed price on MegaTech BoQ matches INR 48,00,000 (not 1,00,000 EMD)."""
        sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_bids", "BoQ_PriceSchedule_MegaTech.xlsx"))
        if os.path.exists(sample_path):
            extracted = extract_document_data(sample_path)
            self.assertEqual(extracted["total_quote_inr"], 4800000.0)

    def test_gate_6_override_recalculates_overall_compliance(self):
        """Gate 6: Overriding a clause dynamically recalculates overall status and compliance."""
        async def run_test():
            payload = RunAuditPayload(
                file_id="Bid_GlobalCorp_Rectified_ReEvaluation.pdf",
                tender_requirements={"min_turnover_cr": 1.0, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000}
            )
            audit_res = await trigger_audit(payload)
            self.assertEqual(audit_res["overall_status"], "COMPLIANT")
            self.assertTrue(audit_res["is_compliant"])

            # Override clause to FAIL
            override_payload = ClauseOverridePayload(
                bid_id="Bid_GlobalCorp_Rectified_ReEvaluation.pdf",
                clause_id="SPEC-WARRANTY",
                clause_name="Comprehensive Onsite Warranty",
                original_status="PASS",
                new_status="FAIL",
                justification="Supervisory officer flagged missing manufacturer authorization."
            )
            override_res = record_clause_override(override_payload)
            self.assertEqual(override_res["overall_status"], "NON_COMPLIANT")
            self.assertFalse(override_res["is_compliant"])

        asyncio.run(run_test())

    def test_gate_7_gstin_checksum_rejects_arbitrary_characters(self):
        """Gate 7: Modulus-36 checksum rejects non-matching characters for a GSTIN prefix."""
        prefix = "27AABCU9603R1Z"
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        passed = [c for c in chars if verify_gstin_checksum(prefix + c)]
        self.assertEqual(len(passed), 1)
        self.assertEqual(passed[0], "N")

    def test_empty_input_produces_neutral_not_false_positive(self):
        """Empty input does not return false positive MCA or EPFO verifications."""
        res = verify_government_credentials({})
        self.assertEqual(res["overall_govt_verification"], "NOT_APPLICABLE")
        gateways = {g["name"]: g["badge"] for g in res["gateways"]}
        self.assertEqual(gateways.get("MCA21 Corporate Affairs"), "NEUTRAL")
        self.assertEqual(gateways.get("EPFO & ESIC Labour Compliance"), "NEUTRAL")


if __name__ == '__main__':
    unittest.main()
