@echo off
title PUSH FLEET-MIND TO GITHUB
color 0b

echo ===============================================================================
echo   ANTI-GRAVITY // PUSH FLEET-MIND CODE TO GITHUB REPOSITORY
echo   Target: https://github.com/evangelin-sheeba/Fleet-Mind.git
echo ===============================================================================
echo.

set VENV_PY=D:\FLEETMIND\.venv\Scripts\python.exe
if not exist "%VENV_PY%" (
    set VENV_PY=python
)

"%VENV_PY%" push_to_github.py %1

echo.
pause
