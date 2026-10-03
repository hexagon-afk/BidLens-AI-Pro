# BidLens judges' demonstration walkthrough

Use synthetic sample documents. The main demo works without a language-model call. Show what executes and identify future work accurately.

## Preparation

- Hosted demo: https://bidlens-ai-prox.vercel.app/. Backend: https://bidlens-ai-pro.onrender.com/.
- Local demo: http://127.0.0.1:3000/. In Settings, use http://127.0.0.1:8000 and confirm Backend Online.
- After deployment, hard-refresh and rerun Run Complete Sample Demo. The backend's /audit/agent/config response should include workflow_version=1. Old evaluation IDs expire when the backend restarts.
- Configure Officer Profile with a demonstration name/designation. It is display metadata, not authenticated login.
- Expected matrix: 1 compliant, 4 under review, 1 non-compliant across six independently evaluated documents.
- Expected tender: INR 50 lakh budget, INR 1 lakh EMD, 1.5 crore turnover, 50% local content, 3-year onsite warranty. Warranty evaluation covers duration/service location, not the full SLA.
- Keep server terminals open and avoid refreshing/restarting during the presentation. Frontend state and backend session results are not durable.

## Five-minute sequence

1. **Purpose and tender (45 seconds).** Show extracted thresholds. Say: "BidLens compares tender requirements with submitted evidence and preserves uncertainty for procurement officers. The officer retains the decision."

2. **Three outcomes (40 seconds).** MegaTech PDF passes the five implemented checks; GlobalCorp original fails five; ApexLabs has three passes and two exemption claims requiring review. Say "meets the evaluated checks", not "guaranteed contract winner". A Udyam identifier alone does not prove entitlement to an exemption.

3. **Inspect original evidence (45 seconds).** Open MegaTech -> Vendor Detail -> Warranty. In Inspect original evidence, read the literal vendor and tender passages, page numbers and extraction labels. Open original PDF at the selected page. Explain: "These keyword candidates help the officer inspect the actual source. A match does not prove authenticity or complete compliance." Recheck source integrity shows whether current bytes still match the recorded baseline.

4. **Receipt checklist (30 seconds).** Add "Audited financial statement, if required by tender". It starts MISSING. Add "Vendor proposal", then choose Use current bid. It should become RECEIVED UNVERIFIED for the readable PDF. Explain: "Received does not mean verified or compliant. Separate attachments are tracked here, but are not merged into the compliance engine." The checklist is officer-defined, not an automatic inventory of every tender requirement.

5. **Revised submission (50 seconds).** Open Re-evaluation for GlobalCorp, then load Bid_GlobalCorp_Rectified_ReEvaluation.pdf. The frozen comparison should show five FAIL -> PASS changes, different source bytes and two evaluation IDs/timestamps. Expand a rule explanation and changed extracted fields. Say: "The original machine result stays frozen. New evidence receives a separate evaluation against the same tender." Apply Updates to Comparison Matrix if desired. This is re-evaluation of a supplied revision; the system does not repair the source PDF automatically.

6. **Officer review (45 seconds).** Open ApexLabs EMD. Choose Mark REVIEW with a truthful note: "Demo review: EMD exemption is claimed. Certificate authenticity, enterprise category and tender-specific eligibility remain unverified. Retain NEEDS_REVIEW pending officer verification." Show the recorded event and recalculated result. Do not mark EXEMPT merely to make the dashboard green. The local event file and officer identity are not tamper-proof/authenticated.

7. **Export (30 seconds).** Download the selected vendor report. Show evaluation ID, source digest, verdict and officer note; a vendor with checklist items also includes their receipt statuses. Matching source bytes are checked before export. Say: "This is a prototype review record for officer inspection, not official certification."

## Optional Gemini segment

Only show live review after a separate successful rehearsal with explicit cloud consent and synthetic documents. These non-LLM upgrades did not make any Gemini calls or reverify provider availability.

Select MegaTech Warranty, acknowledge the cloud-processing notice, and click Run AI Evidence Review. Inspect actual returned model, literal quotations, pages and Executed agent tools. The agent selects search_evidence, read_evidence and get_clause_result; the backend executes them read-only. Up to six tool calls, five model turns and 60 seconds are permitted. Advice cannot change the procurement verdict or authenticate certificates.

If billing/quota/validation fails, stop repeated clicks. Say: "Cloud review is currently unavailable. The audit remains usable and no verdict changed." Open docs/demo/RECORDED_GEMINI_DEMO.html, which visibly labels a genuine recorded MegaTech warranty rehearsal. Do not present it as a current live result or an ApexLabs exemption review.

## Answers to likely questions

- **Which AI?** RapidOCR uses local ONNX models for scans. Optional cloud evidence review uses the configured Gemini model, currently gemini-3.8-flash. The main field parser and five compliance checks are explicit Python rules.
- **What is agentic?** One bounded tool-using agent chooses searches/passages. Three read-only tool types; it is not a multi-agent system or autonomous award engine.
- **Why rules?** Explicit thresholds can be evaluated reproducibly; language-model advice can help inspect text and ambiguity. Both require validation and officer oversight.
- **Live registry verification?** No. GST/PAN checks are offline syntax/checksum/consistency checks. GSTN/Udyam/MCA/EPFO/CPPP connections remain future work.
- **Tamper-proof?** No. We compare stored bytes to their recorded SHA-256 before review/export and block a mismatch. The local baseline and event trail are not cryptographically protected or durable.
- **Complete evidence graph?** No. The graph contains generated check summaries. The new source viewer provides literal page-linked keyword candidates, not complete validated clause-to-evidence mapping.
- **Complete attachment audit?** No. Checklist attachments track receipt/readability separately; the rule audit still evaluates one submitted file at a time.
- **Production government use?** The demo uses synthetic data. Authenticated access, durable storage, approved hosting/data handling, broader rules and verified registry integrations are unfinished.

## Claims to correct in the presentation

Replace certified/legal dossier with prototype review report; fully autonomous procurement with officer decision support; live portal verification with offline identity checks; tamper-proof with active source-digest checks; complete SLA with warranty duration/service checks; fully air-gapped with local OCR/rules plus optional internet-dependent cloud review.

## Next engineering work

Persist the new evaluation IDs, frozen results, tender versions, source baselines and checklists in durable storage, then add authenticated officer permissions. Complete clause citations, vendor document bundles and broader validated rule coverage remain larger tasks. These are not implemented by this demo upgrade.
