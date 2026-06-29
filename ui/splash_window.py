import os
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

class SplashWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Register custom alien font
        self.setup_alien_font()

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
        else:
            logo_path = get_asset_path("assets/newlogo.png")
            fallback_ico = get_asset_path("assets/newlogo.ico")

        if os.path.exists(fallback_ico):
            try:
                self.iconbitmap(fallback_ico)
            except Exception:
                pass

        # Main background container with a border matching the theme
        border_col = "#FF66CC" if saved_style == "unicorn" else "#00FF66"
        self.main_frame = ctk.CTkFrame(
            self,
            width=self.width,
            height=self.height,
            fg_color="#08080C",
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
                self.logo_label = tk.Label(self.main_frame, image=self.logo_img, bg="#08080C")
                self.logo_label.pack(pady=(40, 10))
            except Exception as e:
                print(f"Error loading splash logo: {e}")

        # Fallback and title config based on launcher style
        if saved_style == "unicorn":
            fallback_emoji = "🦄"
            title_text = "UNICORN LAUNCHER"
            title_color = "#FF66CC"
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
        self.title_lbl = ctk.CTkLabel(
            self.main_frame,
            text=title_text,
            font=ctk.CTkFont(family="Orbitron", size=26, weight="bold"),
            text_color=title_color
        )
        self.title_lbl.pack(pady=5)

        # Subtitle / Muted info
        from core.update_manager import LAUNCHER_VERSION
        self.subtitle_lbl = ctk.CTkLabel(
            self.main_frame,
            text=f"COSMIC CLIENT v{LAUNCHER_VERSION}",
            font=ctk.CTkFont(family="Orbitron", size=10, weight="bold"),
            text_color="#555555"
        )
        self.subtitle_lbl.pack(pady=(0, 15))

        # Status Label (what's loading)
        status_text_color = "#FFA6D5" if saved_style == "unicorn" else "#A5D6A7"
        self.status_lbl = ctk.CTkLabel(
            self.main_frame,
            text="BOOTING SYSTEM...",
            font=ctk.CTkFont(family="Orbitron", size=11),
            text_color=status_text_color
        )
        self.status_lbl.pack(pady=(15, 5))

        # Progressbar
        progress_col = "#FF66CC" if saved_style == "unicorn" else "#00FF66"
        self.progress_bar = ctk.CTkProgressBar(
            self.main_frame,
            width=400,
            height=6,
            progress_color=progress_col,
            fg_color="#1C1D24"
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0.0)

        # Progress percentage label
        self.percentage_lbl = ctk.CTkLabel(
            self.main_frame,
            text="0%",
            font=ctk.CTkFont(family="Orbitron", size=11, weight="bold"),
            text_color=progress_col
        )
        self.percentage_lbl.pack(pady=(0, 20))

        # Sci-fi warning message at the bottom
        self.warn_lbl = ctk.CTkLabel(
            self.main_frame,
            text="WARNING: ACCESS RESTRICTED TO CLASSIFIED BEINGS ONLY",
            font=ctk.CTkFont(family="Orbitron", size=8),
            text_color="#E74C3C"
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
