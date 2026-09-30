@echo off
title FLEETMIND // MASTER TRIPLE-LAYER SYSTEM LAUNCHER
echo ===============================================================================
echo            FLEETMIND - 3-LAYER SYSTEM MASTER COMMAND LAUNCHER
echo ===============================================================================
echo [1/3] Starting FastAPI REST Backend on port 8000...
echo [2/3] Starting Driver Cockpit HUD on port 8501...
echo [3/3] Starting Fleet Manager Command Center on port 8502...
echo Database: data/fleet_database.json (Persistent JSON Repository)
echo ===============================================================================

cd /d "%~dp0"

REM Launch FastAPI Server on port 8000 in background
start "FleetMind FastAPI Server" /B "D:\FLEETMIND\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM Wait 2 seconds for FastAPI initialization
timeout /t 2 /nobreak >nul

REM Launch Driver Cockpit on port 8501 in background
start "Driver Cockpit HUD" /B "D:\FLEETMIND\.venv\Scripts\python.exe" -m streamlit run driver_cockpit.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.serverAddress localhost

REM Launch Fleet Manager on port 8502 in background
start "Fleet Manager Center" /B "D:\FLEETMIND\.venv\Scripts\python.exe" -m streamlit run fleet_manager.py --server.port 8502 --server.address 0.0.0.0 --server.headless true --browser.serverAddress localhost

REM Wait 3 seconds for web services to initialize
timeout /t 3 /nobreak >nul

echo Opening interfaces in your default browser...
start http://localhost:8000/docs
start http://localhost:8501
start http://localhost:8502

echo ===============================================================================
echo  All 3 FleetMind Layers are running live:
echo  - API Docs (Swagger):      http://localhost:8000/docs
echo  - Driver Safety Cockpit:   http://localhost:8501
echo  - Fleet Manager Console:   http://localhost:8502
echo ===============================================================================
exit /b
