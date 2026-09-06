# Setup Prompt for Gemini 3.7 Flash (AI IDE on macOS)

> **Instructions for the User**: Copy and paste the entire prompt below into your Gemini 3.7 Flash chat in your Mac IDE (e.g. Gemini Code Assist / Cursor / Windsurf / VS Code).

---

```markdown
You are an expert full-stack AI engineer powered by Gemini 3.7 Flash. You are setting up, configuring, and verifying the "Sovereign On-Prem Agentic AI Workbench (MRPL OmniAI™)" on this Mac (macOS).

This repository is an enterprise-grade, air-gapped sovereign AI workbench designed for refinery operations. It consists of:
1. Backend (FastAPI, Python 3.10+):
   - Database: PostgreSQL on port 5433 (via Docker) with JSONB structured event logging.
   - Vector Store: Local ChromaDB (`backend/storage/chroma`) embedded with `sentence-transformers/all-MiniLM-L6-v2`.
   - Local LLM Fleet: 5 Ollama models (`qwen2.5:3b`, `qwen2.5:7b-instruct`, `qwen2.5vl:7b`, `qwen2.5-coder:3b`, `deepseek-r1:1.5b`).
   - Multi-Agent Pipeline for `doc_gen`: 4 sequential specialist agents (`agent_extractor`, `agent_compliance`, `agent_drafter`, `agent_verifier`) + Corrective RAG grading + Semantic Response Caching (<0.2s short-circuit) + Mandatory human approval gate (`pending_approval`).
   - Equipment Knowledge Graph: `equipment_nodes` and `equipment_events` tables with SQL criteria filtering.
2. Frontend (React 19, TypeScript, Vite, TailwindCSS, Lucide):
   - Omni AI Studio, Document Vision Studio, Task Execution Ledger, Equipment Knowledge Graph Topology & Timelines, Air-Gap SOC Monitor.

YOUR OBJECTIVE:
Autonomously run the required terminal commands, set up all dependencies, pull the 5 models, run database migrations, seed the vector store, execute all verification test scripts, and launch both the Backend and Frontend servers.

Execute the following 5 phases step-by-step:

══════════════════════════════════════════════════════════════════════
PHASE 1: ENVIRONMENT & HARDWARE SERVICES (macOS)
══════════════════════════════════════════════════════════════════════
1. Check that Docker and Ollama are available:
   - Check Docker: `docker info`
     (If Docker is not running, alert the user to open Docker Desktop).
   - Start PostgreSQL container:
     `docker compose up -d`
     Confirm container `sovereign_pg` is active on port 5433 (`docker ps | grep sovereign_pg`).

2. Check Ollama and pull the 5 required models:
   - Check if Ollama is running: `ollama list`
     (If Ollama is stopped, start it via `ollama serve &` or launch the Ollama macOS application).
   - Pull any missing models:
     `ollama pull qwen2.5:3b`             # Low-latency planner & extractor
     `ollama pull qwen2.5:7b-instruct`    # Executive compliance & doc synthesis
     `ollama pull qwen2.5vl:7b`          # Vision-Language Model for OCR
     `ollama pull qwen2.5-coder:3b`       # Python sandbox & math computation
     `ollama pull deepseek-r1:1.5b`       # Chain-of-thought deep reasoning

══════════════════════════════════════════════════════════════════════
PHASE 2: BACKEND VIRTUAL ENVIRONMENT & DATABASE MIGRATIONS
══════════════════════════════════════════════════════════════════════
1. In `backend/`, create a virtual environment and install requirements:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Confirm `backend/.env` exists with:
   `DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@localhost:5433/sovereign_db`

3. Apply Alembic migrations to create tables (`tasks`, `task_steps`, `memory_entries`, `memory_links`, `equipment_nodes`, `equipment_events`):
   ```bash
   python scripts/migrate_db.py
   ```

4. Seed the ChromaDB vector database with official SOP documents:
   ```bash
   python scripts/seed_kb.py
   ```

══════════════════════════════════════════════════════════════════════
PHASE 3: AUTOMATED TEST VERIFICATION
══════════════════════════════════════════════════════════════════════
Run all test scripts in `backend/` to verify every subsystem:
```bash
python scripts/test_equipment_graph.py    # Knowledge Graph ingest & JSONB filtering
python scripts/test_semantic_cache.py     # Vector cache hit (<0.2s short-circuit)
python scripts/test_safety_gate.py        # Corrective RAG grading & approval gate
python scripts/test_cross_doc_count.py    # Cross-document query count & cap
python scripts/test_multi_agent.py        # 4 specialist agents pipeline
```
Ensure all tests complete with exit code 0.

══════════════════════════════════════════════════════════════════════
PHASE 4: FRONTEND SETUP & PRODUCTION BUILD
══════════════════════════════════════════════════════════════════════
1. In `frontend/`, install npm packages and verify TypeScript compilation:
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```

══════════════════════════════════════════════════════════════════════
PHASE 5: START LOCAL SERVERS & CONFIRM HEALTH
══════════════════════════════════════════════════════════════════════
1. Start the Backend server (FastAPI):
   ```bash
   cd ../backend
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Start the Frontend dev server (Vite):
   ```bash
   cd ../frontend
   npm run dev -- --host 0.0.0.0 --port 5173
   ```

3. Health Check:
   - Run `curl -s http://localhost:8000/health` and confirm:
     - `"db": "connected"`
     - `"ollama_status": "connected"`
     - `"active_models_count": 5`
   - Frontend is available at `http://localhost:5173`.

Summarize the system health and provide the clickable URLs once everything is running.
```
