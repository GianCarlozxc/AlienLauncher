import os
import requests
import json

class ModsManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        # As per the user request, the Modrinth API token / authorization key
        self.api_key = "mrp_S3hxu7tTa0kbI1YkWcLI7tE2AtBAIl52ILINLvl4uaafdsszAaw3dgMiXsFT"
        self.base_url = "https://api.modrinth.com/v2"
        # CurseForge default API key and base URL
        self.cf_default_api_key = "$2a$10$.iQoyiZ3z5cRwKMtIVm39O.zEsmrBO0JDVentIncpttrd5MKz0XZy"
        self.cf_base_url = "https://api.curseforge.com/v1"

    def get_cf_api_key(self):
        return self.config_manager.get("curseforge_api_key", self.cf_default_api_key)

    def get_headers(self):
        return {
            "Authorization": self.api_key,
            "User-Agent": "Alien-Launcher/1.0.0 (contact@alien.net)"
        }

    def search_mods(self, query, offset=0, limit=10, project_type="mod"):
        url = f"{self.base_url}/search"
        valid_project_types = {"mod", "resourcepack", "datapack", "shader", "modpack"}
        if project_type not in valid_project_types:
            project_type = "mod"

        facets = [[f"project_type:{project_type}"]]
        if project_type == "datapack":
            facets = [["categories:datapack"]]

        params = {
            "query": query,
            "facets": json.dumps(facets),
            "offset": offset,
            "limit": limit
        }
        try:
            r = requests.get(url, params=params, headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                return True, r.json().get("hits", [])
            else:
                return False, f"HTTP Error {r.status_code}: {r.text}"
        except Exception as e:
            return False, f"Connection error: {e}"

    def search_curseforge(self, query, class_id=6, offset=0, limit=10):
        api_key = self.get_cf_api_key()
        url = f"{self.cf_base_url}/mods/search"
        params = {
            "gameId": 432,
            "classId": class_id,
            "searchFilter": query,
            "sortField": 1,
            "sortOrder": "desc",
            "index": offset,
            "pageSize": limit
        }
        headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "User-Agent": "Alien-Launcher/1.0.0 (contact@alien.net)"
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code == 200:
                return True, r.json().get("data", [])
            elif r.status_code == 403:
                return False, "403 Forbidden: Invalid or missing API key."
            else:
                return False, f"HTTP Error {r.status_code}"
        except Exception as e:
            return False, f"Connection error: {e}"

    def get_project_versions(self, project_id):
        url = f"{self.base_url}/project/{project_id}/version"
        try:
            r = requests.get(url, headers=self.get_headers(), timeout=10)
            if r.status_code == 200:
                return r.json()
            else:
                print(f"Error fetching versions: {r.status_code} {r.text}")
                return []
        except Exception as e:
            print(f"Exception fetching versions: {e}")
            return []

    def get_content_directory(self, project_type="mod"):
        folder_map = {
            "mod": "mods",
            "bukkit_plugin": "plugins",
            "world": "saves",
            "resourcepack": "resourcepacks",
            "customization": "customization",
            "datapack": "datapacks",
            "addon": "addons",
            "modpack": "modpacks",
            "shader": "shaderpacks"
        }
        folder_name = folder_map.get(project_type, "mods")
        return os.path.join(self.config_manager.get_minecraft_folder(), folder_name)

    def get_installed_content(self, project_type="mod"):
        content_dir = self.get_content_directory(project_type)
        if not os.path.exists(content_dir):
            return []
        try:
            return [
                f for f in os.listdir(content_dir)
                if os.path.isfile(os.path.join(content_dir, f))
            ]
        except Exception as e:
            print(f"Error listing installed content: {e}")
            return []

    def get_installed_mods(self):
        return [f for f in self.get_installed_content("mod") if f.endswith(".jar")]

    def delete_content(self, filename, project_type="mod"):
        content_dir = self.get_content_directory(project_type)
        file_path = os.path.join(content_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True, "File deleted successfully."
            except Exception as e:
                return False, f"Failed to delete file: {e}"
        return False, "Mod file not found."

    def delete_mod(self, filename):
        return self.delete_content(filename, "mod")

    def download_content(self, version_file, project_type="mod", progress_callback=None):
        """
        version_file is a dictionary containing:
        - url: download url
        - filename: name of file
        - size: size of file in bytes
        """
        url = version_file.get("url")
        filename = version_file.get("filename")
        if not url or not filename:
            return False, "Invalid file information"

        content_dir = self.get_content_directory(project_type)
        os.makedirs(content_dir, exist_ok=True)
        dest_path = os.path.join(content_dir, filename)

        try:
            r = requests.get(url, headers=self.get_headers(), stream=True, timeout=30)
            if r.status_code != 200:
                return False, f"Failed to download: HTTP {r.status_code}"

            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            # Post-process downloaded ZIP files
            if filename.lower().endswith(".zip"):
                import zipfile
                import shutil
                if project_type == "mod":
                    # Extract any .jar files and delete the zip
                    extracted_jars = []
                    try:
                        with zipfile.ZipFile(dest_path, "r") as z:
                            for name in z.namelist():
                                if name.lower().endswith(".jar"):
                                    base_name = os.path.basename(name)
                                    target_path = os.path.join(content_dir, base_name)
                                    with z.open(name) as source, open(target_path, "wb") as target:
                                        shutil.copyfileobj(source, target)
                                    extracted_jars.append(base_name)
                        try:
                            os.remove(dest_path)
                        except Exception:
                            pass
                        # Return the first extracted .jar filename
                        if extracted_jars:
                            return True, extracted_jars[0]
                    except Exception as e:
                        print(f"Error post-processing mod zip: {e}")
                elif project_type == "world":
                    # Extract full world folder and delete the zip
                    try:
                        world_name = filename[:-4]
                        world_dest = os.path.join(content_dir, world_name)
                        os.makedirs(world_dest, exist_ok=True)
                        with zipfile.ZipFile(dest_path, "r") as z:
                            z.extractall(world_dest)
                        try:
                            os.remove(dest_path)
                        except Exception:
                            pass
                        return True, world_name
                    except Exception as e:
                        print(f"Error post-processing world zip: {e}")

            return True, filename
        except Exception as e:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return False, f"Exception during download: {e}"

    def download_mod(self, version_file, progress_callback=None):
        return self.download_content(version_file, "mod", progress_callback)

    def install_curseforge_modpack(self, zip_path, progress_callback=None):
        """
        Extracts overrides and downloads all mods listed in manifest.json from CurseForge.
        progress_callback signature: progress_callback(step, total, message)
        """
        import zipfile
        import shutil
        
        mc_dir = self.config_manager.get_minecraft_folder()
        mods_dir = self.get_content_directory("mod")
        os.makedirs(mods_dir, exist_ok=True)
        
        if not os.path.exists(zip_path):
            return False, "Modpack zip file not found."
            
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                # Read manifest
                if "manifest.json" not in z.namelist():
                    return False, "Invalid modpack zip: manifest.json is missing."
                
                manifest_data = z.read("manifest.json")
                manifest = json.loads(manifest_data)
                
                # 1. Extract overrides
                if progress_callback:
                    progress_callback(0, 100, "Extracting configurations...")
                    
                for name in z.namelist():
                    if name.startswith("overrides/"):
                        rel_path = name[len("overrides/"):]
                        if not rel_path:
                            continue
                        dest_path = os.path.join(mc_dir, rel_path)
                        
                        if name.endswith("/"):
                            os.makedirs(dest_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            with z.open(name) as source, open(dest_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                                
                # 2. Download mods
                files = manifest.get("files", [])
                total_files = len(files)
                api_key = self.get_cf_api_key()
                headers = {
                    "x-api-key": api_key,
                    "Accept": "application/json",
                    "User-Agent": "Alien-Launcher/1.0.0 (contact@alien.net)"
                }
                
                for idx, f in enumerate(files):
                    project_id = f.get("projectID")
                    file_id = f.get("fileID")
                    
                    if progress_callback:
                        progress_callback(idx, total_files, f"Downloading mods ({idx}/{total_files})...")
                        
                    # Get download URL and filename from CurseForge API
                    url = f"{self.cf_base_url}/mods/{project_id}/files/{file_id}"
                    try:
                        r = requests.get(url, headers=headers, timeout=15)
                        if r.status_code == 200:
                            file_info = r.json().get("data", {})
                            download_url = file_info.get("downloadUrl")
                            filename = file_info.get("fileName")
                            
                            if download_url and filename:
                                dest_file = os.path.join(mods_dir, filename)
                                # Stream download
                                rf = requests.get(download_url, stream=True, timeout=30)
                                if rf.status_code == 200:
                                    with open(dest_file, "wb") as f_out:
                                        for chunk in rf.iter_content(chunk_size=8192):
                                            f_out.write(chunk)
                                else:
                                    print(f"Error downloading {filename}: HTTP {rf.status_code}")
                            else:
                                print(f"Missing downloadUrl or fileName for project {project_id}, file {file_id}")
                        else:
                            print(f"Error fetching file details from CF: HTTP {r.status_code}")
                    except Exception as e:
                        print(f"Exception downloading dependency {project_id}: {e}")
                        
            # Clean up the zip file after successful extraction to save space, if desired
            try:
                os.remove(zip_path)
            except Exception:
                pass
                
            return True, "Modpack installed successfully!"
            
        except Exception as e:
            return False, f"Failed to install modpack: {e}"

