@echo off
title FLEETMIND // FASTAPI BACKEND SERVER (PORT 8000)
echo ===============================================================================
echo            FLEETMIND API - FASTAPI TELEMATICS & RISK BACKEND
echo ===============================================================================
echo Starting FastAPI REST Server on http://localhost:8000 ...
echo Swagger Interactive Docs: http://localhost:8000/docs
echo ReDoc Documentation:      http://localhost:8000/redoc
echo Database Source:          data/fleet_database.json
echo ===============================================================================

cd /d "%~dp0"
"D:\FLEETMIND\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
