import base64
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

ps_script = f"""
$targetPid = {current_pid}
$oldExe = '{test_old}'
$newExe = '{test_new}'
$logFile = '{ps_log}'

"Waiting for PID $targetPid..." | Out-File -FilePath $logFile -Append

while (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {{
    Start-Sleep -Milliseconds 200
}}
"PID $targetPid exited. Starting swap..." | Out-File -FilePath $logFile -Append

for ($i = 0; $i -lt 40; $i++) {{
    try {{
        if (Test-Path -LiteralPath $oldExe) {{
            Remove-Item -LiteralPath $oldExe -Force -ErrorAction Stop
        }}
        Move-Item -LiteralPath $newExe -Destination $oldExe -Force -ErrorAction Stop
        "Swap succeeded at attempt $i" | Out-File -FilePath $logFile -Append
        break
    }} catch {{
        "Attempt $i failed: $_" | Out-File -FilePath $logFile -Append
        Start-Sleep -Milliseconds 500
    }}
}}
"""

b64_script = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

p = subprocess.Popen(
    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64_script],
    creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
    close_fds=True
)

print(f"Spawned PS PID {p.pid}")
