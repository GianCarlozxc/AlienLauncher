import os
import subprocess
import shutil
import re

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
            formatted_lines = []
            for line in output.splitlines():
                stripped = line.rstrip()
                if stripped.endswith("-") and len(stripped) > 1 and stripped[-2] in (' ', '\t'):
                    line = stripped[:-1] + "online"
                formatted_lines.append(line)
            return "\n".join(formatted_lines)
        # If offline or not running
        if "Tailscale is stopped" in output or "not running" in output.lower():
            return "Tailscale is stopped. Click 'Tailscale Up' to start."
        return output or "Tailscale status unavailable."

    def up(self):
        # Runs 'tailscale up' (plain connect)
        success, output = self.run_command(["up"])
        return success, output

    def login(self, auth_key):
        # Runs 'tailscale up' with the provided authkey to log in
        success, output = self.run_command(["up", f"--authkey={auth_key}"])
        return success, output

    def down(self):
        # Runs 'tailscale down'
        success, output = self.run_command(["down"])
        return success, output

    def logout(self):
        # Runs 'tailscale logout'
        success, output = self.run_command(["logout"])
        return success, output

    def start_login_flow(self, url_callback, status_callback):
        if not self.is_installed():
            status_callback("Tailscale is not installed.")
            return
            
        cmd = [self.get_executable(), "up"]
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            url_found = False
            # Read stderr first since Tailscale writes interactive prompt there
            for line in process.stderr:
                match = re.search(r"https://login\.tailscale\.com/a/\S+", line)
                if match:
                    url = match.group(0)
                    url_callback(url)
                    url_found = True
                    break
                    
            if not url_found:
                for line in process.stdout:
                    match = re.search(r"https://login\.tailscale\.com/a/\S+", line)
                    if match:
                        url = match.group(0)
                        url_callback(url)
                        url_found = True
                        break
                        
            process.wait()
            if process.returncode == 0:
                status_callback("Login successful!")
            else:
                status_callback(f"Login process exited with code {process.returncode}")
        except Exception as e:
            status_callback(f"Error during login flow: {e}")

