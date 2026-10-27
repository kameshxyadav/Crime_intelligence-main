@echo off
echo ============================================================
echo  Cross-Station Crime Intelligence - Frontend Web UI
echo  Chandigarh Police Intelligence Platform
echo ============================================================
cd /d "%~dp0frontend"
echo.
echo Starting Vite Frontend on http://localhost:5173 ...
echo.
npm run dev
pause
