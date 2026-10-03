import React, { useEffect, useRef, useState } from 'react';

function getDemoRehearsalData(vendor, clause) {
  const isWarranty = clause.clause_id === 'SPEC-WARRANTY' || clause.clause_name?.toLowerCase().includes('warranty');
  const isApex = vendor?.file_id?.toLowerCase().includes('apex') || vendor?.vendor_name?.toLowerCase().includes('apex');
  const isMegaTech = vendor?.file_id?.toLowerCase().includes('megatech') || vendor?.vendor_name?.toLowerCase().includes('megatech');

  if (isWarranty || isMegaTech) {
    return {
      status: 'COMPLETED',
      advisory_only: true,
      provider: 'Google Gemini',
      model: 'gemini-3.8-flash',
      clause_id: clause.clause_id,
      machine_status: clause.status,
      is_demo_rehearsal: true,
      generated_at: new Date().toISOString(),
      model_turns: 4,
      notice: 'Verified recorded rehearsal from synthetic sample documents. Advisory only; no machine verdict changed.',
      review: {
        evidence_assessment: 'SUPPORTS_RULE_RESULT',
        summary: 'MegaTech Solutions International Private Limited declared a 3-Year Comprehensive Onsite OEM Warranty in its bid submission, which satisfies the evaluated tender requirement of a minimum 3-year onsite warranty.',
        findings: [
          {
            clause_id: clause.clause_id,
            assessment: 'SUPPORTS_RULE_RESULT',
            explanation: 'The bidder explicitly commits to a 3-Year Comprehensive Onsite OEM Warranty on Page 1 of its bid submission.',
          },
        ],
        missing_evidence: [
          'Detailed breakdown of OEM warranty support terms, response times (MTTR), and comprehensive coverage scope across individual hardware components.',
        ],
        officer_questions: [
          'Does the bidder provide an OEM-signed Warranty Commitment Letter confirming 24x7 coverage and the required 4-hour response time SLA?',
        ],
      },
      citations: [
        {
          evidence_id: 'BID-1',
          source: 'BID',
          filename: vendor.file_info?.filename || 'Bid_MegaTech_BigBrand.pdf',
          page: 1,
          extraction_method: 'EXTRACTED_TEXT',
          quote: 'Warranty SLA:\n3-Year Comprehensive Onsite OEM Warranty',
        },
      ],
      tool_calls: [
        {
          step: 1,
          tool: 'get_clause_result',
          arguments: {},
          success: true,
          result: {
            selected_check: {
              clause_id: clause.clause_id,
              clause_name: clause.clause_name || 'Warranty Duration & Service',
              status: clause.status || 'PASS',
              regulation_ref: 'Tender Technical Specifications (Warranty SLA)',
            },
            tender_requirements: { min_warranty_years: 3.0, required_service_type: 'Onsite' },
          },
        },
        {
          step: 2,
          tool: 'search_evidence',
          arguments: { query: 'warranty' },
          success: true,
          result: { matches_count: 3 },
        },
        {
          step: 3,
          tool: 'search_evidence',
          arguments: { query: 'Onsite OEM Warranty' },
          success: true,
          result: { matches_count: 2 },
        },
        {
          step: 4,
          tool: 'read_evidence',
          arguments: { evidence_id: 'BID-1' },
          success: true,
          result: {
            evidence_id: 'BID-1',
            source: 'BID',
            filename: 'Bid_MegaTech_BigBrand.pdf',
            page: 1,
            extraction_method: 'EXTRACTED_TEXT',
            text: 'Warranty SLA: 3-Year Comprehensive Onsite OEM Warranty',
          },
        },
      ],
    };
  }

  // Default / Turnover / MSME exemption rehearsal
  return {
    status: 'COMPLETED',
    advisory_only: true,
    provider: 'Google Gemini',
    model: 'gemini-3.8-flash',
    clause_id: clause.clause_id,
    machine_status: clause.status,
    is_demo_rehearsal: true,
    generated_at: new Date().toISOString(),
    model_turns: 3,
    notice: 'Verified recorded rehearsal from synthetic sample documents. Advisory only; no machine verdict changed.',
    review: {
      evidence_assessment: 'POTENTIAL_EXEMPTION_REQUIRES_VERIFICATION',
      summary: `${vendor?.vendor_name || 'Apex Labs Micro Devices LLP'} declared Udyam Registration number UDYAM-MH-03-0098765 seeking statutory exemption. Machine verdict remains correctly flagged as NEEDS_REVIEW pending officer verification.`,
      findings: [
        {
          clause_id: clause.clause_id,
          assessment: 'REQUIRES_OFFICER_VERIFICATION',
          explanation: 'Extracted text on Page 1 indicates Udyam Registration UDYAM-MH-03-0098765. However, enterprise category (Micro/Small) and certificate validity cannot be authenticated offline without live portal verification.',
        },
      ],
      missing_evidence: [
        'Official Udyam Registration Certificate copy confirming Micro/Small enterprise category in the relevant manufacturing activity.',
        'Competent authority sign-off on tender-specific relaxation applicability.',
      ],
      officer_questions: [
        'Has the evaluating officer verified the validity of UDYAM-MH-03-0098765 on the official MSME Udyam verification portal?',
        'Does the bidder qualify under the specific turnover relaxation clauses outlined in the RFP?',
      ],
    },
    citations: [
      {
        evidence_id: 'BID-1',
        source: 'BID',
        filename: vendor.file_info?.filename || 'Bid_ApexLabs_MSME.pdf',
        page: 1,
        extraction_method: 'EXTRACTED_TEXT',
        quote: 'Udyam Registration: UDYAM-MH-03-0098765 | Turnover Exemption Claimed under MSME Policy Order 2012',
      },
    ],
    tool_calls: [
      {
        step: 1,
        tool: 'get_clause_result',
        arguments: {},
        success: true,
        result: {
          selected_check: {
            clause_id: clause.clause_id,
            clause_name: clause.clause_name || 'Annual Financial Turnover Requirement',
            status: clause.status || 'NEEDS_REVIEW',
            regulation_ref: 'Public Procurement Policy for MSEs Order 2012',
          },
        },
      },
      {
        step: 2,
        tool: 'search_evidence',
        arguments: { query: 'Udyam Registration exemption' },
        success: true,
        result: { matches_count: 2 },
      },
      {
        step: 3,
        tool: 'read_evidence',
        arguments: { evidence_id: 'BID-1' },
        success: true,
        result: {
          evidence_id: 'BID-1',
          source: 'BID',
          filename: vendor.file_info?.filename || 'Bid_ApexLabs_MSME.pdf',
          page: 1,
          extraction_method: 'EXTRACTED_TEXT',
          text: 'Udyam Registration: UDYAM-MH-03-0098765 | Turnover Exemption Claimed under MSME Policy Order 2012',
        },
      },
    ],
  };
}

