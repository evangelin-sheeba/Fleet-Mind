@echo off
title [LAPTOP 2] FLEETGUARD SENTINEL - FLEET MANAGER DISPATCH COMMAND CENTER
color 0a

echo ===============================================================================
echo   FLEETGUARD SENTINEL // LAPTOP 2: FLEET MANAGER DISPATCH COMMAND CENTER
echo ===============================================================================
echo.
echo   Role of this Laptop:
echo     [1] Live Vehicle Tracking Map : 3D Expressway Corridor (Madurai to Chennai)
echo     [2] Real-Time Safety Stream   : Live Fatigue Index, EAR, MAR, Speed
echo     [3] Supervisory Directives    : Order Safe Stop, Broadcast Audio Advisories
echo     [4] Multi-Laptop Sync         : Communicates with Driver Laptop via FastAPI
echo.
echo ===============================================================================
echo.

set VENV_PY=D:\FLEETMIND\.venv\Scripts\python.exe
if not exist "%VENV_PY%" (
    set VENV_PY=python
)

echo [*] Launching Fleet Manager Command Center (Port 8502)...
start "[MANAGER] Fleet Operations Command Center (Port 8502)" cmd /k ""%VENV_PY%" -m streamlit run fleet_manager.py --server.port 8502 --server.address 0.0.0.0 --server.headless true"

echo.
echo [OK] Fleet Manager Dashboard launched!
echo.
echo   NOTE: In the left sidebar of the Fleet Manager Dashboard,
echo   enter the IP address of Laptop 1 (e.g. http://10.58.253.174:8000)
echo   to link with the in-cabin driver sensor and live telematics stream!
echo.
pause
