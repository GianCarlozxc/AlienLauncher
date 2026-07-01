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
        if 'launchermeta.mojang.com' in url:
            new_url = url.replace('launchermeta.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'launcher.mojang.com' in url:
            new_url = url.replace('launcher.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'piston-meta.mojang.com' in url:
            new_url = url.replace('piston-meta.mojang.com', 'bmclapi2.bangbang93.com')
        elif 'libraries.minecraft.net' in url:
            new_url = url.replace('libraries.minecraft.net', 'bmclapi2.bangbang93.com/maven')
        elif 'resources.download.minecraft.net' in url:
            new_url = url.replace('resources.download.minecraft.net', 'bmclapi2.bangbang93.com/assets')
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
            
            # Detect firewalls or network block pages (e.g. FortiGuard) returning HTML for JSON APIs
            is_json_endpoint = url.endswith('.json') or 'api' in url or 'manifest' in url
            if is_json_endpoint and res.text:
                text_prefix = res.text.strip().lower()
                if text_prefix.startswith('<!doctype html') or text_prefix.startswith('<html') or 'fortiguard' in text_prefix or 'blocked' in text_prefix:
                    raise Exception("Network block detected")
            return res
        except Exception as e:
            # Try fallback to mirror URL if it's a Mojang URL
            mirror_url = map_to_mirror(url)
            if mirror_url != url:
                try:
                    res = original_request(self, method, mirror_url, **kwargs)
                    is_json_endpoint = mirror_url.endswith('.json') or 'api' in mirror_url or 'manifest' in mirror_url
                    if is_json_endpoint and res.text:
                        text_prefix = res.text.strip().lower()
                        if text_prefix.startswith('<!doctype html') or text_prefix.startswith('<html') or 'fortiguard' in text_prefix or 'blocked' in text_prefix:
                            raise Exception("Mirror network block detected")
                    return res
                except Exception:
                    pass
            
            if str(e) == "Network block detected":
                raise Exception("Your network connection is blocked by a firewall, web filter, or captive portal (e.g., FortiGuard). Please disable your VPN/filter or check your internet usage policy.")
            raise e

    requests.Session.request = patched_request
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

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
        try:
            old_exe = sys.executable + ".old"
            if os.path.exists(old_exe):
                os.remove(old_exe)
        except Exception:
            pass

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
