import React, { useEffect, useRef, useState } from 'react';

export default function SubmissionChecklist({ backendUrl, vendor }) {
  const [items, setItems] = useState([]);
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const alive = useRef(true);
  const input = useRef(null);
  const selectedItem = useRef(null);
  const auditId = vendor.evaluation_id || vendor.file_id;
  const url = `${backendUrl}/audit/checklist/${encodeURIComponent(auditId)}`;
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    fetch(url, { signal: controller.signal }).then(async response => { const value = await response.json(); if (!response.ok) throw new Error(value.detail || 'Checklist unavailable.'); return value; }).then(value => { if (alive.current) setItems(value.items); }).catch(e => { if (e.name !== 'AbortError' && alive.current) setError(e.message); }).finally(() => { if (alive.current) setLoading(false); });
    return () => { alive.current = false; controller.abort(); };
  }, [url]);
  const save = async next => {
    const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ items: next.map(item => ({ item_id: item.item_id, name: item.name, file_id: item.file_id || null })) }) });
    const value = await response.json();
    if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Checklist could not be saved.');
    if (alive.current) { setItems(value.items); setMessage(value.notice); }
  };
  const update = async next => { setBusy(true); setError(''); setMessage(''); try { await save(next); return true; } catch(e) { if (alive.current) setError(e.message); return false; } finally { if (alive.current) setBusy(false); } };
  const add = async () => { if (name.trim().length < 2) return; if (await update([...items, { item_id: `req_${Date.now()}`, name: name.trim(), file_id: null }])) setName(''); };
  const upload = async file => {
    if (!file || !selectedItem.current) return;
    const itemId = selectedItem.current;
    setBusy(true); setError(''); setMessage('');
    try {
      const body = new FormData(); body.append('file',file);
      const response = await fetch(`${backendUrl}/document/upload`, { method: 'POST', body });
      const value = await response.json();
      if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Attachment upload failed.');
      await save(items.map(item => item.item_id === itemId ? {...item,file_id:value.file_id} : item));
    } catch(e) { if (alive.current) setError(e.message); } finally { if (alive.current) setBusy(false); if (input.current) input.current.value = ''; }
  };
  return <section className="card" aria-label="Submission receipt checklist" style={{ marginBottom: 20 }}>
    <div className="card-header"><h3 style={{ fontSize: 14 }}>Submission completeness checklist</h3><span className="badge badge-neutral">Officer-defined</span></div>
    <div className="card-body">
      <p className="demo-help">Add the documents required by this tender for this bidder. Receipt and readability are tracked separately from compliance. These attachments are not merged into the rule audit. Session records reset when the backend restarts.</p>
      <div style={{ display:'flex',gap:8,flexWrap:'wrap',marginBottom:14 }}><input aria-label="Required document name" value={name} onChange={e => setName(e.target.value)} maxLength={120} placeholder="e.g. audited financial statement, if required" style={{ flex:1,minWidth:220,padding:10,border:'1px solid var(--border)',borderRadius:6 }} /><button className="btn btn-secondary" disabled={busy || loading || name.trim().length < 2 || items.length >= 20} onClick={add}>Add requirement</button></div>
      <input ref={input} type="file" style={{ display:'none' }} accept=".pdf,.docx,.xlsx,.csv,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.webp" onChange={e => upload(e.target.files?.[0])} />
      {loading && <p role="status" className="demo-help">Loading checklist…</p>}
      {error && <p role="alert" className="demo-error">{error}</p>}
      {message && <p role="status" className="demo-help">{message}</p>}
      {!loading && items.length === 0 && <p className="demo-help">No document requirements have been defined. This is not a completeness pass.</p>}
      {items.map(item => <div key={item.item_id} className="demo-checklist-row">
        <div style={{ flex:1,minWidth:180 }}><strong>{item.name}</strong><div className="demo-help" style={{ overflowWrap:'anywhere' }}>{item.filename || 'No file assigned'}</div></div>
        <span className={`badge ${item.receipt_status === 'MISSING' || item.receipt_status === 'NEEDS_INSPECTION' ? 'badge-warning' : 'badge-neutral'}`}>{item.receipt_status.replaceAll('_',' ')}</span>
        <button className="btn btn-secondary" disabled={busy} onClick={() => update(items.map(row => row.item_id === item.item_id ? {...row,file_id:vendor.document_id || vendor.file_id} : row))}>Use current bid</button>
        <button className="btn btn-secondary" disabled={busy} onClick={() => { selectedItem.current=item.item_id; input.current?.click(); }}>{item.file_id ? 'Replace attachment' : 'Upload attachment'}</button>
        <button className="btn btn-secondary" disabled={busy} aria-label={`Remove requirement ${item.name}`} onClick={() => update(items.filter(row => row.item_id !== item.item_id))}>Remove</button>
      </div>)}
      {busy && <p role="status" className="demo-help">Checking document receipt…</p>}
    </div>
  </section>;
}
