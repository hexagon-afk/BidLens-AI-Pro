"""End-to-end regression checks for the non-LLM evidence demo workflow."""
import copy
import json
from pathlib import Path
import pytest
import pymupdf
from fastapi.testclient import TestClient
from fastapi import HTTPException
from main import app
from routers import audit
from evidence_risk.source_review import matching_passages, compare_results, resolve_document


@pytest.fixture
def client():
    return TestClient(app)


def sample(client, filename):
    response = client.post(f'/document/sample/load/{filename}')
    assert response.status_code == 200, response.text
    return response.json()['file_id']


def start(client, filename='Bid_GlobalCorp_Ineligible.pdf'):
    tender = client.get('/document/tender/sample').json()['tender_data']
    file_id = sample(client, filename)
    response = client.post('/audit/run', json={'file_id': file_id, 'tender_id': tender['tender_id']})
    assert response.status_code == 200, response.text
    return response.json()['results']


def revised(client, original):
    file_id = sample(client, 'Bid_GlobalCorp_Rectified_ReEvaluation.pdf')
    return client.post('/audit/run', json={'file_id': file_id, 'tender_id': original['tender_id'], 'previous_evaluation_id': original['evaluation_id']})


def test_revision_uses_frozen_original_even_after_officer_override(client):
    original = start(client)
    original_id = original['evaluation_id']
    assert original['compliance_summary']['failed'] == 5
    note = 'Officer requests verification of the warranty offer.'
    response = client.post('/audit/clause-override', json={'bid_id': original_id, 'clause_id': 'SPEC-WARRANTY', 'new_status': 'NEEDS_REVIEW', 'justification': note})
    assert response.status_code == 200
    response = revised(client, original)
    assert response.status_code == 200, response.text
    after = response.json()['results']
    comparison = client.get(f"/audit/comparison/{after['evaluation_id']}").json()
    assert after['evaluation_id'] != original_id
    assert after['parent_evaluation_id'] == original_id
    assert after['compliance_summary']['passed'] == 5
    assert comparison['changed_status_count'] == 5
    assert all(row['original_status'] == 'FAIL' and row['revised_status'] == 'PASS' for row in comparison['clauses'])
    assert comparison['source_changed'] is True
    assert audit.AUDIT_REVISIONS[original_id] == original
    assert client.get(f'/audit/status/{original_id}').json()['results']['compliance_summary']['needs_review'] == 1


def test_revision_cannot_compare_different_tender_requirements(client):
    original = start(client)
    audit.ACTIVE_TENDER_CRITERIA[original['tender_id']]['min_warranty_years'] = 5
    before = copy.deepcopy(audit.AUDIT_REVISIONS)
    response = revised(client, original)
    assert response.status_code == 409
    assert 'different tender' in response.json()['detail']
    assert audit.AUDIT_REVISIONS == before


def test_old_evaluation_override_cannot_replace_newer_document_result(client):
    original = start(client, 'Bid_MegaTech_BigBrand.pdf')
    newer = client.post('/audit/run', json={'file_id': original['document_id'], 'tender_id': original['tender_id']}).json()['results']
    assert newer['evaluation_id'] != original['evaluation_id']
    response = client.post('/audit/clause-override', json={'bid_id': original['evaluation_id'], 'clause_id': 'SPEC-WARRANTY', 'new_status': 'FAIL', 'justification': 'Review decision on the historical evaluation only.'})
    assert response.status_code == 200
    assert audit.AUDIT_CACHE[original['document_id']]['evaluation_id'] == newer['evaluation_id']
    assert audit.AUDIT_CACHE[original['document_id']]['overall_status'] == 'COMPLIANT'


def test_literal_evidence_has_real_pdf_pages_and_original_source(client):
    result = start(client, 'Bid_MegaTech_BigBrand.pdf')
    response = client.get(f"/audit/evidence/{result['evaluation_id']}/SPEC-WARRANTY")
    assert response.status_code == 200
    evidence = response.json()
    assert evidence['integrity']['status'] == 'UNCHANGED'
    assert evidence['inspection_only'] is True
    for source in evidence['sources']:
        assert source['original_available'] is True
        raw = result['tender_evidence']['raw_text'] if source['source'] == 'TENDER' else result['branch_a_extracted_data']['raw_text']
        assert source['passages']
        for passage in source['passages']:
            assert passage['quote'] in raw
            assert passage['page'] >= 1
            assert passage['match_type'] == 'KEYWORD_CANDIDATE'
        pdf = client.get(f"/audit/source/{result['evaluation_id']}/{source['source']}")
        assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    assert client.get(f"/audit/source/{result['evaluation_id']}/SECRET").status_code == 404
    assert client.get(f"/audit/evidence/{result['evaluation_id']}/UNKNOWN").status_code == 404
    assert 'path' not in json.dumps(evidence['integrity'])


