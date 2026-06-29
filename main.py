import sys
import os

# Disable SSL verification globally to prevent SSL: CERTIFICATE_VERIFY_FAILED errors
# (common behind proxies, school networks, or environments with outdated certificates)
try:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

try:
    import requests
    original_request = requests.Session.request
    def patched_request(self, method, url, **kwargs):
        kwargs.setdefault('verify', False)
        # Ensure a standard User-Agent is set if not already present
        headers = kwargs.get('headers') or {}
        if not any(k.lower() == 'user-agent' for k in headers.keys()):
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            kwargs['headers'] = headers
            
        res = original_request(self, method, url, **kwargs)
        
        # Detect firewalls or network block pages (e.g. FortiGuard) returning HTML for JSON APIs
        is_json_endpoint = url.endswith('.json') or 'api' in url or 'manifest' in url
        if is_json_endpoint and res.text:
            text_prefix = res.text.strip().lower()
            if text_prefix.startswith('<!doctype html') or text_prefix.startswith('<html') or 'fortiguard' in text_prefix or 'blocked' in text_prefix:
                raise Exception("Your network connection is blocked by a firewall, web filter, or captive portal (e.g., FortiGuard). Please disable your VPN/filter or check your internet usage policy.")
                
        return res
    requests.Session.request = patched_request
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

def main():
    try:
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
