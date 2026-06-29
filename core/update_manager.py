import os
import sys
import subprocess
import requests
import json
import time

LAUNCHER_VERSION = "1.0.7"

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
            if not getattr(sys, 'frozen', False):
                # Option B: Python source code update flow
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                url = self.get_update_url()
                zip_url = url.replace("raw.githubusercontent.com", "github.com").replace("/main/update.json", "/archive/refs/heads/main.zip")
                
                temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
                zip_temp_path = os.path.join(temp_dir, "AlienLauncher_source.zip")
                
                headers = {"User-Agent": "Alien-Launcher-Updater/1.0.0"}
                res = requests.get(zip_url, stream=True, headers=headers, timeout=60, verify=False)
                res.raise_for_status()
                
                total_size = int(res.headers.get('content-length', 0))
                downloaded = 0
                
                with open(zip_temp_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)
                
                import zipfile
                import shutil
                extract_temp_dir = os.path.join(temp_dir, "AlienLauncher_extracted")
                if os.path.exists(extract_temp_dir):
                    shutil.rmtree(extract_temp_dir)
                os.makedirs(extract_temp_dir, exist_ok=True)
                
                with zipfile.ZipFile(zip_temp_path, "r") as zip_ref:
                    zip_ref.extractall(extract_temp_dir)
                
                inner_dir = None
                for name in os.listdir(extract_temp_dir):
                    inner_path = os.path.join(extract_temp_dir, name)
                    if os.path.isdir(inner_path):
                        inner_dir = inner_path
                        break
                
                if not inner_dir:
                    return False, "Could not find extracted source folder in zip."
                
                for root, dirs, files in os.walk(inner_dir):
                    rel_path = os.path.relpath(root, inner_dir)
                    target_dir = project_root if rel_path == "." else os.path.join(project_root, rel_path)
                    os.makedirs(target_dir, exist_ok=True)
                    
                    for file in files:
                        if file.lower() in ["config.json", "test_update.json"]:
                            continue
                        src_file = os.path.join(root, file)
                        dest_file = os.path.join(target_dir, file)
                        try:
                            shutil.copy2(src_file, dest_file)
                        except Exception as copy_err:
                            print(f"Error copying {file}: {copy_err}")
                
                shutil.rmtree(extract_temp_dir)
                os.remove(zip_temp_path)
                return True, "Source code updated successfully!"

            # Frozen/EXE update flow
            current_exe_path = sys.executable
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
set /a retry_count=0

:wait_loop
copy /y "{new_exe_temp_path}" "{current_exe_path}" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    set /a retry_count+=1
    if %retry_count% gtr 15 (
        exit /b 1
    )
    ping 127.0.0.1 -n 2 >nul
    goto wait_loop
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
