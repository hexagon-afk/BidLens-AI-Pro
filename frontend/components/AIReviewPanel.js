import React, { useEffect, useRef, useState } from 'react';

export default function AIReviewPanel({ backendUrl, vendor, clause }) {
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

  const runReview = async () => {
    if (!consent || busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    const controller = new AbortController();
    requestController.current = controller;
    const timer = setTimeout(() => controller.abort(), 75000);
    try {
      const response = await fetch(`${backendUrl}/audit/agent/review/${encodeURIComponent(vendor.file_id)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify({ clause_id: clause.clause_id, cloud_consent: true,
          expected_status: clause.status, source_sha256: vendor.file_info?.source_sha256 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'AI review failed. Reload this audit and try again.');
      if (!data.advisory_only || data.status !== 'COMPLETED' || data.clause_id !== clause.clause_id || data.bid_id !== vendor.file_id) {
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

  return (
    <section aria-label="AI evidence review" style={{ padding: '16px', border: '1px solid var(--info-border)', borderRadius: '10px', background: 'var(--info-bg)', marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
        <strong style={{ color: 'var(--navy)', fontSize: '13px' }}>AI Evidence Review</strong>
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
      <button className="btn btn-navy" disabled={!consent || busy} onClick={runReview}>
        {busy ? 'Reviewing evidence…' : 'Run AI Evidence Review'}
      </button>
      {busy && <p role="status" style={{ fontSize: '12px' }}>Searching and inspecting evidence. This can take up to a minute.</p>}
      {error && <p role="alert" style={{ fontSize: '12px', color: 'var(--critical)', lineHeight: 1.5 }}>{error}</p>}
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
