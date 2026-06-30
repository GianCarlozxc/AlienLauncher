import os
import customtkinter as ctk
import tkinter as tk
import ui.theme

class CustomDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, dialog_type="info"):
        super().__init__(parent)
        self.title(title)
        self.message = message
        self.dialog_type = dialog_type
        self.result = None
        
        # Configure window properties
        self.resizable(False, False)
        self.overrideredirect(True) # Borderless window for a modern look
        
        # Get active launcher style
        from core.config_manager import ConfigManager
        config = ConfigManager()
        self.launcher_style = config.get("launcher_style", "alien").lower()
        
        # Define default dimensions first so setup_ui can access them
        self.width = 460
        self.height = 180
        
        # Setup UI
        self.setup_ui()
        
        # Force Tkinter to evaluate frame layout sizes
        self.update_idletasks()
        
        # Determine height dynamically based on text height
        required_height = self.main_frame.winfo_reqheight()
        self.height = max(180, required_height + 15)
        
        # Center Dialog on parent
        if parent and parent.winfo_exists():
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - self.width) // 2
            y = py + (ph - self.height) // 2
        else:
            # Center on screen
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = (sw - self.width) // 2
            y = (sh - self.height) // 2
            
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        # Make modal and force to top of stack
        self.transient(parent)
        self.attributes("-topmost", True)
        self.lift()
        self.grab_set()
        self.focus_set()
        
        # Wait for window to close
        self.wait_window()

    def setup_ui(self):
        from ui.theme import (
            APP_BG, BORDER, TEXT_PRIMARY, ACCENT_COLOR, 
            ACCENT_HOVER_COLOR, ACCENT_TEXT_COLOR, SUCCESS_COLOR, 
            SECONDARY_BUTTON, SECONDARY_HOVER
        )
        
        self.main_frame = ctk.CTkFrame(
            self,
            width=self.width,
            height=self.height,
            fg_color=APP_BG,
            border_width=2,
            border_color=BORDER,
            corner_radius=12
        )
        self.main_frame.pack(fill="both", expand=True)
        
        # Title bar
        title_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=35)
        title_bar.pack(fill="x", padx=15, pady=(15, 0))
        
        title_label = ctk.CTkLabel(
            title_bar,
            text=self.title().upper(),
            font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
            text_color=SUCCESS_COLOR
        )
        title_label.pack(side="left")
        
        # Icon mapping based on dialog type
        emoji = "ℹ️"
        if self.dialog_type == "error":
            emoji = "❌"
        elif self.dialog_type == "warning":
            emoji = "⚠️"
        elif self.dialog_type == "question":
            emoji = "❓"
            
        # Message content
        content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=(10, 10))
        
        emoji_label = ctk.CTkLabel(
            content_frame,
            text=emoji,
            font=ctk.CTkFont(size=32)
        )
        emoji_label.pack(side="left", padx=(5, 15))
        
        msg_label = ctk.CTkLabel(
            content_frame,
            text=self.message,
            font=ctk.CTkFont(family="Outfit", size=12),
            text_color=TEXT_PRIMARY,
            justify="left",
            wraplength=350
        )
        msg_label.pack(side="left", fill="both", expand=True)
        
        # Buttons area
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=45)
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 15))
        
        if self.dialog_type == "question":
            btn_no = ctk.CTkButton(
                btn_frame,
                text="No",
                width=90,
                height=30,
                fg_color=SECONDARY_BUTTON,
                hover_color=SECONDARY_HOVER,
                text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
                command=self.on_no
            )
            btn_no.pack(side="right", padx=(10, 0))
            
            btn_yes = ctk.CTkButton(
                btn_frame,
                text="Yes",
                width=90,
                height=30,
                fg_color=ACCENT_COLOR,
                hover_color=ACCENT_HOVER_COLOR,
                text_color=ACCENT_TEXT_COLOR,
                font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
                command=self.on_yes
            )
            btn_yes.pack(side="right")
        else:
            btn_ok = ctk.CTkButton(
                btn_frame,
                text="OK",
                width=100,
                height=30,
                fg_color=ACCENT_COLOR,
                hover_color=ACCENT_HOVER_COLOR,
                text_color=ACCENT_TEXT_COLOR,
                font=ctk.CTkFont(family="Orbitron", size=12, weight="bold"),
                command=self.on_ok
            )
            btn_ok.pack(side="right")

    def on_yes(self):
        self.result = True
        self.destroy()
        
    def on_no(self):
        self.result = False
        self.destroy()
        
    def on_ok(self):
        self.result = True
        self.destroy()

def get_parent_window(parent=None):
    if parent and parent.winfo_exists():
        try:
            return parent.winfo_toplevel()
        except Exception:
            return parent
    try:
        # Find active CTk root
        if ctk.CTk._top_level_windows:
            for w in ctk.CTk._top_level_windows:
                if w.winfo_exists() and w.winfo_viewable():
                    return w
            for w in ctk.CTk._top_level_windows:
                if w.winfo_exists():
                    return w
    except Exception:
        pass
    return tk._default_root

# Wrapper functions
def showinfo(title, message, parent=None):
    parent = get_parent_window(parent)
    dialog = CustomDialog(parent, title, message, "info")
    return dialog.result

def showerror(title, message, parent=None):
    parent = get_parent_window(parent)
    dialog = CustomDialog(parent, title, message, "error")
    return dialog.result

def showwarning(title, message, parent=None):
    parent = get_parent_window(parent)
    dialog = CustomDialog(parent, title, message, "warning")
    return dialog.result

def askyesno(title, message, parent=None):
    parent = get_parent_window(parent)
    dialog = CustomDialog(parent, title, message, "question")
    return dialog.result
