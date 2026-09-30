@echo off
title STOPPING ALL FLEET SENTINEL PROCESSES
color 0c

echo ===============================================================================
echo   STOPPING ALL RUNNING FLEET SENTINEL PROCESSES (Ports 8000, 8501, 8502)
echo ===============================================================================
echo.

taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul

echo.
echo [OK] All previous background server processes stopped!
echo      Ports 8000, 8501, 8502 are now completely free.
echo.
pause
