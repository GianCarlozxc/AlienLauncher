import os
import subprocess
import shutil

class TailscaleManager:
    def __init__(self):
        self.executable_paths = [
            "tailscale", # If in PATH
            r"C:\Program Files\Tailscale\tailscale.exe",
            r"C:\Program Files (x86)\Tailscale\tailscale.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tailscale\tailscale.exe")
        ]
        self.tailscale_path = self._find_tailscale()

    def _find_tailscale(self):
        # First check if it is in PATH
        path_in_env = shutil.which("tailscale")
        if path_in_env:
            return path_in_env
        
        # Check standard paths
        for path in self.executable_paths:
            if os.path.exists(path):
                return path
        return None

    def is_installed(self):
        self.tailscale_path = self._find_tailscale()
        return self.tailscale_path is not None

    def get_executable(self):
        return self.tailscale_path or "tailscale"

    def run_command(self, args):
        if not self.is_installed():
            return False, "Tailscale is not installed on this system."
        
        cmd = [self.get_executable()] + args
        try:
            # Run hidden, avoid showing cmd window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0 # SW_HIDE
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                # Some commands might fail but still output error messages
                err = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
                return False, err
        except subprocess.TimeoutExpired:
            return False, "Tailscale command timed out."
        except Exception as e:
            return False, str(e)

    def get_ipv4(self):
        # Runs 'tailscale ip -4'
        success, output = self.run_command(["ip", "-4"])
        if success:
            return output.strip()
        return "Not Connected / Unknown"

    def get_status(self):
        # Runs 'tailscale status'
        success, output = self.run_command(["status"])
        if success:
            return output
        # If offline or not running
        if "Tailscale is stopped" in output or "not running" in output.lower():
            return "Tailscale is stopped. Click 'Tailscale Up' to start."
        return output or "Tailscale status unavailable."

    def up(self):
        # Runs 'tailscale up' (non-blocking or run async, but we can do a standard run)
        # Note: on Windows, 'tailscale up' might require admin if running for the first time,
        # but if it's already set up, it will connect.
        # We can run it in the background or with a timeout.
        success, output = self.run_command(["up"])
        return success, output
