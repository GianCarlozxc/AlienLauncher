import os
import webbrowser
import threading
import customtkinter as ctk
from tkinter import filedialog
import ui.custom_dialog as messagebox
from ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_TEXT, BORDER, BORDER_DARK, CARD_BORDER,
    CONTROL_BG, CONTROL_HOVER, SECONDARY_BUTTON, SECONDARY_HOVER, SIDEBAR_BG,
    SURFACE, SURFACE_ALT, SURFACE_HOVER, TEXT_DISABLED, TEXT_MUTED,
    TEXT_PRIMARY, TEXT_SECONDARY, normalize_structural_colors
)

class MicrosoftLoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, minecraft_manager, on_success_callback):
        super().__init__(parent)
        self.minecraft_manager = minecraft_manager
        self.on_success_callback = on_success_callback
        
        self.title("Microsoft Account Login")
        self.geometry("500x380")
        self.resizable(False, False)
        
        # Grab focus and make it modal
        self.grab_set()
        
        # Fetch login URL in background or immediately
        self.login_url, oauth_state, self.code_verifier = self.minecraft_manager.get_ms_login_url_info()
        
        self.setup_ui()
        self.check_clipboard_for_code()
        
        # Stop clipboard polling when destroyed
        self.bind("<Destroy>", lambda e: self.after_cancel(self._clip_poll_id) if hasattr(self, "_clip_poll_id") else None)

    def setup_ui(self):
        # Configure layout
        self.configure(fg_color=SIDEBAR_BG)
        
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        title = ctk.CTkLabel(
            main_frame, text="Microsoft Authentication",
            font=ctk.CTkFont(family="Orbitron", size=16, weight="bold"),
            text_color=ACCENT
        )
        title.pack(pady=(0, 10))

        info_text = (
            "Alien Launcher uses official Microsoft authentication.\n\n"
            "1. Click the button below to sign in via your web browser.\n"
            "2. After signing in, Microsoft will show a warning page:\n"
            "   'You have reached a page that is not normally shown...'\n"
            "3. Copy the ENTIRE URL from your browser's address bar on that page and paste it below."
        )
        info_label = ctk.CTkLabel(
            main_frame, text=info_text, justify="left", wraplength=440,
            font=ctk.CTkFont(family="Orbitron", size=11), text_color=TEXT_SECONDARY
        )
        info_label.pack(pady=10)

        # Button to open browser
        btn_open = ctk.CTkButton(
            main_frame, text="1. Open Browser for Sign-in",
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT,
            font=ctk.CTkFont(weight="bold"), command=self.open_browser
        )
        btn_open.pack(pady=15, fill="x")

        # Code entry
        p_label = ctk.CTkLabel(main_frame, text="2. Paste Redirect URL or Code here:", font=ctk.CTkFont(weight="bold"))
        p_label.pack(anchor="w")

        self.url_entry = ctk.CTkEntry(
            main_frame, placeholder_text="https://login.live.com/oauth20_desktop.srf?code=...",
            fg_color=SURFACE, border_color=BORDER
        )
        self.url_entry.pack(pady=5, fill="x")

        # Status
        self.status_label = ctk.CTkLabel(main_frame, text="", text_color=TEXT_MUTED)
        self.status_label.pack(pady=5)

        # Complete button
        self.btn_submit = ctk.CTkButton(
            main_frame, text="3. Complete Login",
            fg_color=SECONDARY_BUTTON, hover_color=SECONDARY_HOVER,
            command=self.submit_code
        )
        self.btn_submit.pack(pady=(5, 0), fill="x")

    def run_in_gui(self, func, *args):
        if hasattr(self.master, "run_in_gui"):
            self.master.run_in_gui(func, *args)
        else:
            self.after(0, lambda: func(*args))

    def open_browser(self):
        try:
            webbrowser.open(self.login_url)
            self.status_label.configure(text="Browser opened. Please sign in.", text_color="#3498DB")
        except Exception as e:
            self.status_label.configure(text=f"Failed to open browser: {e}", text_color="#E74C3C")

    def submit_code(self):
        input_data = self.url_entry.get().strip()
        if not input_data:
            self.status_label.configure(text="Please paste the URL first!", text_color="#E74C3C")
            return

        self.status_label.configure(text="Authenticating...", text_color="#F39C12")
        self.btn_submit.configure(state="disabled")

        def _auth_thread():
            success, msg = self.minecraft_manager.login_with_ms_code(input_data, self.code_verifier)
            
            def _complete():
                self.btn_submit.configure(state="normal")
                if success:
                    self.status_label.configure(text="Login successful!", text_color="#2ECC71")
                    self.on_success_callback()
                    # Close dialog shortly
                    self.after(1000, self.destroy)
                else:
                    self.status_label.configure(text=msg, text_color="#E74C3C", wraplength=440)
            
            self.run_in_gui(_complete)

        threading.Thread(target=_auth_thread, daemon=True).start()

    def check_clipboard_for_code(self):
        try:
            if self.btn_submit.cget("state") == "disabled":
                self._clip_poll_id = self.after(500, self.check_clipboard_for_code)
                return
                
            clipboard_content = self.clipboard_get().strip()
            if "login.live.com/oauth20_desktop.srf" in clipboard_content and "code=" in clipboard_content:
                # Found it!
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard_content)
                self.status_label.configure(text="Auto-detected URL from clipboard! Logging in...", text_color="#2ECC71")
                try:
                    self.clipboard_clear()
                except Exception:
                    pass
                self.submit_code()
                return
        except Exception:
            pass
        self._clip_poll_id = self.after(500, self.check_clipboard_for_code)


class ElyByLoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, minecraft_manager, on_success_callback):
        super().__init__(parent)
        self.minecraft_manager = minecraft_manager
        self.on_success_callback = on_success_callback

        self.title("Ely.by Login")
        self.geometry("380x280")
        self.resizable(False, False)
        self.grab_set()

        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color=SIDEBAR_BG)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        title = ctk.CTkLabel(
            main_frame, text="Ely.by Account Sign-in",
            font=ctk.CTkFont(family="Orbitron", size=16, weight="bold"),
            text_color=ACCENT
        )
        title.pack(pady=(0, 15))

        # Email / Username Entry
        email_lbl = ctk.CTkLabel(main_frame, text="Email or Ely.by Nickname:", font=ctk.CTkFont(size=12, weight="bold"))
        email_lbl.pack(anchor="w")
        self.entry_email = ctk.CTkEntry(main_frame, placeholder_text="e.g. alex@mail.com", fg_color=SURFACE, border_color=BORDER)
        self.entry_email.pack(pady=(2, 10), fill="x")

        # Password Entry
        pass_lbl = ctk.CTkLabel(main_frame, text="Password:", font=ctk.CTkFont(size=12, weight="bold"))
        pass_lbl.pack(anchor="w")
        self.entry_password = ctk.CTkEntry(main_frame, placeholder_text="••••••••", show="*", fg_color=SURFACE, border_color=BORDER)
        self.entry_password.pack(pady=(2, 15), fill="x")

        # Status
        self.status_lbl = ctk.CTkLabel(main_frame, text="", text_color="#E74C3C")
        self.status_lbl.pack(pady=2)

        # Login button
        self.btn_login = ctk.CTkButton(
            main_frame, text="Sign In",
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT,
            font=ctk.CTkFont(weight="bold"), command=self.do_login
        )
        self.btn_login.pack(fill="x")

    def do_login(self):
        email = self.entry_email.get().strip()
        password = self.entry_password.get().strip()

        if not email or not password:
            self.status_lbl.configure(text="Please fill in all fields.")
            return

        self.btn_login.configure(state="disabled", text="Logging in...")
        self.status_lbl.configure(text="")

        def _thread():
            success, msg = self.minecraft_manager.login_with_elyby(email, password)
            
            def _complete():
                self.btn_login.configure(state="normal", text="Sign In")
                if success:
                    self.on_success_callback()
                    self.destroy()
                else:
                    self.status_lbl.configure(text=msg)

            self.after(0, _complete)

        threading.Thread(target=_thread, daemon=True).start()


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, config_manager, minecraft_manager):
        super().__init__(parent, fg_color="transparent")
        self.config_manager = config_manager
        self.minecraft_manager = minecraft_manager
        self.toplevel = self.winfo_toplevel()
        
        from core.update_manager import UpdateManager
        self.update_manager = UpdateManager(config_manager)

        self.setup_ui()
        self.load_values()

    def run_in_gui(self, func, *args, **kwargs):
        toplevel = getattr(self, "toplevel", None)
        if toplevel and hasattr(toplevel, "run_in_gui_thread"):
            toplevel.run_in_gui_thread(func, *args, **kwargs)
        else:
            self.after(0, lambda: func(*args, **kwargs))

    def setup_ui(self):
        # 1. First, declare all StringVars and scan Java
        self.account_type_var = ctk.StringVar(value="Offline")
        self.java_paths = self.minecraft_manager.detect_java_paths()
        self.java_var = ctk.StringVar(value="Default System Java")
        self.ram_min_var = ctk.StringVar(value="1G")
        self.ram_max_var = ctk.StringVar(value="2G")
        self.theme_var = ctk.StringVar(value="Dark")
        self.launcher_style_var = ctk.StringVar(value="Alien Launcher")

        # 2. Layout scrolling container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        scrollable_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scrollable_container.grid_columnconfigure(0, weight=1)

        # Header
        title_label = ctk.CTkLabel(
            scrollable_container,
            text="Settings & Configuration",
            font=ctk.CTkFont(family="Orbitron", size=22, weight="bold"),
            text_color=ACCENT
        )
        title_label.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        row = 1

        # ----------------------------------------------------
        # Card 1: Account Settings
        # ----------------------------------------------------
        account_card = ctk.CTkFrame(scrollable_container, fg_color=SURFACE, border_width=1, border_color=BORDER)
        account_card.grid(row=row, column=0, padx=15, pady=10, sticky="ew")
        account_card.grid_columnconfigure(0, weight=1)
        row += 1

        card_title_1 = ctk.CTkLabel(account_card, text="Account Configuration", font=ctk.CTkFont(weight="bold", size=14))
        card_title_1.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 10), sticky="w")

        # Row 1: Account Type
        row_frame_1 = ctk.CTkFrame(account_card, fg_color="transparent")
        row_frame_1.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_1.grid_columnconfigure(0, weight=1)
        row_frame_1.grid_columnconfigure(1, weight=0)
        
        lbl_type_title = ctk.CTkLabel(row_frame_1, text="Account Type", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_type_title.grid(row=0, column=0, sticky="w")
        lbl_type_desc = ctk.CTkLabel(row_frame_1, text="Choose Offline Mode or official Microsoft authentication.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_type_desc.grid(row=1, column=0, sticky="w")
        
        self.account_type_btn = ctk.CTkButton(
            row_frame_1, 
            text="Offline  ▼",
            width=180,
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.open_selector_dialog("Select Account Type", ["Offline", "Microsoft", "Ely.by"], self.account_type_var, self.on_account_type_change)
        )
        self.account_type_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # Row 2: Offline Username
        row_frame_2 = ctk.CTkFrame(account_card, fg_color="transparent")
        row_frame_2.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_2.grid_columnconfigure(0, weight=1)
        row_frame_2.grid_columnconfigure(1, weight=0)
        
        self.username_label = ctk.CTkLabel(row_frame_2, text="Offline Username", font=ctk.CTkFont(size=13, weight="bold"))
        self.username_label.grid(row=0, column=0, sticky="w")
        self.username_desc = ctk.CTkLabel(row_frame_2, text="Your display username for offline profiles (no spaces).", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.username_desc.grid(row=1, column=0, sticky="w")

        # Gamer ID Display (deterministic based on current username)
        self.lbl_gamer_id = ctk.CTkLabel(
            row_frame_2, 
            text="Your P2P Gamer ID: #----", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color=ACCENT
        )
        self.lbl_gamer_id.grid(row=2, column=0, sticky="w", pady=(2, 0))
        
        self.username_entry = ctk.CTkEntry(row_frame_2, width=180, fg_color=CONTROL_BG, border_color=CARD_BORDER)
        self.username_entry.grid(row=0, column=1, rowspan=3, sticky="e", padx=(10, 0))
        self.username_entry.bind("<KeyRelease>", lambda e: self.update_gamer_id_label(self.username_entry.get().strip()))

        # Row 3: Microsoft details (dynamically shown)
        self.microsoft_frame = ctk.CTkFrame(account_card, fg_color="transparent")
        self.microsoft_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        self.microsoft_frame.grid_columnconfigure(0, weight=1)
        self.microsoft_frame.grid_columnconfigure(1, weight=0)
        
        ms_info_sub = ctk.CTkFrame(self.microsoft_frame, fg_color="transparent")
        ms_info_sub.grid(row=0, column=0, sticky="w")
        
        ms_lbl_title = ctk.CTkLabel(ms_info_sub, text="Microsoft Authentication", font=ctk.CTkFont(size=13, weight="bold"))
        ms_lbl_title.grid(row=0, column=0, sticky="w")
        
        self.ms_status_label = ctk.CTkLabel(ms_info_sub, text="Logged out", text_color="#E74C3C", font=ctk.CTkFont(size=11, weight="bold"))
        self.ms_status_label.grid(row=1, column=0, sticky="w")
        
        self.btn_ms_action = ctk.CTkButton(
            self.microsoft_frame, text="Login with Microsoft", 
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT, font=ctk.CTkFont(weight="bold"),
            command=self.microsoft_login
        )
        self.btn_ms_action.grid(row=0, column=1, sticky="e")

        # Row 4: Ely.by details (dynamically shown)
        self.elyby_frame = ctk.CTkFrame(account_card, fg_color="transparent")
        self.elyby_frame.grid(row=4, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        self.elyby_frame.grid_columnconfigure(0, weight=1)
        self.elyby_frame.grid_columnconfigure(1, weight=0)

        elyby_info_sub = ctk.CTkFrame(self.elyby_frame, fg_color="transparent")
        elyby_info_sub.grid(row=0, column=0, sticky="w")

        ely_lbl_title = ctk.CTkLabel(elyby_info_sub, text="Ely.by Authentication", font=ctk.CTkFont(size=13, weight="bold"))
        ely_lbl_title.grid(row=0, column=0, sticky="w")

        self.elyby_status_label = ctk.CTkLabel(elyby_info_sub, text="Logged out", text_color="#E74C3C", font=ctk.CTkFont(size=11, weight="bold"))
        self.elyby_status_label.grid(row=1, column=0, sticky="w")

        self.btn_elyby_action = ctk.CTkButton(
            self.elyby_frame, text="Login with Ely.by", 
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT, font=ctk.CTkFont(weight="bold"),
            command=self.elyby_login
        )
        self.btn_elyby_action.grid(row=0, column=1, sticky="e")

        # ----------------------------------------------------
        # Card 2: Minecraft Launch Options
        # ----------------------------------------------------
        mc_card = ctk.CTkFrame(scrollable_container, fg_color=SURFACE, border_width=1, border_color=BORDER)
        mc_card.grid(row=row, column=0, padx=15, pady=10, sticky="ew")
        mc_card.grid_columnconfigure(0, weight=1)
        row += 1

        card_title_2 = ctk.CTkLabel(mc_card, text="Minecraft Engine Settings", font=ctk.CTkFont(weight="bold", size=14))
        card_title_2.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 10), sticky="w")

        # Row 1: Game directory
        row_frame_4 = ctk.CTkFrame(mc_card, fg_color="transparent")
        row_frame_4.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_4.grid_columnconfigure(0, weight=1)
        row_frame_4.grid_columnconfigure(1, weight=0)
        
        lbl_dir_title = ctk.CTkLabel(row_frame_4, text="Game Directory", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_dir_title.grid(row=0, column=0, sticky="w")
        lbl_dir_desc = ctk.CTkLabel(row_frame_4, text="Path where versions, mods, and assets are stored.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_dir_desc.grid(row=1, column=0, sticky="w")
        
        dir_controls = ctk.CTkFrame(row_frame_4, fg_color="transparent")
        dir_controls.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))
        
        self.folder_entry = ctk.CTkEntry(dir_controls, width=220, fg_color=CONTROL_BG, border_color=CARD_BORDER)
        self.folder_entry.pack(side="left", padx=(0, 10))
        
        self.btn_folder_browse = ctk.CTkButton(
            dir_controls, text="Browse", width=70, fg_color=SECONDARY_BUTTON, hover_color=SECONDARY_HOVER,
            command=self.browse_minecraft_folder
        )
        self.btn_folder_browse.pack(side="right")

        # Row 2: Java Path
        row_frame_5 = ctk.CTkFrame(mc_card, fg_color="transparent")
        row_frame_5.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_5.grid_columnconfigure(0, weight=1)
        row_frame_5.grid_columnconfigure(1, weight=0)
        
        lbl_java_title = ctk.CTkLabel(row_frame_5, text="Java Runtime Executable", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_java_title.grid(row=0, column=0, sticky="w")
        lbl_java_desc = ctk.CTkLabel(row_frame_5, text="Select the JRE/JDK used to run Minecraft.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_java_desc.grid(row=1, column=0, sticky="w")
        
        java_controls = ctk.CTkFrame(row_frame_5, fg_color="transparent")
        java_controls.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))
        
        self.java_btn = ctk.CTkButton(
            java_controls, 
            text="Default System Java  ▼",
            width=220,
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.open_selector_dialog("Select Java Path", self.java_paths + ["Default System Java"], self.java_var)
        )
        self.java_btn.pack(side="left", padx=(0, 10))
        
        self.btn_java_browse = ctk.CTkButton(
            java_controls, text="Browse", width=70, fg_color=SECONDARY_BUTTON, hover_color=SECONDARY_HOVER,
            command=self.browse_java_path
        )
        self.btn_java_browse.pack(side="right")

        # Row 3: Min RAM
        row_frame_6 = ctk.CTkFrame(mc_card, fg_color="transparent")
        row_frame_6.grid(row=3, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_6.grid_columnconfigure(0, weight=1)
        row_frame_6.grid_columnconfigure(1, weight=0)
        
        lbl_min_ram_title = ctk.CTkLabel(row_frame_6, text="Minimum Memory Allocation", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_min_ram_title.grid(row=0, column=0, sticky="w")
        lbl_min_ram_desc = ctk.CTkLabel(row_frame_6, text="Minimum RAM allocated to the JVM at game startup.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_min_ram_desc.grid(row=1, column=0, sticky="w")
        
        self.ram_min_btn = ctk.CTkButton(
            row_frame_6, 
            text="1G  ▼",
            width=180,
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.open_selector_dialog("Select Min RAM", ["512M", "1G", "2G", "3G", "4G"], self.ram_min_var)
        )
        self.ram_min_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # Row 4: Max RAM
        row_frame_7 = ctk.CTkFrame(mc_card, fg_color="transparent")
        row_frame_7.grid(row=4, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_7.grid_columnconfigure(0, weight=1)
        row_frame_7.grid_columnconfigure(1, weight=0)
        
        lbl_max_ram_title = ctk.CTkLabel(row_frame_7, text="Maximum Memory Allocation", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_max_ram_title.grid(row=0, column=0, sticky="w")
        lbl_max_ram_desc = ctk.CTkLabel(row_frame_7, text="Maximum RAM allowed for Minecraft (avoids out-of-memory crashes).", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_max_ram_desc.grid(row=1, column=0, sticky="w")
        
        self.ram_max_btn = ctk.CTkButton(
            row_frame_7, 
            text="2G  ▼",
            width=180,
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.open_selector_dialog("Select Max RAM", ["1G", "2G", "3G", "4G", "6G", "8G", "12G", "16G"], self.ram_max_var)
        )
        self.ram_max_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # ----------------------------------------------------
        # Card 3: Launcher Styling
        # ----------------------------------------------------
        style_card = ctk.CTkFrame(scrollable_container, fg_color=SURFACE, border_width=1, border_color=BORDER)
        style_card.grid(row=row, column=0, padx=15, pady=10, sticky="ew")
        style_card.grid_columnconfigure(0, weight=1)
        row += 1

        card_title_3 = ctk.CTkLabel(style_card, text="Visual Customization", font=ctk.CTkFont(weight="bold", size=14))
        card_title_3.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 10), sticky="w")

        # Row 1: Switch Launcher Style
        row_frame_7b = ctk.CTkFrame(style_card, fg_color="transparent")
        row_frame_7b.grid(row=1, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_7b.grid_columnconfigure(0, weight=1)
        row_frame_7b.grid_columnconfigure(1, weight=0)
        
        lbl_style_title = ctk.CTkLabel(row_frame_7b, text="Switch Launcher Style", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_style_title.grid(row=0, column=0, sticky="w")
        lbl_style_desc = ctk.CTkLabel(row_frame_7b, text="Toggle between Alien Launcher and Unicorn Launcher themes.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_style_desc.grid(row=1, column=0, sticky="w")
        
        self.style_btn = ctk.CTkButton(
            row_frame_7b, 
            text="Alien Launcher  ▼",
            width=180,
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.open_selector_dialog("Select Launcher Style", ["Alien Launcher", "Unicorn Launcher"], self.launcher_style_var, self.change_launcher_style)
        )
        self.style_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # Row 2: Theme Mode
        row_frame_8 = ctk.CTkFrame(style_card, fg_color="transparent")
        row_frame_8.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_8.grid_columnconfigure(0, weight=1)
        row_frame_8.grid_columnconfigure(1, weight=0)
        
        lbl_theme_title = ctk.CTkLabel(row_frame_8, text="Launcher Theme Mode", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_theme_title.grid(row=0, column=0, sticky="w")
        lbl_theme_desc = ctk.CTkLabel(row_frame_8, text="Select Dark, Light, or System default appearance.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_theme_desc.grid(row=1, column=0, sticky="w")
        
        self.theme_btn = ctk.CTkButton(
            row_frame_8, 
            text="Dark  ▼",
            width=180,
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.open_selector_dialog("Select Theme", ["System", "Dark", "Light"], self.theme_var, self.change_theme_mode)
        )
        self.theme_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # ----------------------------------------------------
        # Card 4: Launcher Updates
        # ----------------------------------------------------
        update_card = ctk.CTkFrame(scrollable_container, fg_color=SURFACE, border_width=1, border_color=BORDER)
        update_card.grid(row=row, column=0, padx=15, pady=10, sticky="ew")
        update_card.grid_columnconfigure(0, weight=1)
        row += 1

        card_title_4 = ctk.CTkLabel(update_card, text="Launcher Updates", font=ctk.CTkFont(weight="bold", size=14))
        card_title_4.grid(row=0, column=0, columnspan=2, padx=15, pady=(12, 10), sticky="w")

        # Row 1: Enable Update Checks Switch
        import tkinter as tk
        row_frame_9a = ctk.CTkFrame(update_card, fg_color="transparent")
        row_frame_9a.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="ew")
        row_frame_9a.grid_columnconfigure(0, weight=1)
        row_frame_9a.grid_columnconfigure(1, weight=0)
        
        lbl_enable_update_title = ctk.CTkLabel(row_frame_9a, text="Enable Update Checks", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_enable_update_title.grid(row=0, column=0, sticky="w")
        lbl_enable_update_desc = ctk.CTkLabel(row_frame_9a, text="Allow checking for launcher updates manually.", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        lbl_enable_update_desc.grid(row=1, column=0, sticky="w")
        
        self.enable_update_check_var = tk.BooleanVar(value=self.config_manager.get("enable_update_check", True))
        self.enable_update_check_switch = ctk.CTkSwitch(
            row_frame_9a,
            text="",
            variable=self.enable_update_check_var,
            progress_color=ACCENT,
            command=self.toggle_update_check_visibility
        )
        self.enable_update_check_switch.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # Row 2: Check and Update controls
        row_frame_9 = ctk.CTkFrame(update_card, fg_color="transparent")
        row_frame_9.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        row_frame_9.grid_columnconfigure(0, weight=1)
        row_frame_9.grid_columnconfigure(1, weight=0)

        lbl_update_title = ctk.CTkLabel(row_frame_9, text="Version Check & Updates", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_update_title.grid(row=0, column=0, sticky="w")
        
        self.lbl_update_version = ctk.CTkLabel(row_frame_9, text=f"Current version: v{self.update_manager.current_version}", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.lbl_update_version.grid(row=1, column=0, sticky="w")

        self.btn_check_update = ctk.CTkButton(
            row_frame_9, 
            text="Check for Updates",
            width=180,
            height=30,
            fg_color=SECONDARY_BUTTON,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=self.check_for_updates
        )
        self.btn_check_update.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))

        # Progress bar for update download (hidden initially)
        self.update_progress_bar = ctk.CTkProgressBar(row_frame_9, progress_color=ACCENT, height=4)
        self.update_progress_bar.grid(row=2, column=0, columnspan=2, pady=(8, 0), sticky="ew")
        self.update_progress_bar.set(0)
        self.update_progress_bar.grid_remove()

        # ----------------------------------------------------
        # Save Button
        # ----------------------------------------------------
        self.btn_save = ctk.CTkButton(
            scrollable_container, text="Save Settings",
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT,
            font=ctk.CTkFont(weight="bold", size=14), height=38,
            command=self.save_settings
        )
        self.btn_save.grid(row=row, column=0, padx=15, pady=20, sticky="ew")

    def load_values(self):
        # Set account type
        acc_type = self.config_manager.get("account_type", "Offline")
        self.account_type_var.set(acc_type)
        
        # Load username
        username = self.config_manager.get("username", "AlienPlayer")
        self.username_entry.insert(0, username)
        self.update_gamer_id_label(username)
        
        # Show/hide fields based on type
        self.on_account_type_change(acc_type)
        
        # Load Folder
        mc_folder = self.config_manager.get("minecraft_folder")
        self.folder_entry.insert(0, mc_folder)
        
        # Load Java
        saved_java = self.config_manager.get("java_path")
        if saved_java and os.path.exists(saved_java):
            if saved_java not in self.java_paths:
                self.java_paths.append(saved_java)
            self.java_var.set(saved_java)
        else:
            self.java_var.set("Default System Java")

        # Load RAM
        self.ram_min_var.set(self.config_manager.get("ram_min", "2G"))
        self.ram_max_var.set(self.config_manager.get("ram_max", "4G"))
        
        # Load Theme
        saved_theme = self.config_manager.get("theme", "dark")
        self.theme_var.set(saved_theme.capitalize())
        
        # Load Launcher Style
        saved_style = self.config_manager.get("launcher_style", "alien")
        self.launcher_style_var.set("Unicorn Launcher" if saved_style == "unicorn" else "Alien Launcher")
        
        # Load Update Check setting
        enabled = self.config_manager.get("enable_update_check", True)
        self.enable_update_check_var.set(enabled)
        self.toggle_update_check_visibility()

        self.update_button_labels()

    def on_account_type_change(self, value):
        if value == "Microsoft":
            self.username_entry.configure(state="disabled")
            self.username_label.configure(text_color=TEXT_DISABLED)
            self.microsoft_frame.grid()
            self.elyby_frame.grid_remove()
            
            ms_data = self.config_manager.get("microsoft_data")
            if ms_data and "name" in ms_data:
                self.ms_status_label.configure(text=f"Logged in as {ms_data['name']}", text_color=ACCENT)
                self.btn_ms_action.configure(text="Logout", fg_color="#E74C3C", hover_color="#C0392B", text_color="#FFFFFF")
            else:
                self.ms_status_label.configure(text="Logged out", text_color="#E74C3C")
                self.btn_ms_action.configure(text="Login with Microsoft", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT)
        elif value == "Ely.by":
            self.username_entry.configure(state="disabled")
            self.username_label.configure(text_color=TEXT_DISABLED)
            self.microsoft_frame.grid_remove()
            self.elyby_frame.grid()
            
            ely_data = self.config_manager.get("elyby_data")
            if ely_data and "username" in ely_data:
                self.elyby_status_label.configure(text=f"Logged in as {ely_data['username']}", text_color=ACCENT)
                self.btn_elyby_action.configure(text="Logout", fg_color="#E74C3C", hover_color="#C0392B", text_color="#FFFFFF")
            else:
                self.elyby_status_label.configure(text="Logged out", text_color="#E74C3C")
                self.btn_elyby_action.configure(text="Login with Ely.by", fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=ACCENT_TEXT)
        else:
            self.username_entry.configure(state="normal")
            self.username_label.configure(text_color=TEXT_PRIMARY)
            self.microsoft_frame.grid_remove()
            self.elyby_frame.grid_remove()
            
            self.ms_status_label.configure(text="Offline Mode Active", text_color=TEXT_MUTED)
            self.btn_ms_action.configure(text="Setup Microsoft Profile", fg_color=SECONDARY_BUTTON, hover_color=SECONDARY_HOVER, text_color=TEXT_PRIMARY)

    def elyby_login(self):
        action = self.btn_elyby_action.cget("text")
        if action == "Logout":
            self.config_manager.set("account_type", "Offline")
            self.config_manager.set("elyby_data", {})
            self.account_type_var.set("Offline")
            self.on_account_type_change("Offline")
            if hasattr(self.toplevel, "update_sidebar_profile"):
                self.toplevel.update_sidebar_profile()
            messagebox.showinfo("Logged Out", "Successfully logged out from Ely.by Account.")
        else:
            dialog = ElyByLoginDialog(self, self.minecraft_manager, self.on_elyby_login_success)

    def on_elyby_login_success(self):
        self.config_manager.set("account_type", "Ely.by")
        self.account_type_var.set("Ely.by")
        
        ely_data = self.config_manager.get("elyby_data")
        username = ely_data.get("username", "AlienPlayer")
        self.username_entry.configure(state="normal")
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.username_entry.configure(state="disabled")
        self.update_gamer_id_label(username)
        
        self.on_account_type_change("Ely.by")
        if hasattr(self.toplevel, "update_sidebar_profile"):
            self.toplevel.update_sidebar_profile()

    def microsoft_login(self):
        action = self.btn_ms_action.cget("text")
        if action == "Logout":
            # Perform logout
            self.config_manager.set("account_type", "Offline")
            self.config_manager.set("microsoft_data", {})
            self.account_type_var.set("Offline")
            self.on_account_type_change("Offline")
            if hasattr(self.toplevel, "update_sidebar_profile"):
                self.toplevel.update_sidebar_profile()
            messagebox.showinfo("Logged Out", "Successfully logged out from Microsoft Account.")
        else:
            # Open Dialog
            dialog = MicrosoftLoginDialog(self, self.minecraft_manager, self.on_ms_login_success)

    def on_ms_login_success(self):
        # Reload values or toggle
        self.config_manager.set("account_type", "Microsoft")
        self.account_type_var.set("Microsoft")
        
        # Update username in entry
        username = self.config_manager.get("username")
        self.username_entry.configure(state="normal")
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, username)
        self.username_entry.configure(state="disabled")
        self.update_gamer_id_label(username)
        
        self.on_account_type_change("Microsoft")
        if hasattr(self.toplevel, "update_sidebar_profile"):
            self.toplevel.update_sidebar_profile()

    def browse_minecraft_folder(self):
        selected = filedialog.askdirectory(initialdir=self.folder_entry.get())
        if selected:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, selected)

    def browse_java_path(self):
        selected = filedialog.askopenfilename(
            title="Select java.exe",
            filetypes=[("Executable Files", "*.exe")]
        )
        if selected:
            if selected not in self.java_paths:
                self.java_paths.append(selected)
            self.java_var.set(selected)

    def change_launcher_style(self, val):
        style = "unicorn" if "unicorn" in val.lower() else "alien"
        
        # Save style immediately to config
        self.config_manager.set("launcher_style", style)
        self.config_manager.save()
        
        # Restart the application cleanly to apply all changes instantly
        import sys
        import os
        import subprocess
        try:
            self.winfo_toplevel().destroy()
        except Exception:
            pass
            
        if getattr(sys, 'frozen', False):
            args = [sys.executable] + sys.argv[1:]
        else:
            args = [sys.executable] + sys.argv
            
        subprocess.Popen(args)
        os._exit(0)

    def change_theme_mode(self, val):
        theme = val.lower()
        if theme not in ("system", "dark", "light"):
            theme = "dark"
        ctk.set_appearance_mode(theme)
        self.config_manager.set("theme", theme)
        self.theme_var.set(theme.capitalize())
        self.update_button_labels()
        normalize_structural_colors(self.winfo_toplevel())
        toplevel = self.winfo_toplevel()
        if hasattr(toplevel, "update_theme_assets"):
            toplevel.update_theme_assets()

    def save_settings(self):
        username = self.username_entry.get().strip()
        account_type = self.account_type_var.get()
        
        import re
        if account_type == "Offline":
            if not username:
                messagebox.showerror("Error", "Offline username cannot be empty!")
                return
            if len(username) < 3 or len(username) > 16:
                messagebox.showerror("Error", "Username must be between 3 and 16 characters long!")
                return
            if not re.match(r"^[a-zA-Z0-9_]+$", username):
                messagebox.showerror("Error", "Username can only contain letters, numbers, and underscores (no spaces or special characters)!")
                return

        mc_folder = self.folder_entry.get().strip()
        if not mc_folder:
            messagebox.showerror("Error", "Minecraft folder path cannot be empty!")
            return

        java_path = self.java_var.get()
        if java_path == "Default System Java":
            java_path = ""

        ram_min = self.ram_min_var.get()
        ram_max = self.ram_max_var.get()

        theme = self.theme_var.get().lower()
        launcher_style = "unicorn" if "unicorn" in self.launcher_style_var.get().lower() else "alien"

        # Write to config
        self.config_manager.set("username", username)
        self.config_manager.set("account_type", account_type)
        self.config_manager.set("minecraft_folder", mc_folder)
        self.config_manager.set("java_path", java_path)
        self.config_manager.set("ram_min", ram_min)
        self.config_manager.set("ram_max", ram_max)
        self.config_manager.set("theme", theme)
        self.config_manager.set("launcher_style", launcher_style)
        self.config_manager.set("enable_update_check", self.enable_update_check_var.get())

        self.update_gamer_id_label(username)

        # Update sidebar profile widget dynamically
        if hasattr(self.toplevel, "update_sidebar_profile"):
            self.toplevel.update_sidebar_profile()

        # Notify visual
        messagebox.showinfo("Success", "Settings saved successfully!")

    def update_gamer_id_label(self, username):
        if not username:
            self.lbl_gamer_id.configure(text="Your P2P Gamer ID: #----")
            return
        import hashlib
        h = hashlib.md5(username.lower().encode('utf-8')).hexdigest()
        four_digit = f"#{int(h, 16) % 9000 + 1000}"
        self.lbl_gamer_id.configure(text=f"Your P2P Gamer ID: {four_digit}")

    def open_selector_dialog(self, title, values, current_var, callback=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("320x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center on launcher
        x = self.winfo_x() + (self.winfo_width() // 2) - 160
        y = self.winfo_y() + (self.winfo_height() // 2) - 200
        dialog.geometry(f"+{x}+{y}")
        
        # Search Entry for long lists
        search_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        search_entry = None
        if len(values) > 5:
            search_frame.pack(fill="x", padx=15, pady=(15, 10))
            search_var = ctk.StringVar()
            search_entry = ctk.CTkEntry(
                search_frame, 
                placeholder_text="Search...",
                textvariable=search_var,
                fg_color=CONTROL_BG,
                border_color=CARD_BORDER,
                height=30
            )
            search_entry.pack(fill="x")
            
        scroll_frame = ctk.CTkScrollableFrame(dialog, fg_color=SURFACE_ALT, border_width=1, border_color=BORDER_DARK)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(15 if len(values) <= 5 else 0, 15))
        
        buttons = []
        
        def select_and_close(val):
            current_var.set(val)
            self.update_button_labels()
            dialog.destroy()
            if callback:
                callback(val)
                
        def populate(filter_text=""):
            for btn in buttons:
                btn.pack_forget()
            buttons.clear()
            
            for v in values:
                disp_v = v
                if len(disp_v) > 35:
                    disp_v = "..." + disp_v[-32:]
                    
                if not filter_text or filter_text.lower() in v.lower():
                    btn = ctk.CTkButton(
                        scroll_frame,
                        text=disp_v,
                        height=32,
                        anchor="w",
                        fg_color=ACCENT if current_var.get() == v else "transparent",
                        hover_color=SURFACE_HOVER,
                        text_color=ACCENT_TEXT if current_var.get() == v else TEXT_SECONDARY,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        command=lambda value=v: select_and_close(value)
                    )
                    btn.pack(fill="x", pady=2)
                    buttons.append(btn)
                    
        populate()
        
        if search_entry:
            search_entry.bind("<KeyRelease>", lambda e: populate(search_entry.get()))
            search_entry.focus()

    def update_button_labels(self):
        # Account Type
        self.account_type_btn.configure(text=f"{self.account_type_var.get()}  ▼")
        
        # Java Path
        java_val = self.java_var.get()
        if len(java_val) > 24:
            disp_java = "..." + java_val[-21:]
        else:
            disp_java = java_val
        self.java_btn.configure(text=f"{disp_java}  ▼")
        
        # RAM
        self.ram_min_btn.configure(text=f"{self.ram_min_var.get()}  ▼")
        self.ram_max_btn.configure(text=f"{self.ram_max_var.get()}  ▼")
        
        # Theme
        self.theme_btn.configure(text=f"{self.theme_var.get()}  ▼")
        
        # Launcher Style
        self.style_btn.configure(text=f"{self.launcher_style_var.get()}  ▼")

    def check_for_updates(self):
        if not self.enable_update_check_var.get():
            messagebox.showwarning("Updates Disabled", "Update checking is disabled in settings.")
            return

        self.btn_check_update.configure(state="disabled", text="Checking...")
        self.lbl_update_version.configure(text="Checking for updates on server...", text_color=TEXT_MUTED)

        def _thread():
            has_update, version, download_url, changelog = self.update_manager.check_for_updates()
            
            def _gui_update():
                self.btn_check_update.configure(state="normal", text="Check for Updates")
                if has_update:
                    self.lbl_update_version.configure(text=f"New version v{version} is available!", text_color=ACCENT)
                    
                    ans = messagebox.askyesno(
                        "Update Available",
                        f"A new version of the launcher (v{version}) is available!\n\n"
                        f"Changelog:\n{changelog}\n\n"
                        f"Would you like to download and install this update now? "
                        f"The launcher will automatically close and restart."
                    )
                    if ans:
                        self.apply_launcher_update(download_url, version)
                else:
                    self.lbl_update_version.configure(text=f"Current version: v{self.update_manager.current_version} (Latest)", text_color=TEXT_MUTED)
                    messagebox.showinfo("Up to Date", f"You are already running the latest version (v{self.update_manager.current_version}).")

            self.run_in_gui(_gui_update)

        threading.Thread(target=_thread, daemon=True).start()

    def apply_launcher_update(self, download_url, version):
        self.btn_check_update.configure(state="disabled", text="Updating...")
        self.lbl_update_version.configure(text="Downloading launcher update...", text_color=ACCENT)
        self.update_progress_bar.grid()
        self.update_progress_bar.set(0)

        def _thread():
            def progress_cb(downloaded, total):
                pct = int((downloaded / total) * 100)
                self.run_in_gui(self.lbl_update_version.configure, text=f"Downloading update... {pct}%")
                if total > 0:
                    self.run_in_gui(self.update_progress_bar.set, downloaded / total)

            success, msg = self.update_manager.download_and_apply_update(download_url, progress_cb)
            
            def _gui_finish():
                self.update_progress_bar.grid_remove()
                if success:
                    import sys
                    if getattr(sys, 'frozen', False):
                        import os
                        messagebox.showinfo("Updating Launcher", "Update downloaded successfully!\n\nThe launcher will now close and apply the update.")
                        os._exit(0)
                    else:
                        self.update_manager.current_version = version
                        self.lbl_update_version.configure(text=f"Current version: v{version} (Latest)", text_color=TEXT_MUTED)
                        self.btn_check_update.configure(state="normal", text="Check for Updates")
                        messagebox.showinfo("Update Complete", f"Launcher source code has been updated to v{version} successfully! UI refreshed.")
                else:
                    self.btn_check_update.configure(state="normal", text="Check for Updates")
                    self.lbl_update_version.configure(text="Update failed", text_color="#E74C3C")
                    messagebox.showerror("Update Error", f"Failed to apply launcher update:\n{msg}")

            self.run_in_gui(_gui_finish)

        threading.Thread(target=_thread, daemon=True).start()

    def toggle_update_check_visibility(self):
        enabled = self.enable_update_check_var.get()
        if enabled:
            self.btn_check_update.configure(state="normal")
            self.lbl_update_version.configure(text=f"Current version: v{self.update_manager.current_version}", text_color=TEXT_MUTED)
        else:
            self.btn_check_update.configure(state="disabled")
            self.lbl_update_version.configure(text="Update checks are disabled by configuration.", text_color=TEXT_MUTED)
