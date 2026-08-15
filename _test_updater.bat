@echo off
set TARGET_PID=41512
set OLD_EXE="C:\Users\Palash\Documents\GitHub\bulk-email-sender\test_old.exe"
set NEW_EXE="C:\Users\Palash\Documents\GitHub\bulk-email-sender\test_new.exe"

:wait_proc
tasklist /fi "pid eq %TARGET_PID%" | find "%TARGET_PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_proc
)

:retry_swap
timeout /t 1 /nobreak >nul
if exist %OLD_EXE% del /f /q %OLD_EXE% >nul 2>&1
move /y %NEW_EXE% %OLD_EXE% >nul 2>&1
if not exist %OLD_EXE% goto retry_swap

del /f /q "%~f0" >nul 2>&1
