import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

class SplashWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Register custom fonts
        self.setup_alien_font()
        self.setup_space_grotesk_font()
        self.setup_fredoka_font()
        self.setup_oxanium_font()
        self.setup_exo2_font()

        # Window properties
        self.title("Alien Launcher Loading")
        self.width = 580
        self.height = 380

        # Make it borderless
        self.overrideredirect(True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Center on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (self.width // 2)
        y = (screen_height // 2) - (self.height // 2)
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # Set taskbar icon and logo paths based on launcher style
        from core.config_manager import ConfigManager
        config = ConfigManager()
        saved_style = config.get("launcher_style", "alien").lower()

        from ui.theme import get_asset_path
        if saved_style == "unicorn":
            logo_path = get_asset_path("assets/Unicornlogo.png")
            fallback_ico = get_asset_path("assets/Unicornlogo.ico")
        elif saved_style == "onyx":
            logo_path = get_asset_path("assets/Onyxlogo.png")
            fallback_ico = get_asset_path("assets/Onyxlogo.ico")
        elif saved_style == "kitty":
            logo_path = get_asset_path("assets/Kittylogo.png")
            fallback_ico = get_asset_path("assets/Kittylogo.ico")
        elif saved_style == "eclipsex":
            logo_path = get_asset_path("assets/eclipseX.png")
            fallback_ico = get_asset_path("assets/eclipseX.ico")
        elif saved_style == "matrix":
            logo_path = get_asset_path("assets/MatrixLogo.png")
            fallback_ico = get_asset_path("assets/MatrixLogo.ico")
        elif saved_style == "shougun":
            logo_path = get_asset_path("assets/ShougunLogo.png")
            fallback_ico = get_asset_path("assets/ShougunLogo.ico")
        else:
            logo_path = get_asset_path("assets/newlogo.png")
            fallback_ico = get_asset_path("assets/newlogo.ico")

        if os.path.exists(fallback_ico):
            try:
                self.iconbitmap(fallback_ico)
            except Exception:
                pass

        # Main background container with a border matching the theme
        if saved_style == "unicorn":
            border_col = "#FF66CC"
            splash_bg = "#08080C"
        elif saved_style == "onyx":
            border_col = "#2A2A30"
            splash_bg = "#141414"
        elif saved_style == "kitty":
            border_col = "#FF4F9F"
            splash_bg = "#000000"
        elif saved_style == "eclipsex":
            border_col = "#A855F7"
            splash_bg = "#050506"
        elif saved_style == "matrix":
            border_col = "#39FF14"
            splash_bg = "#0A0A0B"
        elif saved_style == "shougun":
            border_col = "#D4AF37"
            splash_bg = "#090909"
        else:
            border_col = "#00FF66"
            splash_bg = "#08080C"
        self.main_frame = ctk.CTkFrame(
            self,
            width=self.width,
            height=self.height,
            fg_color=splash_bg,
            border_width=2,
            border_color=border_col,
            corner_radius=12
        )
        self.main_frame.pack(fill="both", expand=True)

        # Load Alien Logo
        self.logo_label = None
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path).resize((130, 130), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_logo)
                self.logo_label = tk.Label(self.main_frame, image=self.logo_img, bg=splash_bg)
                self.logo_label.pack(pady=(40, 10))
            except Exception as e:
                print(f"Error loading splash logo: {e}")

        # Fallback and title config based on launcher style
        if saved_style == "unicorn":
            fallback_emoji = "🦄"
            title_text = "UNICORN LAUNCHER"
            title_color = "#FF66CC"
        elif saved_style == "onyx":
            fallback_emoji = "💎"
            title_text = "ONYX LAUNCHER"
            title_color = "#8B5CF6"
        elif saved_style == "kitty":
            fallback_emoji = "🐱"
            title_text = "KITTY LAUNCHER"
            title_color = "#FF4F9F"
        elif saved_style == "eclipsex":
            fallback_emoji = "🌑"
            title_text = "ECLIPSEX LAUNCHER"
            title_color = "#7C3AED"
        elif saved_style == "matrix":
            fallback_emoji = "📟"
            title_text = "MATRIX LAUNCHER"
            title_color = "#39FF14"
        elif saved_style == "shougun":
            fallback_emoji = "🏯"
            title_text = "SHOUGUN LAUNCHER"
            title_color = "#C1121F"
        else:
            fallback_emoji = "👽"
            title_text = "ALIEN LAUNCHER"
            title_color = "#00FF66"

        if not self.logo_label:
            # Fallback logo text
            self.logo_lbl = ctk.CTkLabel(
                self.main_frame,
                text=fallback_emoji,
                font=ctk.CTkFont(size=72)
            )
            self.logo_lbl.pack(pady=(50, 10))

        # Title Label
        title_font_family = "Exo 2" if saved_style == "matrix" else ("Cinzel" if saved_style == "shougun" else "Orbitron")
        self.title_lbl = ctk.CTkLabel(
            self.main_frame,
            text=title_text,
            font=ctk.CTkFont(family=title_font_family, size=26, weight="bold"),
            text_color=title_color
        )
        self.title_lbl.pack(pady=5)

        # Subtitle / Muted info
        from core.update_manager import LAUNCHER_VERSION
        subtitle_text = "COSMIC CLIENT v" + LAUNCHER_VERSION
        subtitle_color = "#555555"
        if saved_style == "matrix":
            subtitle_text = "NEO-VIRTUAL NETWORK NODE v" + LAUNCHER_VERSION
            subtitle_color = "#7CFF00"
        elif saved_style == "kitty":
            subtitle_color = "#FF85C8"
        elif saved_style == "shougun":
            subtitle_text = "FEUDAL WARRIOR CLIENT v" + LAUNCHER_VERSION
            subtitle_color = "#D4AF37"
            
        self.subtitle_lbl = ctk.CTkLabel(
            self.main_frame,
            text=subtitle_text,
            font=ctk.CTkFont(family=title_font_family, size=10, weight="bold"),
            text_color=subtitle_color
        )
        self.subtitle_lbl.pack(pady=(0, 15))

        # Status Label (what's loading)
        if saved_style == "unicorn":
            status_text_color = "#FFA6D5"
        elif saved_style == "onyx":
            status_text_color = "#F5F5F5"
        elif saved_style == "kitty":
            status_text_color = "#FF4F9F"
        elif saved_style == "eclipsex":
            status_text_color = "#E5E7EB"
        elif saved_style == "matrix":
            status_text_color = "#39FF14"
        elif saved_style == "shougun":
            status_text_color = "#B8BCC5"
        else:
            status_text_color = "#A5D6A7"
        self.status_lbl = ctk.CTkLabel(
            self.main_frame,
            text="BOOTING SYSTEM...",
            font=ctk.CTkFont(family=title_font_family, size=11),
            text_color=status_text_color
        )
        self.status_lbl.pack(pady=(15, 5))

        # Progressbar
        if saved_style == "unicorn":
            progress_col = "#FF66CC"
        elif saved_style == "onyx":
            progress_col = "#8B5CF6"
        elif saved_style == "kitty":
            progress_col = "#FF4F9F"
        elif saved_style == "eclipsex":
            progress_col = "#7C3AED"
        elif saved_style == "matrix":
            progress_col = "#39FF14"
        elif saved_style == "shougun":
            progress_col = "#C1121F"
        else:
            progress_col = "#00FF66"
        self.progress_bar = ctk.CTkProgressBar(
            self.main_frame,
            width=400,
            height=6,
            progress_color=progress_col,
            fg_color="#121212" if saved_style == "matrix" else ("#1A1A1D" if saved_style == "shougun" else "#1C1D24")
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0.0)

        # Progress percentage label
        self.percentage_lbl = ctk.CTkLabel(
            self.main_frame,
            text="0%",
            font=ctk.CTkFont(family=title_font_family, size=11, weight="bold"),
            text_color=progress_col
        )
        self.percentage_lbl.pack(pady=(0, 20))

        # Matrix specific circuit/digital decor
        if saved_style == "matrix":
            self.matrix_decor = ctk.CTkLabel(
                self.main_frame,
                text="STATUS: SECURE // DECRYPTING CIRCUITS... [01001101]",
                font=ctk.CTkFont(family="Exo 2", size=8),
                text_color="#7CFF00"
            )
            self.matrix_decor.pack(pady=(5, 0))

        # Sci-fi warning message at the bottom
        warn_text = "WARNING: ACCESS RESTRICTED TO CLASSIFIED BEINGS ONLY"
        warn_color = "#E74C3C"
        if saved_style == "matrix":
            warn_text = "SECURE PROTOCOL ACTIVE // HOLOGRAPHIC ENCRYPT LINK"
            warn_color = "#39FF14"
        elif saved_style == "kitty":
            warn_text = "CUTE & PROTOCOL POWERED // ACCESS GRANTED"
            warn_color = "#FF4F9F"
        elif saved_style == "shougun":
            warn_text = "HONOR // ACCESS RESTRICTED TO SAMURAI GUARDS"
            warn_color = "#E63946"
            
        self.warn_lbl = ctk.CTkLabel(
            self.main_frame,
            text=warn_text,
            font=ctk.CTkFont(family=title_font_family, size=8),
            text_color=warn_color
        )
        self.warn_lbl.pack(side="bottom", pady=15)

        # Start loading animation
        self.progress = 0
        self.status_messages = [
            (10, "INITIALIZING QUANTUM ENGINES..."),
            (25, "CONNECTING TO HYPERSPACE NETWORK..."),
            (45, "BYPASSING LOCAL MOJANG PROTOCOLS..."),
            (65, "SYNAPSE LINK ESTABLISHED WITH TAILSCALE..."),
            (85, "COMPILING GRAPHICS ACCELERATOR (SODIUM)..."),
            (95, "FINALIZING COSMIC MATRIX SYNC..."),
            (100, "SYSTEM RUNNING. ENJOY THE RIDE.")
        ]
        self.update_progress()

    def setup_alien_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Orbitron.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Orbitron font in splash: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Orbitron font in splash: {e}")

    def setup_space_grotesk_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/SpaceGrotesk.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Space Grotesk font in splash: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Space Grotesk font in splash: {e}")

    def setup_fredoka_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Fredoka.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth%2Cwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Fredoka font in splash: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Fredoka font in splash: {e}")

    def setup_oxanium_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Oxanium.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/oxanium/Oxanium%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Oxanium font in splash: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Oxanium font in splash: {e}")

    def setup_exo2_font(self):
        from ui.theme import get_asset_path
        font_path = get_asset_path("assets/Exo2.ttf")
        if not os.path.exists(font_path):
            try:
                import urllib.request
                url = "https://github.com/google/fonts/raw/main/ofl/exo2/Exo2%5Bwght%5D.ttf"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download Exo 2 font in splash: {e}")
                
        if os.path.exists(font_path):
            try:
                import ctypes
                ctypes.windll.gdi32.AddFontResourceW(font_path)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x1D, 0, 0)
            except Exception as e:
                print(f"Failed to load Exo 2 font in splash: {e}")

    def on_close(self):
        import os
        os._exit(0)

    def destroy(self):
        # Cancel all pending Tkinter after events to prevent "invalid command name" errors
        try:
            for after_id in self.tk.eval('after info').split():
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            super().destroy()
        except Exception:
            pass

    def update_progress(self):
        # Slowly increment progress to make it look premium
        import random
        self.progress += random.randint(2, 6)
        if self.progress > 100:
            self.progress = 100

        # Update progress bar
        self.progress_bar.set(self.progress / 100.0)
        self.percentage_lbl.configure(text=f"{self.progress}%")

        # Update status message based on progress
        for threshold, msg in self.status_messages:
            if self.progress <= threshold:
                self.status_lbl.configure(text=msg)
                break

        if self.progress < 100:
            # Random delay between steps for a natural loading feel
            delay = random.randint(50, 150)
            self.after(delay, self.update_progress)
        else:
            # Let it sit at 100% for 300ms for finality and destroy
            self.after(300, self.destroy)
