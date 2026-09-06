#!/usr/bin/env bash
set -e

# ==============================================================================
# Sovereign On-Prem Agentic AI Workbench (MRPL OmniAI™) — macOS One-Click Setup
# ==============================================================================

echo "======================================================================"
echo "  Sovereign Agentic AI Workbench — Starting Automated macOS Setup     "
echo "======================================================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Check Docker
echo -e "\n[1/6] Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please open Docker Desktop on your Mac."
    exit 1
fi
echo "Starting PostgreSQL container..."
docker compose up -d

# 2. Check Ollama & Pull Models
echo -e "\n[2/6] Checking Ollama service & downloading models..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama is not installed. Installing via Homebrew..."
    brew install ollama
fi

MODELS=("qwen2.5:3b" "qwen2.5:7b-instruct" "qwen2.5vl:7b" "qwen2.5-coder:3b" "deepseek-r1:1.5b")
for model in "${MODELS[@]}"; do
    if ollama list | grep -q "$model"; then
        echo " -> Model '$model' is already downloaded."
    else
        echo " -> Pulling model '$model'..."
        ollama pull "$model"
    fi
done

# 3. Setup Python Backend Environment
echo -e "\n[3/6] Setting up Python virtual environment..."
cd "$ROOT_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Database Migration & KB Vector Seeding
echo -e "\n[4/6] Running PostgreSQL migrations & seeding SOP Knowledge Base..."
python scripts/migrate_db.py
python scripts/seed_kb.py

# 5. Setup Frontend
echo -e "\n[5/6] Installing Frontend dependencies..."
cd "$ROOT_DIR/frontend"
npm install
npm run build

echo -e "\n======================================================================"
echo "  SETUP COMPLETE!                                                     "
echo "======================================================================"
echo "To start both services:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd backend && source venv/bin/activate"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Access the workbench at: http://localhost:5173"
echo "======================================================================"
