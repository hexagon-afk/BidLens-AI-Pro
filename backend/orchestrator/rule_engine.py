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
        tender_requirements = {
            "min_turnover_cr": 1.50,
            "emd_required_inr": 100000.0,
            "min_local_content_pct": 50,
            "min_warranty_years": 3,
        }

    results = []

    # ── 1. Statutory Tax & GSTIN Registration ─────────────────
    gstin = extracted_data.get("gstin")
    gstin_expired = extracted_data.get("gstin_expired", False)
    if not gstin:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Tax Compliance",
            "status": "FAIL",
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

    if min_turnover is None:
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
            "status": "EXEMPT",
            "regulation_ref": "Public Procurement Policy for MSEs Order 2012 / DoE OM F.20/2/2014-PPD",
            "evidence": f"Registered Micro/Small Enterprise ({udyam}). Statutory exemption granted from prior turnover criteria.",
            "remedy": None
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
    emd_required = tender_requirements.get("emd_required_inr")

    if emd_required is None:
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
            "status": "EXEMPT",
            "regulation_ref": "Public Procurement Policy for MSEs Order 2012, Para 10 / GFR 2017 Rule 170(i)",
            "evidence": f"Exempted from EMD submission under Central Government MSME provisions (Udyam: {udyam}).",
            "remedy": None
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
        results.append({
            "clause_id": "GFR-170-EMD",
            "clause_name": "Earnest Money Deposit (EMD)",
            "status": "PASS",
            "regulation_ref": "Tender Bid Security Clause / GFR 2017 Rule 170",
            "evidence": "Valid EMD Bank Guarantee / FDR submitted as per tender terms.",
            "remedy": None
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
    local_pct = extracted_data.get("local_content_pct", 0)
    min_local = tender_requirements.get("min_local_content_pct", 50)
    if min_local is None:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "NEEDS_REVIEW",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": "Tender local content threshold not established from RFP; officer confirmation required.",
            "remedy": "Verify minimum Class-1 / Class-2 local content threshold in Tender RFP."
        })
    elif local_pct >= min_local:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "PASS",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": f"Local content of {local_pct}% qualifies as Class-1 Local Supplier (Threshold >= {min_local}%).",
            "remedy": None
        })
    else:
        results.append({
            "clause_id": "MII-2017-LC",
            "clause_name": "Make in India Local Content Preference",
            "status": "FAIL",
            "regulation_ref": "Public Procurement (Make in India) Order 2017 (DPIIT)",
            "evidence": f"Local content of {local_pct}% fails Class-1 Local Supplier requirement (Minimum {min_local}%).",
            "remedy": f"Provide OEM certificate verifying >= {min_local}% domestic value addition."
        })

    # ── 5. Warranty & Service Level Compliance ────────────────
    warranty = extracted_data.get("warranty", "")
    offered_years = extracted_data.get("warranty_years")
    if offered_years is None:
        if "5-year" in warranty.lower() or "5 year" in warranty.lower():
            offered_years = 5.0
        elif "3-year" in warranty.lower() or "3 year" in warranty.lower():
            offered_years = 3.0
        elif "1-year" in warranty.lower() or "1 year" in warranty.lower():
            offered_years = 1.0
        elif "6-month" in warranty.lower():
            offered_years = 0.5

    min_warranty_years = tender_requirements.get("min_warranty_years", 3)

    if min_warranty_years is None:
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
            "evidence": f"Warranty terms unspecified or unreadable ({warranty}). Required: {min_warranty_years}-Year.",
            "remedy": f"Provide OEM commitment letter for {min_warranty_years}-Year onsite warranty coverage."
        })
    elif offered_years >= min_warranty_years:
        results.append({
            "clause_id": "SPEC-WARRANTY",
            "clause_name": "Comprehensive Onsite Warranty",
            "status": "PASS",
            "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": f"Offers {warranty} ({offered_years:.0f} yr >= mandatory {min_warranty_years:.0f} yr requirement).",
            "remedy": None
        })
    else:
        results.append({
            "clause_id": "SPEC-WARRANTY",
            "clause_name": "Comprehensive Onsite Warranty",
            "status": "FAIL",
            "regulation_ref": "Tender Technical Specifications (Warranty SLA)",
            "evidence": f"Offers {warranty} ({offered_years:.1f} yr) which fails mandatory {min_warranty_years:.0f}-Year requirement.",
            "remedy": f"Provide OEM commitment letter for {min_warranty_years:.0f}-Year onsite warranty coverage."
        })

    return results
