# PROMPT FOR ANTIGRAVITY (macOS Setup & Deployment)

> **Instructions for the User**: Copy and paste the entire prompt below into Antigravity on your Mac after cloning this repository.

---

```markdown
You are Antigravity, setting up and running the "Sovereign On-Prem Agentic AI Workbench (MRPL OmniAI™)" on macOS (Darwin, Apple Silicon / Intel).

This is an enterprise-grade, air-gapped agentic AI workbench built with:
- Backend: FastAPI, SQLAlchemy (asyncpg), PostgreSQL, Alembic migrations, ChromaDB (local sentence-transformers/all-MiniLM-L6-v2), and local Ollama fleet.
- Multi-Agent Specialist Pipeline: 4 sequential specialist agents for doc_gen (`agent_extractor`, `agent_compliance`, `agent_drafter`, `agent_verifier`), Corrective RAG grading, self-critique, semantic caching (<0.2s short-circuit), and mandatory human approval gates.
- Equipment Knowledge Graph: PostgreSQL JSONB criteria querying (`equipment_nodes`, `equipment_events`) and REST endpoints.
- Frontend: React 19, TypeScript, Vite, TailwindCSS, Lucide icons, interactive Topology & Timeline views.

YOUR GOAL:
Inspect, configure, and launch the complete stack on macOS so that both the Backend (FastAPI on port 8000) and Frontend (Vite on port 5173) are 100% operational with all 5 local Ollama models, PostgreSQL database, ChromaDB vector store, and test suites passing.

Follow this systematic setup workflow:

=====================================================================
STEP 1: PRE-FLIGHT SYSTEM CHECKS & DEPENDENCY INSTALLATION (macOS)
=====================================================================
1. Check Homebrew, Docker, Python 3.10+, Node.js (v18+), and Ollama:
   ```bash
   which docker python3 node npm ollama
   ```
   If Docker is not running, ensure Docker Desktop is started (`open -a Docker`).
   If Ollama is not installed: `brew install ollama` (or download from ollama.com).

2. Start PostgreSQL container using docker-compose:
   ```bash
   docker compose up -d
   ```
   Verify PostgreSQL container `sovereign_pg` is healthy and listening on port 5433:
   ```bash
   docker ps | grep sovereign_pg
   ```

3. Ensure Ollama service is active and pull all 5 required local models:
   ```bash
   ollama list
   ```
   Ensure the following 5 models are present (pull any that are missing):
   - `ollama pull qwen2.5:3b`             # Low-latency planner & extractor
   - `ollama pull qwen2.5:7b-instruct`    # Executive synthesis & compliance agent
   - `ollama pull qwen2.5vl:7b`          # Vision-Language Model for OCR
   - `ollama pull qwen2.5-coder:3b`       # Python sandbox & mathematical computation
   - `ollama pull deepseek-r1:1.5b`       # Deep reasoning & root-cause verification

=====================================================================
STEP 2: BACKEND VIRTUAL ENVIRONMENT & DATABASE MIGRATIONS
=====================================================================
1. Navigate to `backend/`, create a virtual environment, and install dependencies:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Create/Verify `backend/.env`:
   ```bash
   DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@localhost:5433/sovereign_db
   ```

3. Run Alembic Database Migrations & Initial Setup:
   ```bash
   python scripts/migrate_db.py
   ```

4. Seed the ChromaDB Vector Knowledge Base with official SOP documents:
   ```bash
   python scripts/seed_kb.py
   ```

=====================================================================
STEP 3: EXECUTE AUTOMATED TEST SUITE VERIFICATION
=====================================================================
Run the test scripts to verify all subsystems:
```bash
python scripts/test_equipment_graph.py    # Ingest, query & criteria filtering
python scripts/test_semantic_cache.py     # Chroma vector cache hit & speedup
python scripts/test_safety_gate.py        # Corrective RAG + Approval gate
python scripts/test_cross_doc_count.py    # Cross-document query count & cap
python scripts/test_multi_agent.py        # 4 specialist agents pipeline
```
Ensure all tests pass with code 0.

=====================================================================
STEP 4: FRONTEND DEPENDENCY INSTALLATION & BUILD
=====================================================================
1. Navigate to `frontend/`, install npm packages and verify build:
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

=====================================================================
STEP 5: LAUNCH BACKGROUND SERVICES & VERIFY HEALTH
=====================================================================
1. Start the Backend server (FastAPI):
   ```bash
   cd ../backend
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Start the Frontend server (Vite):
   ```bash
   cd ../frontend
   npm run dev -- --host 0.0.0.0 --port 5173
   ```

3. Verify Health:
   - Backend API: `curl -s http://localhost:8000/health` (confirm db="connected", ollama="connected", 5 active models).
   - Frontend UI: Open `http://localhost:5173` in the browser.

Provide a concise status report once all services are active and reachable.
```
