import os
import threading
import queue
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
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
    CARD_BORDER, CONTROL_BG, CONTROL_HOVER, SECONDARY_BUTTON, SECONDARY_HOVER,
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
        
        # Setup Fonts (Orbitron, Chewy, Space Grotesk, Fredoka, Oxanium, Exo 2, and Cinzel)
        self.setup_alien_font()
        self.setup_chewy_font()
        self.setup_space_grotesk_font()
        self.setup_fredoka_font()
        self.setup_oxanium_font()
        self.setup_exo2_font()
        self.setup_cinzel_font()
        
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
        width = 1100
        height = 650
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
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

        # Navigation icons configuration
        self.nav_icon_paths = {
            "Home": "icon_home.png",
            "Tailscale": "icon_vpn.png",
            "Server": "icon_server.png",
            "Mods": "icon_mods.png",
            "Friends": "icon_friends.png",
            "Skin": "icon_skin.png",
            "Settings": "icon_settings.png"
        }
        self.nav_icon_images = {}

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
        elif saved_style == "onyx":
            ico_path = get_asset_path("assets/Onyxlogo.ico")
            logo_path = get_asset_path("assets/Onyxlogo.png")
            logo_light_path = get_asset_path("assets/Onyxlogo.png")
        elif saved_style == "kitty":
            ico_path = get_asset_path("assets/Kittylogo.ico")
            logo_path = get_asset_path("assets/Kittylogo.png")
            logo_light_path = get_asset_path("assets/Kittylogo.png")
        elif saved_style == "eclipsex":
            ico_path = get_asset_path("assets/eclipseX.ico")
            logo_path = get_asset_path("assets/eclipseX.png")
            logo_light_path = get_asset_path("assets/eclipseX.png")
        elif saved_style == "matrix":
            ico_path = get_asset_path("assets/MatrixLogo.ico")
            logo_path = get_asset_path("assets/MatrixLogo.png")
            logo_light_path = get_asset_path("assets/MatrixLogo.png")
        elif saved_style == "shougun":
            ico_path = get_asset_path("assets/ShougunLogo.ico")
            logo_path = get_asset_path("assets/ShougunLogo.png")
            logo_light_path = get_asset_path("assets/ShougunLogo.png")
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

        # 3. Update Titles & Text & Colors
        is_light = self.config_manager.get("theme", "dark").lower() == "light"
        
        # Default/Alien text colors
        title_color = "#FFFFFF"
        subtitle_color = "#A5D6A7"
        
        if saved_style == "unicorn":
            self.title("Unicorn Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Unicorn Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Unicorn Launcher v{LAUNCHER_VERSION}")
            title_color = "#FF66CC"
            subtitle_color = "#FFA6D5"
        elif saved_style == "onyx":
            self.title("Onyx Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Onyx Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Onyx Launcher v{LAUNCHER_VERSION}")
            title_color = "#F5F5F5"
            subtitle_color = "#9CA3AF"
        elif saved_style == "kitty":
            self.title("Kitty Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Kitty Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Kitty Launcher v{LAUNCHER_VERSION}")
            title_color = "#000000" if is_light else "#FF4F9F"
            subtitle_color = "#FF4F9F" if is_light else "#D1D5DB"
        elif saved_style == "eclipsex":
            self.title("EclipseX Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="EclipseX Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"EclipseX Launcher v{LAUNCHER_VERSION}")
            title_color = "#111827" if is_light else "#E5E7EB"
            subtitle_color = "#6B7280" if is_light else "#A1A1AA"
        elif saved_style == "matrix":
            self.title("Matrix Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Matrix Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Matrix Launcher v{LAUNCHER_VERSION}")
            title_color = "#7CFF00"
            subtitle_color = "#39FF14"
        elif saved_style == "shougun":
            self.title("Shougun Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Shougun Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Shougun Launcher v{LAUNCHER_VERSION}")
            title_color = "#C1121F"
            subtitle_color = "#B8BCC5"
        else:
            self.title("Alien Launcher")
            if hasattr(self, "banner_title_label"):
                self.banner_title_label.configure(text="Alien Launcher")
            if hasattr(self, "credit_label"):
                self.credit_label.configure(text=f"Alien Launcher v{LAUNCHER_VERSION}")

        if hasattr(self, "banner_title_label"):
            self.banner_title_label.configure(text_color=title_color)
        if hasattr(self, "banner_subtitle"):
            self.banner_subtitle.configure(text_color=subtitle_color)

        if hasattr(self, "matrix_canvas") and self.matrix_canvas.winfo_exists():
            if saved_style == "matrix":
                canvas_bg = "#050505"
            elif saved_style == "onyx":
                canvas_bg = "#0B0B0D"
            elif saved_style == "kitty":
                canvas_bg = "#FFF5F8" if is_light else "#1E1218"
            elif saved_style == "eclipsex":
                canvas_bg = "#F8FAFC" if is_light else "#050506"
            elif saved_style == "shougun":
                canvas_bg = "#090909"
            else:
                canvas_bg = "transparent"
                
            self.matrix_canvas.configure(bg=canvas_bg)
            
            if hasattr(self, "banner_frame") and self.banner_frame.winfo_exists():
                self.banner_frame.configure(fg_color=canvas_bg)
            if hasattr(self, "cards_row") and self.cards_row.winfo_exists():
                self.cards_row.configure(fg_color=canvas_bg)

        # 4. Load & Update Navigation Icons
        self.load_nav_icons()
        if hasattr(self, "nav_buttons"):
            for name, btn in self.nav_buttons.items():
                if name in self.nav_icon_images:
                    btn.configure(image=self.nav_icon_images[name])

    def tint_image(self, image, color_hex):
        try:
            hex_val = color_hex.lstrip('#')
            r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            r_chan, g_chan, b_chan, a_chan = image.split()
            new_r = r_chan.point(lambda _: r)
            new_g = g_chan.point(lambda _: g)
            new_b = b_chan.point(lambda _: b)
            return Image.merge("RGBA", (new_r, new_g, new_b, a_chan))
        except Exception as e:
            print(f"Error tinting image: {e}")
            return image

    def generate_default_icon_masks(self):
        from ui.theme import get_asset_path
        size = (64, 64)
        
        def draw_home(draw):
            draw.polygon([(32, 10), (10, 32), (54, 32)], fill=(255, 255, 255, 255))
            draw.rectangle([18, 32, 46, 54], fill=(255, 255, 255, 255))
            draw.rectangle([27, 42, 37, 54], fill=(0, 0, 0, 0))
            
        def draw_vpn(draw):
            draw.polygon([(32, 10), (52, 18), (52, 38), (32, 54), (12, 38), (12, 18)], fill=(255, 255, 255, 255))
            draw.polygon([(32, 15), (47, 21), (47, 36), (32, 49), (17, 36), (17, 21)], fill=(0, 0, 0, 0))
            draw.polygon([(32, 22), (40, 27), (40, 34), (32, 42), (24, 34), (24, 27)], fill=(255, 255, 255, 255))
            
        def draw_server(draw):
            for y in [12, 28, 44]:
                draw.rounded_rectangle([10, y, 54, y + 10], radius=3, fill=(255, 255, 255, 255))
                draw.ellipse([15, y + 3.5, 18, y + 6.5], fill=(0, 0, 0, 0))
                draw.ellipse([21, y + 3.5, 24, y + 6.5], fill=(0, 0, 0, 0))
                
        def draw_mods(draw):
            draw.rounded_rectangle([12, 18, 52, 52], radius=4, fill=(255, 255, 255, 255))
            draw.rectangle([12, 32, 52, 38], fill=(0, 0, 0, 0))
            draw.rectangle([29, 18, 35, 52], fill=(0, 0, 0, 0))
            
        def draw_friends(draw):
            draw.ellipse([20, 12, 36, 28], fill=(255, 255, 255, 255))
            draw.chord([10, 32, 46, 60], start=180, end=360, fill=(255, 255, 255, 255))
            draw.rectangle([42, 18, 50, 20], fill=(255, 255, 255, 255))
            draw.rectangle([45, 15, 47, 23], fill=(255, 255, 255, 255))
            
        def draw_skin(draw):
            points = [
                (26, 18), (38, 18),
                (48, 22), (56, 32), (48, 38), (44, 34),
                (44, 52), (20, 52), (20, 34),
                (16, 38), (8, 32), (16, 22)
            ]
            draw.polygon(points, fill=(255, 255, 255, 255))
            draw.ellipse([26, 12, 38, 22], fill=(0, 0, 0, 0))
            
        def draw_settings(draw):
            cx, cy = 32, 32
            r_outer = 18
            r_inner = 8
            draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=(255, 255, 255, 255))
            import math
            for i in range(8):
                angle = i * (2 * math.pi / 8)
                tx = cx + 22 * math.cos(angle)
                ty = cy + 22 * math.sin(angle)
                draw.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=(255, 255, 255, 255))
            draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=(0, 0, 0, 0))

        draw_funcs = {
            "icon_home.png": draw_home,
            "icon_vpn.png": draw_vpn,
            "icon_server.png": draw_server,
            "icon_mods.png": draw_mods,
            "icon_friends.png": draw_friends,
            "icon_skin.png": draw_skin,
            "icon_settings.png": draw_settings
        }

        for filename, draw_func in draw_funcs.items():
            path = get_asset_path(f"assets/{filename}")
            if not os.path.exists(path):
                try:
                    img = Image.new("RGBA", size, (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    draw_func(draw)
                    img.save(path)
                except Exception as e:
                    print(f"Error generating mask {filename}: {e}")

    def load_nav_icons(self):
        self.generate_default_icon_masks()
        from ui.theme import get_asset_path, TEXT_SECONDARY, ACCENT
        for name, filename in self.nav_icon_paths.items():
            mask_path = get_asset_path(f"assets/{filename}")
            if os.path.exists(mask_path):
                try:
                    mask_img = Image.open(mask_path).convert("RGBA")
                    light_color = TEXT_SECONDARY[0]
                    light_img = self.tint_image(mask_img, light_color)
                    dark_color = ACCENT
                    dark_img = self.tint_image(mask_img, dark_color)
                    
                    self.nav_icon_images[name] = ctk.CTkImage(
                        light_image=light_img,
                        dark_image=dark_img,
                        size=(20, 20)
                    )
                except Exception as e:
                    print(f"Error loading nav icon {name}: {e}")


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
                image=self.nav_icon_images.get(name),
                compound="left",
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

    def setup_chewy_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Chewy.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://fonts.gstatic.com/s/chewy/v18/uK_94ruUb-k-wk5x.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Chewy font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Chewy font: {e}")

    def setup_space_grotesk_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/SpaceGrotesk.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Space Grotesk font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Space Grotesk font: {e}")

    def setup_fredoka_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Fredoka.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                # Fredoka Variable Font URL from Google Fonts raw GitHub repo
                url = "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth%2Cwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Fredoka font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Fredoka font: {e}")

    def setup_oxanium_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Oxanium.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/oxanium/Oxanium%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Oxanium font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Oxanium font: {e}")

    def setup_exo2_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Exo2.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                # Exo 2 Variable Font URL from Google Fonts raw GitHub repo
                url = "https://github.com/google/fonts/raw/main/ofl/exo2/Exo2%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Exo 2 font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Exo 2 font: {e}")

    def setup_cinzel_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Cinzel.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                # Cinzel Variable Font URL from Google Fonts raw GitHub repo
                url = "https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Cinzel font: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Cinzel font: {e}")

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
        
        saved_style = self.config_manager.get("launcher_style", "alien").lower()
        if saved_style in ("matrix", "onyx", "eclipsex", "kitty", "shougun"):
            # Canvas background for animations
            is_light = self.config_manager.get("theme", "dark").lower() == "light"
            if saved_style == "matrix":
                bg_color = "#050505"
            elif saved_style == "onyx":
                bg_color = "#0B0B0D"
            elif saved_style == "kitty":
                bg_color = "#FFF5F8" if is_light else "#1E1218"
            elif saved_style == "shougun":
                bg_color = "#090909"
            else:
                bg_color = "#F8FAFC" if is_light else "#050506"
                
            self.matrix_canvas = tk.Canvas(home, bg=bg_color, highlightthickness=0)
            self.matrix_canvas.place(x=0, y=0, relwidth=1, relheight=1)
            
            if saved_style == "matrix":
                # Setup columns for Matrix rain
                self.matrix_columns = 55
                self.matrix_font_size = 12
                self.matrix_drops = [0] * self.matrix_columns
                self.matrix_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%^&*()_+{}[]<>?/\\"
                
                def draw_matrix_rain():
                    if not hasattr(self, "matrix_canvas") or not self.matrix_canvas.winfo_exists():
                        return
                    self.matrix_canvas.delete("all")
                    
                    width = self.matrix_canvas.winfo_width()
                    height = self.matrix_canvas.winfo_height()
                    if width <= 1 or height <= 1:
                        width = 880
                        height = 650
                    
                    col_width = max(width // self.matrix_columns, 15)
                    
                    import random
                    for i in range(len(self.matrix_drops)):
                        char = random.choice(self.matrix_chars)
                        x = i * col_width + 8
                        y = self.matrix_drops[i] * self.matrix_font_size
                        
                        # Draw head
                        self.matrix_canvas.create_text(x, y, text=char, fill="#39FF14", font=("Exo 2", self.matrix_font_size, "bold"))
                        
                        # Draw tail
                        for tail in range(1, 12):
                            tail_y = y - tail * self.matrix_font_size
                            if tail_y > 0:
                                # Fading greens
                                if tail < 4:
                                    color = "#7CFF00"
                                elif tail < 8:
                                    color = "#00AA00"
                                else:
                                    color = "#003300"
                                tail_char = random.choice(self.matrix_chars)
                                self.matrix_canvas.create_text(x, tail_y, text=tail_char, fill=color, font=("Exo 2", self.matrix_font_size))
                                
                        # Update drops
                        if y > height and random.random() > 0.975:
                            self.matrix_drops[i] = 0
                        else:
                            self.matrix_drops[i] += 1
                            
                    self.after(50, draw_matrix_rain)
                    
                self.after(100, draw_matrix_rain)
            elif saved_style == "onyx":
                # Setup particles for Onyx Starfield
                self.onyx_particles = []
                import random
                colors = ["#8B5CF6", "#A855F7", "#C084FC", "#7C3AED", "#6D28D9"]
                for _ in range(75):
                    self.onyx_particles.append({
                        "x": random.uniform(0, 880),
                        "y": random.uniform(0, 650),
                        "vx": random.uniform(-0.4, 0.4),
                        "vy": random.uniform(-0.8, -0.2), # Move slowly upwards
                        "r": random.uniform(1.0, 3.0),
                        "color": random.choice(colors)
                    })
                    
                def draw_onyx_stars():
                    if not hasattr(self, "matrix_canvas") or not self.matrix_canvas.winfo_exists():
                        return
                    self.matrix_canvas.delete("all")
                    
                    width = self.matrix_canvas.winfo_width()
                    height = self.matrix_canvas.winfo_height()
                    if width <= 1 or height <= 1:
                        width = 880
                        height = 650
                        
                    for p in self.onyx_particles:
                        p["x"] += p["vx"]
                        p["y"] += p["vy"]
                        
                        # Wrap around
                        if p["x"] < 0: p["x"] = width
                        if p["x"] > width: p["x"] = 0
                        if p["y"] < 0: p["y"] = height
                        if p["y"] > height: p["y"] = 0
                        
                        x, y, r = p["x"], p["y"], p["r"]
                        # Draw particle
                        self.matrix_canvas.create_oval(
                            x - r, y - r, x + r, y + r,
                            fill=p["color"], outline=""
                        )
                        
                        # Glow ring
                        if r > 2.0:
                            self.matrix_canvas.create_oval(
                                x - r*2.0, y - r*2.0, x + r*2.0, y + r*2.0,
                                outline=p["color"], width=1
                            )
                            
                    self.after(40, draw_onyx_stars)
                    
                self.after(100, draw_onyx_stars)
            elif saved_style == "kitty":
                # Setup floating pawprints, hearts, stars, bubbles for Kitty
                self.kitty_bubbles = []
                import random
                emojis = ["🐾", "🐾", "💗", "🌸", "⭐", "✨", "🎀", "🐈", "🍧", "🍡"]
                for _ in range(25):
                    self.kitty_bubbles.append({
                        "x": random.uniform(0, 880),
                        "y": random.uniform(200, 650),
                        "vy": random.uniform(0.6, 1.5), # Drift upwards slowly
                        "size": random.randint(14, 28),
                        "char": random.choice(emojis)
                    })
                    
                def draw_kitty_bubbles():
                    if not hasattr(self, "matrix_canvas") or not self.matrix_canvas.winfo_exists():
                        return
                    self.matrix_canvas.delete("all")
                    
                    width = self.matrix_canvas.winfo_width()
                    height = self.matrix_canvas.winfo_height()
                    if width <= 1 or height <= 1:
                        width = 880
                        height = 650
                        
                    for b in self.kitty_bubbles:
                        b["y"] -= b["vy"]
                        # Float/sway horizontally a tiny bit
                        import math
                        import time
                        b["x"] += math.sin(time.time() + b["size"]) * 0.2
                        
                        if b["y"] < -30:
                            b["y"] = height + 30
                            b["x"] = random.uniform(0, width)
                            
                        # Use glowing/pastel pink for emojis if in dark mode, or cute pink in light mode
                        emoji_col = "#FF85C8" if not is_light else "#FF4F9F"
                        self.matrix_canvas.create_text(
                            b["x"], b["y"],
                            text=b["char"],
                            font=("Fredoka", b["size"]),
                            fill=emoji_col
                        )
                        
                    self.after(45, draw_kitty_bubbles)
                    
                self.after(100, draw_kitty_bubbles)
            elif saved_style == "eclipsex":
                # EclipseX constellations and shooting stars
                self.eclipse_stars = []
                import random
                star_colors = ["#7C3AED", "#6366F1", "#A855F7"] if is_light else ["#7C3AED", "#A855F7", "#3B82F6"]
                
                for _ in range(35):
                    self.eclipse_stars.append({
                        "x": random.uniform(0, 880),
                        "y": random.uniform(0, 650),
                        "vx": random.uniform(-0.3, 0.3),
                        "vy": random.uniform(-0.3, 0.3),
                        "r": random.uniform(1.2, 2.8),
                        "color": random.choice(star_colors)
                    })
                self.shooting_star = None
                
                def draw_eclipse_constellation():
                    if not hasattr(self, "matrix_canvas") or not self.matrix_canvas.winfo_exists():
                        return
                    self.matrix_canvas.delete("all")
                    
                    width = self.matrix_canvas.winfo_width()
                    height = self.matrix_canvas.winfo_height()
                    if width <= 1 or height <= 1:
                        width = 880
                        height = 650
                        
                    is_light_mode = self.config_manager.get("theme", "dark").lower() == "light"
                    line_col = "#E0E3EB" if is_light_mode else "#18122B"
                    
                    # Update and draw stars
                    for p in self.eclipse_stars:
                        p["x"] += p["vx"]
                        p["y"] += p["vy"]
                        
                        if p["x"] < 0: p["x"] = width
                        if p["x"] > width: p["x"] = 0
                        if p["y"] < 0: p["y"] = height
                        if p["y"] > height: p["y"] = 0
                        
                        x, y, r = p["x"], p["y"], p["r"]
                        self.matrix_canvas.create_oval(
                            x - r, y - r, x + r, y + r,
                            fill=p["color"], outline=""
                        )
                        
                    # Connecting constellation lines
                    import math
                    for i in range(len(self.eclipse_stars)):
                        for j in range(i + 1, len(self.eclipse_stars)):
                            dx = self.eclipse_stars[i]["x"] - self.eclipse_stars[j]["x"]
                            dy = self.eclipse_stars[i]["y"] - self.eclipse_stars[j]["y"]
                            dist = math.sqrt(dx*dx + dy*dy)
                            if dist < 85:
                                self.matrix_canvas.create_line(
                                    self.eclipse_stars[i]["x"], self.eclipse_stars[i]["y"],
                                    self.eclipse_stars[j]["x"], self.eclipse_stars[j]["y"],
                                    fill=line_col, width=1
                                )
                                
                    # Shooting star update
                    import random
                    if self.shooting_star is None:
                        if random.random() > 0.992:
                            self.shooting_star = {
                                "x": random.uniform(0, width * 0.6),
                                "y": 0,
                                "vx": random.uniform(4.0, 7.0),
                                "vy": random.uniform(3.0, 5.0),
                                "length": random.uniform(40.0, 80.0),
                                "color": random.choice(star_colors)
                            }
                    else:
                        s = self.shooting_star
                        s["x"] += s["vx"]
                        s["y"] += s["vy"]
                        
                        self.matrix_canvas.create_line(
                            s["x"] - s["length"], s["y"] - (s["length"] * s["vy"]/s["vx"]),
                            s["x"], s["y"],
                            fill=s["color"], width=2
                        )
                        
                        if s["x"] > width or s["y"] > height:
                            self.shooting_star = None
                            
                    self.after(45, draw_eclipse_constellation)
                    
                self.after(100, draw_eclipse_constellation)
            elif saved_style == "shougun":
                # Setup falling Sakura petals for Shougun
                self.sakura_petals = []
                import random
                colors = ["#C1121F", "#E63946", "#D4AF37", "#FF5C77"]
                for _ in range(45):
                    self.sakura_petals.append({
                        "x": random.uniform(0, 880),
                        "y": random.uniform(-100, 650),
                        "vy": random.uniform(0.7, 1.6), # Fall downwards
                        "vx": random.uniform(-0.4, 0.4), # Drift sideways
                        "size": random.uniform(3, 7),
                        "color": random.choice(colors),
                        "sway_speed": random.uniform(0.01, 0.03),
                        "sway_offset": random.uniform(0, 100)
                    })
                    
                def draw_sakura():
                    if not hasattr(self, "matrix_canvas") or not self.matrix_canvas.winfo_exists():
                        return
                    self.matrix_canvas.delete("all")
                    
                    width = self.matrix_canvas.winfo_width()
                    height = self.matrix_canvas.winfo_height()
                    if width <= 1 or height <= 1:
                        width = 880
                        height = 650
                        
                    import math
                    import time
                    for p in self.sakura_petals:
                        p["y"] += p["vy"]
                        sway = math.sin(time.time() * 2 + p["sway_offset"]) * 0.4
                        p["x"] += p["vx"] + sway
                        
                        if p["y"] > height + 20:
                            p["y"] = -20
                            p["x"] = random.uniform(0, width)
                            
                        x, y, r = p["x"], p["y"], p["size"]
                        self.matrix_canvas.create_oval(
                            x - r, y - r/2, x + r, y + r/2,
                            fill=p["color"], outline=""
                        )
                        
                    self.after(45, draw_sakura)
                    
                self.after(100, draw_sakura)
                
            bg_loaded = True
        elif os.path.exists(bg_path):
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
        if saved_style in ("matrix", "onyx", "eclipsex", "kitty", "shougun"):
            self.home_overlay = self.matrix_canvas
            self.home_overlay.grid_columnconfigure(0, weight=1)
            self.home_overlay.grid_rowconfigure(0, weight=1) # Content spacer
            self.home_overlay.grid_rowconfigure(1, weight=0) # Card area
            self.home_overlay.grid_rowconfigure(2, weight=0) # Control bar
        else:
            self.home_overlay = ctk.CTkFrame(home, fg_color="transparent")
            self.home_overlay.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
            self.home_overlay.grid_columnconfigure(0, weight=1)
            self.home_overlay.grid_rowconfigure(0, weight=1) # Content spacer
            self.home_overlay.grid_rowconfigure(1, weight=0) # Card area
            self.home_overlay.grid_rowconfigure(2, weight=0) # Control bar
 
        # Top Title Banner
        is_light_mode = self.config_manager.get("theme", "dark").lower() == "light"
        if saved_style == "matrix":
            banner_bg = "#050505"
        elif saved_style == "onyx":
            banner_bg = "#0B0B0D"
        elif saved_style == "kitty":
            banner_bg = "#FFF5F8" if is_light_mode else "#1E1218"
        elif saved_style == "eclipsex":
            banner_bg = "#F8FAFC" if is_light_mode else "#050506"
        elif saved_style == "shougun":
            banner_bg = "#090909"
        else:
            banner_bg = "transparent"
            
        self.banner_frame = ctk.CTkFrame(self.home_overlay, fg_color=banner_bg)
        self.banner_frame.grid(row=0, column=0, padx=30, pady=(40, 0), sticky="nw")
        
        self.banner_title_label = ctk.CTkLabel(
            self.banner_frame, text="Alien Launcher",
            font=ctk.CTkFont(family="Orbitron", size=36, weight="bold"),
            text_color="#FFFFFF"
        )
        self.banner_title_label.pack(anchor="w")
        
        self.banner_subtitle = ctk.CTkLabel(
            self.banner_frame, text="Sleek, Secure, and Private Multiplayer launcher.",
            font=ctk.CTkFont(family="Orbitron", size=12),
            text_color="#A5D6A7"
        )
        self.banner_subtitle.pack(anchor="w", pady=(5, 0))
 
        # Horizontal Row of Status Cards
        is_light_mode = self.config_manager.get("theme", "dark").lower() == "light"
        if saved_style == "matrix":
            cards_bg = "#050505"
        elif saved_style == "onyx":
            cards_bg = "#0B0B0D"
        elif saved_style == "kitty":
            cards_bg = "#FFF5F8" if is_light_mode else "#1E1218"
        elif saved_style == "eclipsex":
            cards_bg = "#F8FAFC" if is_light_mode else "#050506"
        elif saved_style == "shougun":
            cards_bg = "#090909"
        else:
            cards_bg = "transparent"
        self.cards_row = ctk.CTkFrame(self.home_overlay, fg_color=cards_bg)
        self.cards_row.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="ew")
        self.cards_row.grid_columnconfigure((0, 1, 2), weight=1, uniform="home_card")

        # Card 1: Account Info
        self.card_acc = ctk.CTkFrame(self.cards_row, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
        self.card_acc.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        lbl_acc_title = ctk.CTkLabel(self.card_acc, text="ACCOUNT PROFILE", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED)
        lbl_acc_title.pack(padx=15, pady=(15, 2), anchor="w")
        self.lbl_acc_val = ctk.CTkLabel(self.card_acc, text="AlienPlayer", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_acc_val.pack(padx=15, pady=(0, 15), anchor="w")

        # Card 2: Settings Preview (RAM)
        self.card_settings = ctk.CTkFrame(self.cards_row, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
        self.card_settings.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        lbl_sett_title = ctk.CTkLabel(self.card_settings, text="RAM ALLOCATION", font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_MUTED)
        lbl_sett_title.pack(padx=15, pady=(15, 2), anchor="w")
        self.lbl_sett_val = ctk.CTkLabel(self.card_settings, text="Min: 2G / Max: 4G", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_sett_val.pack(padx=15, pady=(0, 15), anchor="w")

        # Card 3: VPN Status Preview
        self.card_vpn = ctk.CTkFrame(self.cards_row, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
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
        
        ctk.CTkLabel(l_sub_frame, text="Select Loader", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w")
        
        self.loader_var = ctk.StringVar(value=self.config_manager.get("loader_type", "Fabric"))
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
        force_redownload = False
        
        if force_redownload or not is_ver_installed or not is_loader_installed:
            # We need to download and install
            confirm = messagebox.askyesno(
                "Installation Required",
                f"Minecraft version {selected_ver} ({loader}) is not fully set up.\nDo you want to download and install it now?"
            )
            if not confirm:
                return
            
            self.start_installation(selected_ver, force_redownload)
        else:
            # Already installed, just launch
            self.launch_game(selected_ver)

    def start_installation(self, version_id, force_redownload=False, is_repair_only=False):
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
            success, err = self.minecraft_manager.install_version(
                version_id, 
                progress_cb, 
                status_cb, 
                force_redownload=force_redownload
            )
            
            def _on_finish():
                self.downloading = False
                self.progress_bar.grid_remove()
                self.btn_play.configure(state="normal", text="PLAY GAME")
                
                if success:
                    # Refresh available versions to make sure the newly installed one is detected
                    self.available_versions = self.minecraft_manager.get_available_versions()
                    if is_repair_only:
                        messagebox.showinfo("Repair Success", f"Successfully repaired {version_id}!")
                        self.status_label.configure(text="Ready to Launch")
                    else:
                        self.launch_game(version_id)
                else:
                    messagebox.showerror("Installation/Repair Error", f"Action failed for {version_id}:\n{err}")
                    self.status_label.configure(text="Action failed")
            
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
        self.version_dialog.overrideredirect(True) # Make borderless/non-movable
        self.version_dialog.transient(self) # Keep on top of launcher
        self.version_dialog.grab_set() # Grab focus (modal)
        
        # Position near the mouse cursor where clicked
        mx, my = self.winfo_pointerxy()
        x = max(0, min(mx - 150, self.winfo_screenwidth() - 300))
        y = max(0, min(my - 225, self.winfo_screenheight() - 450))
        self.version_dialog.geometry(f"+{x}+{y}")

        # Calculate offset relative to parent window and bind synchronization
        px, py = self.winfo_x(), self.winfo_y()
        offset_x = x - px
        offset_y = y - py

        def sync_position(event):
            if event.widget == self and hasattr(self, "version_dialog") and self.version_dialog.winfo_exists():
                self.version_dialog.geometry(f"+{self.winfo_x() + offset_x}+{self.winfo_y() + offset_y}")

        bind_id = self.bind("<Configure>", sync_position, add="+")
        
        def on_destroy(event):
            if event.widget == self.version_dialog:
                try:
                    self.unbind("<Configure>", bind_id)
                except Exception:
                    pass
        self.version_dialog.bind("<Destroy>", on_destroy)

        # Main frame wrapper with border
        main_frame = ctk.CTkFrame(
            self.version_dialog,
            fg_color=APP_BG,
            border_width=2,
            border_color=BORDER,
            corner_radius=12
        )
        main_frame.pack(fill="both", expand=True)

        # Header Title Label
        header_lbl = ctk.CTkLabel(
            main_frame,
            text="SELECT VERSION",
            font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
            text_color=SUCCESS_COLOR
        )
        header_lbl.pack(pady=(15, 5))

        # Search frame
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(5, 10))
        
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
        scroll_frame = ctk.CTkScrollableFrame(main_frame, fg_color=SURFACE_ALT, border_width=1, border_color=BORDER_DARK)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Cancel Button
        btn_cancel = ctk.CTkButton(
            main_frame,
            text="CANCEL",
            height=32,
            fg_color=SECONDARY_BUTTON,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Orbitron", size=11, weight="bold"),
            command=self.version_dialog.destroy
        )
        btn_cancel.pack(fill="x", padx=15, pady=(0, 15))

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
        self.loader_dialog.title("Select Loader")
        self.loader_dialog.geometry("300x450")
        self.loader_dialog.resizable(False, False)
        self.loader_dialog.overrideredirect(True) # Make borderless/non-movable
        self.loader_dialog.transient(self) # Keep on top of launcher
        self.loader_dialog.grab_set() # Grab focus (modal)
        
        # Position near the mouse cursor where clicked
        mx, my = self.winfo_pointerxy()
        x = max(0, min(mx - 150, self.winfo_screenwidth() - 300))
        y = max(0, min(my - 225, self.winfo_screenheight() - 450))
        self.loader_dialog.geometry(f"+{x}+{y}")

        # Calculate offset relative to parent window and bind synchronization
        px, py = self.winfo_x(), self.winfo_y()
        offset_x = x - px
        offset_y = y - py

        def sync_position(event):
            if event.widget == self and hasattr(self, "loader_dialog") and self.loader_dialog.winfo_exists():
                self.loader_dialog.geometry(f"+{self.winfo_x() + offset_x}+{self.winfo_y() + offset_y}")

        bind_id = self.bind("<Configure>", sync_position, add="+")
        
        def on_destroy_loader(event):
            if event.widget == self.loader_dialog:
                try:
                    self.unbind("<Configure>", bind_id)
                except Exception:
                    pass
        self.loader_dialog.bind("<Destroy>", on_destroy_loader)

        # Main frame wrapper with border
        main_frame = ctk.CTkFrame(
            self.loader_dialog,
            fg_color=APP_BG,
            border_width=2,
            border_color=BORDER,
            corner_radius=12
        )
        main_frame.pack(fill="both", expand=True)

        # Header Title Label
        header_lbl = ctk.CTkLabel(
            main_frame,
            text="SELECT LOADER",
            font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
            text_color=SUCCESS_COLOR
        )
        header_lbl.pack(pady=(15, 5))

        # Search frame
        search_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=15, pady=(5, 10))
        
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
        scroll_frame = ctk.CTkScrollableFrame(main_frame, fg_color=SURFACE_ALT, border_width=1, border_color=BORDER_DARK)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Cancel Button
        btn_cancel = ctk.CTkButton(
            main_frame,
            text="CANCEL",
            height=32,
            fg_color=SECONDARY_BUTTON,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Orbitron", size=11, weight="bold"),
            command=self.loader_dialog.destroy
        )
        btn_cancel.pack(fill="x", padx=15, pady=(0, 15))

        loaders = [
            "Fabric", "NeoForge", "Forge", "Quilt", 
            "OptiFine", "LiteLoader"
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
                    is_disabled = l in ["OptiFine", "LiteLoader"]
                    btn = ctk.CTkButton(
                        scroll_frame,
                        text=l,
                        height=32,
                        anchor="w",
                        fg_color="transparent",
                        hover_color=SURFACE_HOVER,
                        text_color=TEXT_MUTED if is_disabled else TEXT_SECONDARY,
                        font=ctk.CTkFont(size=12, weight="bold"),
                        state="disabled" if is_disabled else "normal",
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
