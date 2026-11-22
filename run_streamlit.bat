@echo off
echo ========================================================
echo   Starting NexReview AI - Streamlit Application
echo ========================================================
cd /d "%~dp0code_reviewer_agent"
"venv\Scripts\python.exe" -m streamlit run app.py
pause
