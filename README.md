> **Current Demo Baseline:** Read [DEMO_READINESS.md](DEMO_READINESS.md) and [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) for verified scope, test procedures, and system boundaries. This platform performs deterministic statutory checks and on-device OCR. Optional Gemini advisory evidence review operates via bounded read-only tools. Live registry integrations, cryptographically authenticated officer identity, and multi-attachment bundle synthesis remain roadmap items.

# BidLens AI 🔍
### *AI-Powered GeM Bid Compliance & Statutory Verification Platform*
**Smart India Hackathon 2026 | Problem ID: SIH26100 | Category: Software / GeM Track**

---

[![Tests: 106 Passed](https://img.shields.io/badge/Tests-106%20Passed-brightgreen.svg?logo=pytest)](backend/tests/)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI: 0.111.0](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js: 14](https://img.shields.io/badge/Next.js-14.2-black.svg?logo=next.js)](https://nextjs.org/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20ONNX-orange.svg)](https://github.com/RapidAI/RapidOCR)
[![Google Gemini API](https://img.shields.io/badge/AI%20Review-Gemini%20Interactions-4285F4.svg?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🌐 **Repository:** [https://github.com/hexagon-afk/BidLens-AI-Pro](https://github.com/hexagon-afk/BidLens-AI-Pro)  
> ⚡ **Local Backend API:** `http://127.0.0.1:8000` (Docs: `http://127.0.0.1:8000/docs`)  
> 💻 **Local Frontend Portal:** `http://localhost:3000`  
> 🛡️ **Edge System Health Check:** `http://127.0.0.1:8000/system/health`  
> 📹 **Recorded Gemini Evidence Review Demo:** [docs/demo/RECORDED_GEMINI_DEMO.html](docs/demo/RECORDED_GEMINI_DEMO.html)

---

## 📌 Executive Summary

Public procurement via the **Government e-Marketplace (GeM)** requires tender committees to scrutinize hundreds of complex bids comprising thousands of pages of technical specifications, audited financial reports, OEM authorizations, and statutory filings.

Manual scrutiny suffers from:
* **Human Fatigue & Oversight:** Overlooked cross-document discrepancies (e.g. turnover shortfalls between cover letters and balance sheets, or invalid instrument numbers).
* **Unfair Disqualifications:** Accidental disqualification of eligible Micro & Small Enterprises (MSEs) due to intricate waiver clauses under the **Public Procurement Policy for MSEs Order 2012** and **General Financial Rules (GFR 2017)**.
* **Lengthy Evaluation Cycles:** Weeks spent manually validating GSTIN formats, PAN correlation, and technical warranty terms.
* **Integrity & Tampering Risks:** Absence of an immutable supervisory decision trail and cryptographic document hashing.

**BidLens AI** is an intelligent, auditable procurement co-pilot designed for GeM evaluating officers. It pairs **deterministic statutory verification** (enforcing GFR 2017 Rules 149, 160, 170, and Make in India preferences) with an **autonomous Gemini Evidence Review Agent** (`EvidenceReviewAgent`) equipped with bounded, read-only tools to retrieve and verify quoted evidence directly from submitted files.

---

## 🏛️ System Architecture

BidLens AI is structured into a **6-Layer Sovereign Architecture**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      Layer 1: Next.js Frontend Portal                  │
│   Officer Dashboard • AI Evidence Reviewer • Manual Override Portal    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST & Next.js Proxy
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Layer 2: FastAPI Backend Gateway                    │
│   Document Ingestion • SHA-256 Fingerprinting • Boundary Sanitizer     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Async Fan-out & Tender Context
┌───────────────────────────────────▼────────────────────────────────────┐
│                  Layer 3: Central Audit Orchestrator                   │
│  ┌───────────────────────┬──────────────────────┬────────────────────┐ │
│  │      Branch A:        │      Branch B:       │     Branch C:      │ │
│  │   Vision Extraction   │ GFR 2017 Rule Engine │  Statutory Verify  │ │
│  │ (RapidOCR + PyMuPDF)  │ (Deterministic Code) │ (Modulus-36 Check) │ │
│  └───────────────────────┴──────────────────────┴────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Aggregated Findings & 5-State Matrix
┌───────────────────────────────────▼────────────────────────────────────┐
│                 Layer 4: Evidence & Risk Analysis Engine               │
│  Cross-Document Contradiction ───► Knowledge Graph ───► Risk Scorer    │
│            Detector                      (NetworkX)     (Explainable)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Verified Excerpts
┌───────────────────────────────────▼────────────────────────────────────┐
│            Layer 5: Autonomous Gemini Evidence Review Agent            │
│   Bounded Read-Only Tools (get_clause_result, search_evidence,         │
│   read_evidence) • Strict Quote Validation • Anti-Hallucination Guard   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Officer Review & Overrides
┌───────────────────────────────────▼────────────────────────────────────┐
│                Layer 6: Audit Logging & Certified Reports              │
│    Durable JSONL Override Trail • Official 2-Page PDF Audit Dossier    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Core Subsystems & Capabilities

### 1. Multi-Modal Document Extraction Pipeline
* **Digital PDF Parsing:** High-throughput structure and text extraction via `PyMuPDF` (`fitz`), preserving real page numbers and section layouts.
* **On-Device Neural OCR:** `RapidOCR` powered by `ONNX Runtime` using PP-OCRv4 detection and recognition models with an unrotated text classifier, running 100% locally on CPU without external API dependencies.
* **Office Formats:** Deep parsing of Microsoft Word proposals (`python-docx`) and financial BoQ spreadsheets (`openpyxl`).
* **Uncertainty & Incompleteness Model:** Scanned documents and unreadable pages generate candidate values that remain `NEEDS_REVIEW` until an officer manually confirms or overrides them. The system never fabricates placeholder values.

### 2. Deterministic Statutory Rule Engine (5-State Model)
Legal procurement rules are executed exclusively via deterministic Python logic—never generative models:
* **5-State Evaluation Model:** Every requirement produces exactly one authoritative state:
  * `PASS`: Fully meets or exceeds tender specifications.
  * `FAIL`: Unambiguously violates mandatory criteria.
  * `EXEMPT`: Formally waived under statutory authority (e.g. MSE turnover waiver under Order 2012).
  * `NOT_APPLICABLE`: Clause does not apply to this vendor category.
  * `NEEDS_REVIEW`: Ambiguous evidence, claimed exemption lacking category proof, or incomplete scan.
* **Implemented Tender-Bound Clauses:**
  1. `RULE-149-GSTIN`: Offline Modulus-36 checksum calculation and PAN extraction.
  2. `RULE-160-TURNOVER`: Average turnover vs. tender threshold, with MSE exemption review.
  3. `RULE-170-EMD`: EMD amount validation, separating instrument IDs (e.g. Bank Guarantee numbers) from monetary amounts (with Lakh/Crore multipliers).
  4. `MII-LOCAL-CONTENT`: Class-1 / Class-2 local content domestic value-addition threshold verification.
  5. `SPEC-WARRANTY`: Independent evaluation of warranty duration (years) and service SLA location (`Carry-in` vs `Onsite`).

### 3. Cross-Document Contradiction Detector
Scans extracted vendor filings for integrity discrepancies:
* `CONTRA-PAN-01`: Flags multiple conflicting PAN numbers across submitted attachments.
* `CONTRA-GST-PAN-02`: Validates that characters 3–12 of the GSTIN strictly match the declared PAN.
* `CONTRA-TAX-03`: Flags expired or invalid tax validity dates.
* `CONTRA-ELIG-04`: Detects turnover shortfalls against tender requirements for non-MSE bidders.
* `CONTRA-MII-05`: Catches unsubstantiated Make in India self-declarations lacking declared percentage.

### 4. Clause-to-Evidence Knowledge Graph
Constructed via `NetworkX`, generating an auditable compliance graph:
$$\text{Statutory Regulation} \longrightarrow \text{Tender Requirement} \longrightarrow \text{Extracted Evidence} \longrightarrow \text{Audit Verdict}$$

### 5. Autonomous Gemini Evidence Review Agent (`EvidenceReviewAgent`)
An advisory co-pilot that assists officers in scrutinizing evidence without modifying legal verdicts:
* **Interactions API Architecture:** Multi-turn tool execution loop using `google-genai` (SDK 2.28+).
* **Bounded Read-Only Tools:**
  * `get_clause_result`: Inspects machine verdict, tender threshold, and rule explanation.
  * `search_evidence`: Locates candidate text passages across tender and bid records.
  * `read_evidence`: Retrieves exact text snippets by source ID and page number.
* **Strict Anti-Hallucination & Quote Verification:** The agent's final JSON advice is discarded if quoted text does not match extracted source documents or if fabricated citations are detected.
* **Untrusted Document Containment:** Extracted PDF/Word text is sanitized and encapsulated within strict `<UNTRUSTED_DOCUMENT>` XML boundaries to prevent prompt-injection attacks.
* **Safe Diagnostics (Version 2):** Distinct HTTP error handlers (400, 402, 403, 422, 429) provide clear diagnostic references without exposing API keys or document contents.

### 6. Supervisory Review & Durable JSONL Audit Trail
* **Justified Overrides:** Officers can override any machine verdict (`PASS`, `FAIL`, `EXEMPT`, `NEEDS_REVIEW`) by providing a mandatory written justification (minimum 5 characters).
* **Durable Event Log:** Overrides are appended sequentially to [`backend/generated_reports/audit_override_trail.jsonl`](backend/generated_reports/audit_override_trail.jsonl) before results are published.
* **Live Re-Aggregation:** Overriding a clause triggers an instant re-aggregation of overall bid status, risk score, executive summary, and shortlist eligibility.
* **1-Click Reset:** Officers can reset overrides for any bid to instantly restore the original machine evaluation.

---

## 📊 Sample Vendor Bids & Verified Outcomes

Tested against the master tender **`Tender_RFP_GeM_Computers.pdf`** (Budget: ₹50,00,000 | EMD: ₹1,00,000 | Min Turnover: ₹1.50 Cr | Local Content: $\ge$ 50% | Warranty: 3 Years Onsite):

| Vendor Submission | Primary Format | Machine Verdict | Statutory Summary & Test Gates |
| :--- | :--- | :--- | :--- |
| **MegaTech BigBrand** | PDF + Excel BoQ | `COMPLIANT` | Passes all 5 clauses. Turnover (₹15 Cr) and EMD (₹1 Lakh) meet requirements. 3-Year Onsite warranty confirmed. BoQ quote: ₹48 Lakh. |
| **Apex Labs Micro Devices** | Multi-Page PDF | `NEEDS_REVIEW` | Claimed MSE turnover and EMD exemptions require officer verification of Udyam category. Class-1 Local Content (68%) verified. |
| **GlobalCorp Ineligible** | Multi-Page PDF | `CRITICAL_RISK` | Multiple critical failures: Embedded GSTIN/PAN mismatch, expired tax registration, 1-Year Carry-in warranty (fails 3-Year Onsite requirement). |
| **GlobalCorp Rectified** | Multi-Page PDF | `COMPLIANT` | Corrected re-submission: Validated checksum GSTIN, matching PAN, 3-Year Onsite warranty, full EMD submission. |
| **Scanned Letter ApexLabs** | PNG (Image OCR) | `NEEDS_REVIEW` | Processed via local `RapidOCR`. Candidate values extracted and staged for officer review. |
| **BoQ Price Schedule** | XLSX Spreadsheet | `COMPLIANT` | Ingested via `openpyxl`. Itemized prices, quantities, and GST rates parsed deterministically. |

---

## 🧪 Test Suite & Architectural Gates

The test suite contains **106 automated tests** executing in **~8.4 seconds** across unit, integration, and security layers:

```bash
# Run the complete test suite from the backend directory
C:\BIdver\BidLens-AI\backend\venv\Scripts\python.exe -m pytest backend/tests -v
```

```text
======================= 106 passed, 3 warnings in 8.40s =======================
```

### Key Verified Quality Gates:
* `test_gate_1_different_results_when_tender_threshold_changes`
* `test_gate_2_one_year_warranty_fails_three_year_requirement`
* `test_gate_3_unreadable_evidence_produces_needs_review`
* `test_gate_4_negated_msme_does_not_grant_exemption`
* `test_gate_7_gstin_checksum_rejects_arbitrary_characters`
* `test_gate_13_pan_gstin_mismatch_prevents_compliant_verdict`
* `test_gate_22_unmocked_end_to_end_sample_evaluation`
* `test_gate_24_emd_instrument_id_and_units_extraction` (Separation of BG numbers and Lakh/Crore multipliers)
* `test_gate_26_carry_in_warranty_fails_onsite_requirement`
* `test_gate_27_unrecognized_clause_status_forces_needs_review`
* `test_gate_28_durable_append_only_override_trail_and_agent_review`
* `test_llm_review`: 22 tests validating tool loops, quote verification, quota handling, and safe diagnostic references.

---

## 📡 API Reference

### Tender & Document Ingestion
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/document/tender/upload` | Ingest RFP PDF and extract budget, EMD, turnover, and warranty criteria |
| `GET` | `/document/tender/sample` | Load pre-packaged GeM Computer Tender RFP criteria |
| `POST` | `/document/sample/load/{name}` | Load a specific sample bid document into the active evaluation staging |
| `POST` | `/document/samples/load` | 1-Click ingestion of all standard sample bids |
| `POST` | `/document/upload` | Upload vendor document, calculate SHA-256 fingerprint, and stage for audit |

### Compliance Audit & Agent Review
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/audit/run` | Execute 3-branch audit (Vision, GFR 2017 Rules, Govt Check, Knowledge Graph) |
| `GET` | `/audit/status/{audit_id}` | Retrieve cached audit findings, risk score, and clause decisions |
| `POST` | `/audit/clause-override` | Record officer clause override with **mandatory written justification** |
| `POST` | `/audit/overrides/reset/{bid_id}` | Reset overrides for a specific vendor bid and restore machine verdicts |
| `GET` | `/audit/overrides/trail` | Retrieve the **durable append-only JSONL override audit trail** |
| `GET` | `/audit/agent/config` | Check Gemini model presence and configuration status (never leaks API key) |
| `POST` | `/audit/agent/review/{bid_id}` | Trigger autonomous **`EvidenceReviewAgent`** tool-calling evaluation |
| `GET` | `/audit/report/pdf/{audit_id}` | Download official 2-Page Audit Report with override log and manual sign-off |

### System & Health Telemetry
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service status and API version metadata |
| `GET` | `/system/health` | Sovereign edge metrics, memory footprint, and air-gap integrity |

---

## 🚀 Step-by-Step Local Host Execution

### Prerequisites
* **Python 3.10+** (with virtual environment)
* **Node.js v18+** & **npm**
* **Microsoft Visual C++ x64 Redistributable** (required by RapidOCR / ONNX on Windows)

### Option 1: 1-Click Launch (Windows)
Double-click `Start_BidLens.bat` in the project root. This opens two terminal windows:
* 🟢 **Backend:** `http://127.0.0.1:8000`
* 🔵 **Frontend:** `http://localhost:3000`

---

### Option 2: Manual Terminal Setup

#### Terminal 1: FastAPI Sovereign Backend
```powershell
cd C:\BIdver\BidLens-AI-Pro\backend

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
* Backend URL: `http://127.0.0.1:8000`
* Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`
* System Health Telemetry: `http://127.0.0.1:8000/system/health`

#### Terminal 2: Next.js Frontend Portal
```powershell
cd C:\BIdver\BidLens-AI-Pro\frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
* Officer Web Portal: `http://localhost:3000`

---

## 🤖 Optional Gemini Advisory Review Setup

To enable the optional autonomous AI Evidence Review Agent:

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. Create or edit `backend/.env`:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
3. Restart the backend server.
4. In the UI, navigate to any evaluated bid, open a clause card, acknowledge the cloud-processing notice, and click **"Run AI Evidence Review"**.
5. The agent will execute bounded tool calls (`get_clause_result`, `search_evidence`, `read_evidence`) to retrieve and verify evidence excerpts.

> 🔒 **Security Notice:** The Gemini review is strictly advisory and cannot alter audit verdicts. External API keys are never exposed to the frontend, logged, or returned via endpoints.

---

## 🛡️ Sovereign Offline / Air-Gapped Mode

BidLens AI can operate completely offline without internet access:
1. Disconnect your machine from the network.
2. Start the backend and frontend locally.
3. Open `http://127.0.0.1:8000/system/health`:
   * `mode`: `"100% SOVEREIGN_OFFLINE_EDGE"`
   * `data_consumption_kb`: `0.0`
   * `cloud_data_retention`: `"DISABLED (AIR-GAPPED COMPATIBLE)"`
   * Local OCR, deterministic rule evaluation, contradiction detection, and PDF generation function without network calls.

---

## 👥 Team Hexagon

Built with precision for the **Smart India Hackathon (SIH) 2026** under Problem Statement **SIH26100**.

* **Author:** Ankur Ray Choudhury ([archoudhury19@gmail.com](mailto:archoudhury19@gmail.com))
* **Organization:** Team Hexagon | Government e-Marketplace (GeM) Track

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
