@echo off
echo ========================================================
echo Starting AgentSupport AI Multi-Agent Customer Support System
echo ========================================================
echo.

echo Starting FastAPI Backend on http://localhost:8000 ...
start "AgentSupport AI - Backend" cmd /k ".\venv\Scripts\uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 >nul

echo Starting React + Vite Frontend on http://localhost:5173 ...
start "AgentSupport AI - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo ========================================================
