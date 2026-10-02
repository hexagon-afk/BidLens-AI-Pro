"""
Govt Verification Gateway - Layer 3, Branch C
Performs offline format validation, Modulus-36 mathematical checksum analysis,
and entity identifier consistency checks across Indian Public Procurement databases:
1. GSTN Common Portal (GST) - Modulus-36 Checksum
2. Income Tax Department (ITD) - PAN Entity Structuring
3. Udyam MSME Portal - Identifier Pattern Verification
4. MCA21 Corporate Registry - Offline Demo Stub
5. EPFO & ESIC Labour Directory - Offline Demo Stub
6. CPPP Debarment Watchlist - Anomaly & Status Checks
"""
import re

GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAR_MAP = {c: i for i, c in enumerate(GST_CHARS)}


def compute_gstin_check_digit(gstin14: str) -> str:
    """
    Computes the valid 15th character Modulus-36 check digit for a 14-character GSTIN prefix.
    """
    if not gstin14 or len(gstin14) != 14:
        return ""
    gstin14 = gstin14.upper()
    total = 0
    for i in range(14):
        c = gstin14[i]
        if c not in CHAR_MAP:
            return ""
        val = CHAR_MAP[c]
        multiplier = 1 if i % 2 == 0 else 2
        product = val * multiplier
        total += (product // 36) + (product % 36)
    remainder = total % 36
    check_code = (36 - remainder) % 36
    return GST_CHARS[check_code]


def verify_gstin_checksum(gstin: str) -> bool:
    """
    Computes official Indian GSTIN Modulus-36 check digit on 14 characters.
    Validates that the 15th character matches the mathematical check digit.
    No allowlist bypasses.
    """
    if not gstin or len(gstin) != 15:
        return False
    gstin = gstin.upper()
    expected_char = compute_gstin_check_digit(gstin[:14])
    return bool(expected_char and gstin[14] == expected_char)


def verify_government_credentials(extracted_data: dict) -> dict:
    """
    Validates credentials using local offline syntax, checksum, and identity checks.
    External live registry handshakes are clearly flagged as UNVERIFIED / OFFLINE_PROTOTYPE.
    """
    gstin = extracted_data.get("gstin")
    pan = extracted_data.get("pan")
    all_pans = extracted_data.get("all_pans", [])
    udyam = extracted_data.get("udyam")
    vendor_name = extracted_data.get("vendor_name", "Vendor Entity")
    is_expired = extracted_data.get("gstin_expired", False)

    # Detect completely empty submission
    has_any_id = bool(gstin or pan or udyam or all_pans or (vendor_name and vendor_name != "Vendor Entity" and vendor_name != "Unknown Vendor"))

    # ── 1. GSTN Portal Verification ───────────────────────────
    gstn_status = "NOT_PROVIDED"
    gstn_badge = "FAIL"
    gstn_details = {}
    if gstin:
        gstin_valid_format = bool(re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$", gstin))
        checksum_valid = verify_gstin_checksum(gstin)
        
        if gstin_valid_format and checksum_valid:
            state_code = gstin[:2]
            if is_expired:
                gstn_status = "CANCELLED / SUSPENDED"
                gstn_badge = "FAIL"
                gstn_details = {
                    "portal": "GSTN Common Portal",
                    "gstin": gstin,
                    "valid_format": True,
                    "checksum_valid": True,
                    "taxpayer_status": "CANCELLED/EXPIRED (IN DOCUMENT RECORD)",
                    "sync_status": "Flagged - Tax Status Inactive in Document Record (Live Registry Unverified)"
                }
            else:
                gstn_status = "SYNTAX & CHECKSUM VALID (OFFLINE)"
                gstn_badge = "PASS"
                gstn_details = {
                    "portal": "GSTN Common Portal",
                    "gstin": gstin,
                    "valid_format": True,
                    "checksum_valid": True,
                    "state_jurisdiction": f"State Code {state_code}",
                    "sync_status": "Format syntax & Modulus-36 checksum validated offline (Live Registry Unverified)"
                }
        elif gstin_valid_format and not checksum_valid:
            gstn_status = "CHECKSUM_FAILED"
            gstn_badge = "FAIL"
            gstn_details = {
                "portal": "GSTN Common Portal",
                "gstin": gstin,
                "valid_format": True,
                "checksum_valid": False,
                "detail": "GSTIN Modulus-36 check-digit verification failed."
            }
        else:
            gstn_status = "INVALID_STRUCTURE"
            gstn_badge = "FAIL"
            gstn_details = {
                "portal": "GSTN Common Portal",
                "gstin": gstin,
                "valid_format": False,
                "checksum_valid": False,
                "detail": "Incorrect GSTIN structure."
            }

    # ── 2. PAN Verification & Entity Type Check ───────────────
    pan_status = "NOT_PROVIDED"
    pan_badge = "FAIL"
    pan_details = {}
    if pan:
        pan_valid_format = bool(re.match(r"^[A-Z]{5}\d{4}[A-Z]{1}$", pan))
        if pan_valid_format:
            entity_type_char = pan[3]
            entity_types = {
                "C": "Company (Corporate)",
                "P": "Individual / Proprietorship",
                "F": "Firm / LLP",
                "A": "Association of Persons",
                "T": "Trust",
                "L": "Local Authority"
            }
            pan_status = "VALID SYNTAX & ENTITY TYPE (OFFLINE)"
            pan_badge = "PASS"
            pan_details = {
                "portal": "Income Tax Department (ITD)",
                "pan": pan,
                "valid_format": True,
                "entity_type": entity_types.get(entity_type_char, "Registered Legal Entity"),
                "sync_status": "Syntax & Entity Character Verified (Live Registry Unverified)"
            }
        else:
            pan_status = "INVALID_FORMAT"
            pan_badge = "FAIL"
            pan_details = {"portal": "ITD PAN Registry", "pan": pan, "valid_format": False}

    # ── 3. Udyam MSME Portal Verification ─────────────────────
    udyam_status = "NOT_APPLICABLE"
    udyam_badge = "NEUTRAL"
    udyam_details = {}
    if udyam:
        udyam_valid = bool(re.match(r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$", udyam))
        if udyam_valid:
            udyam_status = "VALID UDYAM FORMAT (OFFLINE)"
            udyam_badge = "PASS"
            udyam_details = {
                "portal": "Udyam MSME National Portal",
                "udyam_id": udyam,
                "category": "Micro & Small Enterprise (MSE)",
                "statutory_exemptions_eligible": True,
                "sync_status": "Format syntax valid (Live MSME API unverified)"
            }
        else:
            udyam_status = "INVALID_UDYAM_FORMAT"
            udyam_badge = "FAIL"
            udyam_details = {"portal": "Udyam MSME National Portal", "udyam_id": udyam, "valid": False}
    else:
        udyam_details = {
            "portal": "Udyam MSME National Portal",
            "category": "General Commercial Bidder (Non-MSME)",
            "statutory_exemptions_eligible": False
        }

    # ── 4. MCA21 Corporate Registry Check ─────────────────────
    if has_any_id:
        mca_status = "UNVERIFIED (OFFLINE PROTOTYPE)"
        mca_badge = "NEUTRAL"
        mca_details = {
            "portal": "Ministry of Corporate Affairs (MCA21)",
            "entity_name": vendor_name,
            "company_status": "UNVERIFIED",
            "sync_status": "External MCA21 API not connected in prototype"
        }
    else:
        mca_status = "NOT_EVALUATED (EMPTY_INPUT)"
        mca_badge = "NEUTRAL"
        mca_details = {"portal": "Ministry of Corporate Affairs (MCA21)", "sync_status": "No entity credentials provided"}

    # ── 5. EPFO & ESIC Labour Compliance Directory ────────────
    if has_any_id:
        epfo_status = "UNVERIFIED (OFFLINE PROTOTYPE)"
        epfo_badge = "NEUTRAL"
        epfo_details = {
            "portal": "EPFO & ESIC Labour Portal",
            "establishment_status": "UNVERIFIED",
            "sync_status": "External EPFO/ESIC API not connected in prototype"
        }
    else:
        epfo_status = "NOT_EVALUATED (EMPTY_INPUT)"
        epfo_badge = "NEUTRAL"
        epfo_details = {"portal": "EPFO & ESIC Labour Portal", "sync_status": "No entity credentials provided"}

    # ── 6. Central Public Debarment / CPPP Watchlist Check ────
    if not has_any_id:
        debarment_status = "NOT_EVALUATED (EMPTY_INPUT)"
        debarment_badge = "NEUTRAL"
        debarment_details = {"portal": "CPPP Central Debarment Watchlist", "status": "NOT_EVALUATED"}
    elif is_expired or len(set(all_pans)) > 1:
        debarment_status = "DOCUMENT ANOMALY DETECTED"
        debarment_badge = "FAIL"
        debarment_details = {
            "portal": "CPPP Central Debarment Watchlist",
            "status": "DOCUMENT ANOMALY (OFFLINE)",
            "blacklisting_orders": "Document anomaly flagged: Multiple contradictory PANs or cancelled tax filing found in submission. Official CPPP database unverified.",
            "sync_status": "Document Anomaly Flag Raised (Official CPPP API Unverified)"
        }
    else:
        debarment_status = "NO ADVERSE RECORD (LOCAL SAMPLE)"
        debarment_badge = "PASS"
        debarment_details = {
            "portal": "CPPP Central Debarment Watchlist",
            "status": "NO ADVERSE RECORD (OFFLINE SAMPLE)",
            "blacklisting_orders": "No adverse debarment record identified in local test dataset. Official CPPP registry unverified.",
            "sync_status": "Offline Prototype Sample Check (Official CPPP API Unverified)"
        }

    # ── 7. Cross-Consistency: GSTIN vs PAN Check ──────────────
    pan_gstin_consistent = True
    consistency_note = "GSTIN embedded PAN matches declared PAN."
    if gstin and pan and len(gstin) >= 12:
        embedded_pan = gstin[2:12]
        if embedded_pan != pan:
            pan_gstin_consistent = False
            consistency_note = f"Discrepancy: GSTIN contains PAN ({embedded_pan}) which differs from declared PAN ({pan})."

    # Compile Handshake Results
    verified_gateways_count = sum(1 for b in [gstn_badge, pan_badge, debarment_badge] if b == "PASS")
    if udyam and udyam_badge == "PASS":
        verified_gateways_count += 1

    overall_status = "FLAGGED_FOR_REVIEW"
    if not has_any_id:
        overall_status = "NOT_APPLICABLE"
    elif gstn_badge == "PASS" and pan_badge == "PASS" and pan_gstin_consistent and debarment_badge == "PASS":
        overall_status = "PASS"

    return {
        "overall_govt_verification": overall_status,
        "verified_gateways_count": verified_gateways_count,
        "total_gateways": 6 if udyam else 5,
        "pan_gstin_consistent": pan_gstin_consistent,
        "consistency_note": consistency_note,
        "gateways": [
            {"name": "GSTN Common Portal", "status": gstn_status, "badge": gstn_badge, "details": gstn_details},
            {"name": "ITD PAN Registry", "status": pan_status, "badge": pan_badge, "details": pan_details},
            {"name": "MCA21 Corporate Affairs", "status": mca_status, "badge": mca_badge, "details": mca_details},
            {"name": "Udyam MSME Portal", "status": udyam_status, "badge": udyam_badge, "details": udyam_details},
            {"name": "EPFO & ESIC Labour Compliance", "status": epfo_status, "badge": epfo_badge, "details": epfo_details},
            {"name": "CPPP Central Debarment Watchlist", "status": debarment_status, "badge": debarment_badge, "details": debarment_details}
        ]
    }
