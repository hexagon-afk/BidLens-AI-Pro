"""
Audit Router - Layer 2 (FastAPI Backend)
Triggers compliance audits, logs officer clause overrides with mandatory justification,
and generates downloadable Certified Black & White PDF Dossiers with Page 2 Override Logs.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from orchestrator.orchestrator import run_full_audit
from utils.pdf_generator import generate_certified_audit_pdf
import os
import datetime

router = APIRouter()

ROUTER_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ROUTER_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploaded_docs")
REPORTS_DIR = os.path.join(BACKEND_DIR, "generated_reports")
SAMPLE_DIRS = [
    os.path.join(PROJECT_ROOT, "data", "sample_bids"),
    os.path.join(BACKEND_DIR, "data", "sample_bids"),
    os.path.join(BACKEND_DIR, "..", "data", "sample_bids"),
]
SIG_FILE = os.path.join(UPLOAD_DIR, "officer_signature.png")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

AUDIT_CACHE: Dict[str, Any] = {}
AUDIT_OVERRIDES: Dict[str, Dict[str, Any]] = {}  # bid_id -> { clause_id -> { status, justification, original_status, clause_name, timestamp } }
ACTIVE_TENDER_CRITERIA: Dict[str, Any] = {}  # tender_id -> criteria


class RunAuditPayload(BaseModel):
    file_id: str
    tender_id: Optional[str] = "GEM/2026/B/892100"
    tender_requirements: Optional[Dict[str, Any]] = None


class ClauseOverridePayload(BaseModel):
    bid_id: str
    clause_id: str
    clause_name: str
    original_status: str
    new_status: str  # "PASS", "FAIL", "EXEMPT", "NEEDS_REVIEW", "NOT_APPLICABLE"
    justification: str
    officer_name: Optional[str] = "Procurement Officer"


@router.post("/run")
async def trigger_audit(payload: RunAuditPayload):
    """
    Triggers compliance audit on an uploaded document file_id or sample filename,
    strictly evaluated against the active tender requirements.
    """
    file_id = payload.file_id
    target_file = None

    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f == file_id or f.startswith(file_id) or file_id.lower() in f.lower():
                target_file = os.path.join(UPLOAD_DIR, f)
                break

    if not target_file:
        for sdir in SAMPLE_DIRS:
            if os.path.exists(sdir):
                for f in os.listdir(sdir):
                    if file_id.lower() in f.lower() or f.lower() == file_id.lower():
                        target_file = os.path.join(sdir, f)
                        break
            if target_file:
                break

    if not target_file or not os.path.exists(target_file):
        raise HTTPException(
            status_code=404,
            detail=f"Document '{file_id}' not found in uploaded_docs or sample_bids."
        )

    audit_id = file_id

    # Clean fresh run: reset previous test overrides for this file unless explicitly retained
    if audit_id in AUDIT_OVERRIDES and payload.tender_id != "KEEP_OVERRIDES":
        AUDIT_OVERRIDES.pop(audit_id, None)

    # Determine effective tender requirements
    tender_reqs = payload.tender_requirements
    if not tender_reqs and payload.tender_id and payload.tender_id in ACTIVE_TENDER_CRITERIA:
        tender_reqs = ACTIVE_TENDER_CRITERIA[payload.tender_id]

    audit_results = await run_full_audit(target_file, tender_requirements=tender_reqs)
    AUDIT_CACHE[audit_id] = audit_results

    clean_id = audit_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
    pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
    generate_certified_audit_pdf(
        audit_results,
        pdf_report_path,
        officer_overrides=AUDIT_OVERRIDES.get(audit_id, {})
    )

    return {
        "audit_id": audit_id,
        "status": "COMPLETED",
        "overall_status": audit_results.get("overall_status", "NEEDS_REVIEW"),
        "is_compliant": audit_results.get("is_compliant", False),
        "message": f"Audit completed with overall verdict: {audit_results.get('overall_status')}",
        "pdf_download_url": f"/audit/report/pdf/{audit_id}",
        "results": audit_results
    }


@router.post("/overrides/clear")
def clear_all_overrides():
    """
    Clears all recorded officer overrides across all vendor bids for a clean slate.
    """
    AUDIT_OVERRIDES.clear()
    return {"status": "SUCCESS", "message": "All test overrides have been completely cleared."}


@router.post("/overrides/reset/{bid_id}")
def reset_vendor_overrides(bid_id: str):
    """
    Clears overrides specifically for a single vendor bid.
    """
    if bid_id in AUDIT_OVERRIDES:
        AUDIT_OVERRIDES.pop(bid_id, None)
    return {"status": "SUCCESS", "bid_id": bid_id, "message": f"Overrides for {bid_id} cleared."}


@router.post("/clause-override")
def record_clause_override(payload: ClauseOverridePayload):
    """
    Records a supervisory officer clause verdict override with mandatory justification,
    and dynamically recalculates summary metrics, overall compliance status, and risk tier.
    """
    if not payload.justification or len(payload.justification.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="A mandatory written justification (minimum 5 characters) is required to override any automated verdict."
        )

    bid_id = payload.bid_id
    if bid_id not in AUDIT_OVERRIDES:
        AUDIT_OVERRIDES[bid_id] = {}

    timestamp_str = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")

    AUDIT_OVERRIDES[bid_id][payload.clause_id] = {
        "clause_id": payload.clause_id,
        "clause_name": payload.clause_name,
        "original_status": payload.original_status,
        "status": payload.new_status,
        "justification": payload.justification.strip(),
        "officer_name": payload.officer_name,
        "timestamp": timestamp_str
    }

    # Recalculate summary metrics if audit is cached
    if bid_id in AUDIT_CACHE:
        clauses = AUDIT_CACHE[bid_id].get("clause_level_decisions", [])
        for c in clauses:
            if c.get("clause_id") == payload.clause_id:
                c["status"] = payload.new_status
                c["officer_override_note"] = payload.justification.strip()

        pass_count = sum(1 for c in clauses if c.get("status") == "PASS")
        fail_count = sum(1 for c in clauses if c.get("status") == "FAIL")
        exempt_count = sum(1 for c in clauses if c.get("status") == "EXEMPT")
        needs_review_count = sum(1 for c in clauses if c.get("status") == "NEEDS_REVIEW")
        not_applicable_count = sum(1 for c in clauses if c.get("status") == "NOT_APPLICABLE")

        if fail_count > 0:
            overall_status = "NON_COMPLIANT"
        elif needs_review_count > 0:
            overall_status = "NEEDS_REVIEW"
        else:
            overall_status = "COMPLIANT"

        is_compliant = (overall_status == "COMPLIANT")
        AUDIT_CACHE[bid_id]["is_compliant"] = is_compliant
        AUDIT_CACHE[bid_id]["overall_status"] = overall_status

        if "compliance_summary" in AUDIT_CACHE[bid_id]:
            cs = AUDIT_CACHE[bid_id]["compliance_summary"]
            cs["passed"] = pass_count
            cs["failed"] = fail_count
            cs["exempt"] = exempt_count
            cs["needs_review"] = needs_review_count
            cs["not_applicable"] = not_applicable_count
            cs["overall_status"] = overall_status
            cs["risk_tier"] = "HIGH" if overall_status == "NON_COMPLIANT" else ("MEDIUM" if overall_status == "NEEDS_REVIEW" else "LOW")

        if "rejection_risk_analysis" in AUDIT_CACHE[bid_id]:
            AUDIT_CACHE[bid_id]["rejection_risk_analysis"]["rejection_likely"] = (overall_status == "NON_COMPLIANT")
            AUDIT_CACHE[bid_id]["rejection_risk_analysis"]["risk_tier"] = "HIGH" if overall_status == "NON_COMPLIANT" else ("MEDIUM" if overall_status == "NEEDS_REVIEW" else "LOW")

        clean_id = bid_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
        pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
        generate_certified_audit_pdf(
            AUDIT_CACHE[bid_id],
            pdf_report_path,
            officer_overrides=AUDIT_OVERRIDES.get(bid_id, {})
        )

    return {
        "status": "RECORDED",
        "bid_id": bid_id,
        "clause_id": payload.clause_id,
        "new_status": payload.new_status,
        "overall_status": AUDIT_CACHE.get(bid_id, {}).get("overall_status"),
        "is_compliant": AUDIT_CACHE.get(bid_id, {}).get("is_compliant"),
        "message": f"Verdict for '{payload.clause_name}' overridden to {payload.new_status}. Overall status recalculated to {AUDIT_CACHE.get(bid_id, {}).get('overall_status')}."
    }


@router.get("/status/{audit_id}")
def get_audit_status(audit_id: str):
    """Retrieve cached audit results for a specific audit_id."""
    if audit_id not in AUDIT_CACHE:
        raise HTTPException(status_code=404, detail=f"No audit results found for audit_id '{audit_id}'.")
    return {"audit_id": audit_id, "status": "COMPLETED", "results": AUDIT_CACHE[audit_id]}


@router.get("/report/pdf/{audit_id}")
def download_audit_pdf(
    audit_id: str,
    officer_name: Optional[str] = Query(None, description="Name of evaluating procurement officer"),
    officer_designation: Optional[str] = Query(None, description="Designation of evaluating procurement officer")
):
    """
    Download the Official Black & White PDF Audit Dossier with Page 2 Override Log.
    """
    clean_id = audit_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
    pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
    
    if audit_id in AUDIT_CACHE:
        generate_certified_audit_pdf(
            AUDIT_CACHE[audit_id],
            pdf_report_path,
            officer_name=officer_name,
            officer_designation=officer_designation,
            officer_overrides=AUDIT_OVERRIDES.get(audit_id, {})
        )
    elif not os.path.exists(pdf_report_path):
        raise HTTPException(status_code=404, detail=f"Audit report for audit_id '{audit_id}' not found. Please run the audit first.")

    vendor_name = AUDIT_CACHE.get(audit_id, {}).get("file_info", {}).get("vendor_name", "Vendor").replace(" ", "_")
    download_filename = f"Official_GeM_Audit_Report_{vendor_name}_{clean_id[:8]}.pdf"

    return FileResponse(
        path=pdf_report_path,
        media_type="application/pdf",
        filename=download_filename
    )
