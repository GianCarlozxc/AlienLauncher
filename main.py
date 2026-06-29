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
        return original_request(self, method, url, **kwargs)
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
