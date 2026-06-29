import os
import threading
import queue
import customtkinter as ctk
from PIL import Image, ImageTk
import ui.custom_dialog as messagebox

# Import core managers
from core.config_manager import ConfigManager
from core.minecraft_manager import MinecraftManager
from core.tailscale_manager import TailscaleManager
from core.server_manager import ServerManager
from core.mods_manager import ModsManager
from core.p2p_manager import P2PManager
from core.update_manager import LAUNCHER_VERSION

# Import UI pages
from ui.tailscale_page import TailscalePage
from ui.private_server_page import PrivateServerPage
from ui.settings_page import SettingsPage
from ui.mods_page import ModsPage
from ui.friends_page import FriendsPage
from ui.skin_page import SkinPage
import ui.theme
from ui.theme import (
    APP_BG, BORDER, BORDER_DARK,
    CARD_BORDER, CONTROL_BG, CONTROL_HOVER, SECONDARY_BUTTON,
    SIDEBAR_BG, SURFACE_ALT, SURFACE_HOVER, TEXT_MUTED, TEXT_PRIMARY,
    TEXT_SECONDARY, SUCCESS_COLOR, normalize_structural_colors
)

class LauncherWindow(ctk.CTk):
    def __init__(self):
        # Set AppUserModelID to force Windows to show the custom taskbar icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("alien.launcher.client.v1")
        except Exception as e:
            print(f"Error setting AppUserModelID: {e}")

        super().__init__()

        # Load configurations
        self.config_manager = ConfigManager()
        
        # Setup Alien Font (Orbitron)
        self.setup_alien_font()
        
        # Apply theme settings immediately
        saved_style = self.config_manager.get("launcher_style", "alien").lower()
        saved_theme = self.config_manager.get("theme", "dark").lower()
        
        import ui.theme
        ui.theme.set_theme(saved_style)
        
        if saved_theme not in ("dark", "light", "system"):
            saved_theme = "dark"
        ctk.set_appearance_mode(saved_theme)
        ctk.set_default_color_theme("green")  # Minecraft green accent

        # Initialize managers
        self.tailscale_manager = TailscaleManager()
        self.minecraft_manager = MinecraftManager(self.config_manager)
        self.server_manager = ServerManager(self.config_manager)
        self.mods_manager = ModsManager(self.config_manager)
        self.p2p_manager = P2PManager(
            self.config_manager,
            self.tailscale_manager,
            on_request_received_callback=self.handle_p2p_friend_request
        )
        self.p2p_manager.start_server()

        # Window properties
        self.title("Alien Launcher")
        self.geometry("1100x650")
        self.resizable(False, False)

        # Set Window Icon
        from ui.theme import get_asset_path
        ico_path = get_asset_path("assets/taskbarlogo.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception as e:
                print(f"Error setting window icon: {e}")
        else:
            logo_path = get_asset_path("assets/newlogo.png")
            fallback_ico = get_asset_path("assets/newlogo.ico")
            if os.path.exists(logo_path):
                try:
                    from PIL import Image
                    if not os.path.exists(fallback_ico):
                        # Save in a writeable user directory when frozen, else in assets
                        import sys
                        if getattr(sys, 'frozen', False):
                            fallback_ico = os.path.join(os.path.dirname(sys.executable), "assets", "newlogo.ico")
                            os.makedirs(os.path.dirname(fallback_ico), exist_ok=True)
                        img = Image.open(logo_path)
                        img.save(fallback_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
                    self.iconbitmap(fallback_ico)
                except Exception as e:
                    print(f"Error setting fallback window icon: {e}")

        # Set up state
        self.current_page = None
        self.downloading = False
        self._is_closing = False

        # Thread-safe queue for executing callbacks on GUI thread
        self.gui_queue = queue.Queue()
        self._gui_queue_after_id = None
        self.check_gui_queue()

        # Attempt to refresh Microsoft session if active
        if self.config_manager.get("account_type") == "Microsoft":
            threading.Thread(target=self.minecraft_manager.refresh_ms_login, daemon=True).start()

        # Build application layout
        self.setup_layout()
        self.update_theme_assets() # Load theme assets (icons, logo) dynamically
        normalize_structural_colors(self)
        self.select_page("Home")
        self.update_sidebar_profile()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def run_in_gui_thread(self, func, *args, **kwargs):
        if getattr(self, "_is_closing", False):
            return
        self.gui_queue.put((func, args, kwargs))

    def check_gui_queue(self):
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return
        try:
            while True:
                func, args, kwargs = self.gui_queue.get_nowait()
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    print(f"Error executing GUI callback: {e}")
        except queue.Empty:
            pass
        self._gui_queue_after_id = self.after(50, self.check_gui_queue)

    def on_close(self):
        self._is_closing = True
        if self._gui_queue_after_id is not None:
            try:
                self.after_cancel(self._gui_queue_after_id)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        import os
        os._exit(0)

    def update_theme_assets(self):
        saved_style = self.config_manager.get("launcher_style", "alien").lower()
        
        # 1. Update Window Icon
        from ui.theme import get_asset_path
        if saved_style == "unicorn":
            ico_path = get_asset_path("assets/Unicornlogo.ico")
            logo_path = get_asset_path("assets/Unicornlogo.png")
            logo_light_path = get_asset_path("assets/Unicornlogo-light.png")
        else:
            ico_path = get_asset_path("assets/taskbarlogo.ico")
            logo_path = get_asset_path("assets/newlogo.png")
            logo_light_path = get_asset_path("assets/newlogo-light.png")

        if not os.path.exists(ico_path) and os.path.exists(logo_path):
            ico_path = os.path.splitext(logo_path)[0] + ".ico"
            if not os.path.exists(ico_path):
                try:
                    img = Image.open(logo_path)
                    img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
                except Exception as e:
                    print(f"Error generating fallback icon: {e}")

        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception as e:
                print(f"Error updating window icon: {e}")
                
        # 2. Update Sidebar Logo
        if hasattr(self, "logo_label") and os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)
                pil_logo_light = Image.open(logo_light_path) if os.path.exists(logo_light_path) else pil_logo
                if pil_logo_light.size != pil_logo.size:
                    pil_logo_light = pil_logo_light.resize(pil_logo.size, Image.Resampling.LANCZOS)
                self.logo_img = ctk.CTkImage(light_image=pil_logo_light, dark_image=pil_logo, size=(120, 120))
                self.logo_label.configure(image=self.logo_img, text="")
            except Exception as e:
                print(f"Error updating sidebar logo: {e}")

        # 3. Update Titles & Text
        if saved_style == "unicorn":
            self.title("Unicorn Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Unicorn Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Unicorn Launcher v{LAUNCHER_VERSION}")
        else:
            self.title("Alien Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Alien Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Alien Launcher v{LAUNCHER_VERSION}")


    def setup_layout(self):
        # Master grid layout: 2 columns (sidebar, content)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Content
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------
        # SIDEBAR PANEL
        # ----------------------------------------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=SIDEBAR_BG)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        # Load Logo
        from ui.theme import get_asset_path
        logo_path = get_asset_path("assets/newlogo.png")
        logo_light_path = get_asset_path("assets/newlogo-light.png")
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)
                pil_logo_light = Image.open(logo_light_path) if os.path.exists(logo_light_path) else pil_logo
                if pil_logo_light.size != pil_logo.size:
                    pil_logo_light = pil_logo_light.resize(pil_logo.size, Image.Resampling.LANCZOS)
                self.logo_img = ctk.CTkImage(light_image=pil_logo_light, dark_image=pil_logo, size=(120, 120))
                self.logo_label = ctk.CTkLabel(self.sidebar_frame, image=self.logo_img, text="")
                self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
            except Exception as e:
                print(f"Error loading logo: {e}")
                self.fallback_logo()
        else:
            self.fallback_logo()

        # Sidebar Buttons
        self.nav_buttons = {}
        nav_items = [
            ("Home", "Home"),
            ("Tailscale VPN", "Tailscale"),
            ("Server Helper", "Server"),
            ("Mods Downloader", "Mods"),
            ("Add Friend", "Friends"),
            ("Skin", "Skin"),
            ("Settings", "Settings")
        ]

        for i, (label, name) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=label,
                height=40,
                corner_radius=6,
                fg_color="transparent",
                text_color=TEXT_SECONDARY,
                hover_color=SURFACE_HOVER,
                anchor="w",
                font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
                command=lambda n=name: self.select_page(n)
            )
            btn.grid(row=i, column=0, padx=15, pady=5, sticky="ew")
            self.nav_buttons[name] = btn

        # Configure weight to push credits to bottom dynamically
        self.sidebar_frame.grid_rowconfigure(len(nav_items) + 1, weight=1)

        # Sidebar User Profile Widget
        self.sidebar_profile = ctk.CTkFrame(self.sidebar_frame, fg_color=APP_BG, corner_radius=8, border_width=1, border_color=BORDER)
        self.sidebar_profile.grid(row=len(nav_items) + 2, column=0, padx=15, pady=(10, 5), sticky="ew")
        self.sidebar_profile.grid_columnconfigure(1, weight=1)

        # Avatar Label
        self.sb_avatar_lbl = ctk.CTkLabel(self.sidebar_profile, text="", width=32, height=32)
        self.sb_avatar_lbl.grid(row=0, column=0, padx=(10, 8), pady=8, sticky="w")

        # Info Frame
        sb_info = ctk.CTkFrame(self.sidebar_profile, fg_color="transparent")
        sb_info.grid(row=0, column=1, sticky="w", pady=8)
        
        self.sb_name_lbl = ctk.CTkLabel(sb_info, text="AlienPlayer", font=ctk.CTkFont(family="Orbitron", size=11, weight="bold"), text_color=TEXT_PRIMARY)
        self.sb_name_lbl.pack(anchor="w")

        self.sb_id_lbl = ctk.CTkLabel(sb_info, text="#1234", font=ctk.CTkFont(family="Orbitron", size=9), text_color=TEXT_MUTED)
        self.sb_id_lbl.pack(anchor="w")

        # Bottom Credit Label
        self.credit_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"Alien Launcher v{LAUNCHER_VERSION}",
            font=ctk.CTkFont(family="Orbitron", size=9),
            text_color=TEXT_MUTED,
            justify="center"
        )
        self.credit_label.grid(row=len(nav_items) + 3, column=0, padx=20, pady=(5, 15), sticky="s")

        # ----------------------------------------------------
        # CONTENT CONTAINER
        # ----------------------------------------------------
        self.content_frame = ctk.CTkFrame(self, fg_color=APP_BG, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Initialize all sub-pages
        self.pages = {
            "Home": ctk.CTkFrame(self.content_frame, fg_color="transparent"),
            "Tailscale": TailscalePage(self.content_frame, self.tailscale_manager, self.config_manager),
            "Server": PrivateServerPage(self.content_frame, self.server_manager, self.minecraft_manager, self.config_manager),
            "Mods": ModsPage(self.content_frame, self.mods_manager, self.config_manager),
            "Friends": FriendsPage(self.content_frame, self.config_manager),
            "Skin": SkinPage(self.content_frame, self.config_manager),
            "Settings": SettingsPage(self.content_frame, self.config_manager, self.minecraft_manager)
        }

        # Set up Home Page layout (as it contains the main launch interface)
        self.setup_home_page()

    def setup_alien_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Orbitron.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Orbitron font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Orbitron font: {e}")

    def fallback_logo(self):
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ALIEN",
            font=ctk.CTkFont(family="Orbitron", size=24, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

    def setup_home_page(self):
        home = self.pages["Home"]
        home.grid_columnconfigure(0, weight=1)
        home.grid_rowconfigure(0, weight=1)

        # Background Image container
        from ui.theme import get_asset_path
        bg_path = get_asset_path("assets/background.png")
        bg_loaded = False
        if os.path.exists(bg_path):
            try:
                pil_bg = Image.open(bg_path)
                # Size matches our content frame width (1100-220 = 880) and height (650)
                self.bg_img = ctk.CTkImage(light_image=pil_bg, dark_image=pil_bg, size=(880, 650))
                self.bg_label = ctk.CTkLabel(home, image=self.bg_img, text="")
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                bg_loaded = True
            except Exception as e:
                print(f"Error loading background: {e}")

        if not bg_loaded:
            # Fallback flat color overlay
            self.bg_label = ctk.CTkLabel(home, text="", fg_color=APP_BG)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Overlap Main controls container on top of background
        self.home_overlay = ctk.CTkFrame(home, fg_color="transparent")
        self.home_overlay.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self.home_overlay.grid_columnconfigure(0, weight=1)
        self.home_overlay.grid_rowconfigure(0, weight=1) # Content spacer
        self.home_overlay.grid_rowconfigure(1, weight=0) # Card area
        self.home_overlay.grid_rowconfigure(2, weight=0) # Control bar

        # Top Title Banner
        banner_frame = ctk.CTkFrame(self.home_overlay, fg_color="transparent")
        banner_frame.grid(row=0, column=0, padx=30, pady=(40, 0), sticky="nw")
        
        self.banner_title_label = ctk.CTkLabel(
            banner_frame, text="Alien Launcher",
            font=ctk.CTkFont(family="Orbitron", size=36, weight="bold"),
            text_color="#FFFFFF"
        )
        self.banner_title_label.pack(anchor="w")
        
        banner_subtitle = ctk.CTkLabel(
            banner_frame, text="Sleek, Secure, and Private Multiplayer launcher.",
            font=ctk.CTkFont(family="Orbitron", size=12),
            text_color="#A5D6A7"
        )
        banner_subtitle.pack(anchor="w", pady=(5, 0))

        # Horizontal Row of Status Cards
        cards_row = ctk.CTkFrame(self.home_overlay, fg_color="transparent")
        cards_row.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="ew")
        cards_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="home_card")

        # Card 1: Account Info
        self.card_acc = ctk.CTkFrame(cards_row, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
        self.card_acc.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        lbl_acc_title = ctk.CTkLabel(self.card_acc, text="ACCOUNT PROFILE", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED)
        lbl_acc_title.pack(padx=15, pady=(15, 2), anchor="w")
        self.lbl_acc_val = ctk.CTkLabel(self.card_acc, text="AlienPlayer", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_acc_val.pack(padx=15, pady=(0, 15), anchor="w")

        # Card 2: Settings Preview (RAM)
        self.card_settings = ctk.CTkFrame(cards_row, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
        self.card_settings.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        lbl_sett_title = ctk.CTkLabel(self.card_settings, text="RAM ALLOCATION", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED)
        lbl_sett_title.pack(padx=15, pady=(15, 2), anchor="w")
        self.lbl_sett_val = ctk.CTkLabel(self.card_settings, text="Min: 2G / Max: 4G", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_sett_val.pack(padx=15, pady=(0, 15), anchor="w")

        # Card 3: VPN Status Preview
        self.card_vpn = ctk.CTkFrame(cards_row, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
        self.card_vpn.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        
        lbl_vpn_title = ctk.CTkLabel(self.card_vpn, text="TAILSCALE VPN", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED)
        lbl_vpn_title.pack(padx=15, pady=(15, 2), anchor="w")
        self.lbl_vpn_val = ctk.CTkLabel(self.card_vpn, text="Disconnected", font=ctk.CTkFont(size=14, weight="bold"), text_color="#F39C12")
        self.lbl_vpn_val.pack(padx=15, pady=(0, 15), anchor="w")

        # Bottom Control Panel Deck (Launcher controls)
        control_deck = ctk.CTkFrame(self.home_overlay, fg_color=SURFACE_ALT, corner_radius=10, border_width=1, border_color=BORDER_DARK)
        control_deck.grid(row=2, column=0, padx=30, pady=(0, 30), sticky="ew")
        control_deck.grid_columnconfigure(0, weight=1) # Version selector
        control_deck.grid_columnconfigure(1, weight=1) # Action controls (Play / Install)

        # Version select frame (Left side of control deck)
        v_select_frame = ctk.CTkFrame(control_deck, fg_color="transparent")
        v_select_frame.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Column 0: Game version selection
        v_sub_frame = ctk.CTkFrame(v_select_frame, fg_color="transparent")
        v_sub_frame.grid(row=0, column=0, padx=(0, 15), sticky="w")
        
        ctk.CTkLabel(v_sub_frame, text="Select Game Version", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        
        self.available_versions = self.minecraft_manager.get_available_versions()
        self.version_var = ctk.StringVar(value=self.config_manager.get("selected_version", "1.20.1"))
        
        self.btn_select_version = ctk.CTkButton(
            v_sub_frame, 
            textvariable=self.version_var,
            width=180, 
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=self.open_version_selector_dialog
        )
        self.btn_select_version.pack(pady=(5, 0))

        # Column 1: Mod Loader / Type selection
        l_sub_frame = ctk.CTkFrame(v_select_frame, fg_color="transparent")
        l_sub_frame.grid(row=0, column=1, sticky="w")
        
        ctk.CTkLabel(l_sub_frame, text="Select Loader / Type", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        
        self.loader_var = ctk.StringVar(value=self.config_manager.get("loader_type", "Vanilla"))
        self.btn_select_loader = ctk.CTkButton(
            l_sub_frame, 
            textvariable=self.loader_var,
            width=180, 
            height=30,
            fg_color=CONTROL_BG,
            border_width=1,
            border_color=BORDER,
            hover_color=CONTROL_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(weight="bold"),
            command=self.open_loader_selector_dialog
        )
        self.btn_select_loader.pack(pady=(5, 0))

        # Launch controls (Right side of control deck)
        launch_frame = ctk.CTkFrame(control_deck, fg_color="transparent")
        launch_frame.grid(row=0, column=1, padx=20, pady=15, sticky="e")

        self.btn_play = ctk.CTkButton(
            launch_frame, text="PLAY GAME", 
            width=200, height=44, corner_radius=8,
            fg_color=ui.theme.ACCENT_COLOR, hover_color=ui.theme.ACCENT_HOVER_COLOR, text_color=ui.theme.ACCENT_TEXT_COLOR,
            font=ctk.CTkFont(family="Orbitron", size=16, weight="bold"),
            command=self.action_play
        )
        self.btn_play.pack(anchor="e")

        # Loading / Status Details inside Control Deck
        self.status_label = ctk.CTkLabel(
            control_deck, text="Ready to Launch",
            font=ctk.CTkFont(size=12), text_color=TEXT_MUTED
        )
        self.status_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(control_deck, progress_color=SUCCESS_COLOR, height=4)
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # Hide initially

    def select_page(self, page_name):
        # Hide current page
        if self.current_page:
            self.pages[self.current_page].grid_forget()
            self.nav_buttons[self.current_page].configure(fg_color="transparent", text_color=TEXT_SECONDARY)

        # Show selected page
        self.pages[page_name].grid(row=0, column=0, sticky="nsew")
        normalize_structural_colors(self.pages[page_name])
        self.nav_buttons[page_name].configure(fg_color=ui.theme.ACCENT_COLOR, text_color=ui.theme.ACCENT_TEXT_COLOR)
        self.current_page = page_name

        # Trigger active callbacks on views
        if page_name == "Home":
            self.update_home_dashboard()
        elif page_name == "Server":
            self.pages["Server"].on_view_active()
        elif page_name == "Tailscale":
            self.pages["Tailscale"].refresh_status()

    def update_home_dashboard(self):
        # Update Username Card
        user = self.config_manager.get("username", "AlienPlayer")
        acc_type = self.config_manager.get("account_type", "Offline")
        self.lbl_acc_val.configure(text=f"{user} ({acc_type})")

        # Update RAM Card
        min_ram = self.config_manager.get("ram_min", "2G")
        max_ram = self.config_manager.get("ram_max", "4G")
        self.lbl_sett_val.configure(text=f"Min: {min_ram} / Max: {max_ram}")

        # Update available versions and selection dynamically in case settings changed
        self.available_versions = self.minecraft_manager.get_available_versions()
        current_ver = self.config_manager.get("selected_version", "1.20.1")
        if current_ver not in self.available_versions:
            if self.available_versions:
                current_ver = self.available_versions[0]
                self.config_manager.set("selected_version", current_ver)
        self.version_var.set(current_ver)

        # Update VPN Card in background
        def _get_vpn_status():
            ip = self.tailscale_manager.get_ipv4()
            
            def _update():
                if ip and ip != "Not Connected / Unknown":
                    self.lbl_vpn_val.configure(text=ip, text_color="#2ECC71")
                else:
                    self.lbl_vpn_val.configure(text="Disconnected", text_color="#F39C12")
            
            self.run_in_gui_thread(_update)
            
        threading.Thread(target=_get_vpn_status, daemon=True).start()

    def action_play(self):
        if self.downloading:
            return
            
        if self.minecraft_manager.is_running():
            messagebox.showwarning("Game Running", "Minecraft is already running!")
            return

        selected_ver = self.version_var.get()
        self.config_manager.set("selected_version", selected_ver)

        # Check if version exists in installed versions
        installed = self.minecraft_manager.get_installed_versions()
        loader = self.loader_var.get()
        
        is_ver_installed = selected_ver in installed
        is_loader_installed = self.minecraft_manager.is_loader_installed(selected_ver, loader)
        
        if not is_ver_installed or not is_loader_installed:
            # We need to download and install
            confirm = messagebox.askyesno(
                "Installation Required",
                f"Minecraft version {selected_ver} ({loader}) is not fully set up.\nDo you want to download and install it now?"
            )
            if not confirm:
                return
            
            self.start_installation(selected_ver)
        else:
            # Already installed, just launch
            self.launch_game(selected_ver)

    def start_installation(self, version_id):
        self.downloading = True
        self.btn_play.configure(state="disabled", text="INSTALLING...")
        self.progress_bar.grid()
        self.progress_bar.set(0)

        def progress_cb(val, max_val):
            if max_val > 0:
                pct = val / max_val
                self.run_in_gui_thread(self.progress_bar.set, pct)

        def status_cb(text):
            self.run_in_gui_thread(self.status_label.configure, text=text)

        def install_thread():
            success, err = self.minecraft_manager.install_version(version_id, progress_cb, status_cb)
            
            def _on_finish():
                self.downloading = False
                self.progress_bar.grid_remove()
                self.btn_play.configure(state="normal", text="PLAY GAME")
                
                if success:
                    # Refresh available versions to make sure the newly installed one is detected
                    self.available_versions = self.minecraft_manager.get_available_versions()
                    self.launch_game(version_id)
                else:
                    messagebox.showerror("Installation Error", f"Failed to install {version_id}:\n{err}")
                    self.status_label.configure(text="Installation failed")
            
            self.run_in_gui_thread(_on_finish)

        threading.Thread(target=install_thread, daemon=True).start()

    def launch_game(self, version_id):
        self.status_label.configure(text=f"Launching {version_id}...")
        self.btn_play.configure(state="disabled", text="RUNNING...")

        # Minimize or change status on exit
        def on_exit():
            self.run_in_gui_thread(self.on_game_exit)

        def launch_thread():
            success, err = self.minecraft_manager.launch_minecraft(version_id, on_exit)
            
            def _on_finish():
                if success:
                    self.status_label.configure(text="Minecraft Running (Launcher Minimized)")
                    self.iconify() # Minimize launcher to taskbar
                else:
                    messagebox.showerror("Launch Error", f"Failed to launch game:\n{err}")
                    self.status_label.configure(text="Launch failed")
                    self.btn_play.configure(state="normal", text="PLAY GAME")
            
            self.run_in_gui_thread(_on_finish)

        threading.Thread(target=launch_thread, daemon=True).start()

    def on_game_exit(self):
        self.deiconify() # Restore launcher window
        self.status_label.configure(text="Game closed. Ready to launch.")
        self.btn_play.configure(state="normal", text="PLAY GAME")
        self.update_home_dashboard()

    def open_version_selector_dialog(self):
        # Prevent opening multiple dialogs
        if hasattr(self, "version_dialog") and self.version_dialog.winfo_exists():
            self.version_dialog.focus()
            return

        # Dynamically refresh the available versions list to detect new/updated installations
        self.available_versions = self.minecraft_manager.get_available_versions()

        self.version_dialog = ctk.CTkToplevel(self)
        self.version_dialog.title("Select Version")
        self.version_dialog.geometry("300x450")
        self.version_dialog.resizable(False, False)
        self.version_dialog.transient(self) # Keep on top of launcher
        self.version_dialog.grab_set() # Grab focus (modal)
        
        # Center the dialog on the launcher
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 225
        self.version_dialog.geometry(f"+{x}+{y}")

        # Search frame
        search_frame = ctk.CTkFrame(self.version_dialog, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Search version...",
            textvariable=search_var,
            fg_color=CONTROL_BG,
            border_color=CARD_BORDER,
            height=30
        )
        search_entry.pack(fill="x")
        search_entry.focus()

        # Scrollable Frame for Versions
        scroll_frame = ctk.CTkScrollableFrame(self.version_dialog, fg_color=SURFACE_ALT, border_width=1, border_color=BORDER_DARK)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        buttons = []

        def select_and_close(version):
            self.version_var.set(version)
            self.config_manager.set("selected_version", version)
            self.version_dialog.destroy()

        def populate_list(filter_text=""):
            for btn in buttons:
                btn.pack_forget()
            buttons.clear()
            
            for v in self.available_versions:
                if not filter_text or filter_text.lower() in v.lower():
                    btn = ctk.CTkButton(
                        scroll_frame,
                        text=v,
                        height=32,
                        anchor="w",
                        fg_color="transparent",
                        hover_color=SURFACE_HOVER,
                        text_color=TEXT_SECONDARY,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        command=lambda ver=v: select_and_close(ver)
                    )
                    btn.pack(fill="x", pady=1)
                    buttons.append(btn)

        # Bind search filtering
        search_var.trace_add("write", lambda *args: populate_list(search_var.get()))
        
        # Initial populate
        populate_list()

    def on_loader_changed(self, value):
        self.config_manager.set("loader_type", value)
        # Update available versions based on the new loader type!
        self.available_versions = self.minecraft_manager.get_available_versions()
        
        # If the currently selected version doesn't exist in the new list, update it to the first option
        current_ver = self.version_var.get()
        if current_ver not in self.available_versions:
            fallback = self.available_versions[0] if self.available_versions else "1.20.1"
            self.version_var.set(fallback)
            self.config_manager.set("selected_version", fallback)

    def open_loader_selector_dialog(self):
        # Prevent opening multiple dialogs
        if hasattr(self, "loader_dialog") and self.loader_dialog.winfo_exists():
            self.loader_dialog.focus()
            return

        self.loader_dialog = ctk.CTkToplevel(self)
        self.loader_dialog.title("Select Loader / Type")
        self.loader_dialog.geometry("300x450")
        self.loader_dialog.resizable(False, False)
        self.loader_dialog.transient(self) # Keep on top of launcher
        self.loader_dialog.grab_set() # Grab focus (modal)
        
        # Center the dialog on the launcher
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 225
        self.loader_dialog.geometry(f"+{x}+{y}")

        # Search frame
        search_frame = ctk.CTkFrame(self.loader_dialog, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Search loader...",
            textvariable=search_var,
            fg_color=CONTROL_BG,
            border_color=CARD_BORDER,
            height=30
        )
        search_entry.pack(fill="x")
        search_entry.focus()

        # Scrollable Frame for Loaders
        scroll_frame = ctk.CTkScrollableFrame(self.loader_dialog, fg_color=SURFACE_ALT, border_width=1, border_color=BORDER_DARK)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        loaders = [
            "Vanilla", "Fabric", "NeoForge", "Forge", "Quilt", 
            "OptiFine", "LiteLoader", "Snapshot", "Release", "Old Beta/Alpha"
        ]

        buttons = []

        def select_and_close(loader):
            self.loader_var.set(loader)
            self.on_loader_changed(loader)
            self.loader_dialog.destroy()

        def populate_list(filter_text=""):
            for btn in buttons:
                btn.pack_forget()
            buttons.clear()
            
            for l in loaders:
                if not filter_text or filter_text.lower() in l.lower():
                    btn = ctk.CTkButton(
                        scroll_frame,
                        text=l,
                        height=32,
                        anchor="w",
                        fg_color="transparent",
                        hover_color=SURFACE_HOVER,
                        text_color=TEXT_SECONDARY,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        command=lambda loader=l: select_and_close(loader)
                    )
                    btn.pack(fill="x", pady=1)
                    buttons.append(btn)

        # Bind search filtering
        search_var.trace_add("write", lambda *args: populate_list(search_var.get()))
        
        # Initial populate
        populate_list()

    def handle_p2p_friend_request(self, username, acc_type, ip):
        response_queue = queue.Queue()
        
        def _show_dialog():
            ans = messagebox.askyesno(
                "Friend Request Received",
                f"Minecraft player '{username}' ({acc_type}) at Tailscale IP {ip} wants to add you as a friend!\n\n"
                "Do you want to accept their request and add them to your friends list?"
            )
            response_queue.put(ans)
            
            # If the current page is the Friends Page, refresh the list dynamically!
            if getattr(self, "current_page", "") == "Friends":
                try:
                    self.pages["Friends"].refresh_friends_list()
                except Exception:
                    pass
                    
        self.run_in_gui_thread(_show_dialog)
        
        # Wait up to 30 seconds for the user to respond
        try:
            return response_queue.get(timeout=30)
        except queue.Empty:
            return False

    def update_sidebar_profile(self):
        username = self.config_manager.get("username", "AlienPlayer")
        acc_type = self.config_manager.get("account_type", "Offline")

        self.sb_name_lbl.configure(text=username)

        import hashlib
        h = hashlib.md5(username.lower().encode('utf-8')).hexdigest()
        four_digit = f"#{int(h, 16) % 9000 + 1000}"
        self.sb_id_lbl.configure(text=f"{four_digit} • {acc_type}")

        def _fetch_thread():
            import requests
            import io
            from PIL import Image
            
            if acc_type == "Ely.by":
                url = f"https://ely.by/services/skins/face.php?u={username}&s=32"
            else:
                url = f"https://minotar.net/helm/{username}/32.png"

            cache_dir = os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "alien_launcher_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f"face_{username}.png")

            pil_img = None
            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                except Exception:
                    pass

            if not pil_img:
                try:
                    res = requests.get(url, timeout=5)
                    if res.status_code == 200:
                        pil_img = Image.open(io.BytesIO(res.content))
                        pil_img.save(cache_file)
                except Exception:
                    pass

            if not pil_img:
                try:
                    res = requests.get("https://minotar.net/helm/char/32.png", timeout=5)
                    if res.status_code == 200:
                        pil_img = Image.open(io.BytesIO(res.content))
                except Exception:
                    pass

            if pil_img:
                def _update_gui():
                    try:
                        if getattr(self, "_is_closing", False) or not self.winfo_exists():
                            return
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                        self.sb_avatar_lbl.configure(image=ctk_img)
                        self.sb_avatar_lbl.image = ctk_img
                    except Exception:
                        pass
                try:
                    if not getattr(self, "_is_closing", False) and self.winfo_exists():
                        self.after(0, _update_gui)
                except Exception:
                    pass

        threading.Thread(target=_fetch_thread, daemon=True).start()
