import React, { useEffect, useState } from 'react';

export default function SourceEvidencePanel({ backendUrl, vendor, clause }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const auditId = vendor.evaluation_id || vendor.file_id;
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError('');
    fetch(`${backendUrl}/audit/evidence/${encodeURIComponent(auditId)}/${encodeURIComponent(clause.clause_id)}`, { signal: controller.signal })
      .then(async response => { const value = await response.json(); if (!response.ok) throw new Error(value.detail || 'Source inspection failed.'); return value; })
      .then(setData).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, [backendUrl, auditId, clause.clause_id, refresh]);
  return <section aria-label="Original source evidence" className="source-evidence-panel">
    <div className="demo-section-heading"><strong>Inspect original evidence</strong><button className="btn btn-secondary" style={{ padding: '5px 9px', fontSize: 11 }} onClick={() => setRefresh(n => n + 1)}>Recheck source integrity</button></div>
    <p className="demo-help">Keyword-matched passages for officer inspection. A matching passage is not proof of authenticity or compliance.</p>
    {error && <p role="alert" className="demo-error">{error}</p>}
    {!data && !error && <p role="status" className="demo-help">Checking source bytes and locating passages…</p>}
    {data && <>
      <p className="demo-help"><strong>Source integrity:</strong> {data.integrity.status === 'UNCHANGED' ? 'Matches recorded bytes' : 'Baseline unavailable'} · {data.integrity.notice}</p>
      <div className="demo-source-grid">{data.sources.map(source => <div key={source.source} className="demo-source-card">
        <strong>{source.source === 'TENDER' ? 'Tender requirement source' : 'Vendor submission source'}</strong>
        <div className="demo-help" style={{ overflowWrap: 'anywhere' }}>{source.filename}</div>
        {source.original_available && <a href={`${backendUrl}/audit/source/${encodeURIComponent(auditId)}/${source.source}`} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>Open original document</a>}
        {source.extraction_complete === false && <p className="demo-error">Extraction is incomplete. Inspect the original document.</p>}
        {source.passages.length === 0 && <p className="demo-help">{source.text_available ? 'No matching extracted passage. This does not establish that the original lacks evidence.' : 'Extracted source text is unavailable. Inspect the original or confirm officer-supplied criteria.'}</p>}
        {source.passages.map(p => <div key={p.evidence_id} className="demo-passage">
          <div className="demo-help">{p.page ? `Page ${p.page}` : 'Page unavailable'} · {p.extraction_method === 'OCR' ? 'OCR text: confirm against the image' : 'Extracted text'} · Candidate passage</div>
          <blockquote style={{ whiteSpace: 'pre-wrap', margin: '7px 0', overflowWrap: 'anywhere' }}>{p.quote}</blockquote>
          <a href={`${backendUrl}/audit/source/${encodeURIComponent(auditId)}/${p.source}${p.page ? `#page=${p.page}` : ''}`} target="_blank" rel="noreferrer">{p.filename.toLowerCase().endsWith('.pdf') ? 'Open original PDF' : 'Download original document'}</a>
        </div>)}
      </div>)}</div>
    </>}
  </section>;
}
