"""
Cross-Document Contradiction & Fraud Detection Engine - Layer 4
Detects inconsistencies, fraudulent discrepancies, unverified statutory claims,
and mismatches across GSTIN certificates, PAN cards, OEM Manufacturer Authorization Forms (MAF),
financial statements, and cover letters.
"""


def detect_cross_document_contradictions(extracted_data: dict, govt_verification: dict, tender_requirements: dict = None) -> list:
    """
    Scans the extracted bid metadata, raw text, and government verification logs
    to identify internal discrepancies, fraudulent anomalies, and unsubstantiated claims.
    """
    contradictions = []
    all_pans = extracted_data.get("all_pans", [])
    declared_pan = extracted_data.get("pan")
    gstin = extracted_data.get("gstin")
    gstin_expired = extracted_data.get("gstin_expired", False)
    raw_text = extracted_data.get("raw_text", "").lower()
    is_msme = extracted_data.get("is_msme", False)
    udyam = extracted_data.get("udyam")
    turnover_cr = extracted_data.get("turnover_cr")
    local_content_pct = extracted_data.get("local_content_pct", 0)
    total_quote = extracted_data.get("total_quote_inr")

    # ── 1. Multiple Different PANs within same Bid Proposal ───
    unique_pans = list(set(p.upper().strip() for p in all_pans if p))
    if len(unique_pans) > 1:
        contradictions.append({
            "contradiction_id": "CONTRA-PAN-01",
            "type": "CROSS_ATTACHMENT_PAN_MISMATCH",
            "severity": "HIGH",
            "title": "Multiple PANs Require Entity Review",
            "description": f"Found multiple PANs ({', '.join(sorted(unique_pans))}). Bidder, OEM and other entity roles have not been resolved.",
            "impact": "Officer must check entity roles before determining whether a contradiction exists.",
            "remedy": "Provide legal affidavit explaining entity relationship and submit unified PAN card."
        })

    # ── 2. PAN inside GSTIN vs Declared PAN Discrepancy ───────
    if not govt_verification.get("pan_gstin_consistent", True):
        note = govt_verification.get("consistency_note") or "Discrepancy detected between GSTIN and declared PAN."
        contradictions.append({
            "contradiction_id": "CONTRA-GST-PAN-02",
            "type": "GSTIN_EMBEDDED_PAN_MISMATCH",
            "severity": "HIGH" if len(unique_pans) > 1 else "CRITICAL",
            "title": "GSTIN / PAN Correspondence Requires Review",
            "description": note,
            "impact": "Verify the PAN assigned to the bidder against the GSTIN; document entity roles may be unresolved.",
            "remedy": "Submit GSTIN registration certificate issued strictly in the name of the PAN holder."
        })

    # ── 3. Active Status Claim vs Expired / Cancelled GSTIN ────
    if gstin and gstin_expired:
        contradictions.append({
            "contradiction_id": "CONTRA-TAX-STATUS-03",
            "type": "TAX_STATUS_CONTRADICTION",
            "severity": "HIGH",
            "title": "GSTIN Status Inactive / Cancelled",
            "description": f"Bid claims active commercial operations, but GSTIN {gstin} is recorded as EXPIRED or CANCELLED in tax filings.",
            "impact": "Statutory non-compliance with GFR Rule 149 and GeM General Terms.",
            "remedy": "Obtain GSTIN reactivation order from GST portal."
        })

    # ── 4. Ineligible Turnover without MSME Exemption ─────────
    min_turnover = tender_requirements.get("min_turnover_cr") if tender_requirements else None
    if min_turnover is not None and not is_msme and turnover_cr is not None and turnover_cr < min_turnover:
        contradictions.append({
            "contradiction_id": "CONTRA-ELIGIBILITY-04",
            "type": "NON_MSME_BELOW_THRESHOLD",
            "severity": "HIGH",
            "title": "Ineligible Turnover without MSME Exemption",
            "description": f"Turnover of INR {turnover_cr:.2f} Cr is below the active tender threshold of INR {min_turnover:.2f} Cr, and no valid Udyam registration is provided to claim statutory exemption.",
            "impact": "Mandatory technical rejection under GFR Rule 173 financial criteria.",
            "remedy": "Register under MSME Udyam if eligible or submit audited balance sheets meeting minimum turnover."
        })

    # ── 5. Unsubstantiated Make in India Self-Declaration ─────
    mii_claimed = ("make in india" in raw_text or "class-1" in raw_text or "local supplier" in raw_text)
    if mii_claimed and (local_content_pct is None or local_content_pct == 0):
        contradictions.append({
            "contradiction_id": "CONTRA-FRAUD-MII-05",
            "type": "UNSUBSTANTIATED_MII_CLAIM",
            "severity": "HIGH",
            "title": "Unsubstantiated Make in India Self-Declaration",
            "description": "Proposal asserts Make in India Class-1 compliance in narrative text, but specifies 0% local content or omits OEM manufacturing value addition breakdown.",
            "impact": "Disqualification of domestic purchase preference under DPIIT Public Procurement Order 2017.",
            "remedy": "Submit CA-certified or OEM-verified domestic local value addition certificate with exact percentage."
        })

    # ── 6. MSME Claim without Verifiable Udyam Certificate ────
    msme_claimed_in_text = is_msme
    if msme_claimed_in_text and not udyam:
        contradictions.append({
            "contradiction_id": "CONTRA-FRAUD-UDYAM-06",
            "type": "UNVERIFIED_MSME_CLAIM",
            "severity": "HIGH",
            "title": "Unverified MSME Exemption Claim",
            "description": "Vendor claims statutory MSME status in proposal cover text but failed to provide an active 19-character UDYAM registration identifier.",
            "impact": "Turnover and EMD statutory waivers cannot be applied without valid Udyam certificate.",
            "remedy": "Provide official Udyam Registration Certificate downloaded from udyamregistration.gov.in."
        })

    if extracted_data.get("ocr_only"):
        for finding in contradictions:
            if finding.get("severity") == "CRITICAL":
                finding["severity"] = "HIGH"
                finding["impact"] = "OCR-derived discrepancy requires confirmation from the source image before deciding eligibility."
    return contradictions


def calculate_claim_integrity_score(extracted_data: dict, contradictions: list) -> dict:
    """
    Computes an overall Claim Integrity & Authenticity Index (0.0 to 1.0)
    evaluating evidence substantiation vs superficial claims.
    """
    base_score = 100

    for c in contradictions:
        if c.get("severity") == "CRITICAL":
            base_score -= 45
        elif c.get("severity") == "HIGH":
            base_score -= 25
        elif c.get("severity") == "MEDIUM":
            base_score -= 15

    score = max(0, min(100, base_score))
    
    if score >= 85:
        tier = "HIGH INTEGRITY"
        desc = "High evidentiary substantiation. No configured contradiction checks triggered. Identity checks are offline and do not verify public database records."
    elif score >= 60:
        tier = "MODERATE INTEGRITY"
        desc = "Minor discrepancies or missing statutory annexures detected. Supervisory review recommended before tender award."
    else:
        tier = "CRITICAL RISK / FRAUD ANOMALY"
        desc = "Severe statutory contradictions, unverified exemptions, or conflicting legal entity credentials detected."

    return {
        "integrity_score": score,
        "integrity_tier": tier,
        "description": desc,
        "unsubstantiated_claims_count": len([c for c in contradictions if "UNSUBSTANTIATED" in c.get("type", "") or "UNVERIFIED" in c.get("type", "")])
    }



