@echo off
title [LAPTOP 1] FLEET SENTINEL - DRIVER COCKPIT, WEBCAM SENSOR & IN-CABIN AUDIO
color 0b

echo ===============================================================================
echo   ANTI-GRAVITY FLEET SENTINEL // LAPTOP 1: IN-CABIN DRIVER COCKPIT & SENSOR
echo ===============================================================================
echo.
echo   Role of this Laptop:
echo     [1] Prototype Sensor Node : Laptop Webcam + MediaPipe 468 Face Mesh
echo     [2] In-Cabin HUD Display  : Speedometer, Biometrics, GPS, Safe Stop
echo     [3] Loud In-Cabin Audio   : Physical Laptop Speakers (Siren + Voice Directives)
echo     [4] Core Telematics Server: FastAPI REST Backend on Port 8000
echo.
echo ===============================================================================
echo.

:: Detect local Wi-Fi / LAN IP address
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
:: Remove leading whitespace
set LOCAL_IP=%LOCAL_IP: =%

echo [*] Local Machine IP Address : %LOCAL_IP%
echo [*] FastAPI Backend API URL  : http://%LOCAL_IP%:8000
echo [*] Driver Cockpit URL       : http://localhost:8501
echo.
echo -------------------------------------------------------------------------------
echo   INSTRUCTIONS FOR LAPTOP 2 (FLEET MANAGER COMMAND CENTER):
echo   1. Ensure Laptop 2 is connected to the SAME Wi-Fi network.
echo   2. On Laptop 2, open your browser and navigate to:
echo        http://%LOCAL_IP%:8502
echo      (Or run START_FLEET_MANAGER_LAPTOP.bat and set Driver IP to %LOCAL_IP%)
echo -------------------------------------------------------------------------------
echo.

:: Set environment to use existing virtualenv
set VENV_PY=D:\FLEETMIND\.venv\Scripts\python.exe
if not exist "%VENV_PY%" (
    set VENV_PY=python
)

echo [*] Starting FastAPI Telematics Server (0.0.0.0:8000)...
start "[SERVER] FastAPI Telematics Backend (Port 8000)" cmd /k ""%VENV_PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [*] Waiting 3 seconds for FastAPI to initialize...
timeout /t 3 /nobreak > nul

echo [*] Launching Driver Cockpit with Live Webcam Sensor & In-Cabin Speakers...
start "[COCKPIT] Driver Safety HUD & Biometric Sensor (Port 8501)" cmd /k ""%VENV_PY%" -m streamlit run driver_cockpit.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"

echo.
echo [OK] All Laptop 1 systems armed and online!
echo      Driver Cockpit will open automatically in your browser.
echo.
pause
