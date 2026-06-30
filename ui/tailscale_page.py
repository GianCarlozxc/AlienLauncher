import os
import threading
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

        self.btn_status = ctk.CTkButton(
            buttons_container, text="Check Status", 
            fg_color="#2C2C2C", hover_color="#3A3A3A", text_color="#FFFFFF",
            command=self.action_status
        )
        self.btn_status.pack(side="left", padx=10, pady=5)

        self.btn_copy = ctk.CTkButton(
            buttons_container, text="Copy IP", 
            fg_color="#2C2C2C", hover_color="#3A3A3A", text_color="#FFFFFF",
            command=self.action_copy_ip
        )
        self.btn_copy.pack(side="left", padx=10, pady=5)

        self.btn_download = ctk.CTkButton(
            buttons_container, text="Download Tailscale", 
            fg_color="#3498DB", hover_color="#2980B9", text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold"),
            command=self.action_download_tailscale
        )

        # Status output window
        output_title = ctk.CTkLabel(self, text="Console Output (tailscale status)", font=ctk.CTkFont(weight="bold", size=13))
        output_title.grid(row=4, column=0, padx=20, pady=(15, 0), sticky="w")

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color="#101010",
            border_width=1,
            border_color="#2A2A2A",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#A5D6A7"
        )
        self.textbox.grid(row=5, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.grid_rowconfigure(5, weight=2) # Give console textbox more room

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
        
        # Connection status update
        if is_installed:
            if ip != "Not Connected / Unknown" and "logged out" not in status_output.lower():
                self.conn_status_label.configure(text="Connected", text_color=ui.theme.SUCCESS_COLOR)
                self.conn_card.configure(border_color=ui.theme.SUCCESS_COLOR)
                # Save IP in configuration for reference
                self.config_manager.set("tailscale_ip", ip)
            else:
                self.conn_status_label.configure(text="Disconnected", text_color="#F39C12")
                self.conn_card.configure(border_color="#F39C12")
        else:
            self.conn_status_label.configure(text="Inactive", text_color="#7F8C8D")
            self.conn_card.configure(border_color="#7F8C8D")

        # Update log textbox
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", status_output)
        self.textbox.configure(state="disabled")

        if not is_installed:
            self.btn_download.pack(side="left", padx=10, pady=5)
        else:
            self.btn_download.pack_forget()

    def action_up(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", "Executing 'tailscale up'...\n")
        self.textbox.configure(state="disabled")
        
        def _run_up():
            success, output = self.tailscale_manager.up()
            self.run_in_gui(self.refresh_status)
            
            def _log():
                self.textbox.configure(state="normal")
                if success:
                    self.textbox.insert("end", "\nTailscale brought up successfully!")
                else:
                    self.textbox.insert("end", f"\nFailed to bring Tailscale up: {output}")
                self.textbox.configure(state="disabled")
                
            self.run_in_gui(_log)

        threading.Thread(target=_run_up, daemon=True).start()

    def action_down(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", "Executing 'tailscale down'...\n")
        self.textbox.configure(state="disabled")
        
        def _run_down():
            success, output = self.tailscale_manager.down()
            self.run_in_gui(self.refresh_status)
            
            def _log():
                self.textbox.configure(state="normal")
                if success:
                    self.textbox.insert("end", "\nTailscale disconnected successfully!")
                else:
                    self.textbox.insert("end", f"\nFailed to disconnect Tailscale: {output}")
                self.textbox.configure(state="disabled")
                
            self.run_in_gui(_log)

        threading.Thread(target=_run_down, daemon=True).start()

    def action_status(self):
        self.refresh_status()

    def action_copy_ip(self):
        ip = self.ip_status_label.cget("text")
        if ip and ip != "Checking..." and ip != "Not Connected / Unknown":
            self.clipboard_clear()
            self.clipboard_append(ip)
            self.textbox.configure(state="normal")
            self.textbox.insert("end", f"\n[System] Copied Tailscale IP to clipboard: {ip}\n")
            self.textbox.configure(state="disabled")
            self.textbox.see("end")

    def action_download_tailscale(self):
        import webbrowser
        webbrowser.open("https://tailscale.com/download")
