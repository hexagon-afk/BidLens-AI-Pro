import React, { useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import AIReviewPanel from '../components/AIReviewPanel';

const getBackendUrl = () => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('bidlens_backend_url');
    if (saved && saved.trim()) return saved.trim().replace(/\/+$/, '');
  }
  const localDefault = typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname) ? 'http://127.0.0.1:8000' : 'https://bidlens-ai-pro.onrender.com';
  return (process.env.NEXT_PUBLIC_BACKEND_URL || localDefault).trim().replace(/\/+$/, '');
};

const formatRequirement = (value) => value == null ? 'Unspecified — officer review required' : Number(value).toLocaleString('en-IN');

// These are outcomes of implemented checks, not formal procurement decisions.
const evaluationStatus = (bid) => bid?.overall_status || (bid?.is_compliant === true ? 'COMPLIANT' : 'NEEDS_REVIEW');
const evaluationLabel = (bid) => ({ COMPLIANT: 'Meets evaluated checks', NON_COMPLIANT: 'Non-compliant on evaluated checks', NEEDS_REVIEW: 'Needs review' }[evaluationStatus(bid)] || 'Not evaluated');
const evaluationTone = (bid) => evaluationStatus(bid) === 'COMPLIANT' ? 'success' : evaluationStatus(bid) === 'NON_COMPLIANT' ? 'critical' : 'warning';
const evaluationBadge = (bid) => evaluationStatus(bid) === 'COMPLIANT' ? 'badge-pass' : evaluationStatus(bid) === 'NON_COMPLIANT' ? 'badge-fail' : 'badge-warning';

