import os
import threading
import customtkinter as ctk
import ui.theme
from tkinter import filedialog
import ui.custom_dialog as messagebox

class PrivateServerPage(ctk.CTkFrame):
    def __init__(self, parent, server_manager, minecraft_manager, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.server_manager = server_manager
        self.minecraft_manager = minecraft_manager
        self.config_manager = config_manager
        self.toplevel = self.winfo_toplevel()
        
        self.is_monitoring = False
        self.stopping = False
        
        self.setup_ui()
        self.update_server_status_ui()

    def setup_ui(self):
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(7, weight=3) # Console gets maximum vertical space

        # Header
        title_label = ctk.CTkLabel(
            self,
            text="Private Server Helper",
            font=ctk.CTkFont(family="Orbitron", size=22, weight="bold"),
            text_color="#2ECC71"
        )
        title_label.grid(row=0, column=0, padx=20, pady=(15, 2), sticky="w")

        desc_label = ctk.CTkLabel(
            self,
            text="Manage a local Minecraft server and share the address with friends using Tailscale.",
            font=ctk.CTkFont(family="Orbitron", size=11),
            text_color="#888888"
        )
        desc_label.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # Top Section: Info Cards (using 2 columns)
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=2, column=0, padx=20, pady=0, sticky="ew")
        info_frame.grid_columnconfigure((0, 1), weight=1)

        # Card Left: Connection Info
        self.address_card = ctk.CTkFrame(info_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C")
        self.address_card.grid(row=0, column=0, padx=(0, 10), pady=2, sticky="nsew")
        
        addr_title = ctk.CTkLabel(self.address_card, text="YOUR SERVER ADDRESS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#777777")
        addr_title.pack(padx=15, pady=(12, 5), anchor="w")
        
        self.addr_display = ctk.CTkLabel(self.address_card, text="Loading...", font=ctk.CTkFont(size=16, weight="bold"), text_color=ui.theme.SUCCESS_COLOR)
        self.addr_display.pack(padx=15, pady=(0, 5), anchor="w")
        
        self.btn_copy_addr = ctk.CTkButton(
            self.address_card, text="Copy Server Address", 
            fg_color="#2C2C2C", hover_color="#3A3A3A", height=24, font=ctk.CTkFont(size=11),
            command=self.copy_server_address
        )
        self.btn_copy_addr.pack(padx=15, pady=(0, 12), anchor="w")

        # Card Right: Configuration & File Links
        self.config_card = ctk.CTkFrame(info_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C")
        self.config_card.grid(row=0, column=1, padx=(10, 0), pady=2, sticky="nsew")

        cfg_title = ctk.CTkLabel(self.config_card, text="SERVER CONFIGURATION", font=ctk.CTkFont(size=11, weight="bold"), text_color="#777777")
        cfg_title.pack(padx=15, pady=(12, 5), anchor="w")

        btn_row = ctk.CTkFrame(self.config_card, fg_color="transparent")
        btn_row.pack(padx=15, pady=(0, 12), fill="x", expand=True)

        self.btn_open_properties = ctk.CTkButton(
            btn_row, text="Open server.properties",
            fg_color="#2C2C2C", hover_color="#3A3A3A", height=28,
            command=self.open_properties
        )
        self.btn_open_properties.pack(side="left", padx=(0, 10))

        # Server directory selector
        dir_selector_frame = ctk.CTkFrame(self, fg_color="#1A1A1A", border_width=1, border_color="#2A2A2A")
        dir_selector_frame.grid(row=3, column=0, padx=20, pady=8, sticky="ew")
        
        dir_title = ctk.CTkLabel(dir_selector_frame, text="Server Folder Directory", font=ctk.CTkFont(weight="bold", size=13))
        dir_title.pack(padx=15, pady=(8, 2), anchor="w")
        
        dir_controls = ctk.CTkFrame(dir_selector_frame, fg_color="transparent")
        dir_controls.pack(padx=15, pady=(0, 10), fill="x")
        
        self.dir_entry = ctk.CTkEntry(dir_controls, fg_color="#101010", border_color="#2C2C2C")
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.dir_entry.insert(0, self.server_manager.get_server_directory())
        self.dir_entry.configure(state="readonly")
        
        btn_browse = ctk.CTkButton(
            dir_controls, text="Browse...", width=80, 
            fg_color="#2C2C2C", hover_color="#3A3A3A",
            command=self.browse_server_directory
        )
        btn_browse.pack(side="right")

        # Server Creator Frame (Row 4)
        creator_frame = ctk.CTkFrame(self, fg_color="#1A1A1A", border_width=1, border_color="#2A2A2A")
        creator_frame.grid(row=4, column=0, padx=20, pady=(0, 8), sticky="ew")
        
        creator_title = ctk.CTkLabel(creator_frame, text="Create New Server Instance", font=ctk.CTkFont(weight="bold", size=14))
        creator_title.pack(padx=15, pady=(10, 5), anchor="w")
        
        controls_row = ctk.CTkFrame(creator_frame, fg_color="transparent")
        controls_row.pack(padx=15, pady=(0, 10), fill="x")
        
        type_lbl = ctk.CTkLabel(controls_row, text="Type:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        type_lbl.pack(side="left", padx=(0, 5))
        
        self.creator_type_var = ctk.StringVar(value="Vanilla")
        self.creator_type_combo = ctk.CTkComboBox(
            controls_row,
            values=["Vanilla", "Paper", "Purpur", "Spigot", "Fabric", "Forge", "NeoForge"],
            variable=self.creator_type_var,
            width=100,
            height=28,
            fg_color="#101010",
            border_color="#2C2C2C"
        )
        self.creator_type_combo.pack(side="left", padx=(0, 15))
        
        ver_lbl = ctk.CTkLabel(controls_row, text="Version:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        ver_lbl.pack(side="left", padx=(0, 5))
        
        self.creator_ver_var = ctk.StringVar(value=self.config_manager.get("selected_version", "1.20.1"))
        self.creator_ver_entry = ctk.CTkEntry(
            controls_row,
            textvariable=self.creator_ver_var,
            width=80,
            height=28,
            fg_color="#101010",
            border_color="#2C2C2C"
        )
        self.creator_ver_entry.pack(side="left", padx=(0, 15))
        
        # Gamemode Selection Option
        mode_lbl = ctk.CTkLabel(controls_row, text="Mode:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        mode_lbl.pack(side="left", padx=(0, 5))
        
        self.creator_mode_var = ctk.StringVar(value="Survival")
        self.creator_mode_combo = ctk.CTkComboBox(
            controls_row,
            values=["Survival", "Creative", "Hardcore"],
            variable=self.creator_mode_var,
            width=90,
            height=28,
            fg_color="#101010",
            border_color="#2C2C2C"
        )
        self.creator_mode_combo.pack(side="left", padx=(0, 15))
        
        # Bedrock Compatibility Checkbox
        self.bedrock_var = ctk.BooleanVar(value=False)
        self.bedrock_cb = ctk.CTkCheckBox(
            controls_row,
            text="Java + Bedrock Compatible",
            variable=self.bedrock_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#A5D6A7",
            checkbox_width=18,
            checkbox_height=18
        )
        self.bedrock_cb.pack(side="left", padx=(0, 15))
        
        self.btn_create_server = ctk.CTkButton(
            controls_row,
            text="Create Server",
            width=110,
            height=28,
            fg_color=ui.theme.ACCENT_COLOR,
            hover_color=ui.theme.ACCENT_HOVER_COLOR,
            text_color=ui.theme.ACCENT_TEXT_COLOR,
            font=ctk.CTkFont(weight="bold"),
            command=self.start_create_server_thread
        )
        self.btn_create_server.pack(side="left")

        # Help Description under controls_row
        lbl_help_desc = ctk.CTkLabel(
            creator_frame,
            text="Note: Bedrock Compatibility installs Geyser (translates packets) and Floodgate (bypasses account checks) on Paper, Purpur, or Spigot.",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#888888"
        )
        lbl_help_desc.pack(padx=15, pady=(2, 8), anchor="w")
        
        self.creator_progress_frame = ctk.CTkFrame(creator_frame, fg_color="transparent")
        
        self.creator_progress_bar = ctk.CTkProgressBar(self.creator_progress_frame, width=220, height=4, progress_color=ui.theme.ACCENT_COLOR)
        self.creator_progress_bar.pack(side="left", padx=(5, 15), pady=10)
        self.creator_progress_bar.set(0)
        
        self.creator_status_lbl = ctk.CTkLabel(
            self.creator_progress_frame,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color="#888888"
        )
        self.creator_status_lbl.pack(side="left", pady=10)

        # Control Panel: Buttons & Status (Row 5)
        control_frame = ctk.CTkFrame(self, fg_color="#1A1A1A", border_width=1, border_color="#2A2A2A")
        control_frame.grid(row=5, column=0, padx=20, pady=(0, 8), sticky="ew")

        ctrl_title = ctk.CTkLabel(control_frame, text="Server Controls", font=ctk.CTkFont(weight="bold", size=14))
        ctrl_title.pack(padx=15, pady=(10, 5), anchor="w")

        ctrl_buttons = ctk.CTkFrame(control_frame, fg_color="transparent")
        ctrl_buttons.pack(padx=15, pady=(0, 10), fill="x")

        self.btn_start = ctk.CTkButton(
            ctrl_buttons, text="Start Server", 
            fg_color=ui.theme.ACCENT_COLOR, hover_color=ui.theme.ACCENT_HOVER_COLOR, text_color=ui.theme.ACCENT_TEXT_COLOR,
            font=ctk.CTkFont(weight="bold"), command=self.start_server
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            ctrl_buttons, text="Stop Server", 
            fg_color="#E74C3C", hover_color="#C0392B", text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold"), command=self.stop_server,
            state="disabled"
        )
        self.btn_stop.pack(side="left", padx=10)

        self.server_status_light = ctk.CTkLabel(
            ctrl_buttons, text="● Offline", 
            font=ctk.CTkFont(weight="bold", size=13), text_color="#E74C3C"
        )
        self.server_status_light.pack(side="right", padx=15)

        # Log Console (Row 6)
        console_title = ctk.CTkLabel(self, text="Server Console Logs", font=ctk.CTkFont(weight="bold", size=13))
        console_title.grid(row=6, column=0, padx=20, pady=(0, 0), sticky="w")

        # Textbox (Row 7)
        self.textbox = ctk.CTkTextbox(
            self,
            fg_color="#101010",
            border_width=1,
            border_color="#2A2A2A",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#A5D6A7",
            height=160
        )
        self.textbox.grid(row=7, column=0, padx=20, pady=(5, 10), sticky="nsew")
        self.grid_rowconfigure(7, weight=1) # Console gets maximum vertical space

        self.refresh_address()

    def refresh_address(self):
        # Update server address format: IP:25565
        ip = self.config_manager.get("tailscale_ip")
        if not ip:
            # Let's check from config, if not there, set placeholder
            self.addr_display.configure(text="No Tailscale IP (Check Tailscale tab)", text_color="#E74C3C")
        else:
            self.addr_display.configure(text=f"{ip}:25565", text_color=ui.theme.SUCCESS_COLOR)

    def copy_server_address(self):
        addr = self.addr_display.cget("text")
        if addr and "No Tailscale IP" not in addr and addr != "Loading...":
            self.clipboard_clear()
            self.clipboard_append(addr)
            self.write_log(f"[System] Copied server address '{addr}' to clipboard.\n")

    def open_properties(self):
        success, msg = self.server_manager.open_server_properties()
        self.write_log(f"[System] {msg}\n")

    def browse_server_directory(self):
        selected = filedialog.askdirectory(initialdir=self.server_manager.get_server_directory())
        if selected:
            self.server_manager.set_server_directory(selected)
            self.dir_entry.configure(state="normal")
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, selected)
            self.dir_entry.configure(state="readonly")
            self.write_log(f"[System] Server directory changed to: {selected}\n")

    def start_server(self):
        self.write_log("[System] Launching local Minecraft server...\n")
        
        java_path = self.config_manager.get("java_path")
        min_ram = self.config_manager.get("ram_min", "1G")
        max_ram = self.config_manager.get("ram_max", "2G") # Keep server RAM standard or match settings

        success, msg = self.server_manager.start_server(java_path, min_ram, max_ram)
        self.write_log(f"[System] {msg}\n")
        
        if success:
            self.update_server_status_ui()
            self.start_log_monitoring()

    def stop_server(self):
        if getattr(self, 'stopping', False):
            return
        self.stopping = True
        self.update_server_status_ui()
        self.write_log("[System] Stopping Minecraft server...\n")
        
        def _stop_thread():
            success, msg = self.server_manager.stop_server()
            def _gui_update():
                self.stopping = False
                self.write_log(f"[System] {msg}\n")
                self.update_server_status_ui()
                self.is_monitoring = False
            self.run_in_gui(_gui_update)
            
        threading.Thread(target=_stop_thread, daemon=True).start()

    def update_server_status_ui(self):
        running = self.server_manager.is_running()
        if getattr(self, 'stopping', False):
            self.server_status_light.configure(text="● Stopping...", text_color="#F39C12")
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="disabled")
            self.btn_open_properties.configure(state="disabled")
        elif running:
            self.server_status_light.configure(text="● Online", text_color=ui.theme.SUCCESS_COLOR)
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.btn_open_properties.configure(state="disabled")
        else:
            self.server_status_light.configure(text="● Offline", text_color="#E74C3C")
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.btn_open_properties.configure(state="normal")

    def run_in_gui(self, func, *args, **kwargs):
        toplevel = getattr(self, "toplevel", None)
        if toplevel and hasattr(toplevel, "run_in_gui_thread"):
            toplevel.run_in_gui_thread(func, *args, **kwargs)
        else:
            self.after(0, lambda: func(*args, **kwargs))

    def start_log_monitoring(self):
        if self.is_monitoring:
            return
        self.is_monitoring = True
        self.monitor_logs()

    def monitor_logs(self):
        if not self.is_monitoring:
            return
        
        running = self.server_manager.is_running()
        self.update_server_status_ui()
        
        if not running:
            self.is_monitoring = False
            self.write_log("[System] Server process stopped.\n")
            return
            
        # Get logs and append to text box
        logs = self.server_manager.get_server_log_tail(15)
        
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", logs)
        self.textbox.configure(state="disabled")
        self.textbox.see("end")
        
        # Schedule next refresh in 1 second
        self.after(1000, self.monitor_logs)

    def write_log(self, text):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.configure(state="disabled")
        self.textbox.see("end")

    def on_view_active(self):
        self.refresh_address()
        self.update_server_status_ui()
        if self.server_manager.is_running():
            self.start_log_monitoring()

    def start_create_server_thread(self):
        server_type = self.creator_type_var.get()
        version = self.creator_ver_var.get().strip()
        gamemode = self.creator_mode_var.get()
        setup_bedrock = self.bedrock_var.get()
        if not version:
            self.write_log("[System] Error: Version string cannot be empty.\n")
            return
            
        if setup_bedrock and server_type not in ["Paper", "Purpur", "Spigot", "Fabric"]:
            messagebox.showwarning(
                "Incompatible Server Type",
                "Java + Bedrock compatibility (Geyser & Floodgate) requires a compatible server type:\n\n"
                "• Paper / Purpur / Spigot (via plugins)\n"
                "• Fabric (via mods)\n\n"
                "Vanilla and Forge do not support Geyser natively."
            )
            return
            
        self.btn_create_server.configure(state="disabled")
        self.creator_progress_frame.pack(fill="x", padx=15, pady=(0, 10))
        self.creator_progress_bar.set(0)
        self.creator_status_lbl.configure(text="Starting...")
        
        # Calculate target folder under appdata/servers (ISOLATED - NEVER touches desktop server!)
        appdata_servers_dir = os.path.join(self.config_manager.get_minecraft_folder(), "servers")
        target_dir = os.path.join(appdata_servers_dir, f"{server_type.lower()}_{version.replace('.', '_')}")
        
        def _thread():
            def progress_cb(pct):
                self.run_in_gui(self.creator_progress_bar.set, pct)
                
            def status_cb(text):
                self.run_in_gui(self.creator_status_lbl.configure, text=text)
                
            success, msg = self.server_manager.create_server(
                server_type, version, target_dir, progress_cb, status_cb, 
                gamemode=gamemode, setup_bedrock=setup_bedrock
            )
            
            def _finish():
                self.btn_create_server.configure(state="normal")
                self.creator_progress_frame.pack_forget()
                if success:
                    # Update config to point to this new server
                    self.server_manager.set_server_directory(target_dir)
                    
                    # Update GUI field
                    self.dir_entry.configure(state="normal")
                    self.dir_entry.delete(0, "end")
                    self.dir_entry.insert(0, target_dir)
                    self.dir_entry.configure(state="readonly")
                    
                    self.write_log(f"[System] Server created successfully at: {target_dir}\n")
                    self.write_log(f"[System] Launcher configuration updated to point to new server directory.\n")
                else:
                    self.write_log(f"[System] Error creating server: {msg}\n")
                    
            self.run_in_gui(_finish)
            
        threading.Thread(target=_thread, daemon=True).start()
