@echo off
echo ========================================================
echo   Starting NexReview AI - FastAPI Backend & Frontend
echo ========================================================
cd /d "%~dp0backend"
"..\code_reviewer_agent\venv\Scripts\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
