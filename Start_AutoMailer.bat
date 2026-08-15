@echo off
title AutoMailer Pro Dashboard
cd /d "%~dp0"

echo ========================================================
echo   Launching AutoMailer Pro Dashboard...
echo ========================================================

REM Check if .venv exists
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)

pause
