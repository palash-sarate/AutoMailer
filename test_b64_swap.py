import base64
import os
import subprocess
import time

app_dir = os.getcwd()
test_old = os.path.join(app_dir, "test_old.exe")
test_new = os.path.join(app_dir, "test_new.exe")

with open(test_old, "w") as f:
    f.write("OLD VERSION")

with open(test_new, "w") as f:
    f.write("NEW VERSION")

current_pid = os.getpid()

ps_script = f"""
$targetPid = {current_pid}
$oldExe = '{test_old}'
$newExe = '{test_new}'

while (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {{
    Start-Sleep -Milliseconds 200
}}
Start-Sleep -Milliseconds 500

for ($i = 0; $i -lt 40; $i++) {{
    try {{
        if (Test-Path -LiteralPath $oldExe) {{
            Remove-Item -LiteralPath $oldExe -Force -ErrorAction Stop
        }}
        Move-Item -LiteralPath $newExe -Destination $oldExe -Force -ErrorAction Stop
        break
    }} catch {{
        Start-Sleep -Milliseconds 500
    }}
}}
"""

b64_script = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
creation_flags = CREATE_NO_WINDOW | DETACHED_PROCESS

subprocess.Popen(
    ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", b64_script],
    creationflags=creation_flags,
    close_fds=True
)

print("Encoded PowerShell updater launched successfully!")
