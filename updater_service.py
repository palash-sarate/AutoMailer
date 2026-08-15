import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from typing import Any, Dict, Optional, Tuple

from logger_config import get_logger

logger = get_logger("updater_service")

APP_VERSION = "1.0.3"
GITHUB_REPO = "palash-sarate/AutoMailer"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
IS_FROZEN = getattr(sys, "frozen", False)


def parse_semver(version_str: str) -> Tuple[int, int, int]:
    """Parses a version string like 'v1.0.2' or '1.2.3' into a tuple of ints (major, minor, patch)."""
    clean = re.sub(r"^[^\d]*", "", version_str.strip())
    parts = clean.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    return (major, minor, patch)


def is_newer_version(latest_str: str, current_str: str = APP_VERSION) -> bool:
    """Returns True if latest_str is strictly newer than current_str."""
    return parse_semver(latest_str) > parse_semver(current_str)


def check_for_updates() -> Dict[str, Any]:
    """Queries GitHub Releases API to check if a new version is available."""
    logger.info("Checking for application updates from GitHub repository '%s'...", GITHUB_REPO)
    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "User-Agent": f"AutoMailer/{APP_VERSION}",
            "Accept": "application/vnd.github.v3+json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                logger.warning("GitHub Releases API returned status %d", response.status)
                return {
                    "success": False,
                    "error": f"GitHub returned status code {response.status}"
                }

            data = json.loads(response.read().decode("utf-8"))
            tag_name = data.get("tag_name", "")
            release_notes = data.get("body", "")
            published_at = data.get("published_at", "")
            html_url = data.get("html_url", "")

            # Look for downloadable asset
            assets = data.get("assets", [])
            download_url = ""
            asset_name = ""
            asset_size = 0

            # Find matching Windows asset (.exe or .zip)
            for asset in assets:
                name = asset.get("name", "")
                if name.lower().endswith(".exe") or "automailer" in name.lower():
                    download_url = asset.get("browser_download_url", "")
                    asset_name = name
                    asset_size = asset.get("size", 0)
                    break

            if not download_url and assets:
                # Fallback to first available asset
                download_url = assets[0].get("browser_download_url", "")
                asset_name = assets[0].get("name", "")
                asset_size = assets[0].get("size", 0)

            has_update = is_newer_version(tag_name, APP_VERSION)
            logger.info("Update check result: current=%s, latest=%s, has_update=%s",
                        APP_VERSION, tag_name, has_update)

            return {
                "success": True,
                "current_version": APP_VERSION,
                "latest_version": tag_name,
                "has_update": has_update,
                "release_notes": release_notes,
                "published_at": published_at,
                "html_url": html_url,
                "download_url": download_url,
                "asset_name": asset_name,
                "asset_size": asset_size,
                "is_frozen": IS_FROZEN
            }
    except Exception as e:
        logger.warning("Failed to check for updates: %s", e)
        return {
            "success": False,
            "error": str(e),
            "current_version": APP_VERSION,
            "has_update": False,
            "is_frozen": IS_FROZEN
        }


def download_asset_file(download_url: str, dest_path: str, progress_callback=None) -> bool:
    """Downloads a release asset to destination with optional progress logging."""
    logger.info("Downloading release asset from '%s' to '%s'...", download_url, dest_path)
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"AutoMailer/{APP_VERSION}"}
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            block_size = 64 * 1024  # 64 KB chunks

            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

        logger.info("Download completed successfully (%d bytes).", downloaded)
        return True
    except Exception as e:
        logger.error("Download failed: %s", e, exc_info=True)
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        raise e


import zipfile


def apply_update_and_restart(download_url: str) -> Dict[str, Any]:
    """Downloads the new version and performs a detached Windows binary swap."""
    if not download_url:
        return {"success": False, "error": "No download URL provided."}

    if not IS_FROZEN:
        return {
            "success": False,
            "error": "OTA auto-binary replacement is for packaged executables. In developer mode, pull latest changes via git."
        }

    current_exe = sys.executable
    app_dir = os.path.dirname(current_exe)
    update_file = os.path.join(app_dir, "AutoMailer.update.exe")
    temp_download = os.path.join(app_dir, "AutoMailer.download.tmp")
    current_pid = os.getpid()

    try:
        # 1. Download asset into temp file
        download_asset_file(download_url, temp_download)

        # 2. Extract AutoMailer.exe if downloaded as a zip package
        if download_url.lower().endswith(".zip") or zipfile.is_zipfile(temp_download):
            logger.info("Extracting AutoMailer.exe from downloaded zip archive...")
            with zipfile.ZipFile(temp_download, "r") as z:
                exe_name_in_zip = None
                for member in z.namelist():
                    if member.endswith("AutoMailer.exe") or member.lower() == "automailer.exe":
                        exe_name_in_zip = member
                        break
                if exe_name_in_zip:
                    with z.open(exe_name_in_zip) as zf, open(update_file, "wb") as out_f:
                        out_f.write(zf.read())
                else:
                    raise ValueError("No AutoMailer.exe found inside downloaded zip package.")
            try:
                os.remove(temp_download)
            except Exception:
                pass
        else:
            # Directly .exe binary
            if os.path.exists(update_file):
                os.remove(update_file)
            os.rename(temp_download, update_file)

        # 3. Create standalone batch script to handle the file swap and restart
        bat_file = os.path.join(app_dir, "_automailer_updater.bat")
        bat_content = f"""@echo off
set "TARGET_PID={current_pid}"
set "OLD_EXE={current_exe}"
set "NEW_EXE={update_file}"

:wait_proc
tasklist /fi "pid eq %TARGET_PID%" | findstr /i "%TARGET_PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_proc
)

:retry_swap
timeout /t 1 /nobreak >nul
if exist "%OLD_EXE%" del /f /q "%OLD_EXE%" >nul 2>&1
move /y "%NEW_EXE%" "%OLD_EXE%" >nul 2>&1
if not exist "%OLD_EXE%" goto retry_swap

start "" "%OLD_EXE%"
del /f /q "%~f0" >nul 2>&1
"""
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(bat_content)

        logger.info("Spawning detached updater batch process to replace %s...", current_exe)

        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000

        subprocess.Popen(
            ["cmd.exe", "/c", bat_file],
            creationflags=CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True
        )

        # 3. Schedule graceful exit of current process
        def delayed_shutdown():
            time.sleep(1.0)
            logger.info("Terminating old AutoMailer process (PID %d) for update swap.", current_pid)
            os._exit(0)

        threading.Thread(target=delayed_shutdown, daemon=True).start()

        return {
            "success": True,
            "message": "Update downloaded successfully. AutoMailer is restarting now..."
        }
    except Exception as e:
        logger.error("Failed to apply update: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
