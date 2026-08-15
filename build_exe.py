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
        "--hidden-import=logger_config",
        "--hidden-import=updater_service",
        "--hidden-import=urllib.request",
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

    # Copy or create sample configuration and template files
    if os.path.exists("compose.md"):
        shutil.copy("compose.md", portable_folder)
    else:
        with open(os.path.join(portable_folder, "compose.md"), "w", encoding="utf-8") as f:
            f.write("Invoice Reminder for $NAME - $DATE\n\nDear $NAME,\n\nThis is a friendly reminder regarding your invoice **#$INVOICE_NO**.\n\nBest regards,\n**Operations Team**\n")

    if os.path.exists("data.csv"):
        shutil.copy("data.csv", portable_folder)
    else:
        with open(os.path.join(portable_folder, "data.csv"), "w", encoding="utf-8") as f:
            f.write("NAME,DATE,AMOUNT,INVOICE_NO,EMAIL\nJohn Doe,2026-08-20,$250.00,INV-1001,recipient@example.com\n")

    if os.path.exists(".env"):
        shutil.copy(".env", portable_folder)
    else:
        with open(os.path.join(portable_folder, ".env"), "w", encoding="utf-8") as f:
            f.write('display_name="Sender Name"\nsender_email="your_email@gmail.com"\npassword=""\nsmtp_host="smtp.gmail.com"\nsmtp_port="587"\nmail_compose="compose.md"\nsubject=""\n')

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
