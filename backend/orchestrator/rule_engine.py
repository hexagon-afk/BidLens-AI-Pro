"""
Compliance Rule Engine - Layer 3, Branch B
DETERMINISTIC Python rules. No LLM involved.
Evaluates GFR 2017 statutory procurement rules.
"""

def evaluate_compliance(extracted_data: dict, tender_requirements: dict = None) -> list:
    if tender_requirements is None:
        tender_requirements = {
            "min_turnover_cr": 1.50,
            "emd_required_inr": 100000.0,
            "min_local_content_pct": 50,
            "min_warranty_years": 3,
        }

    results = []

    # 1. GFR Rule 149
    gstin = extracted_data.get("gstin")
    gstin_expired = extracted_data.get("gstin_expired", False)
    if not gstin or gstin_expired:
        results.append({
            "clause_id": "GFR-149-GST",
            "clause_name": "GSTIN Registration & Validity",
            "status": "FAIL",
            "regulation_ref": "GFR 2017 Rule 149",
            "evidence": "GSTIN missing or inactive.",
            "remedy": "Submit active GSTIN certificate."
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

    # 2. GFR Rule 160 (Turnover Check without MSME exemption or None check)
    turnover_cr = extracted_data.get("turnover_cr")
    min_turnover = tender_requirements["min_turnover_cr"]
    if turnover_cr >= min_turnover:
        results.append({
            "clause_id": "GFR-160-TO",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "PASS",
            "regulation_ref": "GFR 2017 Rule 160",
            "evidence": f"Turnover {turnover_cr} Cr meets threshold.",
            "remedy": None
        })
    else:
        results.append({
            "clause_id": "GFR-160-TO",
            "clause_name": "Annual Financial Turnover Requirement",
            "status": "FAIL",
            "regulation_ref": "GFR 2017 Rule 160",
            "evidence": f"Turnover below threshold.",
            "remedy": "Provide audited balance sheets."
        })

    return results
