"""Regression cases for false certainty and officer decision persistence."""
import copy
from pathlib import Path
import pytest
import pymupdf
from fastapi.testclient import TestClient
from main import app
from routers import audit
from orchestrator.ai_processing import extract_document_data, extract_tender_rfp_data
from orchestrator.rule_engine import evaluate_compliance
from orchestrator.govt_verify import verify_government_credentials
from evidence_risk.contradiction import detect_cross_document_contradictions

REQUIREMENTS = {"min_turnover_cr": 1.5, "emd_required_inr": 100000, "min_local_content_pct": 50,
                "min_warranty_years": 3, "required_service_type": "Onsite"}


def extract_text(tmp_path, text):
    file = tmp_path / "bid.txt"
    file.write_text("Company submission for procurement officer document review.\n" + text, encoding="utf-8")
    return extract_document_data(str(file))


def clause(data, clause_id, requirements=None):
    return next(c for c in evaluate_compliance(data, requirements or REQUIREMENTS) if c["clause_id"] == clause_id)


@pytest.mark.parametrize("text,years,service,status", [
    ("Warranty: 3 years.", 3, None, "NEEDS_REVIEW"),
    ("Required warranty: 3 years onsite. Offered warranty: 1 year onsite.", 1, "Onsite", "FAIL"),
    ("Warranty required: 3 years onsite.", None, None, "NEEDS_REVIEW"),
    ("Offered warranty: 3 years onsite. Offered warranty: 1 year onsite.", None, None, "NEEDS_REVIEW"),
    ("Warranty: 3 years, no onsite service offered.", 3, None, "NEEDS_REVIEW"),
    ("Warranty: 60 months onsite.", 5, "Onsite", "PASS"),
    ("Warranty: 5 years carry-in.", 5, "Carry-in", "FAIL"),
])
def test_warranty_evidence_does_not_invent_a_commitment(tmp_path, text, years, service, status):
    data = extract_text(tmp_path, text)
    assert data["warranty_years"] == years
    assert data["offered_service_type"] == service
    assert clause(data, "SPEC-WARRANTY")["status"] == status


def test_unstated_tender_service_is_not_assumed_onsite(tmp_path):
    file = tmp_path / "tender.txt"
    file.write_text("Tender procurement requirements. Warranty required: 3 years.", encoding="utf-8")
    assert extract_tender_rfp_data(str(file))["required_service_type"] is None
    assert clause({"warranty_years": 5, "offered_service_type": "Onsite"}, "SPEC-WARRANTY", {"min_warranty_years": 3})["status"] == "NEEDS_REVIEW"


@pytest.mark.parametrize("amount", [100, 2026, 499])
def test_small_emd_is_a_known_shortfall_not_missing(tmp_path, amount):
    data = extract_text(tmp_path, f"EMD Bank Guarantee for INR {amount} submitted.")
    assert data["emd_amount_inr"] == amount
    assert clause(data, "GFR-170-EMD")["status"] == "FAIL"


def test_absent_emd_text_is_unresolved_but_explicit_missing_is_failure(tmp_path):
    data = extract_text(tmp_path, "Annual turnover is 3 Crore. Warranty: 3 years onsite.")
    assert data["emd_status"] == "UNRESOLVED"
    assert clause(data, "GFR-170-EMD")["status"] == "NEEDS_REVIEW"
    data = extract_text(tmp_path, "EMD Guarantee Status:\nMISSING / NOT SUBMITTED")
    assert clause(data, "GFR-170-EMD")["status"] == "FAIL"


def test_negative_msme_statement_does_not_create_false_exemption_claim(tmp_path):
    data = extract_text(tmp_path, "We are not an MSME. Annual turnover is 3 Crore.")
    findings = detect_cross_document_contradictions(data, {"pan_gstin_consistent": True}, REQUIREMENTS)
    assert not any(c["type"] == "UNVERIFIED_MSME_CLAIM" for c in findings)


def test_udyam_syntax_does_not_grant_exemptions_or_portal_verification():
    data = {"is_msme": True, "udyam": "UDYAM-MH-03-0098765", "turnover_cr": 0.5}
    assert clause(data, "GFR-160-MSME")["status"] == "NEEDS_REVIEW"
    assert clause(data, "GFR-170-EMD")["status"] == "NEEDS_REVIEW"
    result = verify_government_credentials(data)
    assert result["live_registries_verified"] == 0
    udyam = next(g for g in result["gateways"] if g["name"] == "Udyam MSME Portal")
    assert udyam["details"]["statutory_exemptions_eligible"] is None
    cppp = next(g for g in result["gateways"] if "CPPP" in g["name"])
    assert cppp["badge"] == "NEUTRAL"


def test_multiple_entity_pans_require_review_not_automatic_fraud_rejection():
    data = {"all_pans": ["ABCDE1234F", "XYZAB5678C"], "raw_text": "Bidder and OEM identifiers"}
    findings = detect_cross_document_contradictions(data, {"pan_gstin_consistent": True})
    assert findings[0]["severity"] == "HIGH"
    result = audit.compute_unified_audit_verdict([{"status": "PASS"}], findings, {})
    assert result["overall_status"] == "NEEDS_REVIEW"


def test_skipped_pdf_pages_cannot_produce_compliant_verdict(tmp_path, monkeypatch):
    import orchestrator.ai_processing as processing
    monkeypatch.setattr(processing, "get_ocr_engine", lambda: None)
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((50, 80), "Warranty: 3 years onsite. Annual turnover 3 Crore. EMD INR 100000 submitted.")
    pdf.new_page()
    file = tmp_path / "partly_unreadable.pdf"
    pdf.save(file)
    pdf.close()
    data = extract_document_data(str(file))
    assert data["extraction_complete"] is False
    assert all(c["status"] == "NEEDS_REVIEW" for c in evaluate_compliance(data, REQUIREMENTS))


