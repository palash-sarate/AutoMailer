import os
import subprocess

app_dir = os.getcwd()
test_old = os.path.join(app_dir, "test_old.exe")
test_new = os.path.join(app_dir, "test_new.exe")
ps_log = os.path.join(app_dir, "ps_debug.log")

with open(test_old, "w") as f:
    f.write("OLD VERSION")

with open(test_new, "w") as f:
    f.write("NEW VERSION")

current_pid = os.getpid()

# Batch updater script using cmd.exe
bat_file = os.path.join(app_dir, "_swap.bat")
bat_content = f"""@echo off
set "TARGET_PID={current_pid}"
set "OLD_EXE={test_old}"
set "NEW_EXE={test_new}"
set "LOG_FILE={ps_log}"

echo Waiting for PID %TARGET_PID%... >> "%LOG_FILE%"

:wait_loop
tasklist /fi "pid eq %TARGET_PID%" | findstr /i "%TARGET_PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo PID %TARGET_PID% exited! Starting swap... >> "%LOG_FILE%"

:retry_loop
timeout /t 1 /nobreak >nul
if exist "%OLD_EXE%" del /f /q "%OLD_EXE%" >nul 2>&1
move /y "%NEW_EXE%" "%OLD_EXE%" >nul 2>&1
if not exist "%OLD_EXE%" goto retry_loop

echo Swap completed successfully! >> "%LOG_FILE%"
del /f /q "%~f0" >nul 2>&1
"""

with open(bat_file, "w", encoding="utf-8") as f:
    f.write(bat_content)

CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

p = subprocess.Popen(
    ["cmd.exe", "/c", bat_file],
    creationflags=CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    close_fds=True
)

print(f"Spawned cmd.exe PID {p.pid}. Exiting now...")
