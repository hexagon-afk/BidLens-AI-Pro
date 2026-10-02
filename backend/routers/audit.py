"""
Audit Router - Layer 2 (FastAPI Backend)
Triggers compliance audits, logs officer clause overrides with mandatory justification,
and generates downloadable Certified Black & White PDF Dossiers.
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
SAMPLE_BIDS_DIR = os.path.join(PROJECT_ROOT, "data", "sample_bids")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

AUDIT_CACHE: Dict[str, Any] = {}
AUDIT_OVERRIDES: Dict[str, Dict[str, Any]] = {}


class RunAuditPayload(BaseModel):
    file_id: str
    tender_id: Optional[str] = "GEM/2026/B/892100"


class ClauseOverridePayload(BaseModel):
    bid_id: str
    clause_id: str
    clause_name: str
    original_status: str
    new_status: str
    justification: str
    officer_name: Optional[str] = "Procurement Officer"


@router.post("/run")
async def trigger_audit(payload: RunAuditPayload):
    """
    Triggers full compliance audit on an uploaded document file_id.
    """
    file_id = payload.file_id
    target_file = None

    # Draft lookup: only checking UPLOAD_DIR
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f.startswith(file_id) or f == file_id:
                target_file = os.path.join(UPLOAD_DIR, f)
                break

    if not target_file or not os.path.exists(target_file):
        raise HTTPException(
            status_code=404,
            detail=f"Document '{file_id}' not found in uploaded_docs."
        )

    audit_results = await run_full_audit(target_file)
    AUDIT_CACHE[file_id] = audit_results

    clean_id = file_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
    pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
    generate_certified_audit_pdf(audit_results, pdf_report_path, officer_overrides=AUDIT_OVERRIDES.get(file_id, {}))

    return {
        "audit_id": file_id,
        "status": "COMPLETED",
        "message": "Audit completed across all verification branches.",
        "pdf_download_url": f"/audit/report/pdf/{file_id}",
        "results": audit_results
    }


@router.post("/clause-override")
def override_clause(payload: ClauseOverridePayload):
    """
    Logs an officer supervisory override with mandatory justification.
    """
    bid_id = payload.bid_id
    clause_id = payload.clause_id

    if bid_id not in AUDIT_OVERRIDES:
        AUDIT_OVERRIDES[bid_id] = {}

    AUDIT_OVERRIDES[bid_id][clause_id] = {
        "clause_name": payload.clause_name,
        "original_status": payload.original_status,
        "new_status": payload.new_status,
        "justification": payload.justification,
        "officer_name": payload.officer_name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return {
        "status": "OVERRIDE_RECORDED",
        "message": f"Clause '{payload.clause_name}' status overridden from {payload.original_status} to {payload.new_status}.",
        "audit_overrides": AUDIT_OVERRIDES[bid_id]
    }
