"""
Audit Router - Layer 2 (FastAPI Backend)
Triggers compliance audits, logs officer clause overrides with mandatory justification,
and generates downloadable Certified Black & White PDF Dossiers with Page 2 Override Logs.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List, Literal
from orchestrator.orchestrator import run_full_audit, compute_unified_audit_verdict
from evidence_risk.graph_engine import build_compliance_knowledge_graph
from utils.pdf_generator import generate_certified_audit_pdf
import os
import json
import datetime
import copy
import uuid
from orchestrator.llm_agent import EvidenceReviewAgent, ReviewError, get_gemini_config, audit_fingerprint

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
ACTIVE_TENDER_EVIDENCE: Dict[str, Any] = {}
AI_REVIEWS_IN_FLIGHT = set()


def append_override_event_to_disk(event: dict):
    """Persist before publishing a supervisory decision; fail explicitly on disk errors."""
    try:
        with open(OVERRIDE_TRAIL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
            f.flush()
            os.fsync(f.fileno())
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Override trail could not be saved. Decision was not applied.") from exc


def refresh_audit_outputs(cached: dict):
    clauses = cached.get("clause_level_decisions", [])
    extracted = cached.get("branch_a_extracted_data", {})
    unified = compute_unified_audit_verdict(clauses, cached.get("contradictions_detected", []), extracted, cached.get("tender_requirements"))
    cached.update({
        "overall_status": unified["overall_status"], "is_compliant": unified["is_compliant"],
        "compliance_summary": unified["compliance_summary"],
        "rejection_risk_analysis": unified["risk_and_value"]["rejection_risk"],
        "value_spotlight": unified["risk_and_value"]["value_spotlight"],
        "executive_summary": unified["risk_and_value"]["executive_summary"],
        "bid_repair_guidance": unified["risk_and_value"]["bid_repair"],
        "knowledge_graph": build_compliance_knowledge_graph(extracted, clauses, cached.get("branch_c_govt_verification", {}))
    })
    return cached


def publish_audit(bid_id: str, cached: dict):
    AUDIT_CACHE[bid_id] = cached
    if cached.get("tender_id"):
        AUDIT_CACHE[f"{cached['tender_id']}::{bid_id}"] = cached


ValidOverrideStatus = Literal["PASS", "FAIL", "EXEMPT", "NEEDS_REVIEW", "NOT_APPLICABLE"]


class TenderRequirements(BaseModel):
    budget_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    min_turnover_cr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    emd_required_inr: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    min_local_content_pct: Optional[float] = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    min_warranty_years: Optional[float] = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    required_service_type: Optional[Literal["Onsite", "Carry-in"]] = None

    @field_validator("budget_inr", "min_turnover_cr", "emd_required_inr", "min_local_content_pct", "min_warranty_years", mode="before")
    @classmethod
    def reject_boolean_thresholds(cls, value):
        if isinstance(value, bool):
            raise ValueError("A numeric threshold cannot be a boolean")
        return value


class RunAuditPayload(BaseModel):
    file_id: str
    tender_id: Optional[str] = "GEM/2026/B/892100"
    tender_requirements: Optional[TenderRequirements] = None


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
    if not file_id or any(c in file_id for c in ("/", "\\", ":")) or file_id in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid document ID.")
    target_file = None

    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            if f == file_id or f.startswith(file_id + "_"):
                target_file = os.path.join(UPLOAD_DIR, f)
                break

    if not target_file:
        for sdir in SAMPLE_DIRS:
            if os.path.exists(sdir):
                for f in os.listdir(sdir):
                    if f.lower() == file_id.lower():
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

    # Uploaded/sample tender parsing is authoritative when a tender is registered.
    supplied = payload.tender_requirements.model_dump() if payload.tender_requirements is not None else None
    registered = ACTIVE_TENDER_CRITERIA.get(payload.tender_id)
    if registered is not None:
        if supplied is not None and any(supplied.get(k) != v for k, v in registered.items()):
            raise HTTPException(status_code=409, detail="Submitted thresholds differ from the parsed tender. Reload the active tender before auditing.")
        tender_reqs = copy.deepcopy(registered)
        requirement_source = "PARSED_TENDER"
    else:
        tender_reqs = supplied or {}
        requirement_source = "OFFICER_SUPPLIED" if supplied is not None else "UNSPECIFIED"

    audit_results = await run_full_audit(target_file, tender_requirements=tender_reqs)
    audit_results["tender_requirements"] = tender_reqs
    audit_results["tender_id"] = payload.tender_id
    audit_results["requirement_source"] = requirement_source
    audit_results["tender_evidence"] = copy.deepcopy(ACTIVE_TENDER_EVIDENCE.get(payload.tender_id, {})) if registered is not None else {}

    AUDIT_OVERRIDES.pop(audit_id, None)
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
    for bid_id in list(AUDIT_OVERRIDES):
        reset_vendor_overrides(bid_id)
    return {"status": "SUCCESS", "message": "Original machine verdicts restored; event history retained."}


@router.post("/overrides/reset/{bid_id}")
def reset_vendor_overrides(bid_id: str):
    if bid_id not in AUDIT_CACHE:
        raise HTTPException(status_code=404, detail="Audit record not found. Run an audit first.")
    cached = copy.deepcopy(AUDIT_CACHE[bid_id])
    for key in ("clause_level_decisions", "branch_b_clause_results"):
        for clause in cached.get(key, []):
            if "machine_original_status" in clause:
                clause["status"] = clause["machine_original_status"]
                clause.pop("officer_override_note", None)
    refresh_audit_outputs(cached)
    event = {"event_id": str(uuid.uuid4()), "bid_id": bid_id, "action": "RESET",
             "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    append_override_event_to_disk(event)
    AUDIT_OVERRIDE_EVENTS.append(event)
    AUDIT_OVERRIDES.pop(bid_id, None)
    publish_audit(bid_id, cached)
    return {"status": "SUCCESS", "bid_id": bid_id, "overall_status": cached["overall_status"],
            "is_compliant": cached["is_compliant"], "results": cached, "audit_result": cached,
            "message": "Original machine verdicts restored. PDF export reflects this result."}


@router.post("/clause-override")
def record_clause_override(payload: ClauseOverridePayload):
    if len(payload.justification.strip()) < 5:
        raise HTTPException(status_code=400, detail="A written justification of at least 5 characters is required.")
    bid_id = payload.bid_id
    if bid_id not in AUDIT_CACHE:
        raise HTTPException(status_code=404, detail="Audit record not found. Run an audit first.")
    cached = copy.deepcopy(AUDIT_CACHE[bid_id])
    target = next((c for c in cached.get("clause_level_decisions", []) if c.get("clause_id") == payload.clause_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Clause not found in this audit.")
    previous_status = target.get("status")
    for key in ("clause_level_decisions", "branch_b_clause_results"):
        for clause in cached.get(key, []):
            if clause.get("clause_id") == payload.clause_id:
                clause.setdefault("machine_original_status", clause.get("status"))
                clause["status"] = payload.new_status
                clause["officer_override_note"] = payload.justification.strip()
    refresh_audit_outputs(cached)
    event = {"event_id": str(uuid.uuid4()), "bid_id": bid_id, "clause_id": payload.clause_id,
             "original_status": target["machine_original_status"], "previous_status": previous_status,
             "new_status": payload.new_status, "justification": payload.justification.strip(),
             "officer_name": payload.officer_name, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    append_override_event_to_disk(event)
    AUDIT_OVERRIDE_EVENTS.append(event)
    AUDIT_OVERRIDES.setdefault(bid_id, {})[payload.clause_id] = {
        **event, "clause_name": target.get("clause_name"), "status": payload.new_status
    }
    publish_audit(bid_id, cached)
    return {"status": "RECORDED", "bid_id": bid_id, "clause_id": payload.clause_id,
            "new_status": payload.new_status, "overall_status": cached["overall_status"],
            "is_compliant": cached["is_compliant"], "results": cached, "audit_result": cached,
            "message": "Override saved and all dependent results recalculated. PDF export reflects this result."}


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
    Download the prototype procurement review report with recorded officer decisions.
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
    download_filename = f"BidLens_Procurement_Review_{vendor_name}_{clean_id[:8]}.pdf"

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


class AgentReviewPayload(BaseModel):
    model_config = {"extra": "forbid"}
    clause_id: str = Field(min_length=1, max_length=80)
    cloud_consent: bool = False
    expected_status: str = Field(min_length=1, max_length=30)
    source_sha256: str = Field(min_length=64, max_length=64)


@router.get("/agent/config")
def agent_configuration():
    config = get_gemini_config()
    return {"provider": "Google Gemini", "model": config["model"], "configured": bool(config["api_key"]),
            "advisory_only": True, "cloud_processing": True, "max_tool_calls": 6,
            "notice": "Optional cloud review sends selected audit context and retrieved document excerpts to Google. Use synthetic demo documents; free-tier data may be used for product improvement."}


@router.post("/agent/review/{bid_id}")
async def run_agent_evidence_review(bid_id: str, payload: Optional[AgentReviewPayload] = None):
    if bid_id not in AUDIT_CACHE:
        raise HTTPException(status_code=404, detail="Run a tender-bound audit before requesting AI review.")
    if not get_gemini_config()["api_key"]:
        raise HTTPException(status_code=503, detail="Gemini API key is not configured. Add GEMINI_API_KEY to backend/.env; the deterministic audit remains available.")
    if payload is None or not payload.cloud_consent:
        raise HTTPException(status_code=400, detail="Explicit cloud-processing consent and a selected requirement check are required.")
    snapshot = copy.deepcopy(AUDIT_CACHE[bid_id])
    clause = next((c for c in snapshot.get("clause_level_decisions", []) if c.get("clause_id") == payload.clause_id), None)
    if clause is None:
        raise HTTPException(status_code=404, detail="Requirement check not found in this audit.")
    if clause.get("status") != payload.expected_status or snapshot.get("file_info", {}).get("source_sha256") != payload.source_sha256:
        raise HTTPException(status_code=409, detail="This audit changed. Reload the vendor result before requesting AI review.")
    if AI_REVIEWS_IN_FLIGHT:
        raise HTTPException(status_code=429, detail="Another AI review is running. Please wait before trying again.")
    AI_REVIEWS_IN_FLIGHT.add(bid_id)
    version = audit_fingerprint(snapshot)
    try:
        result = await EvidenceReviewAgent().review_bid_submission(snapshot, payload.clause_id)
        current = AUDIT_CACHE.get(bid_id)
        if current is None or audit_fingerprint(current) != version:
            raise HTTPException(status_code=409, detail="The audit changed during AI review. Discarded the stale advice; request a fresh review.")
        return {**result, "bid_id": bid_id}
    except ReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    finally:
        AI_REVIEWS_IN_FLIGHT.discard(bid_id)
