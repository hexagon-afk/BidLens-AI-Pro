import React, { useEffect, useState } from 'react';
const tone = status => status === 'PASS' ? 'badge-pass' : status === 'FAIL' ? 'badge-fail' : status === 'EXEMPT' ? 'badge-exempt' : status === 'NEEDS_REVIEW' ? 'badge-warning' : 'badge-neutral';
const show = value => value == null ? 'Not extracted' : typeof value === 'object' ? JSON.stringify(value) : String(value);

export default function RevisionComparison({ backendUrl, result }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setError('');
    if (!result.evaluation_id || !result.parent_evaluation_id) { setError('Run the original evaluation, then submit its revision to create a linked comparison.'); return () => controller.abort(); }
    fetch(`${backendUrl}/audit/comparison/${encodeURIComponent(result.evaluation_id)}`, { signal: controller.signal })
      .then(async response => { const value = await response.json(); if (!response.ok) throw new Error(value.detail || 'Comparison unavailable.'); return value; })
      .then(setData).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => controller.abort();
  }, [backendUrl, result.evaluation_id, result.parent_evaluation_id]);
  return <section className="card" aria-label="Frozen evaluation comparison" style={{ marginBottom: 24 }}>
    <div className="card-header"><h3 style={{ fontSize: 15 }}>What changed in the revised submission?</h3><span className="badge badge-neutral">Frozen machine results</span></div>
    <div className="card-body">
      {error && <p role="alert" className="demo-error">{error}</p>}
      {!data && !error && <p role="status">Loading the source-checked comparison…</p>}
      {data && <>
        <p className="demo-help">{data.notice}</p>
        <p><strong>{data.changed_status_count} check statuses changed</strong> · {data.source_changed ? 'Different document bytes' : 'Same document bytes'}</p>
        {data.vendor_identity_changed && <p className="demo-error">Extracted vendor names differ. Confirm that the officer-linked documents belong to the same bidder.</p>}
        <div className="demo-source-grid">{['original','revised'].map(key => <div key={key} className="demo-source-card">
          <strong>{key === 'original' ? 'Original machine evaluation' : 'Revised machine evaluation'}</strong>
          <div>{data[key].overall_status.replaceAll('_',' ')}</div>
          <div className="demo-help" style={{ overflowWrap: 'anywhere' }}>{data[key].file_info.filename}</div>
          <div className="demo-help">{new Date(data[key].evaluated_at).toLocaleString()}</div>
          <details className="demo-help"><summary>Evaluation ID and source digest</summary><div style={{ overflowWrap: 'anywhere' }}>{data[key].evaluation_id}<br />{data[key].file_info.source_sha256}</div></details>
        </div>)}</div>
        <div style={{ overflowX: 'auto', marginTop: 16 }}><table className="data-table demo-comparison-table"><thead><tr><th>Requirement</th><th>Original</th><th>Revised</th><th>Change</th></tr></thead><tbody>{data.clauses.map(row => <tr key={row.check}>
          <td><strong>{row.check}</strong><details className="demo-help"><summary>Compare rule explanations</summary><p><strong>Original:</strong> {row.original_evidence || 'Not evaluated'}</p><p><strong>Revised:</strong> {row.revised_evidence || 'Not evaluated'}</p></details></td>
          <td><span className={`badge ${tone(row.original_status)}`}>{row.original_status.replaceAll('_',' ')}</span></td>
          <td><span className={`badge ${tone(row.revised_status)}`}>{row.revised_status.replaceAll('_',' ')}</span></td>
          <td>{row.status_changed ? 'Status changed' : row.evidence_changed ? 'Explanation changed' : 'No change'}</td>
        </tr>)}</tbody></table></div>
        <details style={{ marginTop: 14 }}><summary>Changed extracted fields ({data.changed_fields.length})</summary>{data.changed_fields.map(field => <p key={field.field} style={{ overflowWrap: 'anywhere', fontSize: 12 }}><strong>{field.field.replaceAll('_',' ')}:</strong> {show(field.original)} → {show(field.revised)}</p>)}</details>
      </>}
    </div>
  </section>;
}
