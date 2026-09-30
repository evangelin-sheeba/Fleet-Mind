@echo off
title FLEETMIND // DRIVER SAFETY COCKPIT HUD (PORT 8501)
echo ===============================================================================
echo            FLEETMIND - DRIVER SAFETY COCKPIT & EDGE VISION HUD
echo ===============================================================================
echo Initializing hardware sensors and Edge Vision MediaPipe Mesh...
echo Starting Driver Cockpit UI on http://localhost:8501 ...
echo ===============================================================================

cd /d "%~dp0"
"D:\FLEETMIND\.venv\Scripts\python.exe" -m streamlit run driver_cockpit.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.serverAddress localhost
pause
