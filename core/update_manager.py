import os
import sys
import subprocess
import requests
import json
import time

LAUNCHER_VERSION = "1.5.4"

class UpdateManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.current_version = LAUNCHER_VERSION

    def get_update_url(self):
        default_url = "https://raw.githubusercontent.com/GianCarlozxc/AlienLauncher/main/update.json"
        return self.config_manager.get("update_url", default_url)

    def check_for_updates(self):
        url = self.get_update_url()
        # Fallback to GitHub Releases API if url is raw github content
        api_url = None
        if "raw.githubusercontent.com" in url:
            parts = url.replace("https://raw.githubusercontent.com/", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"

        try:
            if api_url:
                try:
                    headers = {"User-Agent": "Alien-Launcher-Updater/1.0.0"}
                    res = requests.get(api_url, headers=headers, timeout=5, verify=False)
                    if res.status_code == 200:
                        releases = res.json()
                        # Find the highest semantic version release (bypass GitHub's published_at bug)
                        import re
                        latest_release = None
                        for release in releases:
                            if release.get("draft") or release.get("prerelease"):
                                continue
                            
                            tag_name = release.get("tag_name", "")
                            if not re.match(r"^v?\d+(\.\d+)*$", tag_name):
                                continue
                            
                            if not latest_release:
                                latest_release = release
                            else:
                                rel_ver = release.get("tag_name", "").lstrip("v")
                                lat_ver = latest_release.get("tag_name", "").lstrip("v")
                                if self.is_newer_version(rel_ver, lat_ver):
                                    latest_release = release
                                    
                        if latest_release:
                            version = latest_release.get("tag_name", "").lstrip("v")
                            changelog = latest_release.get("body", "No changelog provided.")
                            
                            download_url = None
                            assets = latest_release.get("assets", [])
                            for asset in assets:
                                asset_name = asset.get("name", "")
                                if asset_name.endswith(".exe"):
                                    download_url = asset.get("browser_download_url")
                                    break
                            if not download_url:
                                download_url = latest_release.get("zipball_url")
                            
                            if self.is_newer_version(version, self.current_version):
                                return True, version, download_url, changelog
                            else:
                                return False, self.current_version, None, "You are running the latest version."
                except Exception as api_err:
                    print(f"Failed to check updates via GitHub Releases API: {api_err}. Falling back to raw JSON.")

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

            # Frozen/EXE update flow (Rename-and-swap)
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
                res = requests.get(download_url, stream=True, headers=headers, timeout=60, verify=False)
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

            # Apply rename-and-swap
            old_exe_path = current_exe_path + ".old"
            if os.path.exists(old_exe_path):
                try:
                    os.remove(old_exe_path)
                except Exception:
                    pass

            # Rename the running executable to release the file lock
            os.rename(current_exe_path, old_exe_path)
            
            # Copy new executable to original path
            import shutil
            shutil.move(new_exe_temp_path, current_exe_path)
            
            return True, "Executable updated in-place successfully!"
        except Exception as e:
            return False, str(e)
