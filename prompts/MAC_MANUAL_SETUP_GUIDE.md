# Sovereign On-Prem Agentic AI Workbench — macOS Developer Guide

This guide details how to set up, run, and develop the **Sovereign On-Prem Agentic AI Workbench (MRPL OmniAI™)** on macOS (Apple Silicon M1/M2/M3/M4 or Intel).

---

## Prerequisites (macOS)

1. **Homebrew**:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. **Python 3.10, 3.11, or 3.12**:
   ```bash
   brew install python@3.11
   ```
3. **Node.js (v18+) & npm**:
   ```bash
   brew install node
   ```
4. **Docker Desktop for Mac**:
   Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then open it.
5. **Ollama for Mac**:
   ```bash
   brew install ollama
   # Start Ollama service in background or launch the Ollama macOS application
   ollama serve
   ```

---

## 1. Local Ollama Model Fleet (macOS Apple Silicon / Intel)

Pull the 5 required sovereign models into your local Ollama store:

```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5vl:7b
ollama pull qwen2.5-coder:3b
ollama pull deepseek-r1:1.5b
```

Verify installed models:
```bash
ollama list
```

---

## 2. Start PostgreSQL Database

In the repository root:
```bash
docker compose up -d
```
*Note*: This runs PostgreSQL on host port `5433` (mapped from container port 5432).

---

## 3. Backend Setup & Data Initialization

```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database schema migrations
python scripts/migrate_db.py

# Seed ChromaDB Vector Knowledge Base with official SOP documents
python scripts/seed_kb.py
```

---

## 4. Run Automated Test Verification

Verify all backend subsystems and agent pipelines:

```bash
python scripts/test_equipment_graph.py    # Knowledge graph auto-ingest & SQL JSONB filter
python scripts/test_semantic_cache.py     # Vector cache hits & <0.2s short-circuit
python scripts/test_safety_gate.py        # Corrective RAG grading & human approval gate
python scripts/test_cross_doc_count.py    # Cross-document query count & cap
python scripts/test_multi_agent.py        # 4 specialist agents pipeline (Extractor, Compliance, Drafter, Verifier)
```

---

## 5. Frontend Setup

In a separate terminal tab:

```bash
cd frontend

# Install Node dependencies
npm install

# Test TypeScript compilation and production build
npm run build

# Start Vite Development Server
npm run dev
```

---

## 6. Running the Stack

| Service | Command | URL |
|---|---|---|
| **Frontend UI** | `cd frontend && npm run dev` | [http://localhost:5173](http://localhost:5173) |
| **Backend API** | `cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | [http://localhost:8000](http://localhost:8000) |
| **Swagger Docs** | *Runs with backend* | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Health Check** | `curl -s http://localhost:8000/health` | [http://localhost:8000/health](http://localhost:8000/health) |

---

## Troubleshooting on macOS

- **Port 5433 already in use**:
  If another Postgres instance is running on port 5433, edit `docker-compose.yml` and `backend/.env` to use another port (e.g. `5434`).
- **Ollama connection refused**:
  Ensure Ollama is running (`pgrep ollama` or launch the Ollama app from Applications).
- **HuggingFace Sentence-Transformers Offline warning**:
  On first run of `seed_kb.py`, the system downloads `sentence-transformers/all-MiniLM-L6-v2` to your local cache (`~/.cache/huggingface/hub/`). Subsequent executions run 100% offline.
