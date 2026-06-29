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
