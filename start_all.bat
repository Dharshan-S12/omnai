@echo off
title Sovereign Workbench Launcher
echo ========================================================
echo   Starting MRPL Sovereign On-Prem Agentic AI Workbench
echo ========================================================
echo.

echo [1/2] Launching Backend Server (FastAPI on Port 8000)...
start "MRPL Backend Server (Port 8000)" cmd /k "cd /d c:\sih117\prototype\backend && .\venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 >nul

echo [2/2] Launching Frontend Server (Vite on Port 5173)...
start "MRPL Frontend UI (Port 5173)" cmd /k "cd /d c:\sih117\prototype\frontend && npm run dev"

echo.
echo ========================================================
echo   Both services launched in separate windows!
echo   - Backend:  http://localhost:8000/docs
echo   - Frontend: http://localhost:5173
echo ========================================================
pause