@pytest.mark.parametrize("value", [-1, True, "not a number", float("inf")])
def test_invalid_thresholds_are_rejected(value):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        audit.RunAuditPayload(file_id="bid.pdf", tender_requirements={"min_turnover_cr": value})


def prepare_audit(client):
    bid_id = "Bid_MegaTech_BigBrand.pdf"
    response = client.post("/audit/run", json={"file_id": bid_id, "tender_id": "MANUAL-TEST", "tender_requirements": REQUIREMENTS})
    assert response.status_code == 200, response.text
    assert response.json()["results"]["overall_status"] == "COMPLIANT"
    return bid_id


def test_failed_override_write_leaves_all_results_unchanged(tmp_path, monkeypatch):
    client = TestClient(app)
    bid_id = prepare_audit(client)
    before = copy.deepcopy(audit.AUDIT_CACHE[bid_id])
    monkeypatch.setattr(audit, "OVERRIDE_TRAIL_FILE", str(tmp_path))
    result = client.post("/audit/clause-override", json={"bid_id": bid_id, "clause_id": "SPEC-WARRANTY", "new_status": "FAIL", "justification": "Officer found an unresolved warranty clause"})
    assert result.status_code == 503
    assert audit.AUDIT_CACHE[bid_id] == before
    assert bid_id not in audit.AUDIT_OVERRIDES
    assert audit.AUDIT_OVERRIDE_EVENTS == []


def test_override_reset_pdf_and_literal_justification(client=None):
    client = TestClient(app)
    bid_id = prepare_audit(client)
    note = "Verified A&B terms; offered duration < 3 years."
    result = client.post("/audit/clause-override", json={"bid_id": bid_id, "clause_id": "SPEC-WARRANTY", "new_status": "FAIL", "justification": note})
    assert result.status_code == 200
    data = result.json()["results"]
    assert data["compliance_summary"]["failed"] == 1
    assert data["overall_status"] == "NON_COMPLIANT"
    report = client.get(f"/audit/report/pdf/{bid_id}", params={"officer_name": "Officer A&B <Procurement>"})
    assert report.status_code == 200
    doc = pymupdf.open(stream=report.content, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    assert note in text
    assert "NON_COMPLIANT" in text
    assert "not a probability" in text
    assert audit.AUDIT_CACHE[bid_id]["file_info"]["source_sha256"] in text.replace("\n", "")
    doc.close()
    reset = client.post(f"/audit/overrides/reset/{bid_id}")
    assert reset.json()["results"]["overall_status"] == "COMPLIANT"
    assert reset.json()["results"]["compliance_summary"]["failed"] == 0
    trail = client.get("/audit/overrides/trail").json()["events"]
    assert len(trail) == 2
    assert trail[0]["new_status"] == "FAIL" and trail[1]["action"] == "RESET"


def test_parsed_tender_is_authoritative_and_fuzzy_file_ids_are_rejected():
    client = TestClient(app)
    response = client.get("/document/tender/sample")
    assert response.status_code == 200
    tender_id = response.json()["tender_data"]["tender_id"]
    result = client.post("/audit/run", json={"file_id": "Bid_MegaTech_BigBrand.pdf", "tender_id": tender_id})
    assert result.status_code == 200
    assert result.json()["results"]["requirement_source"] == "PARSED_TENDER"
    assert result.json()["results"]["tender_requirements"]["min_warranty_years"] == 3
    changed = {**audit.ACTIVE_TENDER_CRITERIA[tender_id], "min_warranty_years": 1}
    result = client.post("/audit/run", json={"file_id": "Bid_MegaTech_BigBrand.pdf", "tender_id": tender_id, "tender_requirements": changed})
    assert result.status_code == 409
    assert client.post("/audit/run", json={"file_id": "Bid_"}).status_code == 404


def test_missing_llm_key_cannot_return_simulated_success():
    client = TestClient(app)
    bid_id = prepare_audit(client)
    response = client.post(f"/audit/agent/review/{bid_id}")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_ocr_candidate_failure_is_review_until_source_confirmed():
    data = {"ocr_only": True, "gstin": "27AABCT3456L1Z1", "warranty_years": 1, "offered_service_type": "Carry-in"}
    results = evaluate_compliance(data, REQUIREMENTS)
    assert all(c["status"] == "NEEDS_REVIEW" for c in results)
    warranty = next(c for c in results if c["clause_id"] == "SPEC-WARRANTY")
    assert warranty["unverified_machine_status"] == "FAIL"


def test_failed_ocr_initialization_cannot_mark_a_scan_readable(monkeypatch):
    import orchestrator.ai_processing as processing
    monkeypatch.setattr(processing, "get_ocr_engine", lambda: None)
    sample = Path(__file__).resolve().parents[1] / "data" / "sample_bids" / "Scanned_Letter_ApexLabs.png"
    data = extract_document_data(str(sample))
    assert data["is_unreadable"] is True
    assert data["extraction_complete"] is False


@pytest.mark.parametrize("text", [
    "Vendor Legal Entity: Apex Labs Micro Devices LLP\nLocal Content: 68% Class-1 Local Supplier Declaration.",
    "--- Scanned Image (Scanned_Letter_ApexLabs.png) ---\nApex Labs Micro Devices LLP\nLocal Supplier\nAuthorized Signatory: Dr. Arvind Swamy (Director, Apex Labs)",
])
def test_entity_name_is_not_a_supplier_declaration_or_signatory(tmp_path, text):
    file = tmp_path / "name.txt"
    file.write_text(text, encoding="utf-8")
    assert extract_document_data(str(file))["vendor_name"] == "Apex Labs Micro Devices LLP"
