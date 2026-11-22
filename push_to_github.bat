@echo off
echo ========================================================
echo   Pushing NexReview AI to GitHub
echo   Target: https://github.com/MuraliDungala/code_reviewer_agent.git
echo ========================================================
cd /d "%~dp0"
git remote set-url origin https://github.com/MuraliDungala/code_reviewer_agent.git
git branch -M main
git push -u origin main
echo.
pause
