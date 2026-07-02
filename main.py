import sys
import os

_instance_lock_socket = None

# Disable SSL verification globally to prevent SSL: CERTIFICATE_VERIFY_FAILED errors
# (common behind proxies, school networks, or environments with outdated certificates)
try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

try:
    import requests
    
    def map_to_mirror(url):
        new_url = url
        is_package_json = ('piston-meta.mojang.com' in url or 'launchermeta.mojang.com' in url) and '/packages/' in url and url.endswith('.json')
        if is_package_json:
            version_id = url.split('/')[-1][:-5]
            new_url = f"https://bmclapi2.bangbang93.com/version/{version_id}/json"
        elif 'launchermeta.mojang.com' in url:
            new_url = url.replace('launchermeta.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'launcher.mojang.com' in url:
            new_url = url.replace('launcher.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'piston-meta.mojang.com' in url:
            new_url = url.replace('piston-meta.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'piston-data.mojang.com' in url:
            new_url = url.replace('piston-data.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'libraries.minecraft.net' in url:
            new_url = url.replace('libraries.minecraft.net', 'bmclapi2.bangbang93.com/maven')
        elif 'resources.download.minecraft.net' in url:
            new_url = url.replace('resources.download.minecraft.net', 'bmclapi2.bangbang93.com/assets')
        elif 'maven.fabricmc.net' in url:
            new_url = url.replace('maven.fabricmc.net', 'bmclapi2.bangbang93.com/maven/fabricmc')
        elif 'meta.fabricmc.net' in url:
            new_url = url.replace('meta.fabricmc.net', 'bmclapi2.bangbang93.com/fabric-meta')
        return new_url

    original_request = requests.Session.request
    def patched_request(self, method, url, **kwargs):
        kwargs.setdefault('verify', False)
        # Ensure a standard User-Agent is set if not already present
        headers = kwargs.get('headers') or {}
        if not any(k.lower() == 'user-agent' for k in headers.keys()):
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            kwargs['headers'] = headers
            
        try:
            res = original_request(self, method, url, **kwargs)
            
            if res.content:
                prefix = res.content[:200].strip().lower()
                is_expected_html = "ely.by/skins" in url
                if not is_expected_html and (prefix.startswith(b'<!doctype html') or prefix.startswith(b'<html') or b'fortiguard' in prefix or b'blocked' in prefix):
                    raise Exception("Network block detected")
            return res
        except Exception as e:
            # Try fallback to mirror URL if it's a Mojang URL
            mirror_url = map_to_mirror(url)
            if mirror_url != url:
                try:
                    res = original_request(self, method, mirror_url, **kwargs)
                    if res.content:
                        prefix = res.content[:200].strip().lower()
                        if prefix.startswith(b'<!doctype html') or prefix.startswith(b'<html') or b'fortiguard' in prefix or b'blocked' in prefix:
                            raise Exception("Mirror network block detected")
                    return res
                except Exception:
                    pass
            
            if str(e) == "Network block detected":
                raise Exception("Your network connection is blocked by a firewall, web filter, or captive portal (e.g., FortiGuard). Please disable your VPN/filter or check your internet usage policy.")
            raise e

    requests.Session.request = patched_request
    
    import minecraft_launcher_lib.install
    import hashlib
    import time
    import shutil

    def patched_download_file(url, path, callback=None, sha1=None, lzma_compressed=False, session=None, minecraft_directory=None, overwrite=False):
        """Robust download_file replacement that uses temp files, retries, and checksum verification."""
        if callback is None:
            callback = {}
            
        def get_sha1_hash(file_path):
            h = hashlib.sha1()
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b''):
                        h.update(chunk)
                return h.hexdigest()
            except Exception:
                return None

        if os.path.isfile(path) and not overwrite:
            if sha1 is None:
                if os.path.getsize(path) > 0:
                    return False
            elif get_sha1_hash(path) == sha1:
                return False
                
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            pass

        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

        tmp_path = path + ".tmp"

        urls_to_try = [url]
        mirror = map_to_mirror(url)
        if mirror != url:
            urls_to_try.append(mirror)

        for current_url in urls_to_try:
            delay = 1.0
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                    
                    callback.get("setStatus", lambda x: None)(f"Downloading {os.path.basename(path)} (Attempt {attempt+1}/{max_retries})...")
                    
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    
                    r = session.get(current_url, stream=True, headers=headers, timeout=15) if session else requests.get(current_url, stream=True, headers=headers, timeout=15)
                    
                    content_type = r.headers.get('Content-Type', '').lower()
                    if 'text/html' in content_type:
                        prefix = r.content[:200].strip().lower()
                        if prefix.startswith(b'<!doctype html') or prefix.startswith(b'<html') or b'fortiguard' in prefix or b'blocked' in prefix:
                            raise ValueError("Firewall network block detected")

                    if r.status_code != 200:
                        raise ValueError(f"HTTP Status Code {r.status_code}")

                    content_length = r.headers.get('Content-Length')
                    expected_size = int(content_length) if content_length else None

                    with open(tmp_path, 'wb') as f:
                        r.raw.decode_content = True
                        if lzma_compressed:
                            import lzma
                            f.write(lzma.decompress(r.content))
                        else:
                            shutil.copyfileobj(r.raw, f)

                    if os.path.getsize(tmp_path) == 0:
                        raise ValueError("Downloaded file is 0 bytes")

                    if expected_size and os.path.getsize(tmp_path) != expected_size:
                        raise ValueError(f"Size mismatch: expected {expected_size}, got {os.path.getsize(tmp_path)}")

                    if sha1 is not None:
                        checksum = get_sha1_hash(tmp_path)
                        if checksum != sha1:
                            raise ValueError(f"Checksum mismatch: expected {sha1}, got {checksum}")

                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                    os.rename(tmp_path, path)
                    return True
                except Exception as e:
                    print(f"Error downloading {os.path.basename(path)} from {current_url}: {e}")
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2.0

        return False

    minecraft_launcher_lib.install.download_file = patched_download_file
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception as patch_e:
    print(f"Failed to apply main.py monkeypatches: {patch_e}")

# Optimize scroll speed globally for CustomTkinter scrollable frames
try:
    import customtkinter as ctk
    
    def faster_mouse_wheel_all(self, event):
        if self._check_if_valid_scroll(event.widget):
            if sys.platform.startswith("win"):
                # Scroll 3x faster on Windows (changed division from 6 to 2)
                if self._shift_pressed:
                    if self._parent_canvas.xview() != (0.0, 1.0):
                        self._parent_canvas.xview("scroll", -int(event.delta / 2), "units")
                else:
                    if self._parent_canvas.yview() != (0.0, 1.0):
                        self._parent_canvas.yview("scroll", -int(event.delta / 2), "units")
            elif sys.platform == "darwin":
                # Scroll 3x faster on MacOS
                if self._shift_pressed:
                    if self._parent_canvas.xview() != (0.0, 1.0):
                        self._parent_canvas.xview("scroll", -event.delta * 3, "units")
                else:
                    if self._parent_canvas.yview() != (0.0, 1.0):
                        self._parent_canvas.yview("scroll", -event.delta * 3, "units")
            else:
                # Scroll 3x faster on Linux/X11
                if self._shift_pressed:
                    if self._parent_canvas.xview() != (0.0, 1.0):
                        self._parent_canvas.xview_scroll(-3 if event.num == 4 else 3, "units")
                else:
                    if self._parent_canvas.yview() != (0.0, 1.0):
                        self._parent_canvas.yview_scroll(-3 if event.num == 4 else 3, "units")

    ctk.CTkScrollableFrame._mouse_wheel_all = faster_mouse_wheel_all
except Exception as e:
    print(f"Failed to apply scroll speed optimization patch: {e}")

def main():
    # Prevent multiple instances from running simultaneously
    import socket
    global _instance_lock_socket
    try:
        _instance_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to a localhost port specific to Alien Launcher
        _instance_lock_socket.bind(('127.0.0.1', 58430))
    except socket.error:
        # Another instance is already running
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("Alien Launcher", "Alien Launcher is already running!")
        except Exception:
            pass
        sys.exit(0)

    try:
        # Clean up any leftover .old executable from in-place updates
        def cleanup_old_exe():
            import time
            old_exe = sys.executable + ".old"
            for _ in range(10): # Retry up to 10 times (10 seconds total)
                try:
                    if os.path.exists(old_exe):
                        os.remove(old_exe)
                    break
                except Exception:
                    time.sleep(1)
        
        import threading
        threading.Thread(target=cleanup_old_exe, daemon=True).start()

        # Ensure our assets directory exists
        if not os.path.exists("assets"):
            os.makedirs("assets", exist_ok=True)

        # Show the Alien loading splash screen first
        from ui.splash_window import SplashWindow
        splash = SplashWindow()
        splash.mainloop()

        # Import the window launcher
        from ui.launcher_window import LauncherWindow
        
        # Initialize and start the main window loop
        app = LauncherWindow()
        app.mainloop()
        
    except ImportError as e:
        print(f"Import Error: Missing dependencies. Run 'pip install -r requirements.txt'. Details: {e}")
        # Show a friendly alert box if tkinter is available
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                f"Required Python libraries could not be found.\n\n"
                f"Please run:\n"
                f"pip install -r requirements.txt\n\n"
                f"Error detail: {e}"
            )
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error starting Alien Launcher: {e}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"An unexpected error occurred on startup:\n\n{e}")
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
