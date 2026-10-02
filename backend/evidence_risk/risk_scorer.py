"""
Explainable Rejection-Risk Scorer & Value-for-Money Spotlight - Layer 4
Calculates evidence-grounded rejection risk, highlights MSME value advantages,
and generates actionable Bid Repair guidance.
"""


def compute_risk_and_value_intelligence(
    extracted_data: dict,
    clause_results: list,
    contradictions: list,
    overall_status: str = None,
    tender_requirements: dict = None
) -> dict:
    """
    Computes an explainable rejection-risk profile, MSME value advantages,
    and corrective bid repair actions, strictly aligned with the unified overall verdict.
    """
    fail_clauses = [c for c in clause_results if c.get("status") == "FAIL"]
    exempt_clauses = [c for c in clause_results if c.get("status") == "EXEMPT"]
    pass_clauses = [c for c in clause_results if c.get("status") == "PASS"]
    needs_review_clauses = [c for c in clause_results if c.get("status") == "NEEDS_REVIEW"]
    
    critical_contradictions = [c for c in contradictions if c.get("severity") in ["CRITICAL", "HIGH"]]
    has_critical_contra = any(c.get("severity") == "CRITICAL" for c in contradictions)
    has_high_contra = any(c.get("severity") == "HIGH" for c in contradictions)

    # Determine or validate overall status
    if overall_status is None:
        if len(fail_clauses) > 0 or has_critical_contra:
            overall_status = "NON_COMPLIANT"
        elif len(needs_review_clauses) > 0 or has_high_contra:
            overall_status = "NEEDS_REVIEW"
        else:
            overall_status = "COMPLIANT"

    # ── 1. Rejection Risk Calculation ─────────────────────────
    if overall_status == "NON_COMPLIANT":
        risk_tier = "CRITICAL" if (len(fail_clauses) >= 2 or len(critical_contradictions) >= 2) else "HIGH"
        risk_score = 0.95 if risk_tier == "CRITICAL" else 0.75
        rejection_likely = True
    elif overall_status == "NEEDS_REVIEW":
        risk_tier = "MEDIUM"
        risk_score = 0.40
        rejection_likely = False
    else:
        risk_tier = "LOW"
        risk_score = 0.05
        rejection_likely = False

    # ── 2. Explainable Rejection Grounds ──────────────────────
    risk_explanations = []
    for f in fail_clauses:
        risk_explanations.append({
            "category": "Regulatory Non-Compliance",
            "clause": f.get("clause_name"),
            "regulation": f.get("regulation_ref"),
            "reason": f.get("evidence"),
            "impact": "Grounds for mandatory technical disqualification."
        })

    for c in critical_contradictions:
        risk_explanations.append({
            "category": "Document Discrepancy",
            "clause": c.get("title"),
            "regulation": "GeM Procurement Guidelines",
            "reason": c.get("description"),
            "impact": c.get("impact")
        })

    for nr in needs_review_clauses:
        risk_explanations.append({
            "category": "Verification Pending",
            "clause": nr.get("clause_name"),
            "regulation": nr.get("regulation_ref"),
            "reason": nr.get("evidence"),
            "impact": "Requires officer review of tender criteria or physical annexures."
        })

    # ── 3. Value-for-Money Advantage Spotlight ────────────────
    is_msme = extracted_data.get("is_msme", False)
    quote = extracted_data.get("total_quote_inr")
    bonus_perks = extracted_data.get("bonus_perks", [])
    warranty = extracted_data.get("warranty", "")
    
    value_spotlight_active = False
    spotlight_highlights = []
    savings_inr = None

    budget_inr = tender_requirements.get("budget_inr") if tender_requirements else None
    if quote and budget_inr and quote < budget_inr:
        savings_inr = budget_inr - quote
        spotlight_highlights.append(f"Cost Savings: Quoted INR {quote:,.0f} (Saves INR {savings_inr:,.0f} / {savings_inr/budget_inr*100:.1f}% below tender budget).")
    elif quote:
        spotlight_highlights.append(f"Quoted Price: INR {quote:,.0f} (Competitive financial proposal).")

    if "5-year" in warranty.lower() or "5 year" in warranty.lower():
        spotlight_highlights.append("Extended Service: 5-Year Comprehensive Onsite Warranty (Exceeds baseline specifications).")

    for perk in bonus_perks:
        if perk not in spotlight_highlights:
            spotlight_highlights.append(f"Hardware Value-Add: {perk}")

    if is_msme:
        spotlight_highlights.append("Sovereign MSME Support: Complies with Public Procurement Policy Order 2012 MSE preference.")

    # A bid can only be recommended for value spotlight if it is COMPLIANT
    if overall_status == "COMPLIANT" and (is_msme or (savings_inr and savings_inr > 0) or len(bonus_perks) > 0):
        value_spotlight_active = True

    # ── 4. Bid Repair & Corrective Guidance ───────────────────
    bid_repair_actions = []
    for f in fail_clauses:
        if f.get("remedy"):
            bid_repair_actions.append({
                "issue": f.get("clause_name"),
                "action_required": f.get("remedy")
            })

    for c in contradictions:
        if c.get("remedy"):
            bid_repair_actions.append({
                "issue": c.get("title"),
                "action_required": c.get("remedy")
            })

    for nr in needs_review_clauses:
        if nr.get("remedy"):
            bid_repair_actions.append({
                "issue": nr.get("clause_name"),
                "action_required": nr.get("remedy")
            })

    # ── 5. Executive Officer Recommendation ───────────────────
    if overall_status == "NON_COMPLIANT":
        executive_summary = f"REJECT / CLARIFY: High rejection risk detected ({len(fail_clauses)} failed statutory clause(s), {len(critical_contradictions)} critical discrepancies). Recommend issuing clarification letter before final disqualification."
    elif overall_status == "NEEDS_REVIEW":
        executive_summary = f"SUPERVISORY REVIEW REQUIRED: {len(needs_review_clauses)} clause(s) require officer verification before compliance can be established."
    elif value_spotlight_active:
        savings_text = f"with INR {savings_inr:,.0f} cost savings and " if savings_inr is not None else "with "
        executive_summary = f"RECOMMENDED (VALUE-FOR-MONEY SPOTLIGHT): Fully compliant proposal {savings_text}superior warranty/hardware terms compared to standard bids."
    else:
        executive_summary = "COMPLIANT: Bid meets all evaluated statutory criteria and technical specifications."

    return {
        "rejection_risk": {
            "risk_tier": risk_tier,
            "risk_score": risk_score,
            "rejection_likely": rejection_likely,
            "total_flaws_found": len(fail_clauses) + len(critical_contradictions),
            "reasons": risk_explanations
        },
        "value_spotlight": {
            "is_spotlight_candidate": value_spotlight_active,
            "vendor_type": "Micro & Small Enterprise (MSME)" if is_msme else "Standard Enterprise",
            "quoted_price_inr": quote,
            "estimated_savings_inr": savings_inr,
            "value_highlights": spotlight_highlights
        },
        "bid_repair": {
            "repair_needed": len(bid_repair_actions) > 0,
            "recommended_actions": bid_repair_actions
        },
        "executive_summary": executive_summary
    }
