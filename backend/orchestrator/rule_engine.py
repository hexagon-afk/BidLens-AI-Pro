"""
Compliance Rule Engine - Layer 3, Branch B
DETERMINISTIC Python rules. No LLM involved.
Evaluates GFR 2017 statutory procurement rules, MSME 2012 Exemption Orders,
and Public Procurement (Make in India) Orders.
"""


def evaluate_compliance(extracted_data: dict, tender_requirements: dict = None) -> list:
    """
    Evaluates extracted bid data against GFR rules and tender requirements.
    Returns a structured list of clause-level decisions (PASS, FAIL, EXEMPT).
    """
    if tender_requirements is None:
        tender_requirements = {
            "min_turnover_cr": 1.50,
            "emd_required_inr": 100000.0,
            "min_local_content_pct": 50,
            "min_warranty_years": 3,
        }

    results = []

    # ── 1. GFR Rule 149 & GSTIN Validity ─────────────────────
    gstin = extracted_data.get("gstin")
    gstin_expired = extracted_data.get("gstin_expired", False)
    if not gstin:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Validity",
            "status": "FAIL",
            "regulation_ref": "GFR 2017 Rule 149 / GeM General Terms",
            "evidence": "No valid GSTIN certificate found in submission.",
            "remedy": "Submit active GSTIN certificate with current filing status."
        })
    elif gstin_expired:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Validity",
            "status": "FAIL",
            "regulation_ref": "GFR 2017 Rule 149 / Statutory Tax Compliance",
            "evidence": f"GSTIN {gstin} is flagged as EXPIRED or CANCELLED.",
            "remedy": "Provide active GSTIN reactivation certificate from GST portal."
        })
    else:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Validity",
            "status": "PASS",
            "regulation_ref": "GFR 2017 Rule 149",
            "evidence": f"Active GSTIN {gstin} verified.",
            "remedy": None
        })

