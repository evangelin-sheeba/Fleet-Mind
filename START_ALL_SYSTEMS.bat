@echo off
title ANTI-GRAVITY FLEET SENTINEL - COMPLETE DUAL-DASHBOARD SUITE
color 0e

echo ===============================================================================
echo   ANTI-GRAVITY FLEET SENTINEL // COMPLETE SYSTEM LAUNCHER (3-LAYER STACK)
echo ===============================================================================
echo.
echo   Launching:
echo     [Layer 1 - Backend] : FastAPI REST Server (Port 8000)
echo     [Layer 2 - Database]: JSON Database + SQLite Synchronization
echo     [Layer 3 - Cockpit] : Driver Safety HUD + Webcam Sensor + Audio (Port 8501)
echo     [Layer 3 - Manager] : Fleet Operations 3D Live Map (Port 8502)
echo.
echo ===============================================================================
echo.

set VENV_PY=D:\FLEETMIND\.venv\Scripts\python.exe
if not exist "%VENV_PY%" (
    set VENV_PY=python
)

echo [1/3] Starting FastAPI Server on port 8000...
start "[SERVER] FastAPI REST API (Port 8000)" cmd /k ""%VENV_PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Waiting 3 seconds for FastAPI to initialize...
timeout /t 3 /nobreak > nul

echo [2/3] Starting Driver Cockpit (Webcam + In-Cabin Audio) on port 8501...
start "[COCKPIT] Driver Safety HUD (Port 8501)" cmd /k ""%VENV_PY%" -m streamlit run driver_cockpit.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"

echo Waiting 2 seconds...
timeout /t 2 /nobreak > nul

echo [3/3] Starting Fleet Manager Command Center (3D Live Map) on port 8502...
start "[MANAGER] Fleet Command Center (Port 8502)" cmd /k ""%VENV_PY%" -m streamlit run fleet_manager.py --server.port 8502 --server.address 0.0.0.0 --server.headless true"

echo.
echo ===============================================================================
echo   ALL SYSTEMS ONLINE:
echo     - FastAPI Docs & OpenAPI : http://localhost:8000/docs
echo     - Driver Cockpit HUD     : http://localhost:8501
echo     - Fleet Manager 3D Map   : http://localhost:8502
echo ===============================================================================
echo.
pause
