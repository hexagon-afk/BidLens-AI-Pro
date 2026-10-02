"""
Audit Orchestrator - Layer 3 & Layer 4 Integration
Coordinates:
  1. Branch A: Document & Entity Extraction (PDF, Word, Excel)
  2. Branch B: Compliance Rule Engine (GFR 2017 & MSME Rules)
  3. Branch C: Government Verification (GSTN, PAN, MCA)
  4. Layer 4: Clause-to-Evidence Knowledge Graph
  5. Layer 4: Cross-Document Contradiction Detector
  6. Layer 4: Explainable Rejection-Risk Scorer & Value-for-Money Spotlight
"""
import asyncio
import os
from orchestrator.ai_processing import extract_document_data
from orchestrator.rule_engine import evaluate_compliance
from orchestrator.govt_verify import verify_government_credentials
from evidence_risk.graph_engine import build_compliance_knowledge_graph
from evidence_risk.contradiction import detect_cross_document_contradictions, calculate_claim_integrity_score
from evidence_risk.risk_scorer import compute_risk_and_value_intelligence


async def run_full_audit(file_path: str, tender_requirements: dict = None) -> dict:
    """
    Executes the complete end-to-end intelligence audit pipeline.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if tender_requirements is None:
        tender_requirements = {}

    # ── 1. Branch A: Document Extraction ───────────────────────
    extracted = await asyncio.to_thread(extract_document_data, file_path)

    # ── 2. Branches B & C: Rule Engine & Govt Checks (Parallel)
    rule_task = asyncio.to_thread(evaluate_compliance, extracted, tender_requirements)
    govt_task = asyncio.to_thread(verify_government_credentials, extracted)

    clause_results, govt_verification = await asyncio.gather(rule_task, govt_task)

    # ── 3. Layer 4: Contradiction & Fraud Detection ───────────
    contradictions = detect_cross_document_contradictions(extracted, govt_verification, tender_requirements=tender_requirements)
    claim_integrity = calculate_claim_integrity_score(extracted, contradictions)

    # ── 4. Unified Decision Aggregation & Risk Scoring ────────
    unified = compute_unified_audit_verdict(clause_results, contradictions, extracted, tender_requirements)
    overall_status = unified["overall_status"]
    is_compliant = unified["is_compliant"]
    compliance_summary = unified["compliance_summary"]
    risk_and_value = unified["risk_and_value"]

    # ── 5. Layer 4: Clause-to-Evidence Knowledge Graph ────────
    knowledge_graph = build_compliance_knowledge_graph(extracted, clause_results, govt_verification)

    return {
        "file_info": {
            "filename": extracted["filename"],
            "file_type": extracted["file_type"],
            "vendor_name": extracted["vendor_name"],
            "page_count": extracted["page_count"],
        },
        "is_compliant": is_compliant,
        "overall_status": overall_status,
        "executive_summary": risk_and_value["executive_summary"],
        "compliance_summary": compliance_summary,
        "branch_a_extracted_data": extracted,
        "branch_b_clause_results": clause_results,
        "branch_c_govt_verification": govt_verification,
        "rejection_risk_analysis": risk_and_value["rejection_risk"],
        "value_spotlight": risk_and_value["value_spotlight"],
        "contradictions_detected": contradictions,
        "claim_integrity": claim_integrity,
        "bid_repair_guidance": risk_and_value["bid_repair"],
        "clause_level_decisions": clause_results,
        "government_verification": govt_verification,
        "knowledge_graph": knowledge_graph,
    }


def compute_unified_audit_verdict(
    clause_results: list,
    contradictions: list,
    extracted: dict,
    tender_requirements: dict = None
) -> dict:
    """
    Unified decision-aggregation function used by both initial audits and clause overrides.
    Synchronizes clause results, identity contradictions, summary counts, overall status,
    risk tiers, and executive summaries from a single source of truth.
    """
    pass_count = sum(1 for c in clause_results if c.get("status") == "PASS")
    fail_count = sum(1 for c in clause_results if c.get("status") == "FAIL")
    exempt_count = sum(1 for c in clause_results if c.get("status") == "EXEMPT")
    needs_review_count = sum(1 for c in clause_results if c.get("status") == "NEEDS_REVIEW")
    not_applicable_count = sum(1 for c in clause_results if c.get("status") == "NOT_APPLICABLE")

    has_critical_contra = any(c.get("severity") == "CRITICAL" for c in contradictions)
    has_high_contra = any(c.get("severity") == "HIGH" for c in contradictions)

    # Any statutory failure or critical identity fraud prevents compliance
    if fail_count > 0 or has_critical_contra:
        overall_status = "NON_COMPLIANT"
    elif needs_review_count > 0 or has_high_contra or len(clause_results) == 0:
        overall_status = "NEEDS_REVIEW"
    elif (pass_count + exempt_count + not_applicable_count) == 0:
        overall_status = "NEEDS_REVIEW"
    else:
        overall_status = "COMPLIANT"

    is_compliant = (overall_status == "COMPLIANT")

    risk_and_value = compute_risk_and_value_intelligence(
        extracted,
        clause_results,
        contradictions,
        overall_status=overall_status,
        tender_requirements=tender_requirements
    )

    return {
        "overall_status": overall_status,
        "is_compliant": is_compliant,
        "compliance_summary": {
            "total_clauses_checked": len(clause_results),
            "passed": pass_count,
            "failed": fail_count,
            "exempt": exempt_count,
            "needs_review": needs_review_count,
            "not_applicable": not_applicable_count,
            "overall_status": overall_status,
            "risk_tier": risk_and_value["rejection_risk"]["risk_tier"]
        },
        "risk_and_value": risk_and_value
    }
