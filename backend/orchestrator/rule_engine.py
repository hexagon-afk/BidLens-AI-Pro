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

