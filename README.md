# Sovereign On-Prem Agentic AI Workbench

Phase 1 scaffolding for an air-gapped, sovereign AI processing system.

## Setup Instructions

### 1. Database
Start the local PostgreSQL database using docker-compose (runs on port 5433 to prevent port collision with any native Postgres services):
```bash
docker-compose up -d
```

### 2. Backend (FastAPI)
Open a new PowerShell terminal and navigate to the backend directory:
```powershell
cd c:\sih117\prototype\backend
```

Activate the virtual environment:
```powershell
.\venv\Scripts\Activate.ps1
```

Run database migrations:
```powershell
alembic upgrade head
```

Seed mock demo data:
```powershell
python seed.py
```

Start the FastAPI server:
```powershell
uvicorn app.main:app --reload
```
*(Or directly without activating: `.\venv\Scripts\uvicorn.exe app.main:app --reload`)*

The backend server will be running on `http://localhost:8000`.

### 3. Frontend (React/Vite)
Open a separate terminal and navigate to the frontend directory:
```powershell
cd c:\sih117\prototype\frontend
npm run dev
```

Open `http://localhost:5173` in your browser to interact with the Sovereign Workbench.
