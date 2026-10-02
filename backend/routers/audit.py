"""
Audit Router - Layer 2 (FastAPI Backend)
Triggers compliance audits, logs officer clause overrides with mandatory justification,
and generates downloadable Certified Black & White PDF Dossiers with Page 2 Override Logs.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal
from orchestrator.orchestrator import run_full_audit, compute_unified_audit_verdict
from evidence_risk.graph_engine import build_compliance_knowledge_graph
from utils.pdf_generator import generate_certified_audit_pdf
import os
import json
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
OVERRIDE_TRAIL_FILE = os.path.join(REPORTS_DIR, "audit_override_trail.jsonl")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

AUDIT_CACHE: Dict[str, Any] = {}
AUDIT_OVERRIDES: Dict[str, Dict[str, Any]] = {}  # bid_id -> { clause_id -> override_info }
AUDIT_OVERRIDE_EVENTS: List[Dict[str, Any]] = []  # in-memory cache
ACTIVE_TENDER_CRITERIA: Dict[str, Any] = {}  # tender_id -> criteria


def append_override_event_to_disk(event: dict):
    """Appends an immutable audit event to local append-only JSONL storage."""
    try:
        with open(OVERRIDE_TRAIL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        print(f"[AUDIT LOG WARNING] Failed to persist override event: {e}")

ValidOverrideStatus = Literal["PASS", "FAIL", "EXEMPT", "NEEDS_REVIEW", "NOT_APPLICABLE"]


class RunAuditPayload(BaseModel):
    file_id: str
    tender_id: Optional[str] = "GEM/2026/B/892100"
    tender_requirements: Optional[Dict[str, Any]] = None


class ClauseOverridePayload(BaseModel):
    bid_id: str
    clause_id: str
    clause_name: Optional[str] = ""
    original_status: Optional[str] = None
    new_status: ValidOverrideStatus
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
    audit_results["tender_requirements"] = tender_reqs
    audit_results["tender_id"] = payload.tender_id

    AUDIT_CACHE[audit_id] = audit_results
    if payload.tender_id:
        AUDIT_CACHE[f"{payload.tender_id}::{audit_id}"] = audit_results

    clean_id = audit_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
    pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
    generate_certified_audit_pdf(
        audit_results,
        pdf_report_path,
        officer_overrides=AUDIT_OVERRIDES.get(audit_id, {})
    )

    return {
        "audit_id": audit_id,
        "tender_id": payload.tender_id,
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
    AUDIT_OVERRIDE_EVENTS.clear()
    return {"status": "SUCCESS", "message": "All test overrides have been completely cleared."}


@router.post("/overrides/reset/{bid_id}")
def reset_vendor_overrides(bid_id: str):
    """
    Clears overrides specifically for a single vendor bid and restores original machine verdicts.
    """
    if bid_id in AUDIT_OVERRIDES:
        AUDIT_OVERRIDES.pop(bid_id, None)

    reset_event = {
        "event_id": f"RST-{int(datetime.datetime.now().timestamp() * 1000)}",
        "bid_id": bid_id,
        "action": "RESET",
        "message": f"All overrides for {bid_id} cleared; machine verdicts restored.",
        "timestamp": datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
    }
    AUDIT_OVERRIDE_EVENTS.append(reset_event)
    append_override_event_to_disk(reset_event)

    if bid_id in AUDIT_CACHE:
        cached = AUDIT_CACHE[bid_id]
        clauses = cached.get("clause_level_decisions", [])
        for c in clauses:
            if "machine_original_status" in c:
                c["status"] = c["machine_original_status"]
                c.pop("officer_override_note", None)
        for b in cached.get("branch_b_clause_results", []):
            if "machine_original_status" in b:
                b["status"] = b["machine_original_status"]
                b.pop("officer_override_note", None)

        extracted = cached.get("branch_a_extracted_data", {})
        contradictions = cached.get("contradictions_detected", [])
        tender_reqs = cached.get("tender_requirements")

        unified = compute_unified_audit_verdict(clauses, contradictions, extracted, tender_reqs)
        cached["overall_status"] = unified["overall_status"]
        cached["is_compliant"] = unified["is_compliant"]
        cached["compliance_summary"] = unified["compliance_summary"]
        cached["rejection_risk_analysis"] = unified["risk_and_value"]["rejection_risk"]
        cached["value_spotlight"] = unified["risk_and_value"]["value_spotlight"]
        cached["executive_summary"] = unified["risk_and_value"]["executive_summary"]
        cached["bid_repair_guidance"] = unified["risk_and_value"]["bid_repair"]
        cached["knowledge_graph"] = build_compliance_knowledge_graph(
            extracted, clauses, cached.get("branch_c_govt_verification", {})
        )

        if cached.get("tender_id"):
            AUDIT_CACHE[f"{cached['tender_id']}::{bid_id}"] = cached

        clean_id = bid_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
        pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
        generate_certified_audit_pdf(cached, pdf_report_path, officer_overrides={})

        return {
            "status": "SUCCESS",
            "bid_id": bid_id,
            "overall_status": unified["overall_status"],
            "is_compliant": unified["is_compliant"],
            "message": f"Overrides for {bid_id} cleared and original verdicts restored.",
            "results": cached,
            "audit_result": cached
        }

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
    if bid_id not in AUDIT_CACHE:
        raise HTTPException(
            status_code=404,
            detail=f"Audit record for '{bid_id}' not found. Please trigger audit first."
        )

    cached_audit = AUDIT_CACHE[bid_id]
    clauses = cached_audit.get("clause_level_decisions", [])
    target_clause = None
    for c in clauses:
        if c.get("clause_id") == payload.clause_id:
            target_clause = c
            break

    if not target_clause:
        raise HTTPException(
            status_code=404,
            detail=f"Clause '{payload.clause_id}' not found in audit decisions for '{bid_id}'."
        )

    # Preserve machine original status
    if "machine_original_status" not in target_clause:
        target_clause["machine_original_status"] = target_clause.get("status")

    original_status = target_clause["machine_original_status"]
    target_clause["status"] = payload.new_status
    target_clause["officer_override_note"] = payload.justification.strip()

    for b in cached_audit.get("branch_b_clause_results", []):
        if b.get("clause_id") == payload.clause_id:
            b["status"] = payload.new_status
            b["officer_override_note"] = payload.justification.strip()

    timestamp_str = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")

    if bid_id not in AUDIT_OVERRIDES:
        AUDIT_OVERRIDES[bid_id] = {}

    AUDIT_OVERRIDES[bid_id][payload.clause_id] = {
        "clause_id": payload.clause_id,
        "clause_name": target_clause.get("clause_name") or payload.clause_name,
        "original_status": original_status,
        "status": payload.new_status,
        "justification": payload.justification.strip(),
        "officer_name": payload.officer_name,
        "timestamp": timestamp_str
    }

    override_event = {
        "event_id": f"OVR-{int(datetime.datetime.now().timestamp() * 1000)}",
        "bid_id": bid_id,
        "clause_id": payload.clause_id,
        "original_status": original_status,
        "new_status": payload.new_status,
        "justification": payload.justification.strip(),
        "officer_name": payload.officer_name,
        "timestamp": timestamp_str
    }
    AUDIT_OVERRIDE_EVENTS.append(override_event)
    append_override_event_to_disk(override_event)

    # Recalculate summary metrics and dependent outputs
    extracted = cached_audit.get("branch_a_extracted_data", {})
    contradictions = cached_audit.get("contradictions_detected", [])
    tender_reqs = cached_audit.get("tender_requirements")

    unified = compute_unified_audit_verdict(clauses, contradictions, extracted, tender_reqs)
    cached_audit["overall_status"] = unified["overall_status"]
    cached_audit["is_compliant"] = unified["is_compliant"]
    cached_audit["compliance_summary"] = unified["compliance_summary"]
    cached_audit["rejection_risk_analysis"] = unified["risk_and_value"]["rejection_risk"]
    cached_audit["value_spotlight"] = unified["risk_and_value"]["value_spotlight"]
    cached_audit["executive_summary"] = unified["risk_and_value"]["executive_summary"]
    cached_audit["bid_repair_guidance"] = unified["risk_and_value"]["bid_repair"]
    cached_audit["knowledge_graph"] = build_compliance_knowledge_graph(
        extracted, clauses, cached_audit.get("branch_c_govt_verification", {})
    )

    if cached_audit.get("tender_id"):
        AUDIT_CACHE[f"{cached_audit['tender_id']}::{bid_id}"] = cached_audit

    clean_id = bid_id.replace('.pdf','').replace('.docx','').replace('.xlsx','')
    pdf_report_path = os.path.join(REPORTS_DIR, f"Audit_Report_{clean_id}.pdf")
    generate_certified_audit_pdf(
        cached_audit,
        pdf_report_path,
        officer_overrides=AUDIT_OVERRIDES.get(bid_id, {})
    )

    return {
        "status": "RECORDED",
        "bid_id": bid_id,
        "clause_id": payload.clause_id,
        "original_status": original_status,
        "new_status": payload.new_status,
        "overall_status": unified["overall_status"],
        "is_compliant": unified["is_compliant"],
        "message": f"Verdict for '{target_clause.get('clause_name')}' overridden to {payload.new_status}. Overall status recalculated to {unified['overall_status']}.",
        "results": cached_audit,
        "audit_result": cached_audit
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


@router.get("/overrides/trail")
def get_audit_override_trail():
    """
    Returns the durable, append-only supervisory audit override event trail from JSONL storage.
    """
    events = []
    if os.path.exists(OVERRIDE_TRAIL_FILE):
        try:
            with open(OVERRIDE_TRAIL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line.strip()))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read audit override trail: {e}")
    else:
        events = list(AUDIT_OVERRIDE_EVENTS)

    return {
        "status": "SUCCESS",
        "trail_file": "audit_override_trail.jsonl",
        "total_events": len(events),
        "events": events
    }


@router.post("/agent/review/{bid_id}")
async def run_agent_evidence_review(bid_id: str):
    """
    Executes autonomous agentic review with inspectable multi-step tool calls
    (inspect_document_evidence, evaluate_statutory_discrepancy, synthesize_officer_recommendation).
    """
    cached_audit = None
    if bid_id in AUDIT_CACHE:
        cached_audit = AUDIT_CACHE[bid_id]
    else:
        target_file = None
        for sdir in [UPLOAD_DIR] + SAMPLE_DIRS:
            if os.path.exists(sdir):
                for f in os.listdir(sdir):
                    if bid_id.lower() in f.lower() or f.lower() == bid_id.lower():
                        target_file = os.path.join(sdir, f)
                        break
            if target_file:
                break
        if not target_file or not os.path.exists(target_file):
            raise HTTPException(
                status_code=404,
                detail=f"Audit record or document file for '{bid_id}' not found."
            )
        cached_audit = await run_full_audit(target_file)
        AUDIT_CACHE[bid_id] = cached_audit

    extracted = cached_audit.get("branch_a_extracted_data", {})
    full_text = extracted.get("raw_text", "")
    clauses = cached_audit.get("clause_level_decisions", [])
    contradictions = cached_audit.get("contradictions_detected", [])
    tender_reqs = cached_audit.get("tender_requirements", {})

    from orchestrator.llm_agent import EvidenceReviewAgent
    agent = EvidenceReviewAgent()
    review_output = await agent.review_bid_submission(
        bid_id=bid_id,
        full_text=full_text,
        tender_requirements=tender_reqs,
        extracted_data=extracted,
        clause_results=clauses,
        contradictions=contradictions
    )

    return {
        "status": "SUCCESS",
        "bid_id": bid_id,
        "review": review_output
    }