def test_non_pdf_passages_do_not_invent_page_numbers_or_matches():
    text = 'Vendor declaration\nOffered warranty: 3 years onsite.\nContact: Officer A'
    passages = matching_passages(text, 'BID', 'bid.docx', 'SPEC-WARRANTY')
    assert passages[0]['page'] is None
    assert passages[0]['quote'] in text
    assert matching_passages('No extractable details.', 'BID', 'scan.png', 'SPEC-WARRANTY') == []
    ocr = matching_passages('--- Page 3 (OCR) ---\nWarranty: 3 years onsite.', 'BID', 'scan.pdf', 'SPEC-WARRANTY')
    assert ocr[0]['page'] == 3 and ocr[0]['extraction_method'] == 'OCR'


@pytest.mark.parametrize('source', ['BID', 'TENDER'])
def test_changed_sources_block_review_export_and_all_aliases(client, source, monkeypatch):
    result = start(client, 'Bid_MegaTech_BigBrand.pdf')
    evaluation_id = result['evaluation_id']
    ref = next(ref for ref in audit.AUDIT_SOURCE_REFS[evaluation_id] if ref['source'] == source)
    with open(ref['path'], 'ab') as file:
        file.write(b'\nChanged after evaluation\n')
    before = copy.deepcopy(audit.AUDIT_CACHE)
    for alias in (evaluation_id, result['document_id'], f"{result['tender_id']}::{result['document_id']}"):
        for path in ('integrity', 'report/pdf', 'evidence'):
            endpoint = f'/audit/{path}/{alias}' + ('/SPEC-WARRANTY' if path == 'evidence' else '')
            assert client.get(endpoint).status_code in ((404, 409) if '/' in alias else (409,))
        assert client.post('/audit/clause-override', json={'bid_id': alias, 'clause_id': 'SPEC-WARRANTY', 'new_status': 'FAIL', 'justification': 'Try to override a changed source.'}).status_code == 409
        assert client.post(f'/audit/overrides/reset/{alias}').status_code in ((404, 409) if '/' in alias else (409,))
        with pytest.raises(HTTPException) as blocked:
            audit.require_source_integrity(alias)
        assert blocked.value.status_code == 409
    monkeypatch.setattr(audit, 'get_gemini_config', lambda: {'api_key': 'fake-no-network', 'model': 'mock'})
    review = client.post(f'/audit/agent/review/{evaluation_id}', json={'cloud_consent': True, 'clause_id': 'SPEC-WARRANTY', 'expected_status': 'PASS', 'source_sha256': result['file_info']['source_sha256']})
    assert review.status_code == 409
    assert audit.AUDIT_CACHE == before
    trail = Path(audit.OVERRIDE_TRAIL_FILE).read_text()
    assert 'SOURCE_INTEGRITY_FAILED' in trail
    assert ref['path'] not in trail and 'expected_sha256' in trail


def test_missing_source_blocks_export(client):
    result = start(client)
    Path(audit.AUDIT_SOURCE_REFS[result['evaluation_id']][0]['path']).unlink()
    assert client.get(f"/audit/report/pdf/{result['evaluation_id']}").status_code == 409
    assert client.get('/audit/report/pdf/unknown').status_code == 404


def test_checklist_receipt_does_not_change_compliance_and_is_in_pdf(client):
    result = start(client, 'Bid_MegaTech_BigBrand.pdf')
    evaluation_id = result['evaluation_id']
    note = 'Officer confirmed the original warranty source needs inspection.'
    assert client.post('/audit/clause-override', json={'bid_id': result['document_id'], 'clause_id': 'SPEC-WARRANTY', 'new_status': 'NEEDS_REVIEW', 'justification': note}).status_code == 200
    before = copy.deepcopy(audit.AUDIT_CACHE[evaluation_id])
    response = client.post(f'/audit/checklist/{evaluation_id}', json={'items': [
        {'item_id': 'finance', 'name': 'Audited financial statement'},
        {'item_id': 'proposal', 'name': 'Vendor proposal', 'file_id': result['document_id']}]})
    assert response.status_code == 200, response.text
    items = response.json()['items']
    assert items[0]['receipt_status'] == 'MISSING'
    assert items[1]['receipt_status'] == 'RECEIVED_UNVERIFIED'
    assert len(items[1]['sha256']) == 64
    assert audit.AUDIT_CACHE[evaluation_id] == before
    report = client.get(f'/audit/report/pdf/{evaluation_id}')
    assert report.status_code == 200
    with pymupdf.open(stream=report.content, filetype='pdf') as pdf:
        text = '\n'.join(page.get_text() for page in pdf)
    assert evaluation_id in text and note in ' '.join(text.split())
    assert 'Audited financial statement: MISSING' in text
    assert 'Vendor proposal: RECEIVED_UNVERIFIED' in text
    assert client.post(f'/audit/overrides/reset/{result["document_id"]}').status_code == 200
    assert evaluation_id not in audit.AUDIT_OVERRIDES


