# BidLens demo baseline

This branch prioritizes correct, reviewable procurement checks. Optional Gemini cloud evidence review is implemented; it requires a server API key and explicit officer consent. Live provider execution must be rehearsed before presenting it as operational.

## Latest non-LLM demo workflow (3 October 2026)

- Each audit receives a unique evaluation ID, UTC timestamp and source digest. Machine results are frozen in memory; officer decisions remain separate. Versions still disappear on backend restart.
- Vendor Detail includes original tender/bid passages for the selected check. PDF page numbers come from extraction markers; other formats do not get invented pages. These are literal keyword candidates for inspection, not validated semantic clause mappings. The officer can open the original source, including when no passage is found.
- Re-evaluation links a new submission to the original evaluation ID. The backend rejects different tender criteria/source versions and compares five check families, changed extracted fields and source digests. The sample GlobalCorp revision changes five failed checks to five passes. Officer overrides cannot rewrite the original machine comparison.
- The officer can define up to 20 required documents and assign the current bid or upload attachments. MISSING, RECEIVED_UNVERIFIED and NEEDS_INSPECTION describe receipt/readability only. These files are not merged into compliance evaluation, and checklist receipt never grants a pass or exemption.
- Stored bid/tender/checklist bytes are rehashed before source inspection, revision comparison, officer decisions, model review and PDF export. Changed or missing sources block those operations with HTTP 409 and record a local integrity event; cached verdicts are not rewritten. Matching digests do not authenticate an issuer or make the trail tamper-proof.
- PDF export uses the selected evaluation ID and includes its timestamp, parent ID when present, officer decisions and the receipt checklist. Model advice remains separate.
- Verified locally: 125 backend tests passed; production frontend build passed. Six synthetic sample documents returned 1 COMPLIANT, 4 NEEDS_REVIEW and 1 NON_COMPLIANT. Linked GlobalCorp comparison changed five statuses. Both warranty sources returned literal passages; checklist statuses and evaluation ID appeared in the rendered PDF.
- No Gemini calls were made for these changes. Cloud review availability is not newly verified. Browser automation failed during tool initialization; manually check the new screens before presenting.

### Deployment and restart

The current frontend is https://bidlens-ai-prox.vercel.app/ and the backend is https://bidlens-ai-pro.onrender.com/. Deploy both from the same main commit. GET /audit/agent/config must include workflow_version=1; this is a deployment marker, not proof of model availability. Hard-refresh the frontend and rerun Run Complete Sample Demo after the backend deploys, because prior session evaluations no longer exist.

New read-only routes: /audit/evidence/{evaluation_id}/{clause_id}, /audit/source/{evaluation_id}/BID or TENDER, /audit/integrity/{evaluation_id}, /audit/comparison/{evaluation_id}. GET/POST /audit/checklist/{evaluation_id} manage receipt items. POST /audit/run accepts previous_evaluation_id for a linked revision. Original sources are downloadable by evaluation ID; these prototype routes do not add authentication or access control. Use only synthetic documents on the public demo.

## Run locally

Use two PowerShell terminals from the project root:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2
cd frontend
npm ci
npm run build
npm start -- --hostname 127.0.0.1
```

Open http://localhost:3000. The frontend defaults to the local backend when served on localhost.
The Settings backend URL overrides this default; clear any old hosted URL before a local rehearsal.
On Windows, RapidOCR/ONNX requires the Microsoft Visual C++ x64 runtime.

## Rehearsal

1. Open New Evaluation and click Run Complete Sample Demo, or load the tender and individual sample files manually. Results must come from the running backend.
2. MegaTech PDF should pass the five implemented checks against the sample tender.
3. GlobalCorp original PDF should fail five checks.
4. ApexLabs should require officer review for two claimed exemptions. A Udyam identifier alone does not prove eligibility. Only override after checking certificate/category and tender applicability, and record a real justification.
5. Inspect clause results, then apply a justified override. Verify counts, overall status, graph and shortlist refresh. Reset restores the original machine status.
6. Export the PDF. Check verdict, source hash and any officer justification. Export regenerates the report from the current cached result.
7. Re-evaluate GlobalCorp with the provided rectified sample. Its five implemented checks should pass.

Excel and Word attachments are evaluated independently. A missing field in a standalone attachment may correctly need review.
OCR-only documents provide candidate values for officer confirmation; their automated clause findings remain NEEDS_REVIEW. An unreadable scan or incomplete PDF extraction also remains NEEDS_REVIEW.

## What is implemented

- Server-parsed tender criteria control audits for loaded/uploaded tenders; conflicting client criteria return 409.
- Officer-supplied criteria remain supported for API use and are labeled as such.
- Five checks: GSTIN format/checksum, turnover, EMD amount/status, local-content threshold, warranty duration/service location.
- PASS, FAIL, EXEMPT, NOT_APPLICABLE and NEEDS_REVIEW states. Claimed exemptions require officer verification.
- Missing/ambiguous evidence and incomplete extraction do not produce invented passes.
- Source SHA-256, clause decision graph, heuristic review-risk index and recalculated officer decisions.
- Overrides are published only after the local event is persisted. Reset and clear retain the event history.
- No automatic substitution of cached sample success after network/API failures.

## AI statement for judges

Document OCR uses RapidOCR with local ONNX inference. The installed OCR configuration uses PP-OCRv4 detection/recognition models and a mobile text-orientation classifier. Tender and bid field parsing and compliance evaluation use explicit Python rules. Optional Gemini review uses the configured model (default gemini-3.8-flash) with search_evidence, read_evidence and get_clause_result tools. The model selects tools, the backend dispatches them read-only, and the final advice is validated against inspected excerpts. Up to 6 tool calls, 5 model turns and 60 seconds are allowed. It cannot change audit verdicts. Citation checking verifies source IDs and literal quotes, not legal correctness or the semantic truth of the explanation. There is no simulated fallback. A missing API key, quota error, timeout, invalid quote or changed audit fails explicitly.

## Limits to disclose

This is a demonstration baseline, not a production procurement deployment. There is no authenticated officer authorization or durable audit-result database. Audit results and tender registrations are held in process memory and disappear after restart. The JSONL event file is locally appended and is not cryptographically tamper-evident. Documents are not authenticated by their hash. Live GSTN/Udyam/MCA/EPFO/CPPP registries are not connected. Cross-document signals scan the contents of one submitted file; independently uploaded attachments are not merged into a vendor bundle. The graph links generated rule summaries and does not establish exact source-page citations for every clause. Numeric/negation parsing remains heuristic. Risk values are heuristic indices, not calibrated rejection probabilities. Only warranty duration and service location are implemented; complete SLA/MAF/technical conformity is not certified. Final eligibility, exemptions and award decisions require officer review.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm run build
npm audit
```

