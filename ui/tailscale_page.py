import os
import threading
import subprocess
import customtkinter as ctk
import ui.theme

class TailscalePage(ctk.CTkFrame):
    def __init__(self, parent, tailscale_manager, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.tailscale_manager = tailscale_manager
        self.config_manager = config_manager
        self.toplevel = self.winfo_toplevel()
        
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        # Configure layout grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Tailscale VPN Integration",
            font=ctk.CTkFont(family="Orbitron", size=22, weight="bold"),
            text_color="#2ECC71" # Sleek Minecraft green
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Description
        desc_label = ctk.CTkLabel(
            self,
            text="Tailscale lets you connect to friends' private servers easily without port forwarding.",
            font=ctk.CTkFont(family="Orbitron", size=11),
            text_color="#888888"
        )
        desc_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Cards container
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=2, column=0, padx=20, pady=0, sticky="nsew")
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="card")
        cards_frame.grid_rowconfigure(0, weight=0)

        # Card 1: Installation Status
        self.install_card = ctk.CTkFrame(cards_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C")
        self.install_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        install_title = ctk.CTkLabel(self.install_card, text="INSTALL STATUS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#777777")
        install_title.pack(padx=15, pady=(15, 5), anchor="w")
        
        self.install_status_label = ctk.CTkLabel(self.install_card, text="Checking...", font=ctk.CTkFont(size=18, weight="bold"))
        self.install_status_label.pack(padx=15, pady=(0, 15), anchor="w")

        # Card 2: Connection Status
        self.conn_card = ctk.CTkFrame(cards_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C")
        self.conn_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        conn_title = ctk.CTkLabel(self.conn_card, text="VPN CONNECTION", font=ctk.CTkFont(size=11, weight="bold"), text_color="#777777")
        conn_title.pack(padx=15, pady=(15, 5), anchor="w")
        
        self.conn_status_label = ctk.CTkLabel(self.conn_card, text="Checking...", font=ctk.CTkFont(size=18, weight="bold"))
        self.conn_status_label.pack(padx=15, pady=(0, 15), anchor="w")

        # Card 3: IP Address
        self.ip_card = ctk.CTkFrame(cards_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C")
        self.ip_card.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        ip_title = ctk.CTkLabel(self.ip_card, text="TAILSCALE IP", font=ctk.CTkFont(size=11, weight="bold"), text_color="#777777")
        ip_title.pack(padx=15, pady=(15, 5), anchor="w")
        
        self.ip_status_label = ctk.CTkLabel(self.ip_card, text="Checking...", font=ctk.CTkFont(size=18, weight="bold"), text_color=ui.theme.SUCCESS_COLOR)
        self.ip_status_label.pack(padx=15, pady=(0, 15), anchor="w")

        # Quick Actions Frame
        actions_frame = ctk.CTkFrame(self, fg_color="#1A1A1A", border_width=1, border_color="#2A2A2A")
        actions_frame.grid(row=3, column=0, padx=20, pady=15, sticky="ew")
        
        actions_title = ctk.CTkLabel(actions_frame, text="Quick Actions", font=ctk.CTkFont(weight="bold", size=14))
        actions_title.pack(padx=15, pady=(10, 5), anchor="w")

        buttons_container = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_container.pack(padx=15, pady=(0, 10), fill="x")

        self.btn_up = ctk.CTkButton(
            buttons_container, text="Tailscale Up", 
            fg_color=ui.theme.ACCENT_COLOR, hover_color=ui.theme.ACCENT_HOVER_COLOR, text_color=ui.theme.ACCENT_TEXT_COLOR,
            font=ctk.CTkFont(weight="bold"), command=self.action_up
        )
        self.btn_up.pack(side="left", padx=(0, 10), pady=5)

        self.btn_down = ctk.CTkButton(
            buttons_container, text="Tailscale Down", 
            fg_color="#C0392B", hover_color="#962D22", text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold"), command=self.action_down
        )
        self.btn_down.pack(side="left", padx=10, pady=5)

        self.btn_login_logout = ctk.CTkButton(
            buttons_container, text="Log in", 
            fg_color="#2980B9", hover_color="#1F618D", text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold"), command=self.action_login_logout
        )
        self.btn_login_logout.pack(side="left", padx=10, pady=5)

        self.btn_status = ctk.CTkButton(
            buttons_container, text="Check Status", 
            fg_color="#2C2C2C", hover_color="#3A3A3A", text_color="#FFFFFF",
            command=self.action_status
        )
        self.btn_status.pack(side="left", padx=10, pady=5)


        self.btn_download = ctk.CTkButton(
            buttons_container, text="Download TS", 
            fg_color="#3498DB", hover_color="#2980B9", text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold"),
            command=self.action_download_tailscale
        )

        # Status output window
        output_title = ctk.CTkLabel(self, text="Tailscale Status", font=ctk.CTkFont(weight="bold", size=13))
        output_title.grid(row=4, column=0, padx=20, pady=(15, 0), sticky="w")

        self.devices_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#101010",
            border_width=1,
            border_color="#2A2A2A"
        )
        self.devices_frame.grid(row=5, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.grid_rowconfigure(5, weight=2) # Give scrollable frame more room

    def run_in_gui(self, func, *args, **kwargs):
        toplevel = getattr(self, "toplevel", None)
        if toplevel and hasattr(toplevel, "run_in_gui_thread"):
            toplevel.run_in_gui_thread(func, *args, **kwargs)
        else:
            self.after(0, lambda: func(*args, **kwargs))

    def refresh_status(self):
        def _refresh():
            is_inst = self.tailscale_manager.is_installed()
            ip = self.tailscale_manager.get_ipv4()
            status_output = self.tailscale_manager.get_status()

            # Update UI safely
            self.run_in_gui(self._update_ui_values, is_inst, ip, status_output)

        threading.Thread(target=_refresh, daemon=True).start()

    def _update_ui_values(self, is_installed, ip, status_output):
        # Install status update
        if is_installed:
            self.install_status_label.configure(text="Installed", text_color=ui.theme.SUCCESS_COLOR)
            self.install_card.configure(border_color=ui.theme.SUCCESS_COLOR)
        else:
            self.install_status_label.configure(text="Not Found", text_color="#E74C3C")
            self.install_card.configure(border_color="#E74C3C")

        # IP Status update
        self.ip_status_label.configure(text=ip)
        
        # Enable/Disable status for up and down buttons
        if is_installed:
            self.btn_up.configure(state="normal")
            self.btn_down.configure(state="normal")
            
            if ip != "Not Connected / Unknown" and "logged out" not in status_output.lower():
                self.conn_status_label.configure(text="Connected", text_color=ui.theme.SUCCESS_COLOR)
                self.conn_card.configure(border_color=ui.theme.SUCCESS_COLOR)
                # Save IP in configuration for reference
                self.config_manager.set("tailscale_ip", ip)
                
                # Update login/logout button to Logout state (red)
                self.btn_login_logout.configure(
                    text="Logout",
                    fg_color="#C0392B",
                    hover_color="#962D22",
                    text_color="#FFFFFF",
                    state="normal"
                )
                self.is_logged_in = True
            else:
                self.conn_status_label.configure(text="Disconnected", text_color="#F39C12")
                self.conn_card.configure(border_color="#F39C12")
                
                # Update login/logout button to Log in state (blue)
                self.btn_login_logout.configure(
                    text="Log in",
                    fg_color="#2980B9",
                    hover_color="#1F618D",
                    text_color="#FFFFFF",
                    state="normal"
                )
                self.is_logged_in = False
        else:
            self.btn_up.configure(state="disabled")
            self.btn_down.configure(state="disabled")
            self.conn_status_label.configure(text="Inactive", text_color="#7F8C8D")
            self.conn_card.configure(border_color="#7F8C8D")
            
            # Disable login/logout button since Tailscale is not installed
            self.btn_login_logout.configure(
                text="Log in",
                fg_color="#2980B9",
                hover_color="#1F618D",
                text_color="#FFFFFF",
                state="disabled"
            )
            self.is_logged_in = False

        # Update log/devices panel
        self._update_log(status_output, clear=True)

        if not is_installed:
            self.btn_download.pack(side="left", padx=10, pady=5)
        else:
            self.btn_download.pack_forget()

    def action_up(self):
        self._update_log("Executing 'tailscale up'...\n", clear=True)
        
        def _run_up():
            success, output = self.tailscale_manager.up()
            self.run_in_gui(self.refresh_status)
            
            def _log():
                self._update_log("Executing 'tailscale up'...\n", clear=True)
                if success:
                    self._update_log("\nTailscale brought up successfully!")
                else:
                    self._update_log(f"\nFailed to bring Tailscale up: {output}")
                
            self.run_in_gui(_log)

        threading.Thread(target=_run_up, daemon=True).start()

    def action_down(self):
        self._update_log("Executing 'tailscale down'...\n", clear=True)
        
        def _run_down():
            success, output = self.tailscale_manager.down()
            self.run_in_gui(self.refresh_status)
            
            def _log():
                self._update_log("Executing 'tailscale down'...\n", clear=True)
                if success:
                    self._update_log("\nTailscale disconnected successfully!")
                else:
                    self._update_log(f"\nFailed to disconnect Tailscale: {output}")
                
            self.run_in_gui(_log)

        threading.Thread(target=_run_down, daemon=True).start()

    def action_status(self):
        self.refresh_status()


    def _copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _update_log(self, text, clear=False):
        import re
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        is_devices_list = any(re.match(r"^100\.\d+\.\d+\.\d+", l) for l in lines)
        
        if is_devices_list:
            self._render_devices(lines)
        else:
            self._render_text_log(text, clear)

    def _render_text_log(self, text, clear):
        if clear or not hasattr(self, "log_textbox") or not self.log_textbox.winfo_exists():
            for child in self.devices_frame.winfo_children():
                child.destroy()
                
            self.log_textbox = ctk.CTkTextbox(
                self.devices_frame,
                fg_color="#101010",
                border_width=0,
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color="#A5D6A7"
            )
            self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)
            
        self.log_textbox.configure(state="normal")
        if clear:
            self.log_textbox.delete("1.0", "end")
            
        import re
        import webbrowser
        parts = re.split(r"(https://\S+)", text)
        for part in parts:
            if part.startswith("https://"):
                tag_name = f"link_{hash(part)}"
                self.log_textbox.insert("end", part, tag_name)
                
                self.log_textbox._textbox.tag_config(tag_name, foreground="#3498DB", underline=True)
                self.log_textbox._textbox.tag_bind(tag_name, "<Button-1>", lambda e, u=part: webbrowser.open(u))
                self.log_textbox._textbox.tag_bind(tag_name, "<Enter>", lambda e: self.log_textbox.configure(cursor="hand2"))
                self.log_textbox._textbox.tag_bind(tag_name, "<Leave>", lambda e: self.log_textbox.configure(cursor=""))
            else:
                self.log_textbox.insert("end", part)
                
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def _render_devices(self, lines):
        # Clear all children from frame
        for child in self.devices_frame.winfo_children():
            child.destroy()
            
        import re
        parsed_devices = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                ip = parts[0]
                name = parts[1]
                user = ""
                os_name = ""
                idx = 2
                if idx < len(parts) and '@' in parts[idx]:
                    user = parts[idx]
                    idx += 1
                if idx < len(parts):
                    os_name = parts[idx]
                    idx += 1
                status = " ".join(parts[idx:]) if idx < len(parts) else "offline"
                parsed_devices.append({
                    "ip": ip,
                    "name": name,
                    "user": user,
                    "os": os_name,
                    "status": status
                })
                
        for dev in parsed_devices:
            card = ctk.CTkFrame(
                self.devices_frame,
                fg_color="#181818",
                border_width=1,
                border_color="#262626",
                height=45
            )
            card.pack(fill="x", padx=10, pady=4)
            
            # Status Indicator Dot
            is_online = "online" in dev["status"].lower() or "active" in dev["status"].lower()
            dot_color = "#2ECC71" if is_online else "#95A5A6"
            
            status_dot = ctk.CTkLabel(
                card,
                text="●",
                font=ctk.CTkFont(size=14),
                text_color=dot_color
            )
            status_dot.pack(side="left", padx=(15, 10))
            
            # Info block
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, pady=5)
            
            name_lbl = ctk.CTkLabel(
                info_frame,
                text=dev["name"],
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            )
            name_lbl.pack(anchor="w")
            
            meta_text = f"{dev['os']} | {dev['user']}" if dev['user'] else dev['os']
            if not meta_text:
                meta_text = dev["status"]
            meta_lbl = ctk.CTkLabel(
                info_frame,
                text=meta_text,
                font=ctk.CTkFont(size=10),
                text_color="#888888",
                anchor="w"
            )
            meta_lbl.pack(anchor="w")
            
            # IP Address Label
            ip_lbl = ctk.CTkLabel(
                card,
                text=dev["ip"],
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                text_color="#3498DB"
            )
            ip_lbl.pack(side="left", padx=15)
            
            # Copy Button
            def make_copy_cmd(ip=dev["ip"]):
                return lambda: self._copy_to_clipboard(ip)
                
            copy_btn = ctk.CTkButton(
                card,
                text="Copy IP",
                width=60,
                height=24,
                fg_color="#2C2C2C",
                hover_color="#3A3A3A",
                text_color="#FFFFFF",
                font=ctk.CTkFont(size=10),
                command=make_copy_cmd(dev["ip"])
            )
            copy_btn.pack(side="right", padx=15)

    def action_download_tailscale(self):
        self._update_log("Preparing to download Tailscale installer...\n", clear=True)
        self.btn_download.configure(state="disabled", text="Downloading...")
        
        def _run_download():
            import urllib.request
            import tempfile
            
            url = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe"
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "tailscale-setup.exe")
            
            try:
                self.run_in_gui(self._update_log, "Downloading installer from official servers...\n")
                urllib.request.urlretrieve(url, installer_path)
                self.run_in_gui(self._update_log, "Download complete! Launching installer...\n(Please accept the Windows UAC permission prompt to install)\n")
                
                # Run elevated and wait for completion using PowerShell
                cmd = [
                    "powershell",
                    "-Command",
                    f"Start-Process -FilePath '{installer_path}' -ArgumentList '/quiet /norestart' -Verb RunAs -Wait"
                ]
                
                # Hide CMD popup on Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0 # SW_HIDE
                
                subprocess.run(cmd, startupinfo=startupinfo, check=True)
                
                # Check if installation was successful
                if self.tailscale_manager.is_installed():
                    self.run_in_gui(self._update_log, "\n[System] Tailscale has been successfully installed!\n")
                else:
                    self.run_in_gui(self._update_log, "\n[System] Tailscale installation was cancelled or failed.\n")
                    
            except Exception as e:
                self.run_in_gui(self._update_log, f"Failed to download or run installer: {str(e)}\n")
            finally:
                def _reset_btn():
                    self.btn_download.configure(state="normal", text="Download TS")
                    self.refresh_status()
                self.run_in_gui(_reset_btn)

        threading.Thread(target=_run_download, daemon=True).start()

    def action_logout(self):
        self._update_log("Executing 'tailscale logout'...\n", clear=True)
        
        def _run_logout():
            success, output = self.tailscale_manager.logout()
            self.run_in_gui(self.refresh_status)
            
            def _log():
                self._update_log("Executing 'tailscale logout'...\n", clear=True)
                if success:
                    self._update_log("\nLogged out from Tailscale successfully!")
                else:
                    self._update_log(f"\nFailed to logout: {output}")
                
            self.run_in_gui(_log)

        threading.Thread(target=_run_logout, daemon=True).start()

    def action_login(self):
        import sys
        self._update_log("Starting Tailscale login flow...\n", clear=True)
        
        def _on_url(url):
            self.run_in_gui(self._update_log, f"Login link generated: {url}\nOpening embedded login window...\n")
            
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            script_path = os.path.join(base_dir, "scripts", "show_login.py")
            
            cmd = [sys.executable, script_path, url]
            
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            subprocess.Popen(cmd, startupinfo=startupinfo)
            
        def _on_status(status_msg):
            self.run_in_gui(self._update_log, f"\n[Status] {status_msg}\n")
            self.run_in_gui(self.refresh_status)
            
        def _run():
            self.tailscale_manager.start_login_flow(_on_url, _on_status)
            
        threading.Thread(target=_run, daemon=True).start()

    def action_login_logout(self):
        if getattr(self, "is_logged_in", False):
            self.action_logout()
        else:
            self.action_login()
