import os
import subprocess
import time

app_dir = os.getcwd()
test_old = os.path.join(app_dir, "test_old.exe")
test_new = os.path.join(app_dir, "test_new.exe")
updater_bat = os.path.join(app_dir, "_test_updater.bat")

with open(test_old, "w") as f:
    f.write("OLD VERSION")

with open(test_new, "w") as f:
    f.write("NEW VERSION")

current_pid = os.getpid()

bat_content = f"""@echo off
set TARGET_PID={current_pid}
set OLD_EXE="{test_old}"
set NEW_EXE="{test_new}"

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
"""

with open(updater_bat, "w", encoding="utf-8") as f:
    f.write(bat_content)

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
creation_flags = CREATE_NO_WINDOW | DETACHED_PROCESS

subprocess.Popen(
    ["cmd.exe", "/c", updater_bat],
    creationflags=creation_flags,
    close_fds=True
)

print("Started updater bat! Exiting test script now...")
