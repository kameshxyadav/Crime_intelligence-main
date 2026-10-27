@echo off
echo ============================================================
echo  Cross-Station Crime Intelligence - Backend Server
echo  Chandigarh Police Intelligence Platform
echo ============================================================
cd /d "%~dp0backend"
echo.
echo Starting FastAPI backend on http://localhost:8000 ...
echo API Docs: http://localhost:8000/api/docs
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