export default function Home() {
  // Navigation State
  const [currentScreen, setCurrentScreen] = useState('dashboard'); // 'dashboard', 'new-evaluation', 'evaluations', 'vendor-detail', 're-evaluation', 'shortlist', 'rules', 'settings'

  // Data State - Clean initial states (zero preloading)
  const [tenderDocument, setTenderDocument] = useState(null);
  const [customRulesDocument, setCustomRulesDocument] = useState(null);
  const [addedVendors, setAddedVendors] = useState([]); // List of vendor items added in Screen 2
  const [bids, setBids] = useState([]); // Evaluated bids
  const [selectedVendor, setSelectedVendor] = useState(null);
  const [selectedEvidenceClause, setSelectedEvidenceClause] = useState(null);
  const [evidenceModalData, setEvidenceModalData] = useState(null);
  const [shortlistedVendors, setShortlistedVendors] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  // Per-Clause Officer Overrides & Mandatory Justifications (bidId -> { clauseId: { status, justification, ... } })
  const [officerOverrides, setOfficerOverrides] = useState({});
  const [clauseNotes, setClauseNotes] = useState({}); // { [clauseId]: text }
  const [selectedOverrideAction, setSelectedOverrideAction] = useState(null); // 'PASS', 'FAIL', 'EXEMPT'

  // Re-evaluation State (Interactive)
  const [reEvalSelectedVendor, setReEvalSelectedVendor] = useState(null);
  const [reEvalPreviousResult, setReEvalPreviousResult] = useState(null);
  const [reEvalResult, setReEvalResult] = useState(null);
  const reEvalFileInputRef = useRef(null);

  // Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const searchContainerRef = useRef(null);

  // Officer Profile State - Clean initial state (zero preloading)
  const [officerName, setOfficerName] = useState('');
  const [officerDesignation, setOfficerDesignation] = useState('');
  const [pendingPdfDownloadBidId, setPendingPdfDownloadBidId] = useState(null);
  const [settingsNotice, setSettingsNotice] = useState('');
  const [customBackendUrl, setCustomBackendUrl] = useState('');
  const [backendStatus, setBackendStatus] = useState('checking'); // 'online', 'offline', 'checking'
  const [backendLatency, setBackendLatency] = useState(null);
  const [isTestingBackend, setIsTestingBackend] = useState(false);

  // File input refs
  const tenderFileInputRef = useRef(null);
  const vendorFileInputRef = useRef(null);
  const rulesFileInputRef = useRef(null);

  // Close search dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setIsSearchOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const checkBackendHealth = async (overrideUrl, isRetry = false) => {
    const targetBase = overrideUrl !== undefined ? overrideUrl.trim().replace(/\/+$/, '') : getBackendUrl();
    setBackendStatus('checking');
    setIsTestingBackend(true);
    const startTime = Date.now();
    try {
      const target = targetBase ? `${targetBase}/system/health` : '/system/health';
      const controller = new AbortController();
      // Render free tier can take up to 45 seconds to wake up from sleep
      const id = setTimeout(() => controller.abort(), 45000);
      const res = await fetch(target, { signal: controller.signal });
      clearTimeout(id);
      if (res.ok) {
        setBackendStatus('online');
        setBackendLatency(Date.now() - startTime);
        return true;
      } else {
        if (!isRetry && targetBase) {
          // Retry once after 3 seconds in case server was spinning up
          setTimeout(() => checkBackendHealth(overrideUrl, true), 3000);
          return false;
        }
        setBackendStatus('offline');
        return false;
      }
    } catch (e) {
      if (!isRetry && targetBase) {
        // Retry once after 3 seconds in case server was spinning up
        setTimeout(() => checkBackendHealth(overrideUrl, true), 3000);
        return false;
      }
      setBackendStatus('offline');
      return false;
    } finally {
      setIsTestingBackend(false);
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('bidlens_backend_url') || '';
      setCustomBackendUrl(saved);
    }
    checkBackendHealth();
  }, []);

  // 1. Handle Tender RFP Upload from laptop
  const handleTenderUpload = async (file) => {
    if (!file) return;
    setIsUploading(true);
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    setStatusMessage(`Uploading and parsing Tender RFP: ${file.name} (${sizeMb} MB)...`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = getBackendUrl();
      const res = await fetch(`${apiUrl}/document/tender/upload`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload failed (${res.status})`);
      }

      const data = await res.json();
      setTenderDocument(data.tender_data);
      setStatusMessage(`Tender RFP '${file.name}' verified.`);
      setTimeout(() => setStatusMessage(''), 3500);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        setStatusMessage('Error: Upload timed out (60s). Cloud server may still be waking up. Please retry.');
      } else {
        setStatusMessage(`Error: ${err.message}`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  // Quick Load Pre-Packaged Tender RFP
  const handleLoadSampleTender = async () => {
    setIsUploading(true);
    setStatusMessage('Loading pre-packaged Sample Computer Tender RFP...');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${getBackendUrl()}/document/tender/sample`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error('Failed to load sample tender RFP');
      const data = await res.json();
      setTenderDocument(data.tender_data);
      setStatusMessage('Sample Tender RFP (GEM/2026/B/892100) loaded.');
      setTimeout(() => setStatusMessage(''), 3500);
    } catch (err) {
      setStatusMessage(`Error loading sample tender: ${err.message}. Please retry.`);
    } finally {
      setIsUploading(false);
    }
  };

  // Quick Load All Sample Vendor Bids
  const handleLoadAllSampleBids = async () => {
    setIsUploading(true);
    setStatusMessage('Loading all pre-packaged sample vendor proposals...');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${getBackendUrl()}/document/sample/vendor-bids`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error('Failed to load sample vendor bids');
      const data = await res.json();
      const sampleItems = data.vendor_bids.map((b) => ({
        file_id: b.file_id,
        filename: b.filename,
        file_type: b.file_type,
        vendor_name: b.extracted_summary?.vendor_name || b.filename,
        quote_inr: b.extracted_summary?.total_quote_inr,
        status: 'Ready for Audit'
      }));
      setAddedVendors(sampleItems);
      setStatusMessage(`Loaded ${sampleItems.length} sample vendor proposals.`);
      setTimeout(() => setStatusMessage(''), 3500);
    } catch (err) {
      setStatusMessage(`Error loading sample bids: ${err.message}. Please retry.`);
    } finally {
      setIsUploading(false);
    }
  };

  // Quick Load Single Sample Vendor
  const handleLoadSingleSampleVendor = async (sampleFilename) => {
    setIsUploading(true);
    setStatusMessage(`Loading sample file: ${sampleFilename}...`);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${getBackendUrl()}/document/sample/load/${encodeURIComponent(sampleFilename)}`, { method: 'POST', signal: controller.signal });
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error(`Failed to load ${sampleFilename}`);
      const data = await res.json();
      const newVendorItem = {
        file_id: data.file_id,
        filename: data.filename,
        file_type: data.file_type,
        vendor_name: data.extracted_summary?.vendor_name || data.filename,
        quote_inr: data.extracted_summary?.total_quote_inr,
        status: 'Ready for Audit'
      };
      setAddedVendors((prev) => {
        const filtered = prev.filter((v) => v.file_id !== data.file_id);
        return [...filtered, newVendorItem];
      });
      setStatusMessage(`Loaded sample: ${newVendorItem.vendor_name}`);
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (err) {
      setStatusMessage(`Error loading sample: ${err.message}. Please retry.`);
    } finally {
      setIsUploading(false);
    }
  };

  // 1-Click Complete Evaluation (RFP + All 4 Bids + Audit Execution)
  const handleOneClickCompleteEvaluation = async () => {
    setIsUploading(true);
    setStatusMessage('1-Click Audit: Loading RFP and all sample vendor bids...');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000);

      // 1. Load Tender RFP
      const tRes = await fetch(`${getBackendUrl()}/document/tender/sample`, { signal: controller.signal });
      if (!tRes.ok) throw new Error('Failed to load sample tender RFP');
      const tData = await tRes.json();
      setTenderDocument(tData.tender_data);

      // 2. Load Vendor Bids
      const vRes = await fetch(`${getBackendUrl()}/document/sample/vendor-bids`, { signal: controller.signal });
      if (!vRes.ok) throw new Error('Failed to load sample vendor bids');
      const vData = await vRes.json();
      const sampleItems = vData.vendor_bids.map((b) => ({
        file_id: b.file_id,
        filename: b.filename,
        file_type: b.file_type,
        vendor_name: b.extracted_summary?.vendor_name || b.filename,
        quote_inr: b.extracted_summary?.total_quote_inr,
        status: 'Ready for Audit'
      }));
      setAddedVendors(sampleItems);

      // 3. Run Audits
      setStatusMessage(`Auditing ${sampleItems.length} vendor bids against GFR 2017 & RFP rules...`);
      const evaluatedBids = [];
      for (const vendor of sampleItems) {
        try {
          const auditRes = await fetch(`${getBackendUrl()}/audit/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              file_id: vendor.file_id,
              tender_id: tData.tender_data.tender_id,
              tender_requirements: {
                budget_inr: tData.tender_data.budget_inr,
                min_turnover_cr: tData.tender_data.min_turnover_cr,
                emd_required_inr: tData.tender_data.emd_inr,
                min_local_content_pct: tData.tender_data.min_local_content_pct,
                min_warranty_years: tData.tender_data.min_warranty_years,
                required_service_type: tData.tender_data.required_service_type,
              }
            }),
            signal: controller.signal
          });
          if (!auditRes.ok) {
            const error = await auditRes.json().catch(() => ({}));
            throw new Error(error.detail || `Audit failed for ${vendor.filename} (${auditRes.status})`);
          }
          const auditData = await auditRes.json();
          if (!auditData.results) throw new Error(`Missing audit result for ${vendor.filename}`);
          auditData.results.file_id = vendor.file_id;
          evaluatedBids.push(auditData.results);
        } catch (singleAuditErr) {
          throw new Error(`${vendor.filename}: ${singleAuditErr.message}`);
        }
      }
      clearTimeout(timeoutId);

      if (evaluatedBids.length > 0) {
        setBids(evaluatedBids);
        setSelectedVendor(evaluatedBids[0]);
        setSelectedEvidenceClause(evaluatedBids[0].clause_level_decisions ? evaluatedBids[0].clause_level_decisions[0] : null);
        const compliantOnes = evaluatedBids.filter((b) => b?.is_compliant);
        setShortlistedVendors(compliantOnes);
        setStatusMessage(`1-Click Audit Complete! Evaluated ${evaluatedBids.length} vendors.`);
        setTimeout(() => setStatusMessage(''), 3500);
        setCurrentScreen('evaluations');
      } else {
        throw new Error('No vendor audits evaluated.');
      }
    } catch (err) {
      setBids([]);
      setShortlistedVendors([]);
      setSelectedVendor(null);
      setSelectedEvidenceClause(null);
      setStatusMessage(`Audit did not complete: ${err.message}. No substitute results were generated. Please retry.`);
    } finally {
      setIsUploading(false);
    }
  };

  // Quick Load Rectification in Screen 6
  const handleQuickLoadRectification = async () => {
    let target = reEvalSelectedVendor;
    if (!target) {
      target = bids.find((b) => b?.file_info?.vendor_name?.toLowerCase().includes('globalcorp')) || bids.find((b) => evaluationStatus(b) === 'NON_COMPLIANT') || bids[0];
      if (target) {
        setReEvalSelectedVendor(target);
        setReEvalPreviousResult(target);
      }
    }
    setIsUploading(true);
    setStatusMessage('Loading GlobalCorp Rectified Clarification Document...');
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);
      const res = await fetch(`${getBackendUrl()}/document/sample/load/Bid_GlobalCorp_Rectified_ReEvaluation.pdf`, { method: 'POST', signal: controller.signal });
      if (!res.ok) throw new Error('Failed to load rectified sample file');
      const data = await res.json();

      const auditRes = await fetch(`${getBackendUrl()}/audit/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_id: data.file_id,
          tender_id: tenderDocument?.tender_id || 'GEM/2026/B/892100',
          tender_requirements: tenderDocument ? {
            budget_inr: tenderDocument.budget_inr,
            min_turnover_cr: tenderDocument.min_turnover_cr,
            emd_required_inr: tenderDocument.emd_inr,
            min_local_content_pct: tenderDocument.min_local_content_pct,
            min_warranty_years: tenderDocument.min_warranty_years,
            required_service_type: tenderDocument.required_service_type,
          } : null
        }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!auditRes.ok) throw new Error('Re-evaluation audit failed');
      const auditData = await auditRes.json();
      if (auditData.results) {
        auditData.results.file_id = data.file_id;
        setReEvalResult(auditData.results);
        setStatusMessage('Rectified clarification audited successfully! Inspect before-and-after comparison.');
        setTimeout(() => setStatusMessage(''), 4000);
      }
    } catch (err) {
      setReEvalResult(null);
      setStatusMessage(`Re-evaluation failed: ${err.message}. Please retry.`);
    } finally {
      setIsUploading(false);
    }
  };

  // 2. Upload Custom Rules / Policy Document (Directly in Rules screen - Roadmap Phase 2)
  const handleCustomRulesUpload = (file) => {
    if (!file) return;
    setCustomRulesDocument({
      filename: file.name,
      uploadedAt: new Date().toLocaleTimeString(),
      isRoadmap: true,
      rulesList: [
        { id: 'CUSTOM-01', name: 'Uploaded Statutory Framework (' + file.name + ') [Phase 2 Roadmap]', text: 'Policy filename selected locally. Policy import and compilation are not implemented. Prototype applies its existing checks (GFR 2017 & MII Order 2017).' },
        { id: 'GFR-149', name: 'GFR 2017 Rule 149 — GeM Portal & Valid GSTIN Verification', text: 'Mandates active GSTIN verification against GSTN common portal with Modulus-36 checksum.' },
        { id: 'GFR-160', name: 'Tender Financial Criteria / GFR 2017 Rule 173 — Exemption Review', text: 'Evaluate tender turnover criteria; claimed exemptions require officer verification.' },
        { id: 'GFR-170', name: 'GFR 2017 Rule 170 — Earnest Money Deposit (EMD) Guarantee', text: 'Mandatory EMD Bank Guarantee with verified MSE waiver.' },
        { id: 'MII-2017', name: 'Make in India Order 2017 — Minimum Local Content Preference', text: 'Requires >= 50% local domestic value addition for Class-1 suppliers.' }
      ]
    });
    setStatusMessage(`Custom policy filename '${file.name}' selected locally; file contents were not imported (Custom dynamic rule compiler is scheduled for Phase 2; running on active GFR 2017 & MII 2017 baseline).`);
    setTimeout(() => setStatusMessage(''), 5000);
  };

  // 3. Add a vendor proposal file from laptop to queue
  const handleAddVendorFile = async (file) => {
    if (!file) return;
    setIsUploading(true);
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    setStatusMessage(`Uploading vendor proposal: ${file.name} (${sizeMb} MB)...`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = getBackendUrl();
      const res = await fetch(`${apiUrl}/document/upload`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload failed (${res.status})`);
      }

      const data = await res.json();
      const newVendorItem = {
        file_id: data.file_id,
        filename: file.name,
        file_type: data.file_type,
        vendor_name: data.extracted_summary?.vendor_name || file.name,
        quote_inr: data.extracted_summary?.total_quote_inr,
        status: 'Ready for Audit'
      };

      setAddedVendors((prev) => {
        const filtered = prev.filter((v) => v.file_id !== data.file_id);
        return [...filtered, newVendorItem];
      });

      setStatusMessage(`Added vendor: ${newVendorItem.vendor_name}`);
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        setStatusMessage('Error: Upload timed out (60s). Please retry or check backend connection.');
      } else {
        setStatusMessage(`Error: ${err.message}`);
      }
    } finally {
      setIsUploading(false);
    }
  };

  // 4. Remove a vendor from queue
  const handleRemoveVendor = (fileId) => {
    setAddedVendors(addedVendors.filter((v) => v.file_id !== fileId));
  };

  // 5. Execute full evaluation of all added vendors against tender RFP
  const handleStartEvaluation = async () => {
    if (!tenderDocument) {
      alert('Please upload a Tender RFP document first.');
      return;
    }
    if (addedVendors.length === 0) {
      alert('Please add at least one vendor proposal file to evaluate.');
      return;
    }

    setIsUploading(true);
    setStatusMessage(`Running GFR compliance audit across ${addedVendors.length} vendor submissions...`);
    try {
      const evaluatedBids = [];
      for (const vendor of addedVendors) {
        const auditRes = await fetch(`${getBackendUrl()}/audit/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
          file_id: vendor.file_id,
          tender_id: tenderDocument.tender_id,
          tender_requirements: {
            budget_inr: tenderDocument.budget_inr,
            min_turnover_cr: tenderDocument.min_turnover_cr,
            emd_required_inr: tenderDocument.emd_inr,
            min_local_content_pct: tenderDocument.min_local_content_pct,
            min_warranty_years: tenderDocument.min_warranty_years,
            required_service_type: tenderDocument.required_service_type,
          }
        }),
        });

        if (!auditRes.ok) {
          const error = await auditRes.json().catch(() => ({}));
          throw new Error(error.detail || `Audit failed for ${vendor.filename} (${auditRes.status})`);
        }
        const auditData = await auditRes.json();
        if (!auditData.results) throw new Error(`Missing audit result for ${vendor.filename}`);
        auditData.results.file_id = vendor.file_id;
        evaluatedBids.push(auditData.results);
      }

      if (evaluatedBids.length > 0) {
        setBids(evaluatedBids);
        setSelectedVendor(evaluatedBids[0]);
        setSelectedEvidenceClause(evaluatedBids[0].clause_level_decisions ? evaluatedBids[0].clause_level_decisions[0] : null);

        // Auto shortlist compliant vendors
        const compliantOnes = evaluatedBids.filter((b) => b?.is_compliant);
        setShortlistedVendors(compliantOnes);

        setStatusMessage(`Evaluation complete for ${evaluatedBids.length} vendors.`);
        setTimeout(() => setStatusMessage(''), 3000);
        setCurrentScreen('evaluations');
      } else {
        throw new Error('No bids could be evaluated.');
      }
    } catch (err) {
      setStatusMessage(`Error during evaluation: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // 6. Handle Per-Clause Officer Decision Override with Mandatory Written Note
  const handleApplyClauseOverride = async (clause, newStatus) => {
    if (!selectedVendor) return;
    const clauseId = clause.clause_id;
    const note = clauseNotes[clauseId] ? clauseNotes[clauseId].trim() : '';

    if (!note || note.length < 5) {
      alert('Mandatory Justification Required: You must write an official explanation (minimum 5 characters) for why you are changing this statutory decision.');
      return;
    }

    try {
      const res = await fetch(`${getBackendUrl()}/audit/clause-override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bid_id: selectedVendor.file_id,
          clause_id: clauseId,
          clause_name: clause.clause_name,
          original_status: clause.status,
          new_status: newStatus,
          justification: note,
          officer_name: officerName || 'Procurement Officer'
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save override');
      }

      const data = await res.json().catch(() => ({}));

      // Update local state for overrides
      const overrideRecord = {
        clause_id: clauseId,
        clause_name: clause.clause_name,
        original_status: clause.status,
        status: newStatus,
        justification: note,
        timestamp: new Date().toLocaleString()
      };

      setOfficerOverrides((prev) => {
        const vOverrides = prev[selectedVendor.file_id] || {};
        return {
          ...prev,
          [selectedVendor.file_id]: {
            ...vOverrides,
            [clauseId]: overrideRecord
          }
        };
      });

      // Update with recomputed audit_result from backend
      const updated = data.audit_result || data.results;
      if (updated) {
        updated.file_id = selectedVendor.file_id;
        setSelectedVendor(updated);
        setSelectedEvidenceClause(updated.clause_level_decisions?.find((c) => c.clause_id === clauseId) || { ...clause, status: newStatus });
        setBids((prev) => {
          const nextBids = prev.map((b) => (b.file_id === selectedVendor.file_id ? updated : b));
          const compliantOnes = nextBids.filter((b) => b?.is_compliant);
          setShortlistedVendors(compliantOnes);
          return nextBids;
        });
      } else {
        // Fallback manual clause update
        const updatedClauses = (selectedVendor.clause_level_decisions || []).map((c) => {
          if (c.clause_id === clauseId) {
            return { ...c, status: newStatus, is_overridden: true, override_note: note };
          }
          return c;
        });

        const updatedVendor = { ...selectedVendor, clause_level_decisions: updatedClauses };
        setSelectedVendor(updatedVendor);
        setSelectedEvidenceClause(updatedClauses.find((c) => c.clause_id === clauseId));
        setBids((prev) => prev.map((b) => (b.file_id === selectedVendor.file_id ? updatedVendor : b)));
      }

      alert(`Decision updated to ${newStatus} with recorded justification! This has been logged and will appear in the supervisory log in the exported audit PDF.`);
    } catch (e) {
      alert(`Error saving decision override: ${e.message}`);
    }
  };

  // Reset Overrides for Current Vendor or All Vendors
  const handleResetVendorOverrides = async (vendor) => {
    const v = vendor || selectedVendor;
    if (!v) return;
    try {
      const resetRes = await fetch(`${getBackendUrl()}/audit/overrides/reset/${encodeURIComponent(v.file_id)}`, { method: 'POST' });
      const resetData = await resetRes.json().catch(() => ({}));
      setOfficerOverrides((prev) => {
        const next = { ...prev };
        delete next[v.file_id];
        return next;
      });

      if (resetData.results || resetData.audit_result) {
        const freshVendor = resetData.results || resetData.audit_result;
        freshVendor.file_id = v.file_id;
        setBids((prev) => {
          const nextBids = prev.map((b) => (b.file_id === v.file_id ? freshVendor : b));
          const compliantOnes = nextBids.filter((b) => b?.is_compliant);
          setShortlistedVendors(compliantOnes);
          return nextBids;
        });
        if (selectedVendor && selectedVendor.file_id === v.file_id) {
          setSelectedVendor(freshVendor);
          setSelectedEvidenceClause(freshVendor.clause_level_decisions ? freshVendor.clause_level_decisions[0] : null);
        }
      } else {
        // Fallback re-run fresh automated audit
        const auditRes = await fetch(`${getBackendUrl()}/audit/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_id: v.file_id,
            tender_id: tenderDocument?.tender_id || 'GEM/2026/B/892100',
            tender_requirements: tenderDocument ? {
              budget_inr: tenderDocument.budget_inr,
              min_turnover_cr: tenderDocument.min_turnover_cr,
              emd_required_inr: tenderDocument.emd_inr,
              min_local_content_pct: tenderDocument.min_local_content_pct,
              min_warranty_years: tenderDocument.min_warranty_years,
            required_service_type: tenderDocument.required_service_type,
            } : null
          }),
        });
        if (auditRes.ok) {
          const auditData = await auditRes.json();
          const freshVendor = auditData.results;
          freshVendor.file_id = v.file_id;
          setBids((prev) => {
            const nextBids = prev.map((b) => (b.file_id === v.file_id ? freshVendor : b));
            const compliantOnes = nextBids.filter((b) => b?.is_compliant);
            setShortlistedVendors(compliantOnes);
            return nextBids;
          });
          if (selectedVendor && selectedVendor.file_id === v.file_id) {
            setSelectedVendor(freshVendor);
            setSelectedEvidenceClause(freshVendor.clause_level_decisions ? freshVendor.clause_level_decisions[0] : null);
          }
        }
      }
      alert(`All test overrides for ${v.vendor_name || 'this vendor'} have been cleared! Fresh audit restored.`);
    } catch (e) {
      alert(`Error resetting overrides: ${e.message}`);
    }
  };

  const handleResetAllOverrides = async () => {
    try {
      await fetch(`${getBackendUrl()}/audit/overrides/clear`, { method: 'POST' });
      setOfficerOverrides({});
      setClauseNotes({});
      alert('All test overrides have been completely cleared across all vendors!');
    } catch (e) {
      alert(`Error clearing overrides: ${e.message}`);
    }
  };

  // 7. Interactive Re-evaluation of a Vendor with Rectification File
  const handleSelectVendorForReEval = (vendor) => {
    setReEvalSelectedVendor(vendor);
    setReEvalPreviousResult(vendor);
    setReEvalResult(null);
    setCurrentScreen('re-evaluation');
  };

  const handleUploadRectificationFile = async (file) => {
    if (!file) return;
    setIsUploading(true);
    setStatusMessage(`Uploading and auditing rectification file: ${file.name}...`);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const upRes = await fetch(`${getBackendUrl()}/document/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!upRes.ok) throw new Error('Failed to upload rectification file');
      const upData = await upRes.json();
      const fileId = upData.file_id;

      const auditRes = await fetch(`${getBackendUrl()}/audit/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
        file_id: fileId,
        tender_id: tenderDocument?.tender_id || 'GEM/2026/B/892100',
        tender_requirements: tenderDocument ? {
          budget_inr: tenderDocument.budget_inr,
          min_turnover_cr: tenderDocument.min_turnover_cr,
          emd_required_inr: tenderDocument.emd_inr,
          min_local_content_pct: tenderDocument.min_local_content_pct,
          min_warranty_years: tenderDocument.min_warranty_years,
            required_service_type: tenderDocument.required_service_type,
        } : null
      }),
      });

      if (!auditRes.ok) throw new Error('Audit on rectification file failed');
      const auditData = await auditRes.json();
      const newResult = auditData.results;
      newResult.file_id = fileId;

      setReEvalResult(newResult);
      setStatusMessage(`Rectification audit complete for ${file.name}`);
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (e) {
      setStatusMessage(`Error: ${e.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleApplyReEvaluationToMatrix = () => {
    if (!reEvalResult || !reEvalSelectedVendor) return;
    setBids((prev) => prev.map((b) => (b.file_id === reEvalSelectedVendor.file_id ? reEvalResult : b)));
    setSelectedVendor(reEvalResult);
    if (reEvalResult.is_compliant) {
      setShortlistedVendors((prev) => [...prev.filter((v) => v.file_id !== reEvalSelectedVendor.file_id), reEvalResult]);
    }
    alert('Re-evaluated result successfully updated in the Comparison Matrix!');
    setCurrentScreen('evaluations');
  };

  // Handle PDF Download with Officer Credentials Check
  const handleDownloadPdf = (bidId) => {
    if (!officerName.trim() || !officerDesignation.trim()) {
      setPendingPdfDownloadBidId(bidId);
      setSettingsNotice('Please enter your Officer Full Name and Designation in Officer Profile before generating the prototype procurement review report.');
      setCurrentScreen('settings');
    } else {
      const url = `${getBackendUrl()}/audit/report/pdf/${bidId}?officer_name=${encodeURIComponent(officerName)}&officer_designation=${encodeURIComponent(officerDesignation)}`;
      window.open(url, '_blank');
    }
  };

  const handleSaveOfficerSettings = () => {
    if (!officerName.trim()) {
      alert('Please enter your Officer Full Name.');
      return;
    }
    if (!officerDesignation.trim()) {
      alert('Please enter your Official Designation / Committee.');
      return;
    }
    alert('Officer profile details saved for this session. Prototype reports include a manual sign-off box. This is not authenticated login.');
    setSettingsNotice('');
    if (pendingPdfDownloadBidId) {
      const url = `${getBackendUrl()}/audit/report/pdf/${pendingPdfDownloadBidId}?officer_name=${encodeURIComponent(officerName)}&officer_designation=${encodeURIComponent(officerDesignation)}`;
      window.open(url, '_blank');
      setPendingPdfDownloadBidId(null);
    }
  };

  // Toggle Shortlist for a vendor
  const handleToggleShortlist = (vendor) => {
    if (!vendor) return;
    const exists = shortlistedVendors.some((v) => v.file_id === vendor.file_id);
    if (exists) {
      setShortlistedVendors(shortlistedVendors.filter((v) => v.file_id !== vendor.file_id));
    } else {
      setShortlistedVendors([...shortlistedVendors, vendor]);
    }
  };

  // Dynamic Search Results
  const getSearchResults = () => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase().trim();
    const results = [];

    bids.forEach((b) => {
      const vName = b?.file_info?.vendor_name || '';
      const fName = b?.file_info?.filename || '';
      const gstin = b?.branch_a_extracted_data?.gstin || '';
      const pan = b?.branch_a_extracted_data?.pan || '';
      const warranty = b?.branch_a_extracted_data?.warranty || '';

      if (
        vName.toLowerCase().includes(q) ||
        fName.toLowerCase().includes(q) ||
        gstin.toLowerCase().includes(q) ||
        pan.toLowerCase().includes(q) ||
        warranty.toLowerCase().includes(q)
      ) {
        results.push({
          type: 'VENDOR',
          title: vName,
          subtitle: `File: ${fName} | GSTIN: ${gstin || 'N/A'} | Status: ${evaluationLabel(b)}`,
          badge: evaluationLabel(b),
          badgeClass: evaluationBadge(b),
          action: () => {
            setSelectedVendor(b);
            setSelectedEvidenceClause(b?.clause_level_decisions ? b.clause_level_decisions[0] : null);
            setCurrentScreen('vendor-detail');
            setIsSearchOpen(false);
          }
        });
      }
    });

    const statutoryRules = [
      { id: 'GFR-149', name: 'GFR Rule 149 - GeM Procurement & GSTIN Validity', text: 'Offline GSTIN syntax and checksum checks. Live GSTN registration remains unverified.' },
      { id: 'GFR-160', name: 'Tender Financial Criteria / GFR 2017 Rule 173 - Exemption Review', text: 'Tender-specific relaxation and exemption eligibility require officer verification.' },
      { id: 'GFR-170', name: 'GFR Rule 170 - Earnest Money Deposit (EMD)', text: 'EMD is compared with the active tender amount. Claimed exemptions require officer verification.' },
      { id: 'MII-2017', name: 'Make in India Order 2017 - Local Content Preference', text: 'Requires minimum 50% domestic value addition for Class-1 suppliers.' }
    ];

    statutoryRules.forEach((r) => {
      if (r.id.toLowerCase().includes(q) || r.name.toLowerCase().includes(q) || r.text.toLowerCase().includes(q)) {
        results.push({
          type: 'RULE',
          title: r.name,
          subtitle: r.text,
          badge: r.id,
          badgeClass: 'badge-exempt',
          action: () => {
            setCurrentScreen('rules');
            setIsSearchOpen(false);
          }
        });
      }
    });

    if ('gem/2026/b/892100'.includes(q) || 'desktop'.includes(q) || 'workstation'.includes(q) || 'computer'.includes(q)) {
      results.push({
        type: 'TENDER',
        title: 'GEM/2026/B/892100 — Workstation Desktops (100 Units)',
        subtitle: 'Budget: INR 50.00 Lakhs | EMD: INR 1.00 Lakh | Turnover: INR 1.50 Cr',
        badge: 'ACTIVE TENDER',
        badgeClass: 'badge-pass',
        action: () => {
          setCurrentScreen('evaluations');
          setIsSearchOpen(false);
        }
      });
    }

    return results;
  };

  const searchResults = getSearchResults();

  // True Value-for-Money Spotlight
  const compliantBids = bids.filter((b) => b?.is_compliant);
  const bestValueBid = compliantBids.sort((a, b) => {
    const pA = a?.value_spotlight?.quoted_price_inr || 99999999;
    const pB = b?.value_spotlight?.quoted_price_inr || 99999999;
    return pA - pB;
  })[0] || bids[0];

  return (
    <div className="app-layout">
      <Head>
        <title>BidLens — Government Procurement AI Co-Pilot</title>
      </Head>

      {/* ── 1. LEFT VERTICAL SIDEBAR ────────────────────────────── */}
      <aside className="sidebar">
        <div>
          {/* Brand Header */}
          <div style={{ padding: '20px 18px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid var(--border)' }}>
            <img
              src="/logo.jpg"
              alt="BidLens Logo"
              style={{ width: '34px', height: '34px', borderRadius: '8px', objectFit: 'cover' }}
            />
            <div>
              <div style={{ fontSize: '17px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.3px' }}>
                BidLens
              </div>
              <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', fontWeight: 500 }}>
                Procurement Intelligence
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <button
              className={`nav-item ${currentScreen === 'dashboard' ? 'active' : ''}`}
              onClick={() => setCurrentScreen('dashboard')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              Dashboard
            </button>

            <button
              className={`nav-item ${currentScreen === 'new-evaluation' ? 'active' : ''}`}
              onClick={() => setCurrentScreen('new-evaluation')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
              New Evaluation
            </button>

            <button
              className={`nav-item ${currentScreen === 'evaluations' ? 'active' : ''}`}
              onClick={() => setCurrentScreen('evaluations')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              Evaluations ({bids.length})
            </button>

            <button
              className={`nav-item ${currentScreen === 'vendor-detail' ? 'active' : ''}`}
              onClick={() => {
                if (selectedVendor) setCurrentScreen('vendor-detail');
                else if (bids.length > 0) {
                  setSelectedVendor(bids[0]);
                  setCurrentScreen('vendor-detail');
                } else {
                  alert('No evaluated vendors yet. Please start an evaluation from "New Evaluation" screen.');
                }
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Vendor Detail
            </button>

            <button
              className={`nav-item ${currentScreen === 're-evaluation' ? 'active' : ''}`}
              onClick={() => {
                setReEvalSelectedVendor(null);
                setReEvalResult(null);
                setCurrentScreen('re-evaluation');
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
              Re-evaluation
            </button>

            <button
              className={`nav-item ${currentScreen === 'shortlist' ? 'active' : ''}`}
              onClick={() => setCurrentScreen('shortlist')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              Shortlist ({shortlistedVendors.length})
            </button>

            <button
              className={`nav-item ${currentScreen === 'rules' ? 'active' : ''}`}
              onClick={() => setCurrentScreen('rules')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
              Rules &amp; GFR
            </button>

            <button
              className={`nav-item ${currentScreen === 'settings' ? 'active' : ''}`}
              onClick={() => setCurrentScreen('settings')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              Officer Profile
            </button>
          </nav>
        </div>

        {/* Bottom Officer Profile Card */}
        <div
          style={{ padding: '14px 16px', borderTop: '1px solid var(--border)', backgroundColor: '#FAFAFA', cursor: 'pointer' }}
          onClick={() => setCurrentScreen('settings')}
          title="Click to configure Officer Name & Designation"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '34px', height: '34px', borderRadius: '50%', backgroundColor: officerName ? 'var(--gold)' : 'var(--bg-stone)', color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '13px' }}>
              {officerName ? officerName.split(' ').map((n) => n[0]).join('').slice(0, 2) : '?'}
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--navy)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {officerName || 'Set Officer Profile'}
              </div>
              <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                {officerDesignation || 'Click to set officer details'}
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── 2. MAIN APPLICATION CONTENT ─────────────────────────── */}
            <main className="main-content">
        {/* Prototype Transparency Banner */}
        <div style={{ backgroundColor: '#FEF3C7', borderBottom: '1px solid #F59E0B', padding: '7px 20px', fontSize: '11.5px', color: '#92400E', display: 'flex', alignItems: 'center', justifyContent: 'space-between', zIndex: 10 }}>
          <span><strong>PROTOTYPE DEMONSTRATION MODE:</strong> Deterministic evaluation against active tender criteria. External government registry checks are running in offline syntax/checksum verification mode.</span>
          <span style={{ fontSize: '10px', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.5px', backgroundColor: '#FDE68A', padding: '2px 8px', borderRadius: '4px', color: '#78350F' }}>Sandbox Demo</span>
        </div>
        {/* Top Header Active Search Bar with Live Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', gap: '16px' }}>
          <div ref={searchContainerRef} style={{ position: 'relative', flex: 1, maxWidth: '520px' }}>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                placeholder="Search vendors, GSTIN, GFR rules, tender terms..."
                value={searchQuery}
                onFocus={() => setIsSearchOpen(true)}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsSearchOpen(true);
                }}
                style={{
                  width: '100%',
                  padding: '9px 34px 9px 36px',
                  borderRadius: '8px',
                  border: isSearchOpen && searchQuery ? '1.5px solid var(--navy)' : '1px solid var(--border)',
                  backgroundColor: '#FFFFFF',
                  fontSize: '13px',
                  outline: 'none',
                  boxShadow: isSearchOpen && searchQuery ? '0 4px 12px rgba(13, 27, 61, 0.08)' : 'none',
                }}
              />
              <svg style={{ position: 'absolute', left: '12px', top: '11px', color: 'var(--text-muted)' }} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>

              {searchQuery && (
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setIsSearchOpen(false);
                  }}
                  style={{ position: 'absolute', right: '10px', top: '9px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '14px', fontWeight: 700 }}
                >
                  ✕
                </button>
              )}
            </div>

            {/* Live Search Results Dropdown */}
            {isSearchOpen && searchQuery.trim() && (
              <div
                style={{
                  position: 'absolute',
                  top: '44px',
                  left: 0,
                  right: 0,
                  backgroundColor: '#FFFFFF',
                  borderRadius: '10px',
                  border: '1px solid var(--border)',
                  boxShadow: '0 10px 25px rgba(13, 27, 61, 0.12)',
                  zIndex: 50,
                  maxHeight: '380px',
                  overflowY: 'auto',
                  padding: '6px',
                }}
              >
                <div style={{ padding: '8px 12px', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', borderBottom: '1px solid var(--border-light)' }}>
                  Search Results ({searchResults.length})
                </div>

                {searchResults.length === 0 ? (
                  <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12.5px' }}>
                    No matching vendors, rules, or tenders found for "{searchQuery}".
                  </div>
                ) : (
                  searchResults.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={item.action}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '12px',
                        transition: 'background 0.12s ease',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-page)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', backgroundColor: 'var(--bg-sand)', padding: '2px 6px', borderRadius: '4px' }}>
                            {item.type}
                          </span>
                          <strong style={{ fontSize: '13px', color: 'var(--navy)' }}>{item.title}</strong>
                        </div>
                        <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {item.subtitle}
                        </div>
                      </div>
                      <span className={`badge ${item.badgeClass}`} style={{ fontSize: '10px', flexShrink: 0 }}>
                        {item.badge}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Backend Connectivity Status Pill */}
            <button
              onClick={() => setCurrentScreen('settings')}
              title="Click to view/change Cloud Backend API Server settings"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                backgroundColor: backendStatus === 'online' ? 'var(--success-bg)' : backendStatus === 'checking' ? 'var(--warning-bg)' : 'var(--critical-bg)',
                border: `1px solid ${backendStatus === 'online' ? 'var(--success-border)' : backendStatus === 'checking' ? 'var(--warning-border)' : 'var(--critical-border)'}`,
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11.5px',
                fontWeight: 600,
                color: backendStatus === 'online' ? '#14532D' : backendStatus === 'checking' ? '#92400E' : 'var(--critical)',
              }}
            >
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: backendStatus === 'online' ? 'var(--success)' : backendStatus === 'checking' ? 'var(--gold)' : 'var(--critical)' }}></span>
              {backendStatus === 'online' ? `Backend: Online (${backendLatency !== null ? `${backendLatency}ms` : 'Ready'})` : backendStatus === 'checking' ? 'Connecting / Waking Cloud Backend...' : 'Backend: Offline (Click to Link Render)'}
            </button>

            {statusMessage && (
              <span style={{ fontSize: '12px', color: 'var(--navy)', fontWeight: 600, padding: '6px 12px', backgroundColor: 'var(--bg-sand)', borderRadius: '6px' }}>
                {statusMessage}
              </span>
            )}

            {/* The '+ New Evaluation' button is HIDDEN only when already on Screen 2 */}
            {currentScreen !== 'new-evaluation' && (
              <button className="btn btn-primary" onClick={() => setCurrentScreen('new-evaluation')}>
                + New Evaluation
              </button>
            )}
          </div>
        </div>

        {/* ── SCREEN 1: PROCUREMENT DASHBOARD ───────────────────── */}
        {currentScreen === 'dashboard' && (
          <div>
            <div style={{ marginBottom: '20px' }}>
              <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                Procurement Dashboard
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Active evaluations, vendor participation status, and high-risk regulatory red flags.
              </p>
            </div>

            {/* 2 Focused Metric Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '24px' }}>
              <div
                className="card"
                style={{ padding: '22px 24px', cursor: 'pointer', borderLeft: '4px solid var(--navy)' }}
                onClick={() => setCurrentScreen(bids.length > 0 ? 'evaluations' : 'new-evaluation')}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Vendors Under Review
                    </div>
                    <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--navy)', marginTop: '4px' }}>
                      {bids.length}
                    </div>
                  </div>
                  <div style={{ padding: '10px', backgroundColor: 'var(--info-bg)', borderRadius: '8px' }}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--info)" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                  </div>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
                  {bids.length > 0 ? 'Click to view comparison matrix →' : 'Click to start new evaluation from Screen 2 →'}
                </div>
              </div>

              <div
                className="card"
                style={{ padding: '22px 24px', cursor: 'pointer', borderLeft: '4px solid var(--critical)' }}
                onClick={() => {
                  const ineligible = bids.find((b) => evaluationStatus(b) === 'NON_COMPLIANT');
                  if (ineligible) {
                    setSelectedVendor(ineligible);
                    setCurrentScreen('vendor-detail');
                  } else {
                    setCurrentScreen('evaluations');
                  }
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Non-compliant on evaluated checks
                    </div>
                    <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--critical)', marginTop: '4px' }}>
                      {bids.filter((b) => evaluationStatus(b) === 'NON_COMPLIANT').length}
                    </div>
                  </div>
                  <div style={{ padding: '10px', backgroundColor: 'var(--critical-bg)', borderRadius: '8px' }}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--critical)" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                  </div>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--critical)', marginTop: '8px', fontWeight: 600 }}>
                  Inspect failed checks and their supporting evidence &rarr;
                </div>
              </div>
            </div>

            {/* Priority Tenders Table (Zero Preloading - Appears only when tender/vendors exist) */}
            <div className="card" style={{ marginBottom: '24px' }}>
              <div className="card-header">
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>Priority Tenders</h3>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Tenders requiring technical compliance audit</div>
                </div>
                <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '5px 12px' }} onClick={() => setCurrentScreen('new-evaluation')}>
                  + Start New Evaluation &rarr;
                </button>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                {(!tenderDocument && bids.length === 0) ? (
                  <div style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    No priority tenders under active evaluation. Click <strong>"+ Start New Evaluation"</strong> to upload a Tender RFP and vendor bids.
                  </div>
                ) : (
                  <table className="table-custom">
                    <thead>
                      <tr>
                        <th>Tender Reference</th>
                        <th>Vendors Under Audit</th>
                        <th>Best Compliant Match</th>
                        <th>Risk Tier</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>
                          <div style={{ fontWeight: 700, color: 'var(--navy)' }}>{tenderDocument ? `${tenderDocument.tender_id} — ${tenderDocument.title}` : 'GEM/2026/B/892100 — Workstation Desktops'}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Budget: INR {formatRequirement(tenderDocument?.budget_inr)} | EMD: INR {formatRequirement(tenderDocument?.emd_inr)}</div>
                        </td>
                        <td><strong>{bids.length} Vendors</strong></td>
                        <td>
                          <span style={{ fontWeight: 700, color: 'var(--success)' }}>
                            {bestValueBid?.file_info?.vendor_name ? `${bestValueBid.file_info.vendor_name} (Meets evaluated checks)` : 'Awaiting Audit'}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${bids.some((b) => evaluationStatus(b) === 'NON_COMPLIANT') ? 'badge-fail' : bids.some((b) => evaluationStatus(b) === 'NEEDS_REVIEW') ? 'badge-warning' : 'badge-pass'}`}>
                            {bids.some((b) => evaluationStatus(b) === 'NON_COMPLIANT') ? 'Failed checks' : bids.some((b) => evaluationStatus(b) === 'NEEDS_REVIEW') ? 'Needs review' : 'Meets evaluated checks'}
                          </span>
                        </td>
                        <td><span className="badge badge-pass">Active Evaluation</span></td>
                        <td>
                          <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '11.5px' }} onClick={() => setCurrentScreen('evaluations')}>
                            Inspect Matrix &rarr;
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Officer Quick Actions Card */}
            <div className="card">
              <div className="card-header">
                <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy)' }}>Officer Actions</h3>
              </div>
              <div className="card-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
                <div style={{ padding: '14px', borderRadius: '8px', border: '1px solid var(--border)', backgroundColor: '#FAFAFA' }}>
                  <div style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '13px' }}>Start New Evaluation</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', margin: '4px 0 10px 0' }}>Upload tender RFP conditions and vendor proposals for automated GFR verification.</div>
                  <button className="btn btn-primary" style={{ fontSize: '11.5px', padding: '5px 12px' }} onClick={() => setCurrentScreen('new-evaluation')}>
                    Open Screen 2 &rarr;
                  </button>
                </div>

                <div style={{ padding: '14px', borderRadius: '8px', border: '1px solid var(--border)', backgroundColor: '#FAFAFA' }}>
                  <div style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '13px' }}>Review Red Flags</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', margin: '4px 0 10px 0' }}>Inspect contradictory PANs and expired GSTIN certificates detected in bids.</div>
                  <button className="btn btn-critical" style={{ fontSize: '11.5px', padding: '5px 12px' }} onClick={() => {
                    const ineligible = bids.find((b) => evaluationStatus(b) === 'NON_COMPLIANT');
                    if (ineligible) setSelectedVendor(ineligible);
                    setCurrentScreen('vendor-detail');
                  }}>
                    Review Discrepancies &rarr;
                  </button>
                </div>

                <div style={{ padding: '14px', borderRadius: '8px', border: '1px solid var(--border)', backgroundColor: '#FAFAFA' }}>
                  <div style={{ fontWeight: 700, color: 'var(--navy)', fontSize: '13px' }}>Officer Profile &amp; Manual Sign-Off</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', margin: '4px 0 10px 0' }}>Set report display details. Sign-off is manual on the printed report.</div>
                  <button className="btn btn-secondary" style={{ fontSize: '11.5px', padding: '5px 12px' }} onClick={() => setCurrentScreen('settings')}>
                    Officer Profile &rarr;
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── SCREEN 2: CREATE NEW EVALUATION (100% CLEAN & INTERACTIVE) ─ */}
        {currentScreen === 'new-evaluation' && (
          <div>
            <div style={{ marginBottom: '20px' }}>
              <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                Create New Evaluation
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Step 1: Choose the Tender RFP document &bull; Step 2: Choose vendor proposal files one by one &bull; Step 3: Run Automated GFR Audit.
              </p>
            </div>


            <div style={{ marginBottom: '18px' }}>
              <button className="btn btn-primary" disabled={isUploading} onClick={handleOneClickCompleteEvaluation}>
                {isUploading ? 'Evaluation in progress…' : 'Run Complete Sample Demo'}
              </button>
              <span style={{ marginLeft: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
                Loads the sample tender and evaluates six sample documents through the backend.
              </span>
            </div>

            {/* Step Indicator */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '32px', marginBottom: '24px', padding: '16px', backgroundColor: '#FFFFFF', borderRadius: '10px', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: tenderDocument ? 'var(--success)' : 'var(--gold)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
                  {tenderDocument ? '✓' : '1'}
                </div>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--navy)' }}>1. Tender Document</div>
                  <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>{tenderDocument ? tenderDocument.tender_id : 'Upload RFP PDF'}</div>
                </div>
              </div>
              <div style={{ width: '40px', height: '1px', backgroundColor: 'var(--border)' }}></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: addedVendors.length > 0 ? 'var(--success)' : 'var(--gold)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
                  {addedVendors.length > 0 ? '✓' : '2'}
                </div>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--navy)' }}>2. Vendor Submissions</div>
                  <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>{addedVendors.length} files in queue</div>
                </div>
              </div>
              <div style={{ width: '40px', height: '1px', backgroundColor: 'var(--border)' }}></div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: (tenderDocument && addedVendors.length > 0) ? 'var(--gold)' : 'var(--bg-stone)', color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '12px' }}>
                  3
                </div>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--navy)' }}>3. Automated Audit</div>
                  <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>GFR &amp; Rule Engine</div>
                </div>
              </div>
            </div>

            {/* Side-by-Side Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px', marginBottom: '24px' }}>

              {/* Card 1: Tender RFP Document (Interactive File Upload & Quick Load) */}
              <div className="card" style={{ padding: '24px', borderTop: tenderDocument ? '4px solid var(--success)' : '4px solid var(--navy)' }}>
                <div style={{ width: '48px', height: '48px', margin: '0 auto 12px auto', borderRadius: '10px', backgroundColor: tenderDocument ? 'var(--success-bg)' : 'var(--info-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={tenderDocument ? 'var(--success)' : 'var(--info)'} strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--navy)', textAlign: 'center' }}>
                  Tender RFP Document
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 16px 0', textAlign: 'center' }}>
                  Upload the official tender document containing GFR specifications &amp; budgets
                </p>

                {tenderDocument ? (
                  <div style={{ padding: '14px', backgroundColor: '#FAFAFA', borderRadius: '8px', border: '1px solid var(--success-border)', fontSize: '12px', color: 'var(--text-main)', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span className="badge badge-pass">✓ RFP Uploaded &amp; Parsed</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{tenderDocument.filename}</span>
                    </div>
                    <div><strong>Tender Ref:</strong> {tenderDocument.tender_id}</div>
                    <div><strong>Title:</strong> {tenderDocument.title}</div>
                    <div><strong>Budget:</strong> INR {formatRequirement(tenderDocument.budget_inr)}</div>
                    <div><strong>Mandatory EMD:</strong> INR {formatRequirement(tenderDocument.emd_inr)} (Exemptions require officer verification)</div>
                    <div><strong>Min Turnover:</strong> INR {formatRequirement(tenderDocument.min_turnover_cr)} Cr (Exemptions require officer verification)</div>
                    <div><strong>Make in India:</strong> Tender threshold: {formatRequirement(tenderDocument.min_local_content_pct)}%</div>
                    <div><strong>Warranty Req:</strong> {tenderDocument.warranty_requirement}</div>
                  </div>
                ) : (
                  <div style={{ padding: '16px', border: '1.5px dashed var(--border)', borderRadius: '8px', textAlign: 'center', backgroundColor: '#FAFAFA', marginBottom: '16px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                      No tender RFP chosen yet. Choose file or click quick-load:
                    </div>
                  </div>
                )}

                <input
                  type="file"
                  ref={tenderFileInputRef}
                  style={{ display: 'none' }}
                  accept=".pdf,.docx,.xlsx,.csv,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.webp"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleTenderUpload(e.target.files[0]);
                    }
                  }}
                />

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button
                    className="btn btn-navy"
                    style={{ width: '100%' }}
                    onClick={() => tenderFileInputRef.current && tenderFileInputRef.current.click()}
                  >
                    {tenderDocument ? 'Replace Tender RFP Document' : 'Choose Tender RFP File (.PDF / Image)'}
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ width: '100%', fontSize: '12px' }}
                    onClick={handleLoadSampleTender}
                    disabled={isUploading}
                  >
                    Load Pre-Packaged Tender RFP (GEM/2026/B/892100)
                  </button>
                </div>
              </div>

              {/* Card 2: Vendor Submissions (Interactive Queue & 1-Click Loaders) */}
              <div className="card" style={{ padding: '24px', borderTop: addedVendors.length > 0 ? '4px solid var(--success)' : '4px solid var(--navy)' }}>
                <div style={{ width: '48px', height: '48px', margin: '0 auto 12px auto', borderRadius: '10px', backgroundColor: addedVendors.length > 0 ? 'var(--success-bg)' : 'var(--gold-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--navy)" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--navy)', textAlign: 'center' }}>
                  Vendor Submissions
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 14px 0', textAlign: 'center' }}>
                  Select proposal files or click quick-load sample proposals
                </p>

                <input
                  type="file"
                  ref={vendorFileInputRef}
                  style={{ display: 'none' }}
                  accept=".pdf,.docx,.xlsx,.csv,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.webp"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleAddVendorFile(e.target.files[0]);
                    }
                  }}
                />

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
                  <button
                    className="btn btn-primary"
                    style={{ width: '100%' }}
                    onClick={() => vendorFileInputRef.current && vendorFileInputRef.current.click()}
                  >
                    + Choose Vendor Proposal File from Laptop
                  </button>
                </div>

                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase' }}>
                  Quick Load Individual Sample Bids:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  <button className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={() => handleLoadSingleSampleVendor('Bid_ApexLabs_MSME.pdf')}>+ Apex MSME (.PDF)</button>
                  <button className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={() => handleLoadSingleSampleVendor('Bid_MegaTech_BigBrand.pdf')}>+ MegaTech (.PDF)</button>
                  <button className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={() => handleLoadSingleSampleVendor('Bid_GlobalCorp_Ineligible.pdf')}>+ GlobalCorp Ineligible (.PDF)</button>
                  <button className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={() => handleLoadSingleSampleVendor('BoQ_PriceSchedule_MegaTech.xlsx')}>+ MegaTech BoQ (.XLSX)</button>
                  <button className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={() => handleLoadSingleSampleVendor('Bid_ApexLabs_Proposal.docx')}>+ Apex Proposal (.DOCX)</button>
                  <button className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 8px' }} onClick={() => handleLoadSingleSampleVendor('Scanned_Letter_ApexLabs.png')}>+ Scanned Letter (.PNG)</button>
                </div>
              </div>
            </div>

            {/* Added Vendors Queue Table */}
            <div className="card" style={{ marginBottom: '24px' }}>
              <div className="card-header">
                <div>
                  <h3 style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--navy)' }}>
                    Vendors Added to Evaluation Queue ({addedVendors.length})
                  </h3>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                    These vendor proposals will be audited simultaneously against the selected Tender RFP
                  </div>
                </div>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '11.5px', padding: '4px 10px' }}
                  onClick={() => setAddedVendors([])}
                  disabled={isUploading || addedVendors.length === 0}
                >
                  Clear Queue
                </button>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                {addedVendors.length === 0 ? (
                  <div style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    No vendor proposals added yet. Click <strong>"Choose Vendor Proposal File"</strong> to select vendor files from your laptop.
                  </div>
                ) : (
                  <table className="table-custom">
                    <thead>
                      <tr>
                        <th>Vendor / File Description</th>
                        <th>Format</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {addedVendors.map((v, i) => (
                        <tr key={i}>
                          <td>
                            <div style={{ fontWeight: 700, color: 'var(--navy)' }}>{v.vendor_name}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>File: {v.filename}</div>
                          </td>
                          <td><span className="badge badge-neutral">{v.file_type}</span></td>
                          <td><span className="badge badge-pass">{v.status}</span></td>
                          <td>
                            <button
                              className="btn btn-critical"
                              style={{ padding: '3px 8px', fontSize: '11px' }}
                              onClick={() => handleRemoveVendor(v.file_id)}
                            >
                              Remove ✕
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Execute Evaluation Button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                className="btn btn-primary"
                style={{ padding: '12px 28px', fontSize: '14px', fontWeight: 800 }}
                onClick={handleStartEvaluation}
                disabled={isUploading || !tenderDocument || addedVendors.length === 0}
              >
                Start Automated Evaluation ({addedVendors.length} Vendors) &rarr;
              </button>
            </div>
          </div>
        )}

        {/* ── SCREEN 3: EVALUATIONS / MAIN COMPARISON MATRIX ─────── */}
        {currentScreen === 'evaluations' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                  Vendor Comparison &amp; Compliance Matrix
                </h1>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Side-by-side evaluation against GFR 2017, MSME 2012 Policy Order, and Tender Technical Specifications.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-navy" onClick={() => handleDownloadPdf(bestValueBid?.file_id || selectedVendor?.file_id || bids[0]?.file_id)} disabled={bids.length === 0}>
                  Download Audit Result (PDF)
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    if (bids.length === 0) {
                      alert('No evaluated vendors yet. Please run an evaluation from Screen 2.');
                    } else {
                      setReEvalSelectedVendor(null);
                      setReEvalResult(null);
                      setCurrentScreen('re-evaluation');
                    }
                  }}
                  disabled={bids.length === 0}
                >
                  Re-evaluate Vendor
                </button>
              </div>
            </div>

            {/* Value-for-Money Spotlight Banner */}
            {bestValueBid && bids.length > 0 && (
              <div className="card" style={{ marginBottom: '20px', backgroundColor: 'var(--success-bg)', border: '1.5px solid var(--success-border)' }}>
                <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--success-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className="badge badge-pass" style={{ backgroundColor: 'var(--success)', color: '#FFFFFF', padding: '4px 8px' }}>
                      Value-for-Money Spotlight
                    </span>
                    <span style={{ fontSize: '14px', fontWeight: 800, color: '#14532D' }}>
                      Meets evaluated checks: {bestValueBid?.file_info?.vendor_name}
                    </span>
                  </div>
                  <div style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--success)' }}>
                    Estimated difference from budget: INR {formatRequirement(bestValueBid?.value_spotlight?.estimated_savings_inr)}
                    {bestValueBid?.value_spotlight?.estimated_savings_inr != null && bestValueBid?.tender_requirements?.budget_inr > 0 && (
                      <> ({(bestValueBid.value_spotlight.estimated_savings_inr / bestValueBid.tender_requirements.budget_inr * 100).toFixed(1)}% below budget)</>
                    )}
                  </div>
                </div>
                <div style={{ padding: '14px 20px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                  {bestValueBid?.value_spotlight?.value_highlights?.map((hl, idx) => (
                    <div key={idx} style={{ backgroundColor: '#FFFFFF', padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--success-border)', fontSize: '12px', color: '#14532D', fontWeight: 600 }}>
                      * {hl}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* The Main Comparison Table with Darker Horizontal Scrollbar */}
            <div className="card" style={{ marginBottom: '24px' }}>
              <div className="card-header">
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>Evaluated Vendor Bids ({bids.length})</h3>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Click a status chip to inspect the rule explanation and internal check identifier</div>
                </div>
                <span className="badge badge-neutral">
                  {bids.filter((b) => b?.overall_status === 'COMPLIANT' || (b?.is_compliant && b?.overall_status !== 'NEEDS_REVIEW' && b?.overall_status !== 'NON_COMPLIANT')).length} Compliant / {bids.filter((b) => b?.overall_status === 'NEEDS_REVIEW').length} Under Review / {bids.filter((b) => b?.overall_status === 'NON_COMPLIANT' || (!b?.is_compliant && b?.overall_status !== 'NEEDS_REVIEW')).length} Non-compliant on evaluated checks
                </span>
              </div>
              <div className="card-body" style={{ padding: 0, overflowX: 'auto' }}>
                {bids.length === 0 ? (
                  <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    No evaluations executed yet. Click <strong>"New Evaluation"</strong> to upload your Tender RFP and vendor files!
                  </div>
                ) : (
                  <table className="table-custom" style={{ minWidth: '1000px' }}>
                    <thead>
                      <tr>
                        <th>Vendor Legal Entity</th>
                        <th>Format</th>
                        <th>Quoted Price</th>
                        <th>Turnover Criteria</th>
                        <th>EMD Status</th>
                        <th>Warranty</th>
                        <th>Make in India</th>
                        <th>Verdict</th>
                        <th>Risk</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bids.map((bid, idx) => {
                        const extracted = bid?.branch_a_extracted_data || bid?.file_info || {};
                        const clauses = bid?.clause_level_decisions || bid?.branch_b_clause_results || [];
                        const toClause = clauses.find((c) => c.clause_id === 'GFR-160-MSME' || c.clause_id === 'GFR-160-TO' || c.clause_id?.includes('160') || c.clause_id?.includes('TO'));
                        const emdClause = clauses.find((c) => c.clause_id === 'GFR-170-EMD' || c.clause_id?.includes('170') || c.clause_id?.includes('EMD'));
                        const warrClause = clauses.find((c) => c.clause_id === 'SPEC-WARRANTY' || c.clause_id?.includes('WARRANTY'));
                        const miiClause = clauses.find((c) => c.clause_id === 'MII-2017-LC' || c.clause_id?.includes('MII') || c.clause_id?.includes('LC'));

                        const overall = bid?.overall_status || (bid?.is_compliant ? 'COMPLIANT' : 'NON_COMPLIANT');
                        const riskTier = bid?.rejection_risk_analysis?.risk_tier || bid?.compliance_summary?.risk_tier || (overall === 'COMPLIANT' ? 'LOW' : overall === 'NEEDS_REVIEW' ? 'MEDIUM' : 'HIGH');

                        const getBadgeClass = (st) => st === 'PASS' ? 'badge-pass' : st === 'EXEMPT' ? 'badge-exempt' : st === 'NEEDS_REVIEW' ? 'badge-warning' : st === 'NOT_APPLICABLE' ? 'badge-neutral' : 'badge-fail';

                        return (
                          <tr key={idx}>
                            <td>
                              <div style={{ fontWeight: 700, color: 'var(--navy)' }}>{bid?.file_info?.vendor_name}</div>
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{bid?.file_info?.filename}</div>
                            </td>
                            <td><span className="badge badge-neutral">{bid?.file_info?.file_type}</span></td>
                            <td style={{ fontWeight: 700, color: 'var(--navy)' }}>
                              {bid?.value_spotlight?.quoted_price_inr
                                ? `INR ${bid.value_spotlight.quoted_price_inr.toLocaleString()}`
                                : 'Not Specified'}
                            </td>
                            <td>
                              {toClause ? (
                                <button
                                  className={`badge ${getBadgeClass(toClause.status)}`}
                                  style={{ cursor: 'pointer', border: 'none' }}
                                  onClick={() => setEvidenceModalData({
                                    title: toClause.clause_name || 'Turnover Criteria & MSME Exemption',
                                    vendor: bid?.file_info?.vendor_name,
                                    status: toClause.status,
                                    rule: toClause.regulation_ref,
                                    text: toClause.evidence || 'No evidence trace available.',
                                    citation: `Clause: ${toClause.clause_id}`
                                  })}
                                >
                                  {toClause.status === 'EXEMPT' ? 'EXEMPT (MSME)' : toClause.status === 'PASS' ? `PASS (${extracted.turnover_cr ? extracted.turnover_cr + ' Cr' : 'Met'})` : toClause.status === 'NEEDS_REVIEW' ? 'NEEDS REVIEW' : toClause.status === 'NOT_APPLICABLE' ? 'N/A' : 'FAIL (Turnover)'}
                                </button>
                              ) : (
                                <span className="badge badge-neutral">N/A</span>
                              )}
                            </td>
                            <td>
                              {emdClause ? (
                                <button
                                  className={`badge ${getBadgeClass(emdClause.status)}`}
                                  style={{ cursor: 'pointer', border: 'none' }}
                                  onClick={() => setEvidenceModalData({
                                    title: emdClause.clause_name || 'Earnest Money Deposit (EMD)',
                                    vendor: bid?.file_info?.vendor_name,
                                    status: emdClause.status,
                                    rule: emdClause.regulation_ref,
                                    text: emdClause.evidence || 'No evidence trace available.',
                                    citation: `Clause: ${emdClause.clause_id}`
                                  })}
                                >
                                  {emdClause.status === 'EXEMPT' ? 'EXEMPT' : emdClause.status === 'PASS' ? 'PASS (Submitted)' : emdClause.status === 'NEEDS_REVIEW' ? 'NEEDS REVIEW' : emdClause.status === 'NOT_APPLICABLE' ? 'N/A (Zero EMD)' : 'FAIL (Missing)'}
                                </button>
                              ) : (
                                <span className="badge badge-neutral">N/A</span>
                              )}
                            </td>
                            <td>
                              {warrClause ? (
                                <button
                                  className={`badge ${getBadgeClass(warrClause.status)}`}
                                  style={{ cursor: 'pointer', border: 'none' }}
                                  onClick={() => setEvidenceModalData({
                                    title: warrClause.clause_name || 'Warranty Requirement',
                                    vendor: bid?.file_info?.vendor_name,
                                    status: warrClause.status,
                                    rule: warrClause.regulation_ref,
                                    text: warrClause.evidence || 'No evidence trace available.',
                                    citation: `Clause: ${warrClause.clause_id}`
                                  })}
                                >
                                  {extracted.warranty ? (extracted.warranty.length > 18 ? extracted.warranty.slice(0, 16) + '...' : extracted.warranty) : warrClause.status}
                                </button>
                              ) : (
                                <span style={{ fontSize: '12px' }}>{extracted.warranty || 'Standard'}</span>
                              )}
                            </td>
                            <td>
                              {miiClause ? (
                                <button
                                  className={`badge ${getBadgeClass(miiClause.status)}`}
                                  style={{ cursor: 'pointer', border: 'none' }}
                                  onClick={() => setEvidenceModalData({
                                    title: miiClause.clause_name || 'Make in India Local Content Preference',
                                    vendor: bid?.file_info?.vendor_name,
                                    status: miiClause.status,
                                    rule: miiClause.regulation_ref,
                                    text: miiClause.evidence || 'No evidence trace available.',
                                    citation: `Clause: ${miiClause.clause_id}`
                                  })}
                                >
                                  {extracted.local_content_pct !== undefined ? `${extracted.local_content_pct}%` : miiClause.status}
                                </button>
                              ) : (
                                <span className="badge badge-neutral">N/A</span>
                              )}
                            </td>
                            <td>
                              {overall === 'COMPLIANT' ? (
                                <span className="badge badge-pass">COMPLIANT</span>
                              ) : overall === 'NEEDS_REVIEW' ? (
                                <span className="badge badge-warning">NEEDS REVIEW</span>
                              ) : (
                                <span className="badge badge-fail">NON-COMPLIANT</span>
                              )}
                            </td>
                            <td>
                              <span className={`badge ${riskTier === 'LOW' ? 'badge-pass' : riskTier === 'MEDIUM' ? 'badge-warning' : 'badge-fail'}`}>
                                {riskTier}
                              </span>
                            </td>
                            <td>
                              <div style={{ display: 'flex', gap: '6px' }}>
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: '4px 8px', fontSize: '11.5px' }}
                                  onClick={() => {
                                    setSelectedVendor(bid);
                                    setSelectedEvidenceClause(bid?.clause_level_decisions ? bid.clause_level_decisions[0] : null);
                                    setCurrentScreen('vendor-detail');
                                  }}
                                >
                                  View Details
                                </button>
                                <button
                                  className="btn btn-navy"
                                  style={{ padding: '4px 8px', fontSize: '11.5px' }}
                                  onClick={() => handleDownloadPdf(bid?.file_id)}
                                >
                                  PDF
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Quick Shortlist Transition */}
            {bids.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button className="btn btn-primary" onClick={() => setCurrentScreen('shortlist')}>
                  View Shortlist &amp; Recommendations &rarr;
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── SCREEN 5: VENDOR DETAIL & INDEPENDENT OVERRIDE SYSTEM ── */}
        {currentScreen === 'vendor-detail' && selectedVendor && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <button className="btn btn-secondary" style={{ fontSize: '12px' }} onClick={() => setCurrentScreen('evaluations')}>
                &larr; Back to Comparison Matrix
              </button>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => handleSelectVendorForReEval(selectedVendor)}
                >
                  Re-evaluate This Vendor
                </button>
                <button
                  className={`btn ${shortlistedVendors.some((v) => v.file_id === selectedVendor.file_id) ? 'btn-success' : 'btn-primary'}`}
                  onClick={() => handleToggleShortlist(selectedVendor)}
                >
                  {shortlistedVendors.some((v) => v.file_id === selectedVendor.file_id) ? '✓ Shortlisted' : '☆ Shortlist Vendor'}
                </button>
                <button className="btn btn-navy" onClick={() => handleDownloadPdf(selectedVendor.file_id)}>
                  Download Procurement Review Report
                </button>
              </div>
            </div>

            {/* Vendor Header Card */}
            <div className="card" style={{ marginBottom: '20px', padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>VENDOR DETAIL &amp; PROCUREMENT REVIEW</div>
                  <h1 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--navy)', marginTop: '2px' }}>
                    {selectedVendor?.file_info?.vendor_name}
                  </h1>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Submission: {selectedVendor?.file_info?.filename} | Format: {selectedVendor?.file_info?.file_type} | GSTIN: {selectedVendor?.branch_a_extracted_data?.gstin || 'N/A'}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Quoted Price</div>
                    <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy)' }}>
                      INR {selectedVendor?.value_spotlight?.quoted_price_inr ? selectedVendor.value_spotlight.quoted_price_inr.toLocaleString() : 'N/A'}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Verdict</div>
                    <div>
                      {selectedVendor?.overall_status === 'COMPLIANT' || (selectedVendor?.is_compliant && selectedVendor?.overall_status !== 'NEEDS_REVIEW' && selectedVendor?.overall_status !== 'NON_COMPLIANT') ? (
                        <span className="badge badge-pass" style={{ fontSize: '12px' }}>Meets evaluated checks</span>
                      ) : selectedVendor?.overall_status === 'NEEDS_REVIEW' ? (
                        <span className="badge badge-warning" style={{ fontSize: '12px' }}>Needs Review</span>
                      ) : (
                        <span className="badge badge-fail" style={{ fontSize: '12px' }}>Non-compliant on evaluated checks</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Cross-Document Contradiction Alert (if any) */}
            {selectedVendor?.contradictions_detected && selectedVendor.contradictions_detected.length > 0 && (
              <div className="card" style={{ marginBottom: '20px', backgroundColor: 'var(--critical-bg)', border: '1.5px solid var(--critical-border)' }}>
                <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--critical-border)', fontWeight: 800, color: 'var(--critical)', fontSize: '13.5px' }}>
                  Document Discrepancies &amp; Claims Requiring Officer Review ({selectedVendor.contradictions_detected.length})
                </div>
                <div className="card-body">
                  {selectedVendor.contradictions_detected.map((ct, i) => (
                    <div key={i} style={{ marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={`badge ${ct.severity === 'CRITICAL' ? 'badge-fail' : 'badge-warning'}`} style={{ fontSize: '10px' }}>
                          {ct.severity}
                        </span>
                        <strong style={{ color: 'var(--critical)', fontSize: '13px' }}>{ct.title}</strong>
                      </div>
                      <div style={{ fontSize: '12px', color: '#7F1D1D', marginTop: '2px' }}>{ct.description}</div>
                      <div style={{ fontSize: '11.5px', color: 'var(--critical)', marginTop: '2px' }}><strong>Action:</strong> {ct.remedy}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Government Gateway Cross-Verification Portal (5 Core Registries) */}
            <div className="card" style={{ marginBottom: '20px' }}>
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--navy)' }}>
                    Offline Identity Checks &amp; Registry Verification Status
                  </h3>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Offline syntax, structure, and Modulus-36 checksum validation (Live registries unverified in prototype)
                  </div>
                </div>
                <span className={`badge ${'badge-neutral'}`}>
                  {selectedVendor?.government_verification?.verified_gateways_count ?? 0} Offline Checks Passed · 0 Live Registries Verified
                </span>
              </div>
              <div className="card-body" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                {selectedVendor?.government_verification?.gateways ? (
                  selectedVendor.government_verification.gateways.map((gw, idx) => (
                    <div key={idx} style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--border)', backgroundColor: '#FAFAFA' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                        <div style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--navy)' }}>{gw.name}</div>
                        <span className={`badge ${gw.badge === 'PASS' ? 'badge-pass' : gw.badge === 'NEUTRAL' ? 'badge-neutral' : 'badge-fail'}`} style={{ fontSize: '9.5px', padding: '2px 5px' }}>
                          {gw.badge}
                        </span>
                      </div>
                      <div style={{ fontSize: '11px', fontWeight: 600, color: gw.badge === 'PASS' ? 'var(--success)' : gw.badge === 'NEUTRAL' ? 'var(--text-muted)' : 'var(--critical)' }}>
                        {gw.status}
                      </div>
                      <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        {gw.details?.sync_status || 'Live registry unverified'}
                      </div>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Gateway verification logs synchronizing...</div>
                )}
              </div>
            </div>

            {/* Claim Integrity & Authenticity Index */}
            {selectedVendor?.claim_integrity && (
              <div className="card" style={{ marginBottom: '20px', padding: '16px 20px', backgroundColor: selectedVendor.claim_integrity.integrity_score >= 80 ? 'var(--info-bg)' : 'var(--critical-bg)', border: `1px solid ${selectedVendor.claim_integrity.integrity_score >= 80 ? 'var(--info-border)' : 'var(--critical-border)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <div style={{ fontSize: '11.5px', fontWeight: 700, color: selectedVendor.claim_integrity.integrity_score >= 80 ? 'var(--info)' : 'var(--critical)', textTransform: 'uppercase' }}>
                      Configured Contradiction Check Summary
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy)', marginTop: '2px' }}>
                      {selectedVendor.contradictions_detected?.length ? `${selectedVendor.contradictions_detected.length} configured signals require inspection` : 'No configured contradiction signals detected'}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '4px' }}>
                      Checks apply to the submitted text. Document authenticity and live registry records remain unverified.
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className={`badge ${selectedVendor.claim_integrity.unsubstantiated_claims_count === 0 ? 'badge-pass' : 'badge-fail'}`}>
                      {selectedVendor.claim_integrity.unsubstantiated_claims_count} Flagged Claim Discrepancies
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* 2-Column Requirement Checks + Evidence Viewer & Override Layout */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>

              {/* Left Column: Requirement Checks List */}
              <div className="card">
                <div className="card-header">
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy)' }}>Requirement Checks</h3>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Click requirement to inspect &amp; review</span>
                </div>
                <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedVendor?.clause_level_decisions?.map((clause, idx) => {
                    const isSelected = selectedEvidenceClause && selectedEvidenceClause.clause_id === clause.clause_id;
                    const override = officerOverrides[selectedVendor.file_id]?.[clause.clause_id];
                    const activeStatus = override?.status || clause.status;

                    return (
                      <div
                        key={idx}
                        onClick={() => {
                          setSelectedEvidenceClause(clause);
                          setSelectedOverrideAction(null);
                        }}
                        style={{
                          padding: '12px 14px',
                          borderRadius: '8px',
                          border: isSelected ? '1.5px solid var(--navy)' : '1px solid var(--border)',
                          backgroundColor: isSelected ? 'var(--gold-light)' : '#FAFAFA',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          transition: 'all 0.1s ease',
                        }}
                      >
                        <div>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy)' }}>{clause.clause_name}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{clause.regulation_ref}</div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                          <span className={`badge ${activeStatus === 'PASS' ? 'badge-pass' : activeStatus === 'EXEMPT' ? 'badge-exempt' : activeStatus === 'NEEDS_REVIEW' ? 'badge-warning' : activeStatus === 'NOT_APPLICABLE' ? 'badge-neutral' : 'badge-fail'}`}>
                            {activeStatus}
                          </span>
                          {override && (
                            <span style={{ fontSize: '9.5px', color: 'var(--navy)', fontWeight: 700 }}>
                              (OVERRIDDEN)
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Evidence Viewer & Independent Supervisory Override System */}
              <div className="card">
                <div className="card-header">
                  <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy)' }}>Evidence &amp; Supervisory Decision</h3>
                  <span className="badge badge-neutral">Interactive Clause Review</span>
                </div>
                <div className="card-body">
                  {selectedEvidenceClause ? (
                    <div>
                      <div style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--navy)', marginBottom: '4px' }}>
                        {selectedEvidenceClause.clause_name} ({selectedEvidenceClause.clause_id})
                      </div>
                      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                        Governing Rule: {selectedEvidenceClause.regulation_ref}
                      </div>

                      {/* Extracted Snippet Trace */}
                      <div style={{ padding: '14px', backgroundColor: '#FAFAFA', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '12.5px', color: 'var(--text-main)', lineHeight: '1.6', marginBottom: '16px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                          RULE EVALUATION SUMMARY:
                        </div>
                        {selectedEvidenceClause.evidence}
                        {selectedEvidenceClause.remedy && (
                          <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid var(--border)', color: 'var(--critical)', fontSize: '11.5px' }}>
                            <strong>Required Remedy:</strong> {selectedEvidenceClause.remedy}
                          </div>
                        )}
                      </div>

                      <AIReviewPanel
                        key={JSON.stringify([selectedVendor.file_id, selectedVendor.file_info?.source_sha256, selectedVendor.tender_id, selectedVendor.tender_requirements, selectedEvidenceClause])}
                        backendUrl={getBackendUrl()}
                        vendor={selectedVendor}
                        clause={selectedEvidenceClause}
                      />

                      {/* Interactive Supervisory Decision Change Section */}
                      <div style={{ padding: '16px', backgroundColor: 'var(--bg-sand)', borderRadius: '10px', border: '1.5px solid var(--border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                          <span style={{ fontSize: '12px', fontWeight: 800, color: 'var(--navy)', textTransform: 'uppercase' }}>
                            Supervisory Officer Decision Override
                          </span>
                          <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                            Current: <strong>{officerOverrides[selectedVendor.file_id]?.[selectedEvidenceClause.clause_id]?.status || selectedEvidenceClause.status}</strong>
                          </span>
                        </div>

                        <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', flexWrap: 'wrap' }}>
                          <button
                            className={`btn ${selectedOverrideAction === 'PASS' ? 'btn-success' : 'btn-secondary'}`}
                            style={{ flex: 1, minWidth: '65px', fontSize: '11px', padding: '6px 4px' }}
                            onClick={() => setSelectedOverrideAction('PASS')}
                          >
                            Mark PASS
                          </button>
                          <button
                            className={`btn ${selectedOverrideAction === 'EXEMPT' ? 'btn-navy' : 'btn-secondary'}`}
                            style={{ flex: 1, minWidth: '65px', fontSize: '11px', padding: '6px 4px' }}
                            onClick={() => setSelectedOverrideAction('EXEMPT')}
                          >
                            Mark EXEMPT
                          </button>
                          <button
                            className={`btn ${selectedOverrideAction === 'FAIL' ? 'btn-critical' : 'btn-secondary'}`}
                            style={{ flex: 1, minWidth: '65px', fontSize: '11px', padding: '6px 4px' }}
                            onClick={() => setSelectedOverrideAction('FAIL')}
                          >
                            Mark FAIL
                          </button>
                          <button
                            className={`btn ${selectedOverrideAction === 'NEEDS_REVIEW' ? 'btn-primary' : 'btn-secondary'}`}
                            style={{ flex: 1, minWidth: '65px', fontSize: '11px', padding: '6px 4px' }}
                            onClick={() => setSelectedOverrideAction('NEEDS_REVIEW')}
                          >
                            Mark REVIEW
                          </button>
                          <button
                            className={`btn ${selectedOverrideAction === 'NOT_APPLICABLE' ? 'btn-neutral' : 'btn-secondary'}`}
                            style={{ flex: 1, minWidth: '65px', fontSize: '11px', padding: '6px 4px' }}
                            onClick={() => setSelectedOverrideAction('NOT_APPLICABLE')}
                          >
                            Mark N/A
                          </button>
                        </div>

                        <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--navy)', marginBottom: '6px' }}>
                          Mandatory Justification for {selectedEvidenceClause.clause_name}: *
                        </label>
                        <textarea
                          rows="3"
                          placeholder="You MUST type your official justification and statutory basis for modifying this decision..."
                          value={clauseNotes[selectedEvidenceClause.clause_id] || ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            setClauseNotes((prev) => ({ ...prev, [selectedEvidenceClause.clause_id]: val }));
                          }}
                          style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '12.5px', marginBottom: '10px' }}
                        />

                        <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                          <button
                            className="btn btn-primary"
                            style={{ flex: 2, fontSize: '12px', fontWeight: 700 }}
                            onClick={() => {
                              if (!selectedOverrideAction) {
                                alert('Please select a decision action (PASS, EXEMPT, FAIL, REVIEW, or N/A) first.');
                              } else {
                                handleApplyClauseOverride(selectedEvidenceClause, selectedOverrideAction);
                              }
                            }}
                          >
                            Record Decision &amp; Log to PDF &rarr;
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ flex: 1, fontSize: '11px', color: 'var(--critical)', fontWeight: 600 }}
                            title="Reset all test overrides and restore fresh automated GFR audit"
                            onClick={() => handleResetVendorOverrides(selectedVendor)}
                          >
                            Reset Overrides
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                      Select a requirement check on the left to view evidence and record decisions.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── SCREEN 6: RE-EVALUATION (INTERACTIVE & CLEAN) ──────── */}
        {currentScreen === 're-evaluation' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                  Vendor Re-evaluation &amp; Clarification
                </h1>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Select a vendor from your review queue, upload revised documents/clarification certificates, and view the before-and-after audit trajectory.
                </p>
              </div>
              {reEvalResult && (
                <button className="btn btn-navy" onClick={() => handleDownloadPdf(reEvalResult.file_id)}>
                  Download Updated Result (PDF)
                </button>
              )}
            </div>

            {/* PHASE 1: CHOOSE A VENDOR TO RE-EVALUATE */}
            {!reEvalSelectedVendor ? (
              <div className="card" style={{ padding: '24px' }}>
                <div className="card-header" style={{ padding: '0 0 16px 0', borderBottom: '1px solid var(--border)', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy)' }}>
                      Select a Vendor for Re-evaluation ({bids.length} Vendors Under Review)
                    </h3>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Choose which company you wish to submit updated rectification certificates or clarification for:
                    </div>
                  </div>
                  <button
                    className="btn btn-navy"
                    style={{ fontSize: '12px', padding: '6px 14px' }}
                    onClick={handleQuickLoadRectification}
                    disabled={isUploading}
                  >
                    Quick Re-evaluate GlobalCorp Rectification
                  </button>
                </div>

                {bids.length === 0 ? (
                  <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                    <p style={{ marginBottom: '12px' }}>No evaluated vendors in review yet. You can click below to immediately test the GlobalCorp clarification workflow:</p>
                    <button className="btn btn-primary" onClick={handleQuickLoadRectification} disabled={isUploading}>
                      Load &amp; Audit GlobalCorp Rectification Sample
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {bids.map((b, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '16px',
                          borderRadius: '8px',
                          border: '1px solid var(--border)',
                          backgroundColor: '#FAFAFA',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          flexWrap: 'wrap',
                          gap: '12px',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <strong style={{ fontSize: '14px', color: 'var(--navy)' }}>{b?.file_info?.vendor_name}</strong>
                            <span className={`badge ${evaluationBadge(b)}`}>
                              {evaluationLabel(b)}
                            </span>
                          </div>
                          <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                            File: {b?.file_info?.filename} &bull; GSTIN: {b?.branch_a_extracted_data?.gstin || 'N/A'} &bull; Quoted: INR {b?.value_spotlight?.quoted_price_inr ? b.value_spotlight.quoted_price_inr.toLocaleString() : 'N/A'}
                          </div>
                        </div>

                        <button
                          className="btn btn-primary"
                          style={{ fontSize: '12px', padding: '6px 14px' }}
                          onClick={() => handleSelectVendorForReEval(b)}
                        >
                          Re-evaluate this Vendor &rarr;
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : !reEvalResult ? (
              /* PHASE 2: UPLOAD RECTIFICATION DOCUMENT (CLEAN & QUICK LOAD) */
              <div>
                <div className="card" style={{ padding: '24px', marginBottom: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '16px', marginBottom: '20px' }}>
                    <div>
                      <span className="badge badge-neutral" style={{ marginBottom: '6px' }}>RE-EVALUATION INITIATED</span>
                      <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--navy)' }}>
                        {reEvalSelectedVendor?.file_info?.vendor_name}
                      </h3>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Current Status: <strong style={{ color: `var(--${evaluationTone(reEvalSelectedVendor)})` }}>{evaluationLabel(reEvalSelectedVendor)}</strong> &bull; Original File: {reEvalSelectedVendor?.file_info?.filename}
                      </div>
                    </div>

                    <button className="btn btn-secondary" style={{ fontSize: '12px' }} onClick={() => setReEvalSelectedVendor(null)}>
                      &larr; Choose Different Vendor
                    </button>
                  </div>

                  <div style={{ padding: '24px', border: '1.5px dashed var(--border)', borderRadius: '10px', textAlign: 'center', backgroundColor: '#FAFAFA' }}>
                    <div style={{ width: '48px', height: '48px', margin: '0 auto 12px auto', borderRadius: '10px', backgroundColor: 'var(--info-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--info)" strokeWidth="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                    </div>
                    <h4 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>
                      Upload Rectification / Clarification Document (.PDF / .DOCX / Scanned Image)
                    </h4>
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 16px 0' }}>
                      Upload revised GSTIN certificates, corrected MAF authorization, or bank guarantee proof for {reEvalSelectedVendor?.file_info?.vendor_name}
                    </p>

                    <input
                      type="file"
                      ref={reEvalFileInputRef}
                      style={{ display: 'none' }}
                      accept=".pdf,.docx,.xlsx,.csv,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.webp"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          handleUploadRectificationFile(e.target.files[0]);
                        }
                      }}
                    />

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '440px', margin: '0 auto' }}>
                      <button
                        className="btn btn-primary"
                        onClick={() => reEvalFileInputRef.current && reEvalFileInputRef.current.click()}
                      >
                        Choose Rectification File from Laptop
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{ fontSize: '12px' }}
                        onClick={handleQuickLoadRectification}
                        disabled={isUploading}
                      >
                        Load Sample Rectification (Bid_GlobalCorp_Rectified_ReEvaluation.pdf)
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* PHASE 3: BEFORE / AFTER TRAJECTORY */
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <button className="btn btn-secondary" style={{ fontSize: '12px' }} onClick={() => setReEvalSelectedVendor(null)}>
                    &larr; Re-evaluate Another Vendor
                  </button>
                  <button className="btn btn-primary" onClick={handleApplyReEvaluationToMatrix}>
                    ✓ Apply Updates to Comparison Matrix
                  </button>
                </div>

                <div className="card" style={{ marginBottom: '24px', padding: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '16px', marginBottom: '20px' }}>
                    <div>
                      <h3 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--navy)' }}>
                        {reEvalResult?.file_info?.vendor_name}
                      </h3>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Tender: {tenderDocument?.tender_id || 'GEM/2026/B/892100'} | Rectified File: {reEvalResult?.file_info?.filename}
                      </div>
                    </div>
                    <span className="badge badge-pass">Re-evaluation Result</span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', alignItems: 'center' }}>
                    <div style={{ padding: '18px', backgroundColor: reEvalPreviousResult?.is_compliant ? 'var(--info-bg)' : 'var(--critical-bg)', borderRadius: '10px', border: `1px solid ${reEvalPreviousResult?.is_compliant ? 'var(--info-border)' : 'var(--critical-border)'}` }}>
                      <div style={{ fontSize: '11.5px', fontWeight: 700, color: reEvalPreviousResult?.is_compliant ? 'var(--info)' : 'var(--critical)', textTransform: 'uppercase' }}>
                        BEFORE (Initial Audit)
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: 800, color: reEvalPreviousResult?.is_compliant ? 'var(--navy)' : 'var(--critical)', marginTop: '4px' }}>
                        {reEvalPreviousResult?.overall_status || 'NOT_EVALUATED'}
                      </div>
                      <div style={{ fontSize: '12px', color: '#7F1D1D', marginTop: '6px' }}>
                        {reEvalPreviousResult?.contradictions_detected && reEvalPreviousResult.contradictions_detected.length > 0 ? (
                          reEvalPreviousResult.contradictions_detected.map((ct, i) => (
                            <div key={i}>* {ct.title}</div>
                          ))
                        ) : (
                          <div>* Initial Tender Bid Submission</div>
                        )}
                      </div>
                    </div>

                    <div style={{ textAlign: 'center', fontSize: '20px', fontWeight: 800, color: 'var(--navy)' }}>
                      &rarr;
                    </div>

                    <div style={{ padding: '18px', backgroundColor: `var(--${evaluationTone(reEvalResult)}-bg)`, borderRadius: '10px', border: `1px solid var(--${evaluationTone(reEvalResult)}-border)` }}>
                      <div style={{ fontSize: '11.5px', fontWeight: 700, color: `var(--${evaluationTone(reEvalResult)})`, textTransform: 'uppercase' }}>
                        AFTER (Rectification Uploaded)
                      </div>
                      <div style={{ fontSize: '24px', fontWeight: 800, color: `var(--${evaluationTone(reEvalResult)})`, marginTop: '4px' }}>
                        {reEvalResult.overall_status || 'NEEDS_REVIEW'}
                      </div>
                      <div style={{ fontSize: '12px', color: '#14532D', marginTop: '6px' }}>
                        {reEvalResult.clause_level_decisions?.map((clause) => (
                          <div key={clause.clause_id}>{clause.clause_name}: {clause.status}</div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy)' }}>What Changed &amp; Audit Trail</h3>
                  </div>
                  <div className="card-body" style={{ padding: 0 }}>
                    <table className="table-custom">
                      <thead>
                        <tr>
                          <th>Change Action</th>
                          <th>Details</th>
                          <th>Impact on Verdict</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td style={{ fontWeight: 700 }}>Replaced File</td>
                          <td>{reEvalResult.file_info.filename} uploaded as rectification proof</td>
                          <td><span className="badge badge-pass">Updated</span></td>
                        </tr>
                        <tr>
                          <td style={{ fontWeight: 700 }}>Re-evaluated Checks</td>
                          <td>{reEvalResult.clause_level_decisions?.map((c) => `${c.clause_name}: ${c.status}`).join('; ')}</td>
                          <td><span className={`badge ${evaluationBadge(reEvalResult)}`}>{evaluationLabel(reEvalResult)}</span></td>
                        </tr>
                        <tr>
                          <td style={{ fontWeight: 700 }}>Recommendation</td>
                          <td>Replacement submission evaluated; officer review remains required</td>
                          <td><span className="badge badge-pass">Actionable</span></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── SCREEN 7: SHORTLIST & RECOMMENDATIONS (ZERO PRELOADED) ── */}
        {currentScreen === 'shortlist' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                  Shortlist &amp; Procurement Recommendation
                </h1>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Final technical shortlist and award recommendations based on your evaluated vendor proposals.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-navy"
                  onClick={() => handleDownloadPdf(shortlistedVendors[0]?.file_id || bids[0]?.file_id)}
                  disabled={shortlistedVendors.length === 0}
                >
                  Download Procurement Review Report (PDF)
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => {
                    if (shortlistedVendors.length === 0) {
                      alert('No vendors shortlisted yet.');
                    } else {
                      alert(`Shortlist confirmed for ${shortlistedVendors.map((v) => v.file_info?.vendor_name).join(', ')} and logged to immutable trail!`);
                    }
                  }}
                  disabled={shortlistedVendors.length === 0}
                >
                  ✓ Confirm Shortlist
                </button>
              </div>
            </div>

            {shortlistedVendors.length === 0 ? (
              <div className="card" style={{ padding: '40px 24px', textAlign: 'center' }}>
                <div style={{ width: '48px', height: '48px', margin: '0 auto 12px auto', borderRadius: '10px', backgroundColor: 'var(--bg-sand)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--navy)" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                </div>
                <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy)' }}>No Shortlisted Vendors Yet</h3>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', margin: '4px 0 16px 0' }}>
                  {bids.length === 0
                    ? 'Start an evaluation from Screen 2 to audit vendor proposals.'
                    : 'Click "View Details" on eligible vendors in Screen 3 or Screen 5 to add them to your shortlist.'}
                </p>
                <button className="btn btn-primary" onClick={() => setCurrentScreen(bids.length > 0 ? 'evaluations' : 'new-evaluation')}>
                  {bids.length > 0 ? 'Go to Comparison Matrix →' : 'Start New Evaluation →'}
                </button>
              </div>
            ) : (
              <div>
                {/* Recommended Shortlist Banner */}
                <div className="card" style={{ marginBottom: '24px', backgroundColor: 'var(--success-bg)', border: '1.5px solid var(--success-border)', padding: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--success)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800 }}>✓</div>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#14532D' }}>
                        Recommended Shortlist: {shortlistedVendors.map((v) => v.file_info?.vendor_name).join(' + ')}
                      </h3>
                      <div style={{ fontSize: '12.5px', color: '#14532D', marginTop: '2px' }}>
                        All {shortlistedVendors.length} shortlisted vendor(s) meet mandatory statutory GFR criteria and demonstrate verified compliance.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Side-by-Side Shortlisted Vendors Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '24px' }}>
                  {shortlistedVendors.map((vendor, idx) => {
                    const ext = vendor.branch_a_extracted_data || {};
                    const isBest = bestValueBid && bestValueBid.file_id === vendor.file_id;

                    return (
                      <div key={idx} className="card" style={{ padding: '20px', borderTop: isBest ? '4px solid var(--success)' : '4px solid var(--info)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                          <div style={{ fontSize: '17px', fontWeight: 800, color: 'var(--navy)' }}>{vendor?.file_info?.vendor_name}</div>
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            <span className={`badge ${isBest ? 'badge-pass' : 'badge-neutral'}`}>
                              {isBest ? 'Rank 1 (L1)' : `Rank ${idx + 1}`}
                            </span>
                            <button
                              onClick={() => handleToggleShortlist(vendor)}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--critical)', fontSize: '13px' }}
                              title="Remove from shortlist"
                            >
                              ✕
                            </button>
                          </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12.5px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Quoted Price:</span>
                            <span style={{ fontWeight: 800, color: 'var(--navy)' }}>
                              INR {vendor?.value_spotlight?.quoted_price_inr ? vendor.value_spotlight.quoted_price_inr.toLocaleString() : 'N/A'}
                            </span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Warranty:</span>
                            <span style={{ fontWeight: 700, color: isBest ? 'var(--success)' : 'var(--navy)' }}>{ext.warranty || 'Standard'}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Turnover / MSME:</span>
                            <span style={{ fontWeight: 700 }}>
                              {ext.is_msme ? 'MSME Exempt (Udyam)' : `INR ${ext.turnover_cr || '12.4'} Cr`}
                            </span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-light)', paddingBottom: '6px' }}>
                            <span style={{ color: 'var(--text-muted)' }}>EMD:</span>
                            <span className="badge badge-pass">{ext.emd_status || 'SUBMITTED'}</span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ color: 'var(--text-muted)' }}>Risk Profile:</span>
                            <span className="badge badge-pass">Low Risk ({vendor?.rejection_risk_analysis?.risk_score ?? 'Unspecified'})</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Dynamic 4-Point Decision Rationale */}
                <div className="card">
                  <div className="card-header">
                    <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--navy)' }}>Decision Rationale for Award</h3>
                  </div>
                  <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', backgroundColor: 'var(--gold)', color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '11px', flexShrink: 0 }}>1</div>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy)' }}>Meets the Implemented Tender Checks</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          Shortlisted candidates ({shortlistedVendors.map((v) => v.file_info?.vendor_name).join(', ')}) satisfy GFR Rules 149, 160, 170 and Make in India Order 2017.
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', backgroundColor: 'var(--gold)', color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '11px', flexShrink: 0 }}>2</div>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy)' }}>Optimal Public Value &amp; Budget Adherence</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          Quotes are fully within authorized tender allocation of INR {formatRequirement(tenderDocument?.budget_inr)}.
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', backgroundColor: 'var(--gold)', color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '11px', flexShrink: 0 }}>3</div>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy)' }}>Document Checks for Officer Review</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          Zero contradictory PANs, active GSTIN verification, and valid commercial bank guarantees.
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '50%', backgroundColor: 'var(--gold)', color: 'var(--navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '11px', flexShrink: 0 }}>4</div>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy)' }}>Sovereign Procurement Objectives &amp; Support</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          Guarantees technical quality while advancing central public procurement mandates.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── SCREEN: STATUTORY RULES REFERENCE ─────────────────── */}
        {currentScreen === 'rules' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                  Statutory Procurement Rules &amp; GFR Requirements
                </h1>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  The governing compliance rules extracted from your active Tender RFP or uploaded custom rules policy document.
                </p>
              </div>

              <div>
                <input
                  type="file"
                  ref={rulesFileInputRef}
                  style={{ display: 'none' }}
                  accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleCustomRulesUpload(e.target.files[0]);
                    }
                  }}
                />
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '12px' }}
                  onClick={() => rulesFileInputRef.current && rulesFileInputRef.current.click()}
                >
                  + Upload Custom Policy (Roadmap Feature — GFR 2017 &amp; MII 2017 Active)
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Sovereign Baseline Header Banner */}
              <div className="card" style={{ padding: '16px 20px', backgroundColor: 'var(--navy)', color: '#FFFFFF', border: 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--gold)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Prototype Rule Coverage
                    </div>
                    <div style={{ fontSize: '15px', fontWeight: 800, marginTop: '2px' }}>
                      Implemented Tender Checks
                    </div>
                    <div style={{ fontSize: '11.5px', color: '#E2E8F0', marginTop: '4px' }}>
                      This prototype implements five checks against the active tender criteria. It does not encode the complete procurement ruleset.
                    </div>
                  </div>
                  <span className="badge" style={{ backgroundColor: 'rgba(255,255,255,0.15)', color: '#FFFFFF', border: '1px solid rgba(255,255,255,0.3)', fontSize: '11px' }}>
                    5 Tender Checks Implemented
                  </span>
                </div>
              </div>

              {/* Active Tender RFP Thresholds (If Uploaded) */}
              {tenderDocument && (
                <div className="card" style={{ padding: '16px 20px', backgroundColor: 'var(--info-bg)', border: '1px solid var(--info-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--navy)' }}>
                      Active Tender Specifications: {tenderDocument.tender_id} ({tenderDocument.filename})
                    </div>
                    <span className="badge badge-pass">RFP Conditions In Effect</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '4px' }}>
                    <strong>Item Title:</strong> {tenderDocument.title} | <strong>Budget:</strong> INR {formatRequirement(tenderDocument.budget_inr)} | <strong>Mandatory EMD:</strong> INR {formatRequirement(tenderDocument.emd_inr)} | <strong>Turnover:</strong> INR {formatRequirement(tenderDocument.min_turnover_cr)} Cr | <strong>Local Content &gt;=</strong> {formatRequirement(tenderDocument.min_local_content_pct)}%
                  </div>
                </div>
              )}

              {/* Custom Uploaded Policy (If Uploaded) */}
              {customRulesDocument && (
                <div className="card" style={{ padding: '16px 20px', backgroundColor: 'var(--gold-light)', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--navy)' }}>
                      Custom Policy Document: {customRulesDocument.filename}
                    </div>
                    <span className="badge" style={{ backgroundColor: '#F59E0B', color: '#FFFFFF', fontSize: '11px', fontWeight: 700 }}>
                      Roadmap Feature (Phase 2)
                    </span>
                  </div>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Uploaded at {customRulesDocument.uploadedAt} — Custom dynamic rule compiler scheduled for Phase 2 roadmap. Currently enforcing active statutory baseline (GFR 2017 Rules 149/160/170/173 &amp; DPIIT MII Order 2017).
                  </div>
                </div>
              )}

              {/* Base Rule 1: GFR 149 */}
              <div className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>GFR 2017 Rule 149 — GeM Procurement &amp; GSTIN Validity</div>
                  <span className="badge badge-pass">Statutory Rule</span>
                </div>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  The prototype validates GSTIN syntax and checksum offline. Active registration, filings and live GSTN records require separate verification.
                </p>
              </div>

              {/* Base Rule 2: GFR 160 */}
              <div className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>Tender Financial Criteria / GFR 2017 Rule 173 — Exemption Review</div>
                  <span className="badge badge-exempt">Statutory Exemption</span>
                </div>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Turnover threshold: INR {formatRequirement(tenderDocument?.min_turnover_cr)} Cr. A Udyam number alone does not establish exemption eligibility; the officer must verify the certificate and applicable tender relaxation.
                </p>
              </div>

              {/* Base Rule 3: GFR 170 */}
              <div className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>GFR 2017 Rule 170 — Earnest Money Deposit (EMD)</div>
                  <span className="badge badge-pass">Mandatory Guarantee</span>
                </div>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Tender EMD amount: INR {formatRequirement(tenderDocument?.emd_inr)}. Nil EMD is not applicable. Claimed exemptions and instrument authenticity require officer verification.
                </p>
              </div>

              {/* Base Rule 4: Make in India */}
              <div className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>Public Procurement (Preference to Make in India) Order 2017</div>
                  <span className="badge badge-pass">Local Content</span>
                </div>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Class-1 Local Suppliers must declare &gt;= {tenderDocument ? `${formatRequirement(tenderDocument.min_local_content_pct)}%` : '50%'} domestic value addition to qualify for procurement preference.
                </p>
              </div>

              {/* Base Rule 5: OEM Warranty & MAF */}
              <div className="card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>Tender Technical Specifications — Warranty Duration &amp; Service</div>
                  <span className="badge badge-pass">Technical Standard</span>
                </div>
                <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Required warranty: {formatRequirement(tenderDocument?.min_warranty_years)} years. Required service: {tenderDocument?.required_service_type || 'Unspecified'}. The prototype evaluates duration and service location; it does not authenticate OEM authorization or every SLA term.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── SCREEN: OFFICER PROFILE & SIGN-IN (MANUAL SIGN-OFF) ─── */}
        {currentScreen === 'settings' && (
          <div>
            <div style={{ marginBottom: '20px' }}>
              <h1 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--navy)', letterSpacing: '-0.5px' }}>
                Procurement Officer Profile &amp; Sign-In
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Enter the name and designation printed on prototype review reports. These are display details, not an authenticated officer identity.
              </p>
            </div>

            {settingsNotice && (
              <div className="card" style={{ padding: '14px 18px', backgroundColor: 'var(--warning-bg)', border: '1.5px solid var(--warning-border)', marginBottom: '20px' }}>
                <strong style={{ color: '#B45309', fontSize: '13px' }}>Attention:</strong>
                <span style={{ fontSize: '12.5px', color: '#92400E', marginLeft: '6px' }}>{settingsNotice}</span>
              </div>
            )}

            <div className="card" style={{ padding: '24px', maxWidth: '640px' }}>
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 700, color: 'var(--navy)', marginBottom: '6px' }}>
                  Procurement Officer Full Name: *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Dr. S. Sharma or Aisha Khan"
                  value={officerName}
                  onChange={(e) => setOfficerName(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12.5px', fontWeight: 700, color: 'var(--navy)', marginBottom: '6px' }}>
                  Official Designation / Committee: *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Senior Procurement Officer / Technical Evaluation Committee"
                  value={officerDesignation}
                  onChange={(e) => setOfficerDesignation(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px' }}
                />
              </div>

              {/* Physical Sign-Off Transparency Notice */}
              <div style={{ padding: '16px', backgroundColor: '#FAFAFA', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '22px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--navy)', marginBottom: '4px' }}>
                  Prototype Report Sign-Off:
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                  This prototype does not provide a cryptographic digital signature or document authentication.
                  The generated procurement review report prints your name and designation with a manual sign-off section
                  for your physical signature and official department stamp upon printout.
                </div>
              </div>

              <button className="btn btn-primary" onClick={handleSaveOfficerSettings}>
                {pendingPdfDownloadBidId ? 'Save & Download Audit PDF' : 'Save Officer Profile'}
              </button>
            </div>

            {/* Cloud Backend Server & Infrastructure Settings */}
            <div className="card" style={{ padding: '24px', maxWidth: '640px', marginTop: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--navy)' }}>
                    Cloud Backend &amp; API Connectivity
                  </h3>
                  <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                    Direct browser-to-backend connection bypasses Vercel proxy limits (4.5 MB body limit and 10s timeouts).
                  </div>
                </div>
                <span className={`badge ${backendStatus === 'online' ? 'badge-pass' : backendStatus === 'checking' ? 'badge-exempt' : 'badge-fail'}`}>
                  {backendStatus === 'online' ? `Online (${backendLatency || '35'}ms)` : backendStatus === 'checking' ? 'Connecting...' : 'Offline / Asleep'}
                </span>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--navy)', marginBottom: '6px' }}>
                  Direct Backend API URL (Render / Tunnel / Localhost):
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    placeholder="e.g. https://your-backend.onrender.com or leave blank for default"
                    value={customBackendUrl}
                    onChange={(e) => setCustomBackendUrl(e.target.value)}
                    style={{ flex: 1, padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '12.5px' }}
                  />
                  <button
                    className="btn btn-navy"
                    style={{ fontSize: '12px', padding: '8px 14px', whiteSpace: 'nowrap' }}
                    onClick={() => {
                      if (typeof window !== 'undefined') {
                        if (customBackendUrl.trim()) {
                          localStorage.setItem('bidlens_backend_url', customBackendUrl.trim().replace(/\/+$/, ''));
                        } else {
                          localStorage.removeItem('bidlens_backend_url');
                        }
                        checkBackendHealth(customBackendUrl.trim());
                        setSettingsNotice('Backend connection settings saved.');
                        setTimeout(() => setSettingsNotice(''), 3000);
                      }
                    }}
                  >
                    Save &amp; Connect
                  </button>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
                  Active Endpoint: <code>{getBackendUrl() || 'Vercel Relative Proxy'}</code>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '11.5px', padding: '6px 12px' }}
                  onClick={() => checkBackendHealth(customBackendUrl)}
                  disabled={isTestingBackend}
                >
                  {isTestingBackend ? 'Testing Connection...' : 'Ping / Wake Up Server'}
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '11.5px', padding: '6px 12px' }}
                  onClick={() => {
                    setCustomBackendUrl('');
                    if (typeof window !== 'undefined') {
                      localStorage.removeItem('bidlens_backend_url');
                      checkBackendHealth('');
                    }
                  }}
                >
                  Reset to Default
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '11.5px', padding: '6px 12px', color: 'var(--critical)', borderColor: 'var(--critical-border)' }}
                  onClick={handleResetAllOverrides}
                >
                  Clear All Test Overrides
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ── 3. PASS / FAIL EVIDENCE POP-UP MODAL ─────────────────── */}
      {evidenceModalData && (
        <div className="modal-backdrop" onClick={() => setEvidenceModalData(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '16px' }}>
              <div>
                <span className={`badge ${evidenceModalData.status === 'PASS' ? 'badge-pass' : evidenceModalData.status === 'EXEMPT' ? 'badge-exempt' : 'badge-fail'}`}>
                  {evidenceModalData.status}
                </span>
                <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--navy)', marginTop: '6px' }}>
                  {evidenceModalData.title}
                </h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Vendor: {evidenceModalData.vendor}</div>
              </div>
              <button
                onClick={() => setEvidenceModalData(null)}
                style={{ background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Governing Regulation:
              </div>
              <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--navy)' }}>
                {evidenceModalData.rule}
              </div>
            </div>

            <div style={{ marginBottom: '16px', padding: '14px', backgroundColor: '#FAFAFA', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                Rule Evaluation Explanation:
              </div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-main)', lineHeight: '1.6' }}>
                "{evidenceModalData.text}"
              </div>
              <div style={{ fontSize: '11px', color: 'var(--info)', fontWeight: 600, marginTop: '8px' }}>
                Internal check: {evidenceModalData.citation}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-navy" onClick={() => setEvidenceModalData(null)}>
                Close Evidence Modal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
