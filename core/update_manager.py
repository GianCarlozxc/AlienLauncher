import os
import sys
import subprocess
import requests
import json
import time

LAUNCHER_VERSION = "1.0.3"

class UpdateManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.current_version = LAUNCHER_VERSION

    def get_update_url(self):
        default_url = "https://raw.githubusercontent.com/GianCarlozxc/AlienLauncher/main/update.json"
        return self.config_manager.get("update_url", default_url)

    def check_for_updates(self):
        url = self.get_update_url()
        try:
            # Local test update support to demonstrate the update flow easily
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            test_json_path = os.path.join(project_root, "test_update.json")
            
            if os.path.exists(test_json_path):
                with open(test_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return True, data.get("version"), data.get("download_url"), data.get("changelog", "No changelog provided.")

            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                version = data.get("version")
                download_url = data.get("download_url")
                changelog = data.get("changelog", "")
                
                if self.is_newer_version(version, self.current_version):
                    return True, version, download_url, changelog
                else:
                    return False, self.current_version, None, "You are running the latest version."
            else:
                return False, self.current_version, None, f"Failed to check updates (HTTP {res.status_code})"
        except Exception as e:
            return False, self.current_version, None, f"Error checking updates: {e}"

    def is_newer_version(self, new_ver, current_ver):
        try:
            new_parts = [int(x) for x in new_ver.strip().replace("v", "").split(".")]
            curr_parts = [int(x) for x in current_ver.strip().replace("v", "").split(".")]
            return new_parts > curr_parts
        except Exception:
            return new_ver != current_ver

    def download_and_apply_update(self, download_url, progress_callback=None):
        try:
            # 1. Resolve executable path
            if getattr(sys, 'frozen', False):
                current_exe_path = sys.executable
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                current_exe_path = os.path.join(project_root, "dist", "Alien Launcher.exe")
                os.makedirs(os.path.dirname(current_exe_path), exist_ok=True)

            temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
            new_exe_temp_path = os.path.join(temp_dir, "Alien_Launcher_New.exe")

            # 2. Download executable (or copy local file for testing)
            if download_url.startswith("file://"):
                local_path = download_url.replace("file://", "").replace("/", "\\")
                if local_path.startswith("\\") and not local_path.startswith("\\\\"):
                    local_path = local_path[1:]
                import shutil
                shutil.copy2(local_path, new_exe_temp_path)
            elif os.path.exists(download_url):
                import shutil
                shutil.copy2(download_url, new_exe_temp_path)
            else:
                headers = {"User-Agent": "Alien-Launcher-Updater/1.0.0"}
                res = requests.get(download_url, stream=True, headers=headers, timeout=60)
                res.raise_for_status()
                
                total_size = int(res.headers.get('content-length', 0))
                downloaded = 0
                
                with open(new_exe_temp_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)

            # 3. Create update.bat
            bat_path = os.path.join(temp_dir, "apply_update.bat")
            bat_content = f"""@echo off
title Updating Alien Launcher...
echo Waiting for Alien Launcher to close...
:wait_loop
tasklist /fi "pid eq {os.getpid()}" 2>NUL | find /I "{os.getpid()}" >NUL
if %ERRORLEVEL%==0 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Replacing executable...
copy /y "{new_exe_temp_path}" "{current_exe_path}" >nul
if %ERRORLEVEL% neq 0 (
    echo Failed to apply update. Retrying in 2 seconds...
    timeout /t 2 /nobreak >nul
    copy /y "{new_exe_temp_path}" "{current_exe_path}" >nul
)

echo Restarting launcher...
start "" "{current_exe_path}"

echo Cleaning up...
del "{new_exe_temp_path}"
(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="ansi") as f:
                f.write(bat_content)

            # 4. Launch the batch script detached
            if sys.platform == "win32":
                # We use creationflags to run completely in background without cmd window popup
                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path],
                    creationflags=0x08000000 | 0x00000008 # CREATE_NO_WINDOW | DETACHED_PROCESS
                )
                
            return True, "Restarting to apply update..."
        except Exception as e:
            return False, str(e)
