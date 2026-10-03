"""Read-only source inspection and machine-result comparison. No model calls."""
import hashlib
import os
import re
from pathlib import Path


CHECKS = {
    'GST': ('GSTIN Registration & Tax Compliance', r'\b(?:gstin|gst|pan|tax registration)\b'),
    'TURNOVER': ('Annual Financial Turnover', r'\b(?:turnover|annual revenue|financial statement|udyam|msme|mse)\b'),
    'EMD': ('Earnest Money Deposit', r'\b(?:emd|earnest|bank guarantee|bid security|udyam|msme|mse)\b'),
    'LOCAL_CONTENT': ('Local Content', r'\b(?:local content|make in india|class[ -]?[12]|domestic content)\b'),
    'WARRANTY': ('Warranty & Service', r'\b(?:warranty|onsite|on-site|carry[ -]?in|service support)\b'),
}


def check_family(clause_id):
    if clause_id.startswith('GFR-149'):
        return 'GST'
    if clause_id.startswith('GFR-160'):
        return 'TURNOVER'
    if clause_id.startswith('GFR-170'):
        return 'EMD'
    if clause_id.startswith('MII'):
        return 'LOCAL_CONTENT'
    if clause_id.startswith('SPEC-WARRANTY'):
        return 'WARRANTY'
    return clause_id


def resolve_document(file_id, upload_dir, sample_dirs):
    """Resolve an opaque document ID within configured storage, never an arbitrary path."""
    if not file_id or any(c in file_id for c in ('/', '\\', ':')) or file_id in ('.', '..'):
        raise ValueError('Invalid document ID.')
    for directory, uploaded in [(upload_dir, True)] + [(d, False) for d in sample_dirs]:
        root = Path(directory).resolve()
        if not root.is_dir():
            continue
        for name in sorted(os.listdir(root)):
            match = name == file_id or (uploaded and name.startswith(file_id + '_')) or (not uploaded and name.lower() == file_id.lower())
            if match:
                path = (root / name).resolve()
                if path.is_file() and path.is_relative_to(root):
                    return str(path)
    return None


def matching_passages(text, source, filename, clause_id, digest=None):
    """Return literal candidate passages, not a claim that keyword matches prove compliance."""
    pattern = CHECKS.get(check_family(clause_id), ('', re.escape(clause_id)))[1]
    markers = list(re.finditer(r'--- Page (\d+)([^\n]*)---\s*', text))
    spans = [(int(m.group(1)), 'OCR' if 'OCR' in m.group(2) else 'EXTRACTED_TEXT', text[m.end():markers[i+1].start() if i+1 < len(markers) else len(text)]) for i,m in enumerate(markers)]
    if not markers:
        spans = [(None, 'EXTRACTED_TEXT', text)]
    passages = []
    seen = set()
    for page, method, content in spans:
        lines = list(re.finditer(r'[^\n]+', content))
        for index, line in enumerate(lines):
            if not re.search(pattern, line.group(), re.I):
                continue
            end = lines[min(index + 1, len(lines)-1)].end()
            quote = content[line.start():min(end, line.start()+700)].strip()
            if len(quote) < 5 or quote in seen:
                continue
            seen.add(quote)
            evidence_id = hashlib.sha256(f'{source}:{page}:{line.start()}:{quote}'.encode()).hexdigest()[:16]
            passages.append({'evidence_id': evidence_id, 'source': source, 'filename': filename,
                             'page': page, 'extraction_method': method, 'quote': quote,
                             'source_sha256': digest, 'match_type': 'KEYWORD_CANDIDATE'})
            if len(passages) == 4:
                return passages
    return passages


def inspect_check(result, clause_id):
    clause = next((c for c in result.get('clause_level_decisions', []) if c['clause_id'] == clause_id), None)
    if clause is None:
        raise KeyError(clause_id)
    extracted = result.get('branch_a_extracted_data', {})
    tender = result.get('tender_evidence', {})
    groups = []
    for source, text, filename, digest, complete in [
        ('TENDER', tender.get('raw_text') or '', tender.get('filename') or 'Tender source', tender.get('sha256'), tender.get('extraction_complete')),
        ('BID', extracted.get('raw_text') or '', result.get('file_info', {}).get('filename', 'Bid source'), result.get('file_info', {}).get('source_sha256'), extracted.get('extraction_complete')),
    ]:
        groups.append({'source': source, 'filename': filename, 'text_available': bool(text.strip()),
                       'extraction_complete': complete,
                       'passages': matching_passages(text, source, filename, clause_id, digest)})
    return {'clause_id': clause_id, 'machine_status': clause.get('machine_original_status', clause.get('status')),
            'current_status': clause.get('status'), 'evaluation_id': result.get('evaluation_id'),
            'tender_requirements': result.get('tender_requirements', {}), 'sources': groups,
            'inspection_only': True,
            'notice': 'These are literal keyword-matched passages for officer inspection, not verified clause-to-evidence mappings. Missing matches do not prove missing evidence. No verdict changed.'}


def compare_results(original, revised):
    if original.get('tender_id') != revised.get('tender_id') or original.get('tender_requirements') != revised.get('tender_requirements') or original.get('tender_evidence', {}).get('sha256') != revised.get('tender_evidence', {}).get('sha256'):
        raise ValueError('These evaluations use different tender criteria or source versions. Re-evaluate both against the same tender before comparison.')
    before = {check_family(c['clause_id']): c for c in original.get('clause_level_decisions', [])}
    after = {check_family(c['clause_id']): c for c in revised.get('clause_level_decisions', [])}
    rows = []
    for family in dict.fromkeys([*before, *after]):
        a, b = before.get(family, {}), after.get(family, {})
        rows.append({'check': CHECKS.get(family, (family,''))[0], 'original_clause_id': a.get('clause_id'), 'revised_clause_id': b.get('clause_id'),
                     'original_status': a.get('status', 'NOT_EVALUATED'), 'revised_status': b.get('status', 'NOT_EVALUATED'),
                     'status_changed': a.get('status') != b.get('status'), 'evidence_changed': a.get('evidence') != b.get('evidence'),
                     'original_evidence': a.get('evidence'), 'revised_evidence': b.get('evidence')})
    fields = ('gstin','pan','turnover_cr','emd_status','emd_amount_inr','local_content_pct','warranty','total_quote_inr')
    a, b = original.get('branch_a_extracted_data', {}), revised.get('branch_a_extracted_data', {})
    changes = [{'field': key, 'original': a.get(key), 'revised': b.get(key)} for key in fields if a.get(key) != b.get(key)]
    return {'original': {k: original.get(k) for k in ('evaluation_id','evaluated_at','overall_status','compliance_summary','file_info')},
            'revised': {k: revised.get(k) for k in ('evaluation_id','evaluated_at','overall_status','compliance_summary','file_info')},
            'clauses': rows, 'changed_fields': changes, 'changed_status_count': sum(r['status_changed'] for r in rows),
            'source_changed': original.get('file_info', {}).get('source_sha256') != revised.get('file_info', {}).get('source_sha256'),
            'vendor_identity_changed': original.get('file_info', {}).get('vendor_name') != revised.get('file_info', {}).get('vendor_name'),
            'notice': 'Comparison uses frozen machine evaluations linked by the officer. Attachment authenticity and vendor identity are not verified. Session records disappear after backend restart.'}
