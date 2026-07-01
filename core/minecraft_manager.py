import os
import sys
import uuid
import shutil
import subprocess
import threading
import hashlib
import time
import minecraft_launcher_lib
import minecraft_launcher_lib.fabric
import minecraft_launcher_lib.quilt
from minecraft_launcher_lib.microsoft_account import (
    get_secure_login_data,
    complete_login,
    complete_refresh,
    url_contains_auth_code,
    get_auth_code_from_url
)

# Standard Microsoft/Xbox Live Client ID and Redirect URI for Desktop Apps
CLIENT_ID = "000000004C12AE29"
REDIRECT_URI = "https://login.live.com/oauth20_desktop.srf"

class MinecraftManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.launch_process = None
        self._online_versions_cache = None

    def clean_corrupted_cache_files(self):
        """Finds and deletes 0-byte jar, json, and asset files in the minecraft folder to prevent download skip bugs."""
        mc_dir = self.config_manager.get_minecraft_folder()
        if not os.path.exists(mc_dir):
            return
            
        target_subdirs = ["libraries", "assets", "versions"]
        for subdir in target_subdirs:
            path = os.path.join(mc_dir, subdir)
            if os.path.exists(path):
                try:
                    for root, dirs, files in os.walk(path):
                        for f in files:
                            # We target .jar, .json, and other metadata/library files
                            # Check if the file is 0 bytes
                            if f.endswith(('.jar', '.json', '.zip', '.class')):
                                file_path = os.path.join(root, f)
                                try:
                                    if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
                                        os.remove(file_path)
                                        print(f"Removed 0-byte corrupted cache file: {file_path}")
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"Error scanning corrupted cache files in {subdir}: {e}")

    def download_file_with_retry(self, url, path, expected_sha1=None, max_retries=3, status_callback=None):
        """Downloads a file with exponential backoff retry and SHA-1 verification, switching to mirror if blocked/failed."""
        import requests
        
        # Function to compute sha1
        def get_sha1(file_path):
            h = hashlib.sha1()
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b''):
                        h.update(chunk)
                return h.hexdigest()
            except Exception:
                return None

        # Check if the file is already valid
        if os.path.exists(path) and os.path.getsize(path) > 0:
            if not expected_sha1 or get_sha1(path) == expected_sha1:
                return True

        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Mirror mapping
        def map_to_mirror(u):
            new_u = u
            is_package_json = ('piston-meta.mojang.com' in u or 'launchermeta.mojang.com' in u) and '/packages/' in u and u.endswith('.json')
            if is_package_json:
                version_id = u.split('/')[-1][:-5]
                new_u = f"https://bmclapi2.bangbang93.com/version/{version_id}/json"
            elif 'launchermeta.mojang.com' in u:
                new_u = u.replace('launchermeta.mojang.com', 'bmclapi2.bangbang93.com')
            elif 'launcher.mojang.com' in u:
                new_u = u.replace('launcher.mojang.com', 'bmclapi2.bangbang93.com')
            elif 'piston-meta.mojang.com' in u:
                new_u = u.replace('piston-meta.mojang.com', 'bmclapi2.bangbang93.com')
            elif 'piston-data.mojang.com' in u:
                new_u = u.replace('piston-data.mojang.com', 'bmclapi2.bangbang93.com')
            elif 'libraries.minecraft.net' in u:
                new_u = u.replace('libraries.minecraft.net', 'bmclapi2.bangbang93.com/maven')
            elif 'resources.download.minecraft.net' in u:
                new_u = u.replace('resources.download.minecraft.net', 'bmclapi2.bangbang93.com/assets')
            elif 'maven.fabricmc.net' in u:
                new_u = u.replace('maven.fabricmc.net', 'bmclapi2.bangbang93.com/maven/fabricmc')
            elif 'meta.fabricmc.net' in u:
                new_u = u.replace('meta.fabricmc.net', 'bmclapi2.bangbang93.com/fabric-meta')
            return new_u

        urls_to_try = [url]
        mirror = map_to_mirror(url)
        if mirror != url:
            urls_to_try.append(mirror)

        for current_url in urls_to_try:
            delay = 1.0
            for attempt in range(max_retries):
                try:
                    if status_callback:
                        status_callback(f"Downloading {os.path.basename(path)} (Attempt {attempt+1}/{max_retries})...")
                    
                    headers = {"User-Agent": "AlienLauncher/1.0"}
                    res = requests.get(current_url, stream=True, headers=headers, timeout=15)
                    
                    # Verify it's not a block page
                    content_type = res.headers.get('Content-Type', '').lower()
                    if 'text/html' in content_type:
                        if res.text and ('fortiguard' in res.text.lower() or 'blocked' in res.text.lower() or res.text.strip().lower().startswith(('<!doctype html', '<html'))):
                            raise ValueError("Block page received instead of binary file")

                    if res.status_code == 200:
                        with open(path, 'wb') as f:
                            for chunk in res.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        # Validate SHA-1
                        if expected_sha1:
                            actual_sha1 = get_sha1(path)
                            if actual_sha1 != expected_sha1:
                                raise ValueError(f"Checksum mismatch: expected {expected_sha1}, got {actual_sha1}")
                                
                        if status_callback:
                            status_callback(f"Successfully downloaded {os.path.basename(path)}")
                        return True
                    else:
                        raise ValueError(f"HTTP Status {res.status_code}")
                except Exception as e:
                    print(f"Failed download attempt {attempt+1} for {current_url}: {e}")
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2.0
                        
        return False

    def scan_and_repair_version(self, version_id, force_redownload=False, progress_callback=None, status_callback=None):
        """Scans and repairs all library files, assets, native DLLs, client jars, and manifests for the selected version."""
        mc_dir = self.config_manager.get_minecraft_folder()
        
        def set_status(text):
            if status_callback:
                status_callback(text)
                
        def set_progress(val, max_val):
            if progress_callback:
                progress_callback(val, max_val)

        # 1. Clean corrupted cache files first
        self.clean_corrupted_cache_files()

        version_json_path = os.path.join(mc_dir, "versions", version_id, f"{version_id}.json")
        version_jar_path = os.path.join(mc_dir, "versions", version_id, f"{version_id}.jar")

        if force_redownload:
            set_status("Force clearing version cache directory...")
            try:
                version_dir = os.path.dirname(version_json_path)
                if os.path.exists(version_dir):
                    shutil.rmtree(version_dir)
            except Exception as e:
                print(f"Error clearing version directory: {e}")

        # Download version JSON
        if not os.path.exists(version_json_path) or force_redownload:
            url = None
            self._online_versions_cache = self.get_online_version_list()
            if self._online_versions_cache:
                for v in self._online_versions_cache:
                    if v.get("id") == version_id:
                        url = v.get("url")
                        break
            if url:
                success = self.download_file_with_retry(url, version_json_path, status_callback=set_status)
                if not success:
                    return False, "Failed to download version metadata JSON file."

        # Validate version JSON existence
        if not os.path.exists(version_json_path):
            return False, f"Version JSON manifest for {version_id} does not exist on disk, and could not be downloaded from Mojang's manifest. Please verify the version name is correct and you have an active internet connection."

        # Parse version JSON
        try:
            import json
            with open(version_json_path, "r", encoding="utf-8") as f:
                version_data = json.load(f)
        except Exception as e:
            if os.path.exists(version_json_path):
                try:
                    os.remove(version_json_path)
                except Exception:
                    pass
            return False, f"Failed to parse version JSON: {e}"

        # Get libraries and assets lists
        libraries = version_data.get("libraries", [])
        downloads = version_data.get("downloads", {})
        
        # Download client JAR
        client_download = downloads.get("client", {})
        client_url = client_download.get("url")
        client_sha1 = client_download.get("sha1")
        if client_url and (not os.path.exists(version_jar_path) or force_redownload):
            success = self.download_file_with_retry(client_url, version_jar_path, client_sha1, status_callback=set_status)
            if not success:
                return False, "Failed to download Minecraft client JAR."

        # Download libraries
        total_libs = len(libraries)
        for idx, lib in enumerate(libraries):
            set_progress(idx, total_libs + 10) # 10 is padding for assets
            lib_downloads = lib.get("downloads", {})
            artifact = lib_downloads.get("artifact", {})
            lib_url = artifact.get("url")
            lib_sha1 = artifact.get("sha1")
            lib_path = os.path.join(mc_dir, "libraries", artifact.get("path", ""))
            
            if lib_url:
                if not os.path.exists(lib_path) or force_redownload or os.path.getsize(lib_path) == 0:
                    set_status(f"Repairing library {idx+1}/{total_libs}: {os.path.basename(lib_path)}")
                    self.download_file_with_retry(lib_url, lib_path, lib_sha1, status_callback=set_status)

        # Download assets
        asset_index = version_data.get("assetIndex", {})
        asset_index_id = asset_index.get("id")
        asset_index_url = asset_index.get("url")
        asset_index_sha1 = asset_index.get("sha1")
        
        if asset_index_url and asset_index_id:
            asset_index_path = os.path.join(mc_dir, "assets", "indexes", f"{asset_index_id}.json")
            if not os.path.exists(asset_index_path) or force_redownload:
                set_status(f"Downloading asset index: {asset_index_id}")
                self.download_file_with_retry(asset_index_url, asset_index_path, asset_index_sha1, status_callback=set_status)
            
            # Read asset index and download asset files
            try:
                with open(asset_index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                objects = index_data.get("objects", {})
                total_objects = len(objects)
                for obj_idx, (name, obj_info) in enumerate(objects.items()):
                    if obj_idx % 50 == 0: # Update progress every 50 objects to keep UI fast
                        set_progress(total_libs + int(10 * (obj_idx / total_objects)), total_libs + 10)
                        set_status(f"Verifying assets ({obj_idx}/{total_objects})...")
                    obj_hash = obj_info.get("hash")
                    obj_path = os.path.join(mc_dir, "assets", "objects", obj_hash[:2], obj_hash)
                    obj_url = f"https://resources.download.minecraft.net/{obj_hash[:2]}/{obj_hash}"
                    
                    if not os.path.exists(obj_path) or force_redownload or os.path.getsize(obj_path) == 0:
                        self.download_file_with_retry(obj_url, obj_path, obj_hash, max_retries=2)
            except Exception as e:
                print(f"Error repairing assets: {e}")

        # Ensure directory structures are clean
        set_status("Verification and repair complete.")
        set_progress(total_libs + 10, total_libs + 10)
        return True, "Installation repaired successfully."

    def get_installed_versions(self):
        self.clean_corrupted_cache_files()
        mc_dir = self.config_manager.get_minecraft_folder()
        if not os.path.exists(mc_dir):
            return []
        
        versions_dir = os.path.join(mc_dir, "versions")
        if not os.path.exists(versions_dir):
            return []
            
        try:
            import json
            installed_dirs = []
            for d in os.listdir(versions_dir):
                dir_path = os.path.join(versions_dir, d)
                if os.path.isdir(dir_path):
                    json_file = os.path.join(dir_path, f"{d}.json")
                    if os.path.exists(json_file):
                        # Verify the json is not empty and is valid JSON
                        try:
                            if os.path.getsize(json_file) > 0:
                                with open(json_file, "r", encoding="utf-8") as f:
                                    version_data = json.load(f)
                                
                                # Verify jar file existence
                                inherits = version_data.get("inheritsFrom")
                                if inherits:
                                    # Loader version: check if inherited base jar exists
                                    base_jar = os.path.join(versions_dir, inherits, f"{inherits}.jar")
                                    if not os.path.exists(base_jar):
                                        raise ValueError("Base jar file missing")
                                else:
                                    # Vanilla version: jar file must exist
                                    jar_file = os.path.join(dir_path, f"{d}.jar")
                                    if not os.path.exists(jar_file):
                                        raise ValueError("Jar file missing")
                                
                                installed_dirs.append(d)
                            else:
                                raise ValueError("Empty file")
                        except Exception:
                            # If it is empty or invalid, try to remove it so that it can be clean-reinstalled
                            try:
                                os.remove(json_file)
                            except Exception:
                                pass
            return installed_dirs
        except Exception as e:
            print(f"Error reading installed versions: {e}")
            return []

    def get_online_version_list(self):
        """Robustly fetches the version list from Mojang or the mirror."""
        if self._online_versions_cache:
            return self._online_versions_cache
            
        url = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
        import requests
        
        # Try map_to_mirror
        def map_to_mirror(u):
            if 'launchermeta.mojang.com' in u:
                return u.replace('launchermeta.mojang.com', 'bmclapi2.bangbang93.com')
            return u
            
        urls = [url, map_to_mirror(url)]
        for current_url in urls:
            try:
                res = requests.get(current_url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    self._online_versions_cache = data.get("versions", [])
                    return self._online_versions_cache
            except Exception:
                pass
                
        # If both fail, try local file manifest fallback
        try:
            import json
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_path = os.path.join(base_path, "assets", "version_manifest_v2.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._online_versions_cache = data.get("versions", [])
                return self._online_versions_cache
        except Exception:
            pass
            
        return []

    def get_available_versions(self):
        try:
            loader_type = self.config_manager.get("loader_type", "Vanilla")
            versions = self.get_online_version_list()
            installed = self.get_installed_versions()
            selected = self.config_manager.get("selected_version")
            
            # Gathers all releases matching the loader type
            releases = []
            for v in versions:
                v_type = v.get("type")
                v_id = v.get("id")
                
                if loader_type == "Snapshot":
                    if v_type == "snapshot":
                        releases.append(v_id)
                elif loader_type == "Old Beta/Alpha":
                    if v_type in ["old_beta", "old_alpha"]:
                        releases.append(v_id)
                else:
                    # Release, Vanilla, Fabric, Forge, etc.
                    if v_type == "release":
                        releases.append(v_id)

            # Build filtered list prioritizing selected/installed
            filtered = []
            
            if selected:
                filtered.append(selected)
            for inst in installed:
                if inst not in filtered:
                    filtered.append(inst)
            for r in releases:
                if r not in filtered:
                    filtered.append(r)
                    
            return filtered
        except Exception as e:
            print(f"Error fetching version list: {e}")
            # Even when fetching online versions fails, we MUST preserve selected and installed versions!
            installed = []
            try:
                installed = self.get_installed_versions()
            except Exception:
                pass
            selected = self.config_manager.get("selected_version")
            loader_type = self.config_manager.get("loader_type", "Vanilla")
            
            # Attempt to load local offline versions manifest
            versions = []
            try:
                import json
                if getattr(sys, 'frozen', False):
                    base_path = sys._MEIPASS
                else:
                    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cache_path = os.path.join(base_path, "assets", "version_manifest_v2.json")
                if os.path.exists(cache_path):
                    with open(cache_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    versions = data.get("versions", [])
            except Exception as cache_err:
                print(f"Error loading offline version cache: {cache_err}")
                
            releases = []
            if versions:
                for v in versions:
                    v_type = v.get("type")
                    v_id = v.get("id")
                    
                    if loader_type == "Snapshot":
                        if v_type == "snapshot":
                            releases.append(v_id)
                    elif loader_type == "Old Beta/Alpha":
                        if v_type in ["old_beta", "old_alpha"]:
                            releases.append(v_id)
                    else:
                        # Release, Vanilla, Fabric, Forge, etc.
                        if v_type == "release":
                            releases.append(v_id)
            else:
                # Absolute fallback if offline cache is missing/corrupted
                releases = ["1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.12.2", "1.8.9"]
            
            filtered = []
            if selected:
                filtered.append(selected)
            for inst in installed:
                if inst not in filtered:
                    filtered.append(inst)
            for r in releases:
                if r not in filtered:
                    filtered.append(r)
            return filtered

    def get_java_major_version(self, java_exe):
        """Runs java -version or reads version from path to determine its major version."""
        if not os.path.exists(java_exe):
            return None
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = 0x08000000 # CREATE_NO_WINDOW
            res = subprocess.run(
                [java_exe, "-version"],
                capture_output=True,
                text=True,
                creationflags=creationflags,
                timeout=5
            )
            # Java version output is on stderr
            output = res.stderr or res.stdout
            if output:
                import re
                # Matches "1.8.0_xxx" or "11.x.x" or "17.x.x" or "21.x.x"
                match = re.search(r'version "(\d+)\.?(\d+)?', output)
                if match:
                    major = int(match.group(1))
                    if major == 1: # 1.8 -> 8
                        major = int(match.group(2))
                    return major
        except Exception as e:
            print(f"Error checking Java version for {java_exe}: {e}")
        return None

    def detect_java_paths(self):
        java_paths = []
        
        # Check standard environmental variable
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            exe_w = os.path.join(java_home, "bin", "javaw.exe") if sys.platform == "win32" else os.path.join(java_home, "bin", "java")
            exe = os.path.join(java_home, "bin", "java.exe") if sys.platform == "win32" else os.path.join(java_home, "bin", "java")
            if sys.platform == "win32" and os.path.exists(exe_w):
                java_paths.append(exe_w)
            elif os.path.exists(exe):
                java_paths.append(exe)

        # Check in PATH
        path_java = shutil.which("javaw") if sys.platform == "win32" else shutil.which("java")
        if not path_java and sys.platform == "win32":
            path_java = shutil.which("java")
        if path_java and path_java not in java_paths:
            java_paths.append(path_java)

        # Check standard Adoptium/OpenJDK locations
        search_dirs = [
            r"C:\Program Files\Eclipse Adoptium",
            r"C:\Program Files\Java",
            r"C:\Program Files (x86)\Java",
            r"C:\Program Files\Microsoft"
        ]
        target_exe = "javaw.exe" if sys.platform == "win32" else "java"
        for s_dir in search_dirs:
            if os.path.exists(s_dir):
                try:
                    for root, dirs, files in os.walk(s_dir):
                        if target_exe in files:
                            exe = os.path.join(root, target_exe)
                            if exe not in java_paths:
                                java_paths.append(exe)
                except Exception as e:
                    print(f"Error scanning {s_dir}: {e}")
                    
        return java_paths

    def get_ms_login_url_info(self):
        """Generates login URL and returns (url, state, code_verifier)"""
        return get_secure_login_data(CLIENT_ID, REDIRECT_URI)

    def login_with_ms_code(self, code_or_url, code_verifier):
        """Completes Microsoft login using the auth code or the redirect URL"""
        auth_code = code_or_url
        if url_contains_auth_code(code_or_url):
            auth_code = get_auth_code_from_url(code_or_url)
            
        try:
            response = complete_login(
                client_id=CLIENT_ID,
                client_secret=None,
                redirect_uri=REDIRECT_URI,
                auth_code=auth_code,
                code_verifier=code_verifier
            )
            
            if "error" in response:
                return False, f"Login error: {response.get('errorMessage', response.get('error'))}"
                
            # Success! Save login info
            self.config_manager.set("account_type", "Microsoft")
            self.config_manager.set("username", response["name"])
            self.config_manager.set("microsoft_data", {
                "id": response["id"],
                "name": response["name"],
                "access_token": response["access_token"],
                "refresh_token": response["refresh_token"],
                "xuid": response.get("xuid", "")
            })
            return True, f"Successfully logged in as {response['name']}"
        except Exception as e:
            return False, f"Exception during Microsoft login: {str(e)}"

    def refresh_ms_login(self):
        """Refreshes saved Microsoft session"""
        ms_data = self.config_manager.get("microsoft_data")
        if not ms_data or "refresh_token" not in ms_data:
            return False, "No saved Microsoft account found."
            
        try:
            response = complete_refresh(
                client_id=CLIENT_ID,
                client_secret=None,
                redirect_uri=REDIRECT_URI,
                refresh_token=ms_data["refresh_token"]
            )
            
            if "error" in response:
                return False, f"Session refresh failed: {response.get('errorMessage', response.get('error'))}"
                
            self.config_manager.set("username", response["name"])
            self.config_manager.set("microsoft_data", {
                "id": response["id"],
                "name": response["name"],
                "access_token": response["access_token"],
                "refresh_token": response["refresh_token"],
                "xuid": response.get("xuid", "")
            })
            return True, f"Session refreshed. Welcome back, {response['name']}!"
        except Exception as e:
            return False, f"Exception refreshing session: {str(e)}"

    def find_loader_version_id(self, vanilla_version_id, loader_prefix):
        versions_dir = os.path.join(self.config_manager.get_minecraft_folder(), "versions")
        if not os.path.exists(versions_dir):
            return vanilla_version_id
        try:
            import json
            matches = []
            for d in os.listdir(versions_dir):
                if loader_prefix.lower() in d.lower() and vanilla_version_id in d:
                    dir_path = os.path.join(versions_dir, d)
                    if os.path.isdir(dir_path):
                        json_file = os.path.join(dir_path, f"{d}.json")
                        if os.path.exists(json_file):
                            try:
                                if os.path.getsize(json_file) > 0:
                                    with open(json_file, "r", encoding="utf-8") as f:
                                        version_data = json.load(f)
                                    
                                    # Verify base jar exists
                                    inherits = version_data.get("inheritsFrom")
                                    if inherits:
                                        base_jar = os.path.join(versions_dir, inherits, f"{inherits}.jar")
                                        if not os.path.exists(base_jar):
                                            raise ValueError("Base jar missing")
                                    else:
                                        jar_file = os.path.join(dir_path, f"{d}.jar")
                                        if not os.path.exists(jar_file):
                                            raise ValueError("Jar file missing")
                                            
                                    matches.append(d)
                                else:
                                    raise ValueError("Empty file")
                            except Exception:
                                try:
                                    os.remove(json_file)
                                except Exception:
                                    pass
            if matches:
                # Sort matching versions numerically so that the newest version is returned
                import re
                def version_key(name):
                    return [int(c) for c in re.findall(r'\d+', name)]
                matches.sort(key=version_key)
                return matches[-1]
        except Exception as e:
            print(f"Error finding loader version: {e}")
        return vanilla_version_id

    def is_loader_installed(self, vanilla_version_id, loader_type):
        lowered_ver = vanilla_version_id.lower()
        if "fabric-loader" in lowered_ver or "quilt-loader" in lowered_ver or "forge" in lowered_ver or "neoforge" in lowered_ver:
            return True
            
        if loader_type in ["Vanilla", "Snapshot", "Old Beta/Alpha", "Release"]:
            return True
        elif loader_type == "Fabric":
            return self.find_loader_version_id(vanilla_version_id, "fabric-loader") != vanilla_version_id
        elif loader_type == "Quilt":
            return self.find_loader_version_id(vanilla_version_id, "quilt-loader") != vanilla_version_id
        elif loader_type == "Forge":
            return self.find_loader_version_id(vanilla_version_id, "forge") != vanilla_version_id
        elif loader_type == "NeoForge":
            return self.find_loader_version_id(vanilla_version_id, "neoforge") != vanilla_version_id
        elif loader_type == "OptiFine":
            return self.find_loader_version_id(vanilla_version_id, "OptiFine") != vanilla_version_id
        elif loader_type == "LiteLoader":
            return self.find_loader_version_id(vanilla_version_id, "LiteLoader") != vanilla_version_id
        return True

    def install_version(self, version_id, progress_callback=None, status_callback=None, force_redownload=False):
        """Installs the selected version of Minecraft in a thread-safe way, with full integrity repair."""
        mc_dir = self.config_manager.get_minecraft_folder()
        loader_type = self.config_manager.get("loader_type", "Vanilla")
        
        # 1. Run the custom integrity scanner & repair first (which handles vanilla client, libraries, assets)
        success, msg = self.scan_and_repair_version(
            version_id, 
            force_redownload=force_redownload, 
            progress_callback=progress_callback, 
            status_callback=status_callback
        )
        
        if not success:
            return False, msg
            
        # 2. Install loaders if requested
        try:
            if loader_type == "Fabric":
                if status_callback:
                    status_callback("Installing Fabric loader...")
                minecraft_launcher_lib.fabric.install_fabric(version_id, mc_dir)
            elif loader_type == "Quilt":
                if status_callback:
                    status_callback("Installing Quilt loader...")
                minecraft_launcher_lib.quilt.install_quilt(version_id, mc_dir)
            elif loader_type in ["Forge", "NeoForge"]:
                if status_callback:
                    status_callback(f"Checking if {loader_type} files exist...")
                loader_id = self.find_loader_version_id(version_id, loader_type.lower())
                if loader_id == version_id:
                    return False, f"{loader_type} cannot be auto-downloaded. Please run the {loader_type} installer and point it to {mc_dir}."
                
            if status_callback:
                status_callback(f"Installation of {version_id} ({loader_type}) completed successfully!")
            return True, "Installation complete"
        except Exception as e:
            if status_callback:
                status_callback(f"Error during loader installation: {e}")
            return False, str(e)

    def ensure_authlib_injector(self, injector_path):
        import requests

        os.makedirs(os.path.dirname(injector_path), exist_ok=True)
        headers = {"User-Agent": "Alien-Launcher/1.0.0"}
        download_urls = [
            "https://authlib-injector.yushi.moe/artifact/latest/authlib-injector.jar",
            "https://authlib-injector.yushijinhun.com/artifact/latest/authlib-injector.jar"
        ]

        try:
            release = requests.get(
                "https://api.github.com/repos/yushijinhun/authlib-injector/releases/latest",
                headers=headers,
                timeout=10
            )
            if release.status_code == 200:
                assets = release.json().get("assets", [])
                jar_asset = next((a for a in assets if a.get("name", "").endswith(".jar")), None)
                if jar_asset and jar_asset.get("browser_download_url"):
                    download_urls.insert(1, jar_asset["browser_download_url"])
        except Exception as e:
            print(f"Could not resolve authlib-injector GitHub fallback: {e}")

        errors = []
        for url in download_urls:
            try:
                res = requests.get(url, headers=headers, timeout=30)
                if res.status_code == 200 and res.content:
                    with open(injector_path, "wb") as f:
                        f.write(res.content)
                    return True, None
                errors.append(f"{url}: HTTP {res.status_code}")
            except Exception as e:
                errors.append(f"{url}: {e}")

        return False, "; ".join(errors)

    def launch_minecraft(self, version_id, on_exit_callback=None):
        """Launches Minecraft under a new process"""
        self.clean_corrupted_cache_files()
        mc_dir = self.config_manager.get_minecraft_folder()
        account_type = self.config_manager.get("account_type", "Offline")
        username = self.config_manager.get("username", "AlienPlayer")
        ram_min = self.config_manager.get("ram_min", "2G")
        ram_max = self.config_manager.get("ram_max", "4G")
        java_path = self.config_manager.get("java_path")
        loader_type = self.config_manager.get("loader_type", "Vanilla")

        # Resolve launch version ID based on loader type
        launch_version_id = version_id
        if loader_type == "Fabric":
            launch_version_id = self.find_loader_version_id(version_id, "fabric-loader")
        elif loader_type == "Quilt":
            launch_version_id = self.find_loader_version_id(version_id, "quilt-loader")
        elif loader_type == "Forge":
            launch_version_id = self.find_loader_version_id(version_id, "forge")
        elif loader_type == "NeoForge":
            launch_version_id = self.find_loader_version_id(version_id, "neoforge")
        elif loader_type == "OptiFine":
            launch_version_id = self.find_loader_version_id(version_id, "OptiFine")
        elif loader_type == "LiteLoader":
            launch_version_id = self.find_loader_version_id(version_id, "LiteLoader")

        # Set up options
        options = {
            "username": username,
            "jvmArguments": [
                f"-Xms{ram_min}", 
                f"-Xmx{ram_max}",
                "-Djava.net.preferIPv4Stack=true",
                "-Dsun.net.client.defaultConnectTimeout=5000",
                "-Dsun.net.client.defaultReadTimeout=5000"
            ],
            "gameDirectory": mc_dir
        }

        # Resolve required Java major version from JSON manifest
        required_java_major = None
        version_json_path = os.path.join(mc_dir, "versions", launch_version_id, f"{launch_version_id}.json")
        if os.path.exists(version_json_path):
            try:
                import json
                with open(version_json_path, "r", encoding="utf-8") as f:
                    v_data = json.load(f)
                required_java_major = v_data.get("javaVersion", {}).get("majorVersion")
            except Exception:
                pass

        # Set Custom Java Path if set, otherwise try to find a matched javaw.exe
        if java_path:
            # If the user has a custom java.exe path, convert it to javaw.exe
            if sys.platform == "win32" and java_path.lower().endswith("java.exe"):
                java_path_w = java_path[:-8] + "javaw.exe"
                if os.path.exists(java_path_w):
                    java_path = java_path_w
            options["executablePath"] = java_path
        else:
            detected = self.detect_java_paths()
            matched_java = None
            if required_java_major and detected:
                for path in detected:
                    # Resolve real path to java.exe if it is javaw.exe for version checking
                    java_check_path = path
                    if sys.platform == "win32" and path.lower().endswith("javaw.exe"):
                        java_check_path = path[:-9] + "java.exe"
                        if not os.path.exists(java_check_path):
                            java_check_path = path
                    major = self.get_java_major_version(java_check_path)
                    if major == required_java_major:
                        matched_java = path
                        break
            if matched_java:
                options["executablePath"] = matched_java
                print(f"Auto-matched Java {required_java_major}: {matched_java}")
            elif detected:
                options["executablePath"] = detected[0]
                print(f"Using default detected Java: {detected[0]}")

        # Authentication options
        client_id_val = ""
        xuid_val = ""
        
        if account_type == "Microsoft":
            ms_data = self.config_manager.get("microsoft_data")
            if ms_data and "access_token" in ms_data:
                options["uuid"] = ms_data.get("id")
                options["token"] = ms_data.get("access_token")
                client_id_val = CLIENT_ID
                xuid_val = ms_data.get("xuid", "")
            else:
                return False, "Microsoft login credentials missing. Please log in again."
        elif account_type == "Ely.by":
            ely_data = self.config_manager.get("elyby_data")
            if ely_data and "access_token" in ely_data:
                options["uuid"] = ely_data.get("uuid")
                options["token"] = ely_data.get("access_token")
                client_id_val = "elyby"
                
                # Setup authlib-injector JavaAgent to redirect session calls to Ely.by
                if getattr(sys, 'frozen', False):
                    injector_dir = os.path.join(os.path.dirname(sys.executable), "assets")
                else:
                    injector_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
                os.makedirs(injector_dir, exist_ok=True)
                injector_path = os.path.join(injector_dir, "authlib-injector.jar")
                
                if not os.path.exists(injector_path):
                    success, error = self.ensure_authlib_injector(injector_path)
                    if not success:
                        return False, f"Failed to download authlib-injector: {error}"
                
                if os.path.exists(injector_path):
                    options["jvmArguments"].append(f"-javaagent:{injector_path}=ely.by")
                else:
                    return False, "authlib-injector.jar is missing. Ely.by launch cannot continue."
            else:
                return False, "Ely.by login credentials missing. Please log in again."
        else:
            # Offline mode
            offline_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, username))
            options["uuid"] = offline_uuid
            options["token"] = "0"
            client_id_val = "offline"

        try:
            # Generate the launch command
            cmd = minecraft_launcher_lib.command.get_minecraft_command(
                version=launch_version_id,
                minecraft_directory=mc_dir,
                options=options
            )

            # Manually replace clientid and auth_xuid placeholders in case the installed
            # version of minecraft-launcher-lib does not support newer snapshot template variables
            cmd = [arg.replace("${clientid}", client_id_val).replace("${auth_xuid}", xuid_val) for arg in cmd]

            # Run process
            log_path = os.path.join(mc_dir, "minecraft_launch.log")
            try:
                log_file = open(log_path, "w", encoding="utf-8")
            except Exception:
                log_file = subprocess.DEVNULL

            creationflags = 0
            if sys.platform == "win32":
                creationflags = 0x08000000 # CREATE_NO_WINDOW

            self.launch_process = subprocess.Popen(
                cmd,
                cwd=mc_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT if log_file != subprocess.DEVNULL else subprocess.DEVNULL,
                creationflags=creationflags
            )

            if log_file != subprocess.DEVNULL:
                try:
                    log_file.close()
                except Exception:
                    pass

            # Wait for exit in a separate thread to notify the UI
            if on_exit_callback:
                def wait_thread():
                    self.launch_process.wait()
                    on_exit_callback()
                threading.Thread(target=wait_thread, daemon=True).start()

            return True, "Minecraft launched successfully."
        except Exception as e:
            return False, f"Failed to launch Minecraft: {str(e)}"

    def is_running(self):
        if self.launch_process is None:
            return False
        return self.launch_process.poll() is None

    def login_with_elyby(self, username_or_email, password):
        import requests
        url = "https://authserver.ely.by/auth/authenticate"
        payload = {
            "agent": {
                "name": "Minecraft",
                "version": 1
            },
            "username": username_or_email,
            "password": password,
            "requestUser": True
        }
        try:
            r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            data = r.json()
            if r.status_code == 200 and "accessToken" in data:
                profile = data["selectedProfile"]
                elyby_data = {
                    "username": profile["name"],
                    "uuid": profile["id"],
                    "access_token": data["accessToken"],
                    "client_token": data.get("clientToken", "")
                }
                
                # Save to config
                self.config_manager.set("account_type", "Ely.by")
                self.config_manager.set("username", profile["name"])
                self.config_manager.set("elyby_data", elyby_data)
                return True, f"Logged in as {profile['name']} via Ely.by"
            else:
                error_msg = data.get("errorMessage", "Unknown authentication error.")
                return False, f"Ely.by Error: {error_msg}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def validate_elyby_session(self):
        elyby_data = self.config_manager.get("elyby_data")
        if not elyby_data or "access_token" not in elyby_data:
            return False
            
        import requests
        url = "https://authserver.ely.by/auth/validate"
        payload = {
            "accessToken": elyby_data["access_token"],
            "clientToken": elyby_data.get("client_token", "")
        }
        try:
            r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
            if r.status_code == 204:
                return True
        except Exception:
            pass
            
        # Try refreshing
        url_refresh = "https://authserver.ely.by/auth/refresh"
        payload_refresh = {
            "accessToken": elyby_data["access_token"],
            "clientToken": elyby_data.get("client_token", "")
        }
        try:
            r = requests.post(url_refresh, json=payload_refresh, headers={"Content-Type": "application/json"}, timeout=10)
            data = r.json()
            if r.status_code == 200 and "accessToken" in data:
                profile = data["selectedProfile"]
                new_data = {
                    "username": profile["name"],
                    "uuid": profile["id"],
                    "access_token": data["accessToken"],
                    "client_token": data.get("clientToken", "")
                }
                self.config_manager.set("username", profile["name"])
                self.config_manager.set("elyby_data", new_data)
                return True
        except Exception:
            pass
        return False
