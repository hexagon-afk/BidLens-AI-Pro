> **Current Demo Baseline:** Read [DEMO_READINESS.md](DEMO_READINESS.md) and [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) for verified scope, test procedures, and system boundaries. This platform performs five deterministic tender checks and on-device OCR. The latest upgrade adds original-source keyword inspection, frozen session revision comparisons, an officer-defined receipt checklist and active source-integrity guards. Results and versions still disappear on backend restart; matching source bytes do not authenticate documents. Optional Gemini advisory evidence review operates via bounded read-only tools. Live registry integrations, cryptographically authenticated officer identity, and multi-attachment bundle synthesis remain roadmap items.

# BidLens AI 🔍
### *AI-Powered GeM Bid Compliance & Statutory Verification Platform*
**Smart India Hackathon 2026 | Problem ID: SIH26100 | Category: Software / GeM Track**

---

[![Tests: 125 Passed](https://img.shields.io/badge/Tests-125%20Passed-brightgreen.svg?logo=pytest)](backend/tests/)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI: 0.111.0](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js: 15.5.27](https://img.shields.io/badge/Next.js-15.5.27-black.svg?logo=next.js)](https://nextjs.org/)
[![RapidOCR](https://img.shields.io/badge/OCR-RapidOCR%20ONNX-orange.svg)](https://github.com/RapidAI/RapidOCR)
[![Google Gemini API](https://img.shields.io/badge/AI%20Review-Gemini%20Interactions-4285F4.svg?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 🌐 **Repository:** [https://github.com/hexagon-afk/BidLens-AI-Pro](https://github.com/hexagon-afk/BidLens-AI-Pro)  
> 🌐 **Hosted Prototype:** [bidlens-ai-prox.vercel.app](https://bidlens-ai-prox.vercel.app/) | [Render backend](https://bidlens-ai-pro.onrender.com/)
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

**BidLens AI** is an intelligent, auditable procurement co-pilot designed for GeM evaluating officers. It pairs **five implemented tender checks and offline identity validation** with an **autonomous Gemini Evidence Review Agent** (`EvidenceReviewAgent`) equipped with bounded, read-only tools to retrieve and verify quoted evidence directly from submitted files.

---

## 🏛️ System Architecture

BidLens AI is structured into a **six logical application layers**:

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
                                    │ Inspected Excerpts
┌───────────────────────────────────▼────────────────────────────────────┐
│            Layer 5: Autonomous Gemini Evidence Review Agent            │
│   Bounded Read-Only Tools (get_clause_result, search_evidence,         │
│   read_evidence) • Strict Quote Validation • Anti-Hallucination Guard   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Officer Review & Overrides
┌───────────────────────────────────▼────────────────────────────────────┐
│                Layer 6: Audit Logging & Prototype Reports              │
│    Local JSONL Override Trail • Prototype PDF Review Report    │
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
  2. `RULE-160-TURNOVER`: Declared turnover vs. tender threshold, with MSE exemption review. This internal ID is not a citation establishing a turnover rule under GFR Rule 160.
  3. `RULE-170-EMD`: EMD amount validation, separating instrument IDs (e.g. Bank Guarantee numbers) from monetary amounts (with Lakh/Crore multipliers).
  4. `MII-LOCAL-CONTENT`: Class-1 / Class-2 local content domestic value-addition threshold verification.
  5. `SPEC-WARRANTY`: Independent evaluation of warranty duration (years) and service SLA location (`Carry-in` vs `Onsite`).

### 3. Cross-Document Contradiction Detector
Scans extracted vendor filings for integrity discrepancies:
* `CONTRA-PAN-01`: Flags differing PAN numbers within one submitted file; separate attachments are not combined.
* `CONTRA-GST-PAN-02`: Validates that characters 3–12 of the GSTIN strictly match the declared PAN.
* `CONTRA-TAX-03`: Flags expired or invalid tax validity dates.
* `CONTRA-ELIG-04`: Detects turnover shortfalls against tender requirements for non-MSE bidders.
* `CONTRA-MII-05`: Catches unsubstantiated Make in India self-declarations lacking declared percentage.

### 4. Clause-to-Evidence Knowledge Graph
Constructed via `NetworkX`, linking generated check summaries. It is not a complete verified source-page evidence graph:
$$\text{Statutory Regulation} \longrightarrow \text{Tender Requirement} \longrightarrow \text{Extracted Evidence} \longrightarrow \text{Audit Verdict}$$

### 5. Autonomous Gemini Evidence Review Agent (`EvidenceReviewAgent`)
An advisory co-pilot that assists officers in scrutinizing evidence without modifying machine verdicts:
* **Interactions API Architecture:** Multi-turn tool execution loop using `google-genai` (SDK 2.28+).
* **Bounded Read-Only Tools:**
  * `get_clause_result`: Inspects machine verdict, tender threshold, and rule explanation.
  * `search_evidence`: Locates candidate text passages across tender and bid records.
  * `read_evidence`: Retrieves exact text snippets by source ID and page number.
* **Strict Anti-Hallucination & Quote Verification:** The agent's final JSON advice is discarded if quoted text does not match extracted source documents or if fabricated citations are detected.
* **Untrusted Document Containment:** Extracted PDF/Word text is sanitized and encapsulated within strict `<UNTRUSTED_DOCUMENT>` XML boundaries to reduce prompt-injection exposure; this is not proof that all such attacks are prevented.
* **Safe Diagnostics (Version 2):** Distinct HTTP error handlers (400, 402, 403, 422, 429) provide clear diagnostic references without exposing API keys or document contents.

### 6. Supervisory Review & Local JSONL Event Trail
* **Justified Overrides:** Officers can override any machine verdict (`PASS`, `FAIL`, `EXEMPT`, `NEEDS_REVIEW`) by providing a mandatory written justification (minimum 5 characters).
* **Local Event Log:** Overrides are appended sequentially to [`backend/generated_reports/audit_override_trail.jsonl`](backend/generated_reports/audit_override_trail.jsonl) before results are published.
* **Live Re-Aggregation:** Overriding a clause triggers an instant re-aggregation of overall bid status, risk score, executive summary, and shortlist eligibility.
* **1-Click Reset:** Officers can reset overrides for any bid to instantly restore the original machine evaluation.

---

## 📊 Sample Vendor Bids & Verified Outcomes

Tested against the master tender **`Tender_RFP_GeM_Computers.pdf`** (Budget: ₹50,00,000 | EMD: ₹1,00,000 | Min Turnover: ₹1.50 Cr | Local Content: $\ge$ 50% | Warranty: 3 Years Onsite):

| Vendor submission | Format | Machine verdict | Verified demo outcome |
| :--- | :--- | :--- | :--- |
| MegaTech BigBrand | PDF | `COMPLIANT` | Five implemented checks pass. Authenticity and award suitability remain unverified. |
| ApexLabs MSME | PDF | `NEEDS_REVIEW` | Three checks pass; turnover and EMD exemption claims require officer verification. |
| GlobalCorp original | PDF | `NON_COMPLIANT` | Five implemented checks fail. |
| GlobalCorp rectified | PDF | `COMPLIANT` | Five implemented checks pass; linked comparison preserves the original machine result. |
| ApexLabs proposal | DOCX | `NEEDS_REVIEW` | Independently evaluated; unresolved evidence requires inspection. |
| BoQ price schedule | XLSX | `NEEDS_REVIEW` | A price attachment alone does not establish the other compliance requirements. |
| Scanned ApexLabs letter | PNG | `NEEDS_REVIEW` | OCR candidate values require confirmation against the source image. |

---

## 🧪 Test Suite & Architectural Gates

The test suite contains **125 automated tests** executing in **20.60 seconds** in this local run across unit, integration, and security layers:

```bash
# Run the complete test suite from the project root
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

```text
======================= 125 passed, 1 warning in 20.60s =======================
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

## Latest evidence workflow

- **Original-source inspection:** literal tender/bid keyword candidates, real PDF page markers and original document downloads, including unreadable sources. Matches are not validated semantic mappings.
- **Linked re-evaluation:** unique evaluation IDs and frozen machine results in memory; the backend rejects a comparison against different tender criteria/source versions. Officer decisions remain separate.
- **Receipt checklist:** up to 20 officer-defined requirements. MISSING, RECEIVED_UNVERIFIED and NEEDS_INSPECTION track receipt/readability; attachments do not get merged into the rule audit.
- **Active integrity guards:** changed/missing source bytes block inspection, comparison, officer decisions, model review and export with HTTP 409. Local digests/events are not tamper-proof or document authentication.
- **Validation:** 125 backend tests and the production frontend build passed. The local six-document rehearsal returned 1 compliant, 4 under review and 1 non-compliant; the GlobalCorp revision changed five statuses. No model call was made for this upgrade.

## 📡 API Reference

### Tender & Document Ingestion
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/document/tender/upload` | Ingest RFP PDF and extract budget, EMD, turnover, and warranty criteria |
| `GET` | `/document/tender/sample` | Load pre-packaged GeM Computer Tender RFP criteria |
| `POST` | `/document/sample/load/{name}` | Load a specific sample bid document into the active evaluation staging |
| `POST` | `/document/sample/vendor-bids` | 1-Click ingestion of all standard sample bids |
| `POST` | `/document/upload` | Upload vendor document, calculate SHA-256 fingerprint, and stage for audit |

### Compliance Audit & Agent Review
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/audit/run` | Execute 3-branch audit (Vision, GFR 2017 Rules, Govt Check, Knowledge Graph) |
| `GET` | `/audit/status/{audit_id}` | Retrieve cached audit findings, risk score, and clause decisions |
| `POST` | `/audit/clause-override` | Record officer clause override with **mandatory written justification** |
| `POST` | `/audit/overrides/reset/{bid_id}` | Reset overrides for a specific vendor bid and restore machine verdicts |
| `GET` | `/audit/overrides/trail` | Retrieve the locally appended JSONL override trail (not cryptographically protected or guaranteed to survive deployment) |
| `GET` | `/audit/agent/config` | Check Gemini model presence and configuration status (never leaks API key) |
| `POST` | `/audit/agent/review/{bid_id}` | Trigger autonomous **`EvidenceReviewAgent`** tool-calling evaluation |
| `GET` | `/audit/report/pdf/{audit_id}` | Download a prototype review report with evaluation ID, receipt checklist, officer decisions and manual sign-off |

### Source inspection, session comparison and receipt
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/audit/evidence/{evaluation_id}/{clause_id}` | Source-checked literal keyword passages |
| `GET` | `/audit/source/{evaluation_id}/BID` or `/TENDER` | Original document for officer inspection |
| `GET` | `/audit/integrity/{evaluation_id}` | Rehash source bytes; mismatch blocks review/export |
| `GET` | `/audit/comparison/{evaluation_id}` | Frozen original/revised machine comparison |
| `GET` / `POST` | `/audit/checklist/{evaluation_id}` | Officer-defined document receipt checklist |

POST /audit/run accepts previous_evaluation_id for a revision. Prototype routes do not add authentication/access control; use synthetic documents on the public demo. GET /audit/agent/config includes workflow_version=1 to identify the deployed workflow, not to prove live Gemini availability.

### System & Health Telemetry
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Root service status and API version metadata |
| `GET` | `/system/health` | Backend status and local runtime metrics; not proof of air-gap integrity |

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

#### Terminal 1: FastAPI Prototype Backend
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
