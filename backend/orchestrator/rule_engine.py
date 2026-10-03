"""
Compliance Rule Engine - Layer 3, Branch B
DETERMINISTIC Python rules. No LLM involved.
Evaluates GFR 2017 statutory procurement rules, MSME 2012 Exemption Orders,
and Public Procurement (Make in India) Orders against tender requirements.
Supports 5 evaluation statuses: PASS, FAIL, EXEMPT, NOT_APPLICABLE, NEEDS_REVIEW.
"""
from orchestrator.govt_verify import verify_gstin_checksum


def evaluate_compliance(extracted_data: dict, tender_requirements: dict = None) -> list:
    """
    Evaluates extracted bid data against tender requirements and statutory procurement rules.
    Returns structured list of clause-level decisions (PASS, FAIL, EXEMPT, NOT_APPLICABLE, NEEDS_REVIEW).
    """
    if tender_requirements is None:
        tender_requirements = {}

    results = []
    is_unreadable = extracted_data.get("is_unreadable", False) or extracted_data.get("extraction_complete") is False
    if not is_unreadable and "raw_text_length" in extracted_data:
        if extracted_data.get("raw_text_length", 0) < 50 and not any([
            extracted_data.get("gstin"),
            extracted_data.get("pan"),
            extracted_data.get("turnover_cr"),
            extracted_data.get("warranty_years")
        ]):
            is_unreadable = True

    # ── 1. Statutory Tax & GSTIN Registration ─────────────────
    gstin = extracted_data.get("gstin")
    gstin_expired = extracted_data.get("gstin_expired", False)
    if is_unreadable:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Tax Compliance",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Statutory Tax Compliance / GeM Registration Norms",
            "evidence": "Document is unreadable or extraction is incomplete; GSTIN unverified.",
            "remedy": "Upload clear digital PDF or legible scanned document."
        })
    elif not gstin:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Tax Compliance",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Statutory Tax Compliance / GeM Registration Norms",
            "evidence": "No GSTIN certificate or registration found in submission.",
            "remedy": "Submit active GSTIN certificate with current filing proof."
        })
    elif gstin_expired:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Tax Compliance",
            "status": "FAIL",
            "regulation_ref": "Statutory Tax Compliance / GeM Registration Norms",
            "evidence": f"GSTIN {gstin} is flagged as EXPIRED or CANCELLED in document records.",
            "remedy": "Provide active GSTIN reactivation certificate from GST portal."
        })
    else:
        checksum_valid = verify_gstin_checksum(gstin)
        if checksum_valid:
            results.append({
                "clause_id": "GFR-149-GST",
                "clause_name": "GSTIN Registration & Tax Compliance",
                "status": "PASS",
                "regulation_ref": "Statutory Tax Compliance / GeM Registration Norms",
                "evidence": f"GSTIN {gstin} format & Modulus-36 checksum validated offline.",
                "remedy": None
            })
        else:
            results.append({
                "clause_id": "GFR-149-GST",
                "clause_name": "GSTIN Registration & Tax Compliance",
                "status": "FAIL",
                "regulation_ref": "Statutory Tax Compliance / GeM Registration Norms",
                "evidence": f"GSTIN {gstin} failed Modulus-36 checksum verification.",
                "remedy": "Provide correct, valid 15-character GSTIN certificate."
            })

    # ── 2. Turnover Criteria & MSME Relaxations ───────────────
    is_msme = extracted_data.get("is_msme", False)
    turnover_cr = extracted_data.get("turnover_cr")
    min_turnover = tender_requirements.get("min_turnover_cr")
    udyam = extracted_data.get("udyam")

    if is_unreadable:
        results.append({
            "clause_id": "GFR-160-TO",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Financial Criteria / GFR 2017 Rule 173",
            "evidence": "Document is unreadable or extraction is incomplete; turnover unresolved.",
            "remedy": "Upload clear digital PDF or audited balance sheets."
        })
    elif min_turnover is None:
        results.append({
            "clause_id": "GFR-160-TO",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Financial Criteria / GFR 2017 Rule 173",
            "evidence": "Tender turnover threshold not established from RFP; officer confirmation required.",
            "remedy": "Verify applicable financial turnover threshold in Tender RFP."
        })
    elif is_msme and udyam:
        results.append({
            "clause_id": "GFR-160-MSME",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement Policy for MSEs Order 2012 / DoE OM F.20/2/2014-PPD",
            "evidence": f"Udyam identifier {udyam} is declared. Enterprise category, certificate authenticity and tender-specific turnover relaxation require officer verification.",
            "remedy": "Verify exemption eligibility and tender applicability; record an officer decision with supporting justification."
        })
    elif is_msme and not udyam:
        # Vendor claims MSME but no valid Udyam identifier provided
        results.append({
            "clause_id": "GFR-160-MSME",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement Policy for MSEs Order 2012",
            "evidence": "Vendor self-declares as MSME but valid Udyam certificate registration number was not found.",
            "remedy": "Upload official Udyam Registration Certificate with verification QR code."
        })
    elif turnover_cr is not None:
        if turnover_cr >= min_turnover:
            results.append({
                "clause_id": "GFR-160-TO",
                "clause_name": "Annual Financial Turnover Requirement",
                "status": "PASS",
                "regulation_ref": "Tender Financial Criteria / GFR 2017 Rule 173",
                "evidence": f"Declared turnover of INR {turnover_cr:.2f} Cr meets minimum requirement of INR {min_turnover:.2f} Cr.",
                "remedy": None
            })
        else:
            results.append({
                "clause_id": "GFR-160-TO",
                "clause_name": "Annual Financial Turnover Requirement",
                "status": "FAIL",
                "regulation_ref": "Tender Financial Criteria / GFR 2017 Rule 173",
                "evidence": f"Turnover of INR {turnover_cr:.2f} Cr is below mandatory requirement of INR {min_turnover:.2f} Cr (Non-MSME).",
                "remedy": "Provide audited financial statements meeting minimum turnover or valid Udyam registration."
            })
    else:
        results.append({
            "clause_id": "GFR-160-TO",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Financial Criteria / GFR 2017 Rule 173",
            "evidence": "Turnover documentation or audited balance sheet unresolved in submission.",
            "remedy": "Upload last 3 years CA-audited balance sheets with UDIN or verify physical annexures."
        })

    # ── 3. EMD (Earnest Money Deposit) ────────────────────────
    emd_status = extracted_data.get("emd_status")
    emd_amount_inr = extracted_data.get("emd_amount_inr")
    emd_required = tender_requirements.get("emd_required_inr")

    if is_unreadable:
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
            "evidence": "Document is unreadable or extraction is incomplete; EMD submission unresolved.",
            "remedy": "Upload clear digital PDF or legible EMD Bank Guarantee copy."
        })
    elif emd_required is None:
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
            "evidence": "Tender EMD threshold not established from RFP; officer confirmation required.",
            "remedy": "Verify applicable EMD amount in Tender RFP."
        })
    elif emd_required == 0.0:
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "NOT_APPLICABLE",
            "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
            "evidence": "Tender specifies nil / zero EMD requirement.",
            "remedy": None
        })
    elif is_msme and udyam:
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement Policy for MSEs Order 2012, Para 10 / GFR 2017 Rule 170(i)",
            "evidence": f"EMD exemption claimed using {udyam}; certificate authenticity, eligible enterprise category and tender applicability remain unverified.",
            "remedy": "Verify exemption eligibility and tender applicability; record an officer decision with supporting justification."
        })
    elif is_msme and not udyam:
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement Policy for MSEs Order 2012, Para 10 / GFR 2017 Rule 170(i)",
            "evidence": "Vendor self-declares as MSME requesting EMD waiver, but valid Udyam certificate registration number was not found.",
            "remedy": "Upload official Udyam Registration Certificate with verification QR code."
        })
    elif emd_status == "SUBMITTED":
        if emd_amount_inr is not None and emd_required is not None:
            if emd_amount_inr < emd_required:
                shortfall = emd_required - emd_amount_inr
                results.append({
                    "clause_id": "GFR-170-EMD",
                    "clause_name": "Earnest Money Deposit (EMD)",
                    "status": "FAIL",
                    "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
                    "evidence": f"EMD instrument submitted for INR {emd_amount_inr:,.0f} falls short of required INR {emd_required:,.0f} (Shortfall: INR {shortfall:,.0f}).",
                    "remedy": f"Submit supplementary Bank Guarantee for remaining INR {shortfall:,.0f}."
                })
            else:
                inst_txt = f" (Instrument ID: {extracted_data.get('emd_instrument_id')})" if extracted_data.get("emd_instrument_id") else ""
                results.append({
                    "clause_id": "GFR-170-EMD",
                    "clause_name": "Earnest Money Deposit (EMD)",
                    "status": "PASS",
                    "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
                    "evidence": f"Declared EMD amount INR {emd_amount_inr:,.0f}{inst_txt} meets tender amount; instrument authenticity and validity are not verified offline.",
                    "remedy": None
                })
        else:
            # Bank Guarantee / EMD instrument submitted, but monetary face value is unverified
            inst_desc = f"Instrument ID: {extracted_data.get('emd_instrument_id')}" if extracted_data.get("emd_instrument_id") else "Bank Guarantee reference declared"
            req_str = f"INR {emd_required:,.0f}" if emd_required else "tender requirement"
            results.append({
                "clause_id": "GFR-170-EMD",
                "clause_name": "Earnest Money Deposit (EMD)",
                "status": "NEEDS_REVIEW",
                "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
                "evidence": f"EMD instrument submitted ({inst_desc}), but monetary face value could not be reliably verified against required {req_str}.",
                "remedy": "Officer verification required: inspect physical Bank Guarantee / FDR copy to confirm face value."
            })
    elif emd_status == "MISSING":
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "FAIL",
            "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
            "evidence": f"EMD Bank Guarantee missing and vendor is not an exempt MSE (Required: INR {emd_required:,.0f}).",
            "remedy": f"Submit EMD Bank Guarantee for INR {emd_required:,.0f} or valid Udyam registration."
        })
    else:
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
            "evidence": "EMD submission status unresolved in proposal documents.",
            "remedy": "Confirm EMD instrument in physical submission or tender portal."
        })

    # ── 4. Public Procurement (Make in India) Local Content ───
    local_pct = extracted_data.get("local_content_pct")
    min_local = tender_requirements.get("min_local_content_pct")
    if is_unreadable:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": "Document is unreadable or extraction is incomplete; local content unresolved.",
            "remedy": "Upload clear digital PDF or legible local content self-declaration."
        })
    elif min_local is None:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": "Tender local content threshold not established from RFP; officer confirmation required.",
            "remedy": "Verify minimum Class-1 / Class-2 local content threshold in Tender RFP."
        })
    elif local_pct is None:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": "Local content percentage not declared in proposal; officer review required.",
            "remedy": f"Upload Class-1 Local Supplier self-declaration certifying >= {min_local}% local content."
        })
    elif local_pct >= min_local:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "PASS",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": f"Declared local content of {local_pct}% meets tender threshold >= {min_local}%; certificate authenticity requires officer verification.",
            "remedy": None
        })
    else:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "FAIL",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": f"Declared local content of {local_pct}% falls below tender minimum {min_local}%.",
            "remedy": f"Provide OEM certificate verifying >= {min_local}% domestic value addition."
        })

    # ── 5. Warranty & Service Level Compliance ────────────────
    warranty = extracted_data.get("warranty", "")
    offered_years = extracted_data.get("warranty_years")
    offered_service_type = extracted_data.get("offered_service_type", "Standard")
    if not offered_service_type or offered_service_type == "Standard":
        if "carry-in" in warranty.lower() or "carry in" in warranty.lower() or "offsite" in warranty.lower():
            offered_service_type = "Carry-in"
        elif "onsite" in warranty.lower() or "on-site" in warranty.lower():
            offered_service_type = "Onsite"

    required_service_type = tender_requirements.get("required_service_type")
    min_warranty_years = tender_requirements.get("min_warranty_years")

    if offered_years is None and warranty:
        if "5-year" in warranty.lower() or "5 year" in warranty.lower():
            offered_years = 5.0
        elif "3-year" in warranty.lower() or "3 year" in warranty.lower():
            offered_years = 3.0
        elif "2-year" in warranty.lower() or "2 year" in warranty.lower():
            offered_years = 2.0
        elif "1-year" in warranty.lower() or "1 year" in warranty.lower():
            offered_years = 1.0
        elif "6-month" in warranty.lower():
            offered_years = 0.5

    if is_unreadable:
        results.append({
            "clause_id": "SPEC-WARRANTY",
            "clause_name": "Comprehensive Onsite Warranty",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": "Document is unreadable or extraction is incomplete; warranty terms unresolved.",
            "remedy": "Upload clear digital PDF or legible warranty certificate."
        })
    elif min_warranty_years is None:
        results.append({
            "clause_id": "SPEC-WARRANTY",
            "clause_name": "Comprehensive Onsite Warranty",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": "Tender mandatory warranty duration not established from RFP; officer review required.",
            "remedy": "Confirm warranty requirement in Tender Technical Specifications."
        })
    elif offered_years is None:
        results.append({
            "clause_id": "SPEC-WARRANTY",
            "clause_name": "Comprehensive Onsite Warranty",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": f"Warranty terms unspecified or unreadable ({warranty}). Required: {min_warranty_years:.0f}-Year {required_service_type}.",
            "remedy": f"Provide OEM commitment letter for {min_warranty_years:.0f}-Year {required_service_type} warranty coverage."
        })
    elif offered_years < min_warranty_years:
        results.append({
            "clause_id": "SPEC-WARRANTY", "clause_name": "Warranty Duration & Service",
            "status": "FAIL", "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": f"Offers {offered_years:g} years; fails mandatory {min_warranty_years:g}-Year requirement.",
            "remedy": "Provide evidence meeting the applicable warranty duration."
        })
    elif not required_service_type or offered_service_type in (None, "Standard", ""):
        results.append({
            "clause_id": "SPEC-WARRANTY", "clause_name": "Warranty Duration & Service",
            "status": "NEEDS_REVIEW", "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": "Duration is sufficient, but required or offered service location is unresolved.",
            "remedy": "Confirm the tender service location and vendor commitment from source evidence."
        })
    elif required_service_type.lower() != offered_service_type.lower():
        results.append({
            "clause_id": "SPEC-WARRANTY", "clause_name": "Warranty Duration & Service",
            "status": "FAIL" if required_service_type == "Onsite" and offered_service_type == "Carry-in" else "NEEDS_REVIEW",
            "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": f"Offered {offered_service_type}; required {required_service_type}: service location mismatch.",
            "remedy": "Officer must resolve service compatibility against the tender."
        })
    else:
        results.append({
            "clause_id": "SPEC-WARRANTY", "clause_name": "Warranty Duration & Service",
            "status": "PASS", "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": f"Declared {offered_years:g}-Year {offered_service_type} warranty meets evaluated duration and location requirements.",
            "remedy": None
        })

    if extracted_data.get("ocr_only"):
        # OCR transcription supplies candidate values, not independently verified evidence.
        for result in results:
            if result["status"] in {"PASS", "FAIL", "EXEMPT"}:
                result["unverified_machine_status"] = result["status"]
                result["status"] = "NEEDS_REVIEW"
                result["evidence"] += " OCR-derived finding: inspect the source image before confirming this verdict."
                result["remedy"] = "Compare the extracted value with the scanned source and record the officer decision."
    return results
