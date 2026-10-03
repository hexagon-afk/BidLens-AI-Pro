import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture(autouse=True)
def isolated_audit_storage(tmp_path, monkeypatch):
    from routers import audit, document, review
    reports = tmp_path / "reports"
    uploads = tmp_path / "uploads"
    reports.mkdir()
    uploads.mkdir()
    monkeypatch.setattr(audit, "REPORTS_DIR", str(reports))
    monkeypatch.setattr(audit, "OVERRIDE_TRAIL_FILE", str(reports / "override.jsonl"))
    for module in (audit, document, review):
        monkeypatch.setattr(module, "UPLOAD_DIR", str(uploads))
    monkeypatch.setattr(review, "LOG_FILE", str(tmp_path / "review.json"))
    for cache in (audit.AUDIT_CACHE, audit.AUDIT_OVERRIDES, audit.ACTIVE_TENDER_CRITERIA, audit.ACTIVE_TENDER_EVIDENCE, audit.ACTIVE_TENDER_SOURCE_PATHS, audit.AUDIT_REVISIONS, audit.AUDIT_SOURCE_REFS, audit.AUDIT_CHECKLISTS):
        cache.clear()
    audit.AUDIT_OVERRIDE_EVENTS.clear()
    audit.AI_REVIEWS_IN_FLIGHT.clear()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("orchestrator.llm_agent.dotenv_values", lambda *a, **kw: {})
    yield
    audit.AUDIT_CACHE.clear()
    audit.AUDIT_OVERRIDES.clear()
    audit.AUDIT_OVERRIDE_EVENTS.clear()
