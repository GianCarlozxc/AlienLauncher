import sys
import os

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