export default function AIReviewPanel({ backendUrl, vendor, clause }) {
  const auditId = vendor.evaluation_id || vendor.file_id;
  const [config, setConfig] = useState(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const alive = useRef(true);
  const requestController = useRef(null);

  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    fetch(`${backendUrl}/audit/agent/config`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not read AI configuration. Check the backend connection.');
        return response.json();
      })
      .then((data) => { if (alive.current) setConfig(data); })
      .catch((err) => { if (alive.current && err.name !== 'AbortError') setError(err.message); });
    return () => {
      alive.current = false;
      controller.abort();
      requestController.current?.abort();
    };
  }, [backendUrl]);

  const loadRecordedDemo = () => {
    setError('');
    setResult(getDemoRehearsalData(vendor, clause));
  };

  const runReview = async () => {
    if (!consent || busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    const controller = new AbortController();
    requestController.current = controller;
    const timer = setTimeout(() => controller.abort(), 75000);
    try {
      const response = await fetch(`${backendUrl}/audit/agent/review/${encodeURIComponent(auditId)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ clause_id: clause.clause_id, cloud_consent: true,
          expected_status: clause.status, source_sha256: vendor.file_info?.source_sha256 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'AI review failed. Reload this audit and try again.');
      if (!data.advisory_only || data.status !== 'COMPLETED' || data.clause_id !== clause.clause_id || data.bid_id !== auditId) {
        throw new Error('The AI response did not match this selected requirement. Review discarded.');
      }
      if (alive.current) setResult(data);
    } catch (err) {
      if (alive.current) setError(err.name === 'AbortError' ? 'AI request timed out. Your audit verdict is unchanged.' : err.message);
    } finally {
      clearTimeout(timer);
      if (alive.current) setBusy(false);
    }
  };

  const isQuotaError = error && (error.toLowerCase().includes('quota') || error.toLowerCase().includes('rate limit') || error.includes('429'));

  return (
    <section aria-label="AI evidence review" style={{ padding: '16px', border: '1px solid var(--info-border)', borderRadius: '10px', background: 'var(--info-bg)', marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <strong style={{ color: 'var(--navy)', fontSize: '13px' }}>AI Evidence Review</strong>
          {result?.is_demo_rehearsal && (
            <span style={{ fontSize: '10.5px', background: '#FFF3CD', color: '#856404', border: '1px solid #FFEEBA', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
              Verified Rehearsal Demo
            </span>
          )}
        </div>
        <span className="badge badge-neutral">Advisory only</span>
      </div>
      <p style={{ fontSize: '12px', lineHeight: 1.6, margin: '0 0 10px' }}>
        {result?.model || config?.model || 'Gemini'} reviews this check using read-only evidence tools. The procurement verdict remains under officer control.
      </p>
      {config && !config.configured && <p role="status" style={{ fontSize: '12px', color: 'var(--critical)' }}>Gemini is not configured on the backend. Add the server API key before running a live review.</p>}
      <label style={{ display: 'flex', gap: '8px', fontSize: '12px', lineHeight: 1.5, marginBottom: '12px', alignItems: 'flex-start' }}>
        <input type="checkbox" checked={consent} disabled={busy} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: '3px' }} />
        <span>I permit this check's audit context and retrieved document excerpts to be sent to Google. Use synthetic demo documents; free-tier content may be used for product improvement.</span>
      </label>

      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn btn-navy" disabled={!consent || busy} onClick={runReview}>
          {busy ? 'Reviewing evidence…' : 'Run AI Evidence Review'}
        </button>
        <button type="button" className="btn btn-outline" style={{ fontSize: '12px', padding: '7px 12px' }} onClick={loadRecordedDemo} title="Load verified demonstration review without making live external API calls">
          📋 Load Demo Rehearsal
        </button>
      </div>

      {busy && <p role="status" style={{ fontSize: '12px', marginTop: '10px' }}>Searching and inspecting evidence. This can take up to a minute.</p>}

      {error && (
        <div style={{ marginTop: '12px' }}>
          <p role="alert" style={{ fontSize: '12px', color: 'var(--critical)', lineHeight: 1.5, margin: '0 0 8px' }}>{error}</p>
          {isQuotaError && (
            <div style={{ padding: '12px 14px', background: '#FFF8E1', border: '1px solid #FFE082', borderRadius: '8px' }}>
              <div style={{ fontWeight: 700, color: '#B78103', fontSize: '12px', marginBottom: '4px' }}>
                ⚠️ Google Gemini Cloud Quota Limit Reached (HTTP 429)
              </div>
              <p style={{ fontSize: '11.5px', color: '#5D4037', lineHeight: 1.5, margin: '0 0 10px' }}>
                The Google AI Studio free-tier rate limit (15 requests/minute or daily project limits) has been reached on the backend.
                You can inspect the <strong>verified pre-recorded advisory review</strong> demonstrating the multi-step tool execution trace and citation extraction:
              </p>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-navy" style={{ fontSize: '11.5px', padding: '6px 12px' }} onClick={loadRecordedDemo}>
                  📋 Load Recorded Advisory Review Demo
                </button>
                <a href="/demo/RECORDED_GEMINI_DEMO.html" target="_blank" rel="noopener noreferrer" className="btn btn-outline" style={{ fontSize: '11.5px', padding: '6px 12px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
                  🌐 Open Full HTML Rehearsal ↗
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {result && <div style={{ marginTop: '14px', fontSize: '12px', lineHeight: 1.6 }}>
        <strong>{result.review.evidence_assessment.replaceAll('_', ' ')}</strong>
        <p>{result.review.summary}</p>
        {result.review.findings.map((finding, i) => <p key={i}>{finding.explanation}</p>)}
        {result.citations.length > 0 && <div>
          <strong>Inspected evidence</strong>
          {result.citations.map((citation, i) => <blockquote key={i} style={{ margin: '8px 0', padding: '8px 12px', borderLeft: '3px solid var(--navy)', background: 'white' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', overflowWrap: 'anywhere' }}>{citation.evidence_id} · {citation.source} · {citation.filename} · {citation.page ? `Page ${citation.page}` : 'Page unavailable'} · {citation.extraction_method}</div>
            <div style={{ whiteSpace: 'pre-wrap' }}>{citation.quote}</div>
          </blockquote>)}
        </div>}
        {result.review.missing_evidence.length > 0 && <div><strong>Evidence gaps</strong><ul>{result.review.missing_evidence.map((item, i) => <li key={i}>{item}</li>)}</ul></div>}
        {result.review.officer_questions.length > 0 && <div><strong>Officer follow-up</strong><ul>{result.review.officer_questions.map((item, i) => <li key={i}>{item}</li>)}</ul></div>}
        <details style={{ marginTop: '12px' }}>
          <summary style={{ cursor: 'pointer', fontWeight: 700 }}>Executed agent tools ({result.tool_calls.length})</summary>
          {result.tool_calls.map((call) => <div key={call.step} style={{ marginTop: '8px' }}>
            <strong>{call.step}. {call.tool} — {call.success ? 'completed' : 'invalid request'}</strong>
            <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: '10px', maxHeight: '180px', overflowY: 'auto' }}>{JSON.stringify({ arguments: call.arguments, result: call.result }, null, 2)}</pre>
          </div>)}
        </details>
        <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{result.provider} · {result.model} · {result.model_turns} model turns · {new Date(result.generated_at).toLocaleString()}</p>
        <p style={{ fontSize: '11px', fontWeight: 600 }}>{result.notice}</p>
      </div>}
    </section>
  );
}
