import os
import sys
import uuid
import shutil
import subprocess
import threading
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

    def get_installed_versions(self):
        mc_dir = self.config_manager.get_minecraft_folder()
        if not os.path.exists(mc_dir):
            return []
        
        versions_dir = os.path.join(mc_dir, "versions")
        if not os.path.exists(versions_dir):
            return []
            
        try:
            return [d for d in os.listdir(versions_dir) if os.path.isdir(os.path.join(versions_dir, d))]
        except Exception as e:
            print(f"Error reading installed versions: {e}")
            return []

    def get_available_versions(self):
        try:
            loader_type = self.config_manager.get("loader_type", "Vanilla")
            versions = minecraft_launcher_lib.utils.get_version_list()
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
            # Return some common default versions as fallback
            return ["1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.12.2", "1.8.9"]

    def detect_java_paths(self):
        java_paths = []
        
        # Check standard environmental variable
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            exe = os.path.join(java_home, "bin", "java.exe")
            if os.path.exists(exe):
                java_paths.append(exe)

        # Check in PATH
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
        for s_dir in search_dirs:
            if os.path.exists(s_dir):
                try:
                    for root, dirs, files in os.walk(s_dir):
                        if "java.exe" in files:
                            exe = os.path.join(root, "java.exe")
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
            for d in os.listdir(versions_dir):
                if loader_prefix.lower() in d.lower() and vanilla_version_id in d:
                    return d
        except Exception:
            pass
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

    def install_version(self, version_id, progress_callback=None, status_callback=None):
        """Installs the selected version of Minecraft in a thread-safe way"""
        mc_dir = self.config_manager.get_minecraft_folder()
        loader_type = self.config_manager.get("loader_type", "Vanilla")
        
        current_max = 100
        
        def set_status(text):
            if status_callback:
                status_callback(text)

        def set_progress(val):
            if progress_callback:
                progress_callback(val, current_max)

        def set_max(val):
            nonlocal current_max
            current_max = val

        callback = {
            "setStatus": set_status,
            "setProgress": set_progress,
            "setMax": set_max
        }

        try:
            set_status(f"Starting installation of vanilla {version_id}...")
            minecraft_launcher_lib.install.install_minecraft_version(
                version=version_id,
                minecraft_directory=mc_dir,
                callback=callback
            )
            
            if loader_type == "Fabric":
                set_status("Installing Fabric loader...")
                minecraft_launcher_lib.fabric.install_fabric(version_id, mc_dir)
            elif loader_type == "Quilt":
                set_status("Installing Quilt loader...")
                minecraft_launcher_lib.quilt.install_quilt(version_id, mc_dir)
                
            set_status(f"Installation of {version_id} ({loader_type}) completed successfully!")
            return True, "Installation complete"
        except Exception as e:
            set_status(f"Error during installation: {e}")
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

        # Set Custom Java Path if set
        if java_path:
            options["executablePath"] = java_path

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
                import sys
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
