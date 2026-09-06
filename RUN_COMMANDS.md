# MRPL Sovereign On-Prem Agentic AI Workbench
## Complete Running Commands Reference

This file contains every command required to initialize, configure, start, test, and interact with the MRPL Sovereign Workbench.

---

## 1. Quick Start (All-in-One Commands)

### A. Start Backend Server (Terminal 1)
```powershell
cd c:\sih117\prototype\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*(Or single-line without activating: `cd c:\sih117\prototype\backend; .\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000`)*

### B. Start Frontend UI (Terminal 2)
```powershell
cd c:\sih117\prototype\frontend
npm run dev
```

### Access URLs:
- **Frontend Workbench UI**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 2. Environment & Model Setup

### A. Pull Local Ollama AI Models
Ensure Ollama is running (`ollama serve`), then pull the required models:
```powershell
# High-throughput reasoning, code generation & multi-agent synthesis
ollama pull qwen2.5:3b

# Scanned engineering drawing & PDF multimodal vision OCR
ollama pull qwen2.5vl:7b

# (Optional) Deep reasoning and memorandum drafting
ollama pull qwen2.5:7b-instruct
```

### B. Start Local Database (PostgreSQL)
```powershell
cd c:\sih117\prototype
docker-compose up -d
```
> **Note on Database Auto-Fallback**: If Docker is not running or port `5433` is unavailable, the backend automatically falls back to local SQLite at `backend/storage/sovereign.db`.

---

## 3. Database Initialization & Seeding

Navigate to backend directory:
```powershell
cd c:\sih117\prototype\backend
.\venv\Scripts\Activate.ps1
```

### A. Run Database Migrations (Alembic)
```powershell
alembic upgrade head
```

### B. Seed Initial Demo Equipment & Tasks
```powershell
python seed.py
```

### C. Seed Vector Knowledge Base (ChromaDB)
```powershell
python scripts/seed_kb.py
```

---

## 4. Running Backend Automated Test Suites & Hardening Verification

All test suites can be executed independently from the `backend/` directory using the virtualenv python:

```powershell
cd c:\sih117\prototype\backend
```

### A. Architectural Hardening Test Suites (Items 1 – 14)

#### 1. Versioned Rule Config & Locale Decimal Sanitization (Items 2, 10)
Verifies external JSON thresholds (`thresholds_config.json` v1.2.0), comma parsing (`7,1` -> `7.1`), and >100x implausible reading rejection:
```powershell
.\venv\Scripts\python.exe scripts/test_rule_config_and_sanitization.py
```

#### 2. Deterministic Rule Engine Safety Override Block (Item 2)
Proves that no code path exists where an advisory LLM verdict can override a deterministic rule engine `NON_COMPLIANT` verdict:
```powershell
.\venv\Scripts\python.exe scripts/test_rule_safety_override_block.py
```

#### 3. Intent Router Precision & Disambiguation Evaluation (Item 1)
Tests 52 held-out refinery engineering prompts; reports precision/recall (>90%) and verifies below-threshold (<0.65) interactive disambiguation:
```powershell
.\venv\Scripts\python.exe scripts/test_intent_router_eval.py
```

#### 4. Diverse 3-Model Ensemble & Dissent Auditing (Item 3)
Verifies 3 distinct model configurations (7B temp 0.0, 7B temp 0.3, 3B temp 0.7) and verbatim split vote dissent logging to `storage/dissent_records.jsonl`:
```powershell
.\venv\Scripts\python.exe scripts/test_ensemble_dissent_logging.py
```

#### 5. Python AST Code Sandbox Isolation (Item 5)
Proves that blocked imports (`subprocess`, `os`, `socket`, `eval`, `exec`, `sys`) and arbitrary file access are rejected via AST analysis before execution:
```powershell
.\venv\Scripts\python.exe scripts/test_sandbox_hardening.py
```

#### 6. Safety-Critical Zero-Decay Memory (Item 6)
Proves that Zone C/D faults and SOP violations (`safety_critical=True`) maintain 100% weight retention while casual entries experience normal Ebbinghaus decay:
```powershell
.\venv\Scripts\python.exe scripts/test_memory_decay_safety.py
```

#### 7. Tamper-Evident Approval Hash Chain & Verification (Item 7)
Proves cryptographic hash chaining ($H_n = \text{SHA256}(H_{n-1} + \text{Payload})$), independent forensics mirroring, and `/audit/verify` tampering detection:
```powershell
.\venv\Scripts\python.exe scripts/test_audit_hash_chain.py
```

#### 8. Air-Gap Dependency & Network Call Scanner (Item 8)
Scans codebase dependencies for rogue outbound network calls outside local allow-listed endpoints:
```powershell
.\venv\Scripts\python.exe scripts/scan_airgap_dependencies.py
```

#### 9. Dual-Engine DB Feature Parity & Role Gating (Items 4, 9)
Tests PostgreSQL vs SQLite feature parity on concurrent writes, JSON-graph queries, and role-gating (Supervisor vs Operator 403 blocks):
```powershell
.\venv\Scripts\python.exe scripts/test_db_backend_parity.py
```

#### 10. DocGen 5-Stage Partial Failure Halting & Grounding Breakdown (Item 11)
Proves that stage failures halt the pipeline at stage N and never reach pending approval; verifies explainable verifier deductions:
```powershell
.\venv\Scripts\python.exe scripts/test_docgen_failure_handling.py
```

#### 11. OCR Text Layer Quality & Vision Confidence Gating (Item 12)
Proves garbled/partial digital PDFs fall back to Vision OCR and low-confidence numeric extractions (<85%) are gated:
```powershell
.\venv\Scripts\python.exe scripts/test_ocr_quality_and_confidence.py
```

#### 12. Non-Linear Polynomial & Exponential Trend Forecasting (Item 13)
Compares linear vs degree-2 polynomial fits, detects accelerating degradation, and selects conservative failure dates:
```powershell
.\venv\Scripts\python.exe scripts/test_predictive_nonlinear_trends.py
```

#### 13. Cross-Document Inline Citation & Verification (Item 14)
Proves that multi-document briefings generate inline `[Task #<id>:<field>]` citations and hallucinations are caught during the post-verification pass:
```powershell
.\venv\Scripts\python.exe scripts/test_cross_doc_citations.py
```

---

### B. Execute Master Automated Test Runner (All 20 Test Suites)
Run the master PowerShell test runner from the root directory:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
```

---

## 5. Frontend Development & Build Commands

Navigate to frontend directory:
```powershell
cd c:\sih117\prototype\frontend
```

### A. Install Frontend Dependencies
```powershell
npm install
```

### B. Start Vite Development Server
```powershell
npm run dev
```

### C. Build Production Bundle (TypeScript + Vite)
```powershell
npm run build
```

### D. Preview Production Build Locally
```powershell
npm run preview
```

---

## 6. Convenient One-Click Windows Launcher Scripts

For immediate convenience, you can also run the helper scripts located in the root directory:

- **Start All (New Windows)**: Double-click `start_all.bat` or run:
  ```cmd
  .\start_all.bat
  ```
- **Run All Verification Tests**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\run_tests.ps1
  ```
