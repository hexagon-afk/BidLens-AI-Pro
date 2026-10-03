"""Reports implemented local capabilities; no inferred security certification."""
import os
import platform
from orchestrator.llm_agent import get_gemini_config


def get_system_health_status() -> dict:
    gemini = get_gemini_config()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploaded_dir = os.path.join(base_dir, "uploaded_docs")
    reports_dir = os.path.join(base_dir, "generated_reports")
    return {
        "system_status": "OPERATIONAL", "mode": "LOCAL_DETERMINISTIC_CORE",
        "data_consumption_kb": None, "network_traffic_measurement": "NOT_INSTRUMENTED",
        "cloud_data_retention": "Core evaluation runs locally. Optional Gemini review sends retrieved excerpts to Google; provider terms apply.",
        "ai_capabilities": {"document_ocr": "RapidOCR / ONNX Runtime", "llm_review_enabled": bool(gemini["api_key"]),
                            "llm_integration": "IMPLEMENTED_CONFIGURED" if gemini["api_key"] else "IMPLEMENTED_KEY_REQUIRED", "llm_model": gemini["model"],
                            "llm_cloud_processing": True, "agentic_llm_flow": "BOUNDED_READ_ONLY_EVIDENCE_TOOLS"},
        "security_integrity": {
            "cryptographic_fingerprinting": "SHA-256 source document digest",
            "audit_log": "Local append-only JSONL; not cryptographically tamper-evident",
            "compliance_ruleset": "Deterministic checks against parsed or officer-supplied tender criteria",
            "guidelines_alignment": "PROTOTYPE_BASELINE"
        },
        "environment": {"os": platform.system() + " " + platform.release(),
                        "python_runtime": platform.python_version(), "backend_port": 8000, "frontend_port": 3000},
        "storage": {"uploaded_documents_count": len(os.listdir(uploaded_dir)) if os.path.isdir(uploaded_dir) else 0,
                    "generated_reports_count": len(os.listdir(reports_dir)) if os.path.isdir(reports_dir) else 0}
    }
