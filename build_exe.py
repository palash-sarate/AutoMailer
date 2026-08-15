import os
import subprocess
import sys
import shutil

def build_executable():
    print("==================================================")
    print("  AutoMailer Pro - Standalone Executable Builder   ")
    print("==================================================")

    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    dist_dir = os.path.join(os.getcwd(), "dist")
    build_dir = os.path.join(os.getcwd(), "build")

    # Clean old builds
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir, ignore_errors=True)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    # 2. PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AutoMailer",
        "--onefile",
        "--add-data=static;static",
        "--hidden-import=markdown",
        "--hidden-import=dotenv",
        "--hidden-import=email",
        "--hidden-import=smtplib",
        "--hidden-import=flask",
        "app.py"
    ]

    print("\n[*] Packaging into standalone single executable...")
    print(f"    Running: {' '.join(cmd)}\n")
    subprocess.check_call(cmd)

    # 3. Create a clean distribution folder
    portable_folder = os.path.join(dist_dir, "AutoMailer_Portable")
    os.makedirs(portable_folder, exist_ok=True)

    exe_path = os.path.join(dist_dir, "AutoMailer.exe")
    if os.path.exists(exe_path):
        shutil.copy(exe_path, portable_folder)

    # Copy sample configuration and template files
    for item in ["compose.md", "data.csv", ".env"]:
        if os.path.exists(item):
            shutil.copy(item, portable_folder)

    attach_dir = os.path.join(portable_folder, "ATTACH")
    os.makedirs(attach_dir, exist_ok=True)

    print("\n==================================================")
    print("  [SUCCESS] BUILD COMPLETED!")
    print(f"  Folder: {portable_folder}")
    print("  You can zip this folder and send it to anyone.")
    print("  They can double-click 'AutoMailer.exe' to run.")
    print("==================================================")

if __name__ == "__main__":
    build_executable()