def test_unreadable_attachment_is_needs_inspection_and_tamper_blocks_export(client, monkeypatch):
    result = start(client)
    import orchestrator.ai_processing as processing
    monkeypatch.setattr(processing, 'get_ocr_engine', lambda: None)
    with pymupdf.open() as pdf:
        pdf.new_page()
        content = pdf.tobytes()
    uploaded = client.post('/document/upload', files={'file': ('blank.pdf', content, 'application/pdf')})
    assert uploaded.status_code == 200
    file_id = uploaded.json()['file_id']
    endpoint = f"/audit/checklist/{result['evaluation_id']}"
    response = client.post(endpoint, json={'items': [{'item_id': 'cert', 'name': 'Certificate', 'file_id': file_id}]})
    assert response.status_code == 200
    assert response.json()['items'][0]['receipt_status'] == 'NEEDS_INSPECTION'
    path = Path(resolve_document(file_id, audit.UPLOAD_DIR, audit.SAMPLE_DIRS))
    path.write_bytes(content + b'\nCHANGED')
    assert client.get(endpoint).status_code == 409
    assert client.post(endpoint, json={'items': []}).status_code == 409
    assert client.get(f"/audit/report/pdf/{result['evaluation_id']}").status_code == 409


@pytest.mark.parametrize('items,status', [
    ([{'item_id': 'x', 'name': 'First'}, {'item_id': 'x', 'name': 'Second'}], 400),
    ([{'item_id': 'x', 'name': '  '}], 400),
    ([{'item_id': 'x', 'name': 'Document', 'file_id': '../outside.pdf'}], 400),
    ([{'item_id': 'x', 'name': 'Document', 'file_id': 'not-uploaded'}], 404),
    ([{'item_id': str(i), 'name': 'Document'} for i in range(21)], 422),
])
def test_invalid_checklists_do_not_save_partial_results(client, items, status):
    result = start(client)
    endpoint = f"/audit/checklist/{result['evaluation_id']}"
    assert client.post(endpoint, json={'items': items}).status_code == status
    assert client.get(endpoint).json()['items'] == []


def test_turnover_comparison_aligns_msme_and_non_msme_clause_ids():
    original = {'tender_id': 'T1', 'tender_requirements': {}, 'clause_level_decisions': [{'clause_id': 'GFR-160-MSME', 'status': 'NEEDS_REVIEW'}]}
    revised = {**original, 'clause_level_decisions': [{'clause_id': 'GFR-160-TO', 'status': 'PASS'}]}
    rows = compare_results(original, revised)['clauses']
    assert len(rows) == 1 and rows[0]['original_status'] == 'NEEDS_REVIEW' and rows[0]['revised_status'] == 'PASS'


def test_unknown_parent_or_expired_session_is_explicit(client):
    file_id = sample(client, 'Bid_GlobalCorp_Rectified_ReEvaluation.pdf')
    assert client.post('/audit/run', json={'file_id': file_id, 'previous_evaluation_id': 'expired'}).status_code == 404
    assert client.get('/audit/comparison/expired').status_code == 404


def test_unreadable_bid_still_has_an_original_document_link(client, monkeypatch):
    import orchestrator.ai_processing as processing
    monkeypatch.setattr(processing, 'get_ocr_engine', lambda: None)
    with pymupdf.open() as pdf:
        pdf.new_page()
        content = pdf.tobytes()
    uploaded = client.post('/document/upload', files={'file': ('blank.pdf', content, 'application/pdf')}).json()
    response = client.post('/audit/run', json={'file_id': uploaded['file_id']})
    assert response.status_code == 200
    result = response.json()['results']
    evidence = client.get(f"/audit/evidence/{result['evaluation_id']}/SPEC-WARRANTY").json()
    bid = next(group for group in evidence['sources'] if group['source'] == 'BID')
    assert bid['original_available'] is True and bid['passages'] == []
    assert evidence['current_status'] == 'NEEDS_REVIEW'
    assert client.get(f"/audit/source/{result['evaluation_id']}/BID").content == content
