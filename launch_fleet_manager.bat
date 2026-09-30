@echo off
title FLEETMIND // FLEET OPERATIONS & DISPATCH CENTER (PORT 8502)
echo ===============================================================================
echo            FLEETMIND - FLEET OPERATIONS & DISPATCH COMMAND CENTER
echo ===============================================================================
echo Connecting to FastAPI Backend (http://localhost:8000) and JSON Database...
echo Starting Fleet Manager UI on http://localhost:8502 ...
echo ===============================================================================

cd /d "%~dp0"
"D:\FLEETMIND\.venv\Scripts\python.exe" -m streamlit run fleet_manager.py --server.port 8502 --server.address 0.0.0.0 --server.headless true --browser.serverAddress localhost
pause
