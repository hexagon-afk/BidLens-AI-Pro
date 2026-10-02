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

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TEST_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

sys.path.insert(0, BACKEND_DIR)

from orchestrator.orchestrator import run_full_audit

from orchestrator.rule_engine import evaluate_compliance
from orchestrator.ai_processing import extract_document_data, extract_tender_rfp_data
from orchestrator.govt_verify import verify_government_credentials, verify_gstin_checksum
from orchestrator.orchestrator import compute_unified_audit_verdict
from routers.audit import trigger_audit, record_clause_override, reset_vendor_overrides, RunAuditPayload, ClauseOverridePayload
from pydantic import ValidationError


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

    def test_gate_8_minimal_tender_rfp_returns_none_for_unstated_criteria(self):
        """Gate 8: Minimal tender RFP returns None for unstated criteria (no invented defaults)."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as fp:
            fp.write("Government of India Tender Ref GEM/2026/B/1000. Supply of 100 Desktop Computers. Delivery within 30 days.")
            temp_path = fp.name

        try:
            extracted = extract_tender_rfp_data(temp_path)
            self.assertIsNone(extracted.get("budget_inr"))
            self.assertIsNone(extracted.get("min_turnover_cr"))
            self.assertIsNone(extracted.get("emd_inr"))
            self.assertIsNone(extracted.get("min_local_content_pct"))
            self.assertIsNone(extracted.get("min_warranty_years"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_9_banana_override_rejected_with_validation_error(self):
        """Gate 9: Non-enum override action (e.g. 'BANANA') is strictly rejected by Pydantic."""
        with self.assertRaises(ValidationError):
            ClauseOverridePayload(
                bid_id="test_bid.pdf",
                clause_id="GFR-149-GST",
                clause_name="GSTIN Registration",
                original_status="PASS",
                new_status="BANANA",
                justification="Arbitrary invalid status test"
            )

    def test_gate_10_corporate_experience_vs_warranty_parsing(self):
        """Gate 10: '5 years experience. Offered warranty: 1 year' extracts 1.0 yr warranty (not 5.0)."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as fp:
            fp.write("Company has 5 years experience in supplying IT hardware. Offered warranty: 1 year.")
            temp_path = fp.name

        try:
            extracted = extract_document_data(temp_path)
            self.assertEqual(extracted.get("warranty_years"), 1.0)
            self.assertEqual(extracted.get("warranty"), "1-Year Standard OEM Warranty")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_11_unrelated_negation_does_not_break_emd(self):
        """Gate 11: Unrelated negation does not falsely mark submitted EMD as missing."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as fp:
            fp.write("OEM authorization not provided. EMD Bank Guarantee for INR 1,00,000 submitted via SBI.")
            temp_path = fp.name

        try:
            extracted = extract_document_data(temp_path)
            self.assertEqual(extracted.get("emd_status"), "SUBMITTED")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_12_gstin_not_expired_negation_handling(self):
        """Gate 12: 'GST registration is not expired' parses as gstin_expired == False."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as fp:
            fp.write("GSTIN 27AABCT3456L1Z1 is active and registration is not expired.")
            temp_path = fp.name

        try:
            extracted = extract_document_data(temp_path)
            self.assertFalse(extracted.get("gstin_expired"))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_13_pan_gstin_mismatch_prevents_compliant_verdict(self):
        """Gate 13: Critical PAN mismatch strictly prevents COMPLIANT verdict even if all clauses pass."""
        clauses = [
            {"clause_id": "GFR-149-GST", "status": "PASS"},
            {"clause_id": "GFR-160-TO", "status": "PASS"},
            {"clause_id": "GFR-170-EMD", "status": "PASS"},
            {"clause_id": "MII-2017-LC", "status": "PASS"},
            {"clause_id": "SPEC-WARRANTY", "status": "PASS"}
        ]
        contradictions = [{
            "contradiction_id": "CONTRA-GST-PAN-02",
            "type": "GSTIN_EMBEDDED_PAN_MISMATCH",
            "severity": "CRITICAL",
            "title": "GSTIN Entity Mismatch with Declared PAN",
            "description": "Embedded PAN does not match declared PAN.",
            "impact": "Proxy bidding risk.",
            "remedy": "Provide matching tax certificate."
        }]
        verdict = compute_unified_audit_verdict(clauses, contradictions, extracted={})
        self.assertNotEqual(verdict["overall_status"], "COMPLIANT")
        self.assertFalse(verdict["is_compliant"])
        self.assertEqual(verdict["overall_status"], "NON_COMPLIANT")
        self.assertIn(verdict["risk_and_value"]["rejection_risk"]["risk_tier"], ["HIGH", "CRITICAL"])

    def test_gate_14_override_reset_restores_original_verdict(self):
        """Gate 14: Resetting vendor overrides restores original machine status and recalculates."""
        async def run_test():
            payload = RunAuditPayload(
                file_id="Bid_GlobalCorp_Rectified_ReEvaluation.pdf",
                tender_requirements={"min_turnover_cr": 1.0, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000}
            )
            audit_res = await trigger_audit(payload)
            self.assertEqual(audit_res["overall_status"], "COMPLIANT")

            # Override clause to FAIL
            override_payload = ClauseOverridePayload(
                bid_id="Bid_GlobalCorp_Rectified_ReEvaluation.pdf",
                clause_id="SPEC-WARRANTY",
                clause_name="Comprehensive Onsite Warranty",
                original_status="PASS",
                new_status="FAIL",
                justification="Officer test override to FAIL"
            )
            override_res = record_clause_override(override_payload)
            self.assertEqual(override_res["overall_status"], "NON_COMPLIANT")

            # Reset overrides
            reset_res = reset_vendor_overrides("Bid_GlobalCorp_Rectified_ReEvaluation.pdf")
            self.assertEqual(reset_res["overall_status"], "COMPLIANT")

    def test_gate_15_tender_emd_not_wiped_by_mse_exemption(self):
        """Gate 15: Tender with positive EMD and MSE exemption text extracts base EMD, not 0.0."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Government e-Marketplace. Tender Ref: GEM/2026/B/892100. EMD INR 100000. EMD exempted for eligible MSE bidders.")
            temp_path = f.name
        try:
            t_data = extract_tender_rfp_data(temp_path)
            self.assertEqual(t_data["emd_inr"], 100000.0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_16_warranty_offer_vs_quoted_requirement(self):
        """Gate 16: Proposal quoting tender requirement (3 yr) but offering (1 yr) resolves to 1.0 yr."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Bidder Proposal. GSTIN: 27AABCT3456L1Z1. PAN: AABCT3456L. Required warranty: 3 years. Offered warranty: 1 year. Local content 60%.")
            temp_path = f.name
        try:
            v_data = extract_document_data(temp_path)
            self.assertEqual(v_data["warranty_years"], 1.0)
            self.assertIn("1-Year", v_data["warranty"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_17_warranty_carry_in_no_hallucinated_onsite(self):
        """Gate 17: Proposal offering 5 years carry-in does not hallucinate onsite or 24x7 coverage."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Commercial Bid. GSTIN: 27AABCT3456L1Z1. PAN: AABCT3456L. Warranty: 5 years carry-in only. Local content 60%.")
            temp_path = f.name
        try:
            v_data = extract_document_data(temp_path)
            self.assertEqual(v_data["warranty_years"], 5.0)
            self.assertIn("Carry-in", v_data["warranty"])
            self.assertNotIn("Onsite", v_data["warranty"])
            self.assertNotIn("24x7", v_data["warranty"])
            self.assertEqual(v_data["bonus_perks"], [])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_gate_18_emd_shortfall_fails(self):
        """Gate 18: Submitting an instrument amount below tender requirement results in FAIL with shortfall."""
        bidder = {
            "gstin": "27AABCT3456L1Z1",
            "turnover_cr": 5.0,
            "emd_status": "SUBMITTED",
            "emd_amount_inr": 100.0,
            "local_content_pct": 60,
            "warranty_years": 3.0
        }
        res = evaluate_compliance(bidder, {"emd_required_inr": 100000.0, "min_turnover_cr": 1.5, "min_local_content_pct": 50, "min_warranty_years": 3})
        emd_clause = next(c for c in res if c["clause_id"] == "GFR-170-EMD")
        self.assertEqual(emd_clause["status"], "FAIL")
        self.assertIn("falls short of required", emd_clause["evidence"])
        self.assertIn("Shortfall: INR 99,900", emd_clause["evidence"])

    def test_gate_19_empty_unreadable_document_returns_needs_review_all_clauses(self):
        """Gate 19: Empty or unreadable document returns NEEDS_REVIEW across all 5 clauses."""
        bidder = {"raw_text_length": 5, "is_unreadable": True}
        res = evaluate_compliance(bidder, {"min_turnover_cr": 1.5, "emd_required_inr": 100000.0, "min_local_content_pct": 50, "min_warranty_years": 3})
        self.assertEqual(len(res), 5)
        for clause in res:
            self.assertEqual(clause["status"], "NEEDS_REVIEW", f"Clause {clause['clause_id']} did not return NEEDS_REVIEW")

    def test_gate_20_empty_clause_evaluation_prevents_compliant(self):
        """Gate 20: An empty clause results list in compute_unified_audit_verdict returns NEEDS_REVIEW, never COMPLIANT."""
        verdict = compute_unified_audit_verdict([], [], extracted={})
        self.assertEqual(verdict["overall_status"], "NEEDS_REVIEW")
        self.assertFalse(verdict["is_compliant"])

    def test_gate_21_override_endpoint_returns_both_results_and_audit_result_and_updates_graph(self):
        """Gate 21: Override endpoint returns both results and audit_result keys and rebuilds knowledge graph."""
        async def run_test():
            payload = RunAuditPayload(
                file_id="Bid_GlobalCorp_Rectified_ReEvaluation.pdf",
                tender_requirements={"min_turnover_cr": 1.0, "min_warranty_years": 3, "min_local_content_pct": 50, "emd_required_inr": 100000}
            )
            audit_res = await trigger_audit(payload)
            self.assertIn("results", audit_res)

            override_payload = ClauseOverridePayload(
                bid_id="Bid_GlobalCorp_Rectified_ReEvaluation.pdf",
                clause_id="SPEC-WARRANTY",
                clause_name="Comprehensive Onsite Warranty",
                original_status="PASS",
                new_status="FAIL",
                justification="Supervisory override for testing"
            )
            override_res = record_clause_override(override_payload)
            self.assertIn("results", override_res)
            self.assertIn("audit_result", override_res)
            self.assertIn("knowledge_graph", override_res["results"])

            reset_res = reset_vendor_overrides("Bid_GlobalCorp_Rectified_ReEvaluation.pdf")
            self.assertIn("results", reset_res)
            self.assertIn("audit_result", reset_res)
            self.assertIn("knowledge_graph", reset_res["results"])

        asyncio.run(run_test())

    def test_gate_22_unmocked_end_to_end_sample_evaluation(self):
        """Gate 22: Un-mocked end-to-end sample PDF evaluation strictly from Tender RFP data."""
        async def run_test():
            tender_path = os.path.join(BACKEND_DIR, "data", "sample_bids", "Tender_RFP_GeM_Computers.pdf")
            self.assertTrue(os.path.exists(tender_path))
            t_data = extract_tender_rfp_data(tender_path)
            self.assertEqual(t_data.get("budget_inr"), 5000000.0)
            self.assertEqual(t_data.get("emd_inr"), 100000.0)
            self.assertEqual(t_data.get("min_turnover_cr"), 1.5)
            self.assertEqual(t_data.get("min_local_content_pct"), 50)
            self.assertEqual(t_data.get("min_warranty_years"), 3.0)
            self.assertEqual(t_data.get("required_service_type"), "Onsite")

            tender_reqs = {
                "budget_inr": t_data.get("budget_inr"),
                "min_turnover_cr": t_data.get("min_turnover_cr"),
                "emd_required_inr": t_data.get("emd_inr"),
                "min_local_content_pct": t_data.get("min_local_content_pct"),
                "min_warranty_years": t_data.get("min_warranty_years"),
                "required_service_type": t_data.get("required_service_type")
            }

            bids_dir = os.path.join(BACKEND_DIR, "data", "sample_bids")
            # 1. ApexLabs MSME
            apex_res = await run_full_audit(os.path.join(bids_dir, "Bid_ApexLabs_MSME.pdf"), tender_reqs)
            self.assertEqual(apex_res["overall_status"], "COMPLIANT")
            self.assertTrue(apex_res["is_compliant"])
            self.assertEqual(apex_res["compliance_summary"]["exempt"], 2)

            # 2. MegaTech BigBrand
            mega_res = await run_full_audit(os.path.join(bids_dir, "Bid_MegaTech_BigBrand.pdf"), tender_reqs)
            self.assertEqual(mega_res["overall_status"], "COMPLIANT")
            self.assertTrue(mega_res["is_compliant"])
            self.assertEqual(mega_res["compliance_summary"]["passed"], 5)

            # 3. GlobalCorp Ineligible
            glob_res = await run_full_audit(os.path.join(bids_dir, "Bid_GlobalCorp_Ineligible.pdf"), tender_reqs)
            self.assertEqual(glob_res["overall_status"], "NON_COMPLIANT")
            self.assertFalse(glob_res["is_compliant"])
            self.assertEqual(glob_res["compliance_summary"]["failed"], 5)

            # 4. GlobalCorp Rectified
            rect_res = await run_full_audit(os.path.join(bids_dir, "Bid_GlobalCorp_Rectified_ReEvaluation.pdf"), tender_reqs)
            self.assertEqual(rect_res["overall_status"], "COMPLIANT")
            self.assertTrue(rect_res["is_compliant"])
            self.assertEqual(rect_res["compliance_summary"]["passed"], 5)

        asyncio.run(run_test())

    def test_gate_23_tender_emd_percentage_isolated_from_delivery_penalty(self):
        """Gate 23: Delivery penalty percentage does not create an EMD requirement."""
        clean_text = "Estimated Tender Value: INR 50,00,000.\nDelivery penalty 2% per week for delay.\nEMD: Nil."
        # Priority check: Nil EMD should not be overridden by generic 2% delivery penalty
        # Extract from dummy file
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tf:
            tf.write(clean_text)
            temp_path = tf.name

        try:
            res = extract_tender_rfp_data(temp_path)
            self.assertEqual(res.get("budget_inr"), 5000000.0)
            self.assertEqual(res.get("emd_inr"), 0.0)
        finally:
            os.remove(temp_path)

    def test_gate_24_emd_instrument_id_and_units_extraction(self):
        """Gate 24: Separate EMD instrument ID from amount and support Lakh/Crore units."""
        import tempfile
        # Test A: Instrument ID with slashes and years
        text_a = "Bank Guarantee No. BG/SBI/2026/8821 for INR 1,00,000 issued by State Bank of India."
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tf:
            tf.write(text_a)
            path_a = tf.name

        try:
            res_a = extract_document_data(path_a)
            self.assertEqual(res_a.get("emd_instrument_id"), "BG/SBI/2026/8821")
            self.assertEqual(res_a.get("emd_amount_inr"), 100000.0)
            self.assertEqual(res_a.get("emd_status"), "SUBMITTED")
        finally:
            os.remove(path_a)

        # Test B: Amount in Lakhs
        text_b = "EMD Bank Guarantee of 2.5 Lakhs submitted with ID BG-99128."
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as tf:
            tf.write(text_b)
            path_b = tf.name

        try:
            res_b = extract_document_data(path_b)
            self.assertEqual(res_b.get("emd_amount_inr"), 250000.0)
            self.assertEqual(res_b.get("emd_status"), "SUBMITTED")
        finally:
            os.remove(path_b)

    def test_gate_25_submitted_emd_with_unknown_amount_returns_needs_review(self):
        """Gate 25: A submitted EMD with unverified face value returns NEEDS_REVIEW, never PASS."""
        vendor_data = {
            "vendor_name": "Test Corp",
            "is_msme": False,
            "udyam": None,
            "emd_status": "SUBMITTED",
            "emd_amount_inr": None,  # Amount unknown!
            "emd_instrument_id": "BG-UNKNOWN-001"
        }
        tender_reqs = {"emd_required_inr": 100000.0}
        clauses = evaluate_compliance(vendor_data, tender_reqs)
        emd_clause = next(c for c in clauses if c["clause_id"] == "GFR-170-EMD")
        self.assertEqual(emd_clause["status"], "NEEDS_REVIEW")
        self.assertIn("officer verification required", emd_clause["remedy"].lower())

    def test_gate_26_carry_in_warranty_fails_onsite_requirement(self):
        """Gate 26: 5-Year Carry-in warranty fails a 3-Year Onsite warranty requirement."""
        vendor_data = {
            "warranty": "5-Year Carry-in Warranty",
            "warranty_years": 5.0,
            "offered_service_type": "Carry-in"
        }
        tender_reqs = {
            "min_warranty_years": 3.0,
            "required_service_type": "Onsite"
        }
        clauses = evaluate_compliance(vendor_data, tender_reqs)
        w_clause = next(c for c in clauses if c["clause_id"] == "SPEC-WARRANTY")
        self.assertEqual(w_clause["status"], "FAIL")
        self.assertIn("Carry-in", w_clause["evidence"])
        self.assertIn("mismatch", w_clause["evidence"].lower())

    def test_gate_27_unrecognized_clause_status_forces_needs_review(self):
        """Gate 27: Unrecognized clause status in compute_unified_audit_verdict returns NEEDS_REVIEW."""
        clause_results = [
            {"clause_id": "C-1", "status": "PASS"},
            {"clause_id": "C-2", "status": "UNKNOWN_MANUAL_STATE"}
        ]
        verdict = compute_unified_audit_verdict(clause_results, [], extracted={})
        self.assertEqual(verdict["overall_status"], "NEEDS_REVIEW")
        self.assertFalse(verdict["is_compliant"])

    def test_gate_28_durable_append_only_override_trail_and_agent_review(self):
        """Gate 28: Overrides append to JSONL trail and agent review produces structured tool calls."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)

        # Agent review endpoint
        res = client.post("/audit/agent/review/Bid_MegaTech_BigBrand.pdf")
        self.assertEqual(res.status_code, 200)
        review = res.json().get("review", {})
        self.assertIn("agent_trajectory", review)
        self.assertGreater(len(review["agent_trajectory"]), 5)
        self.assertEqual(review.get("officer_recommendation", {}).get("final_verdict"), "ACCEPT_FOR_FINANCIAL_OPENING")

        # Override trail endpoint
        trail_res = client.get("/audit/overrides/trail")
        self.assertEqual(trail_res.status_code, 200)
        self.assertIn("events", trail_res.json())


if __name__ == '__main__':
    unittest.main()