The regression suite isolates uploads, reports and decision logs in temporary directories. It exercises real sample PDFs and API override/reset/PDF flows, alongside controlled failure cases.

## Gemini configuration and rehearsal

1. Create a Gemini API key in Google AI Studio: https://aistudio.google.com/apikey.
2. Add GEMINI_API_KEY to backend/.env and GEMINI_MODEL=gemini-3.8-flash. Never put the key in NEXT_PUBLIC variables or commit it. The configuration is read on each request.
3. Install backend requirements. Run the local backend and rebuild/restart the frontend after code changes.
4. Run the sample tender audit. Open a vendor, select a requirement, acknowledge the cloud-processing notice and click Run AI Evidence Review.
5. Inspect the actual returned model, executed tools and literal quoted evidence. Confirm the audit verdict/counts remain unchanged.
6. Use only synthetic demo documents on the unpaid tier. Gemini's free-tier terms allow content use for product improvement. store=False prevents stored Interactions history; it is not a zero-retention or no-training guarantee.
7. Local OCR and rules can run without the cloud. This optional review requires internet; do not describe the full configured workflow as air-gapped.

GET /audit/agent/config reports model/configuration presence without exposing the key. POST /audit/agent/review/{bid_id} requires clause_id, cloud_consent=true, expected_status and source_sha256. Reviews are serialized to reduce free-tier bursts. Advice is not persisted or inserted into the official PDF. Evidence passages cite real extracted PDF page markers; Word/Excel/image passages show page unavailable rather than invented locations.

## Judges' walkthrough and recorded fallback

See DEMO_WALKTHROUGH.md for the click sequence, narration, honest answers and fallback. The rehearsal exposed real HTTP 429 rate/quota errors; a configured key does not guarantee service availability. An HTTP-response guard surfaces service errors before SDK Retry-After delays. Per-call and overall deadlines bound network waits. Reviews inspect both available source documents using combined passage reads and use low thinking effort for this bounded retrieval task. The offline file docs/demo/RECORDED_GEMINI_DEMO.html contains only a genuine recorded successful MegaTech warranty review and is visibly labelled as recorded.

## Final demo polish and verification (3 October 2026)

- UI labels describe implemented check outcomes rather than official eligibility or disqualification. Needs-review results retain their own status in search, the dashboard and re-evaluation.
- The officer profile is identified as display information; reports use manual sign-off and do not claim cryptographic signatures or authenticated officer identity.
- Prototype PDF titles, download names and officer acknowledgement wording no longer claim official certification.
- Six sample documents produce one compliant result, four under review and one non-compliant result.
- A synthetic MegaTech warranty decision changes five passes to four passes plus one review. Export includes the decision, justification and source digest. Reset restores five passes.
- Final approved Gemini check returned HTTP 429 in 3.4 seconds. Audit data remained unchanged. Do not promise live availability; retain the clearly labelled recorded successful review.
- Backend regressions: 100 passed. Targeted decision/PDF tests passed again after report layout corrections. Production frontend build passed.
- Browser automation was unavailable during the final pass because of a local tool setup error. Server responses and rendered PDF pages were checked directly; manually refresh the full browser and rerun Run Complete Sample Demo before presenting.

The synthetic officer-review report is docs/demo/demo-officer-review.pdf. The live sample cache is reset to its original results; the rehearsal decision and reset remain in the local event trail. This rehearsal did not publicly deploy the application.
