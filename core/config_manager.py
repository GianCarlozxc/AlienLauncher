import os
import json

DEFAULT_CONFIG = {
    "username": "AlienPlayer",
    "account_type": "Offline",  # "Offline" or "Microsoft"
    "selected_version": "1.20.1",
    "ram_min": "2G",
    "ram_max": "4G",
    "minecraft_folder": os.path.join(os.getenv("APPDATA", ""), ".giancraft"),
    "java_path": "",
    "theme": "dark",
    "tailscale_ip": "",
    "local_server_path": "",
    "microsoft_data": {}
}

class ConfigManager:
    def __init__(self, filepath="config.json"):
        if not os.path.isabs(filepath):
            import sys
            if getattr(sys, 'frozen', False):
                project_root = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(base_dir)
            filepath = os.path.join(project_root, filepath)
        self.filepath = filepath
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    loaded = json.load(f)
                    # Merge to ensure all keys exist
                    for k, v in DEFAULT_CONFIG.items():
                        if k not in loaded:
                            loaded[k] = v
                    self.config = loaded
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.save()

    def save(self):
        try:
            # Ensure the directory containing the config file exists
            dir_name = os.path.dirname(os.path.abspath(self.filepath))
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
                
            with open(self.filepath, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def get_minecraft_folder(self):
        folder = self.config.get("minecraft_folder")
        if not folder:
            folder = DEFAULT_CONFIG["minecraft_folder"]
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                print(f"Error creating minecraft directory: {e}")
        return folder
