# BidLens judges' demonstration walkthrough

This is a prototype demonstration using synthetic sample documents. Show what executes today and label future work accurately.

## Preparation

- Open http://127.0.0.1:3000/ in a full browser window. Keep both local server terminals running.
- Verify Settings points to http://127.0.0.1:8000. Confirm Backend Online.
- Configure Officer Profile with your name and a designation that identifies this as a demonstration. This profile is display metadata, not authenticated login.
- In New Evaluation, click Run Complete Sample Demo. Wait for the complete comparison matrix.
- Expected matrix: 1 compliant, 4 under review, 1 non-compliant across six independently evaluated documents.
- Expected tender thresholds: INR 50 lakh budget, INR 1 lakh EMD, 1.5 crore turnover, 50% local content and 3-year onsite warranty. Only duration and service location are evaluated for warranty; the full SLA is not verified.
- Do not restart the backend or refresh the frontend during the presentation: records are not yet durable and browser state resets. If needed, rerun the sample workflow.
- Before presenting, run one AI request. A real success is necessary to call the cloud service available at that moment. A configured key alone is not proof.

## Five-minute sequence

### 1. State the purpose (20 seconds)

Say: "BidLens helps procurement officers compare tender requirements with bidder evidence, identify clear shortfalls and locate unresolved claims. The officer retains the procurement decision."

### 2. Show the tender and baseline (40 seconds)

Open New Evaluation and point to the extracted EMD, turnover, local-content and warranty thresholds. Explain that these control the implemented checks.

Say: "The tender sets the thresholds. Missing or ambiguous evidence goes to review."

### 3. Show three different outcomes (40 seconds)

Use the comparison matrix:

- MegaTech PDF: five implemented checks pass. Say "meets these evaluated checks", not "guaranteed contract winner".
- GlobalCorp original PDF: five checks fail. Inspect the warranty or EMD rule explanation.
- ApexLabs PDF: three checks pass; turnover and EMD exemptions remain under review.

Say: "A claimed exemption does not establish entitlement. The system preserves uncertainty for the officer."

### 4. Demonstrate useful AI review (allow up to one minute)

Primary scenario, when successfully rehearsed: ApexLabs PDF -> View Details -> Earnest Money Deposit (EMD) -> cloud-processing checkbox -> Run AI Evidence Review.

Inspect the returned quotations, source pages, evidence gaps and officer questions. Expand Executed agent tools. The agent should inspect available tender and vendor passages. It cannot authenticate a certificate or access live government registries.

Say: "Gemini selects evidence-search and reading tools. The backend executes them read-only. The explanation helps the officer investigate the exemption claim; it does not apply an exemption automatically."

Do not promise specific wording or a specific assessment from a probabilistic model. The procurement verdict must remain unchanged.

Simpler live scenario: MegaTech PDF -> Warranty Duration & Service. A previous live rehearsal returned a real vendor quotation and preserved PASS. Rehearse again with the current provider before presenting it live.

### 5. Demonstrate the officer workflow (45 seconds)

ApexLabs EMD is unresolved. Show the mandatory justification box. A truthful demonstration note is:

"Demo review: an EMD exemption is claimed. Certificate authenticity, enterprise category and tender-specific eligibility remain unverified. Retain NEEDS_REVIEW pending officer verification."

Choose Mark REVIEW and record this note if demonstrating the event trail. Do not mark EXEMPT merely to make the dashboard green. If you actually confirm eligibility from appropriate evidence, document that real basis before changing the outcome.

Explain that stored event notes are locally appended; the trail is not cryptographically tamper-evident and the officer identity is not yet authenticated.

### 6. Export and close (30 seconds)

Download the audit PDF and show the source digest, verdict and recorded officer note. A SHA-256 digest identifies the submitted bytes; it does not authenticate the document. AI advice and tool traces are currently separate from this PDF.

Say: "The result is an evidence-supported review record for an officer, with explicit uncertainty and human oversight."

## If Gemini fails during the presentation

- A quota/rate limit is an external service failure; do not repeatedly click the button.
- Say: "The cloud review is currently unavailable. The local audit remains usable, and no verdict was changed. I will show a recorded successful rehearsal."
- Open docs/demo/RECORDED_GEMINI_DEMO.html in a browser. Its banner explicitly identifies it as recorded and it runs offline.
- The backup is the genuine saved MegaTech warranty review. It is not an ApexLabs exemption review and must not be presented as one.
- Continue with the deterministic results, source evidence and officer workflow.

## Answers to likely questions

Which LLM? "Google Gemini 3.8 Flash, called through the backend. The UI shows the actual configured model and returned tool trace."

Where is AI used? "RapidOCR uses local ONNX models for scans. Gemini performs optional cloud evidence review. The main field parser and compliance checks are explicit Python rules."

What is agentic? "One bounded tool-using agent selects searches and passages. It has three read-only tool types, up to six tool calls and five model turns. It is not a multi-agent system."

Why keep rules? "Explicit thresholds are evaluated reproducibly; language-model review helps inspect textual evidence and ambiguities. Both still need validation and officer oversight."

Does it verify GST/Udyam online? "No. Implemented identity checks are offline syntax/checksum checks. Live registries are future work."

Can government documents be sent to this cloud service? "This demo uses synthetic documents. Production deployment would require the department's approved hosting and data-handling arrangements."

What remains? "Durable versioned audits, authenticated officer permissions, complete requirement citations, vendor attachment bundles and broader rule coverage."

## Presentation wording to correct

- Replace "certified/legal audit dossier" with "prototype procurement review report".
- Replace "fully autonomous procurement" with "officer decision support with bounded AI evidence review".
- Replace "live portal verification" with "offline format/checksum checks; live registries planned".
- Replace "tamper-proof" with "SHA-256 source digest and local append-only decision events".
- Replace "complete SLA compliance" with "implemented warranty duration/service checks; full SLA coverage planned".
- Replace "fully air-gapped" with "local OCR and rules; optional cloud LLM review requires internet".
- Do not describe confidence/risk indices as calibrated probabilities or use the word certified for the prototype.

## Next code upgrade after the rehearsal

Persist versioned audits and officer decisions with unique evaluation IDs, so results survive restarts and re-evaluations remain distinguishable. Add authentication before public exposure. These are still unfinished; this walkthrough does not implement them.
