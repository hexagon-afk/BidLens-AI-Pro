# BidLens AI — Documentation & Evaluator Dossier 📚

**Smart India Hackathon (SIH) 2026 — Problem Statement ID: 26100**  
**Team Hexagon (SIH26009)**

---

## 📄 Master Project Handover
The official evaluated dossier is preserved in this directory:
- [`SIH26100_BidLens_Project_Master_Handover.pdf`](./SIH26100_BidLens_Project_Master_Handover.pdf) — Comprehensive architecture, statutory rule matrix, and operational deployment guide.

## 🏛️ System Architecture Summary
- **Layer 1: Edge Document Ingestion & Sanitization** (`backend/security/sha256_audit.py`)
- **Layer 2: Sovereign FastAPI Backend** (`backend/main.py`, `backend/routers/`)
- **Layer 3: Deterministic GFR 2017 Rule Engine** (`backend/orchestrator/rule_engine.py`)
- **Layer 4: Cross-Document Contradiction & Knowledge Graph** (`backend/orchestrator/contradiction.py`, `backend/orchestrator/graph_engine.py`)
- **Layer 5: Certified PDF Audit Dossier Generator** (`backend/utils/pdf_generator.py`)
- **Layer 6: Edge Sovereignty & CERT-In Compliance** (`backend/security/offline_mode.py`)

## 🧪 Verification & Testing
Run all automated tests locally:
```bash
python -m unittest discover backend/tests
```
