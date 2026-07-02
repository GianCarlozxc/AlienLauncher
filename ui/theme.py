import customtkinter as ctk

ACCENT = "#2ECC71"
ACCENT_HOVER = "#27AE60"
ACCENT_TEXT = "#121212"

ACCENT_COLOR = [ACCENT, ACCENT]
ACCENT_HOVER_COLOR = [ACCENT_HOVER, ACCENT_HOVER]
ACCENT_TEXT_COLOR = [ACCENT_TEXT, ACCENT_TEXT]

APP_BG = ["#F4F7F3", "#181818"]
SIDEBAR_BG = ["#E9EFE7", "#121212"]
SURFACE = ["#FFFFFF", "#1A1A1A"]
SURFACE_ALT = ["#F7FAF6", "#141414"]
SURFACE_HOVER = ["#E7EEE5", "#1E1E1E"]
CONTROL_BG = ["#F8FBF7", "#101010"]
CONTROL_HOVER = ["#E3EBE1", "#222222"]
SECONDARY_BUTTON = ["#E0E8DD", "#2C2C2C"]
SECONDARY_HOVER = ["#D2DDCF", "#3A3A3A"]
BORDER = ["#D6E0D3", "#2A2A2A"]
BORDER_DARK = ["#CAD6C7", "#222222"]
CARD_BORDER = ["#CAD6C7", "#2C2C2C"]

TEXT_PRIMARY = ["#000000", ACCENT]
TEXT_SECONDARY = ["#000000", ACCENT]
TEXT_MUTED = ["#000000", ACCENT]
TEXT_DISABLED = ["#333333", "#1F9F56"]

SUCCESS_COLOR = ["#2ECC71", "#2ECC71"]
HIGHLIGHT_COLOR = ["#A5D6A7", "#2ECC71"]

STRUCTURAL_COLOR_MAP = {
    "#0F0F0F": SURFACE_ALT,
    "#101010": CONTROL_BG,
    "#121212": SIDEBAR_BG,
    "#141414": SURFACE_ALT,
    "#181818": APP_BG,
    "#1A1A1A": SURFACE,
    "#1C1C1C": SURFACE_ALT,
    "#1E1E1E": SURFACE_HOVER,
    "#222222": BORDER_DARK,
    "#2A2A2A": BORDER,
    "#2C2C2C": CARD_BORDER,
    "#333333": CARD_BORDER,
    "#3A3A3A": SECONDARY_HOVER,
    "#2ECC71": ACCENT_COLOR,
    "#27AE60": ACCENT_HOVER_COLOR,
}

STRUCTURAL_OPTIONS = ("fg_color", "border_color", "hover_color", "unselected_color")

TEXT_COLOR_MAP = {
    "#2ECC71": SUCCESS_COLOR,
    "#27AE60": SUCCESS_COLOR,
    "#A5D6A7": SUCCESS_COLOR,
    "#FFFFFF": TEXT_PRIMARY,
    "#CCCCCC": TEXT_PRIMARY,
    "#AAAAAA": TEXT_PRIMARY,
    "#888888": TEXT_PRIMARY,
    "#777777": TEXT_PRIMARY,
    "#666666": TEXT_PRIMARY,
    "#555555": TEXT_DISABLED,
    "#142018": TEXT_PRIMARY,
    "#5C6B60": TEXT_PRIMARY,
    "#708075": TEXT_PRIMARY,
    "#9AA59D": TEXT_DISABLED,
}

TEXT_OPTIONS = ("text_color",)

def update_list(lst, new_vals):
    lst[0] = new_vals[0]
    lst[1] = new_vals[1]

CURRENT_THEME = "alien"

def set_theme(theme_name):
    global ACCENT, ACCENT_HOVER, ACCENT_TEXT, CURRENT_THEME
    theme_name = theme_name.lower()
    CURRENT_THEME = theme_name
    
    if theme_name == "unicorn":
        # Unicorn theme colors (pastels, pinks, purples)
        ACCENT = "#FF66CC"
        ACCENT_HOVER = "#FF3399"
        ACCENT_TEXT = "#000000" # Black in light mode
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, ["#000000", "#1B0B22"]) # Black in light, dark purple/black in dark
        
        update_list(APP_BG, ["#FFF0F8", "#121212"])
        update_list(SIDEBAR_BG, ["#FFE4F2", "#0D0D0D"])
        update_list(SURFACE, ["#FFFFFF", "#1E1E1E"])
        update_list(SURFACE_ALT, ["#FFF5FA", "#151515"])
        update_list(SURFACE_HOVER, ["#FFE4F2", "#2A2A2A"])
        update_list(CONTROL_BG, ["#FFF8FC", "#141414"])
        update_list(CONTROL_HOVER, ["#FFD6EB", "#2D2D2D"])
        update_list(SECONDARY_BUTTON, ["#FFD6EB", "#222222"])
        update_list(SECONDARY_HOVER, ["#FFAEDC", "#333333"])
        update_list(BORDER, ["#FFC2E3", "#4A203B"])
        update_list(BORDER_DARK, ["#FFA6D8", "#2E1425"])
        update_list(CARD_BORDER, ["#FFC2E3", "#4A203B"])
        
        update_list(TEXT_PRIMARY, ["#000000", "#FF66CC"]) # Black in light mode, pink in dark mode
        update_list(TEXT_SECONDARY, ["#000000", "#FF8AD8"]) # Black in light mode, pink in dark mode
        update_list(TEXT_MUTED, ["#000000", "#FFA6D5"]) # Black in light mode, pink in dark mode
        update_list(TEXT_DISABLED, ["#333333", "#A84C8F"])
        update_list(SUCCESS_COLOR, ["#000000", "#FF66CC"]) # Black in light mode, pink in dark mode
        update_list(HIGHLIGHT_COLOR, ["#FFC2E3", "#FF66CC"]) # Light pink in light mode, bright pink in dark mode
    elif theme_name == "onyx":
        # Onyx theme colors (dark onyx black, graphite, purple/violet)
        ACCENT = "#8B5CF6"
        ACCENT_HOVER = "#A855F7"
        ACCENT_TEXT = "#F5F5F5"
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, [ACCENT_TEXT, ACCENT_TEXT])
        
        update_list(APP_BG, ["#0B0B0D", "#0B0B0D"])
        update_list(SIDEBAR_BG, ["#1A1C22", "#1A1C22"])
        update_list(SURFACE, ["#1A1C22", "#1A1C22"])
        update_list(SURFACE_ALT, ["#0B0B0D", "#0B0B0D"])
        update_list(SURFACE_HOVER, ["#2D3139", "#2D3139"])
        update_list(CONTROL_BG, ["#1A1C22", "#1A1C22"])
        update_list(CONTROL_HOVER, ["#2D3139", "#2D3139"])
        update_list(SECONDARY_BUTTON, ["#1A1C22", "#1A1C22"])
        update_list(SECONDARY_HOVER, ["#2D3139", "#2D3139"])
        update_list(BORDER, ["#2D3139", "#2D3139"])
        update_list(BORDER_DARK, ["#2D3139", "#2D3139"])
        update_list(CARD_BORDER, ["#2D3139", "#2D3139"])
        
        update_list(TEXT_PRIMARY, ["#F5F5F5", "#F5F5F5"])
        update_list(TEXT_SECONDARY, ["#9CA3AF", "#9CA3AF"])
        update_list(TEXT_MUTED, ["#9CA3AF", "#9CA3AF"])
        update_list(TEXT_DISABLED, ["#4B5563", "#4B5563"])
        update_list(SUCCESS_COLOR, ["#8B5CF6", "#8B5CF6"])
        update_list(HIGHLIGHT_COLOR, ["#A855F7", "#A855F7"])
    elif theme_name == "kitty":
        # Kitty theme colors (pink, soft gray, mint green, Fredoka font)
        ACCENT = "#FF4F9F"
        ACCENT_HOVER = "#FF85C8"
        ACCENT_TEXT = "#000000"
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, [ACCENT_TEXT, ACCENT_TEXT])
        
        update_list(APP_BG, ["#FFF5F8", "#1E1218"])
        update_list(SIDEBAR_BG, ["#FFE8F0", "#180E13"])
        update_list(SURFACE, ["#FFFFFF", "#281920"])
        update_list(SURFACE_ALT, ["#FFFafc", "#1A0F15"])
        update_list(SURFACE_HOVER, ["#FFD3E3", "#38232D"])
        update_list(CONTROL_BG, ["#FFF0F5", "#20141A"])
        update_list(CONTROL_HOVER, ["#FFD6E8", "#301E27"])
        update_list(SECONDARY_BUTTON, ["#FFE0ED", "#2E1C25"])
        update_list(SECONDARY_HOVER, ["#FFC2DB", "#3E2532"])
        update_list(BORDER, ["#FFC7E0", "#4A2F3D"])
        update_list(BORDER_DARK, ["#FFA6CC", "#5A394B"])
        update_list(CARD_BORDER, ["#FFC7E0", "#4A2F3D"])
        
        update_list(TEXT_PRIMARY, ["#000000", "#FF4F9F"])
        update_list(TEXT_SECONDARY, ["#4B5563", "#D1D5DB"])
        update_list(TEXT_MUTED, ["#71717A", "#9CA3AF"])
        update_list(TEXT_DISABLED, ["#9CA3AF", "#4B5563"])
        update_list(SUCCESS_COLOR, ["#4ADE80", "#4ADE80"])
        update_list(HIGHLIGHT_COLOR, ["#FFC2DB", "#FF4F9F"])
    elif theme_name == "eclipsex":
        # EclipseX theme colors (Eclipse Black, Space Gray, Cosmic Purple, Neon Violet, Silver, Cool Gray, White)
        ACCENT = "#7C3AED"
        ACCENT_HOVER = "#A855F7"
        ACCENT_TEXT = "#FFFFFF"
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, ["#FFFFFF", "#E5E7EB"])
        
        update_list(APP_BG, ["#F8FAFC", "#050506"])
        update_list(SIDEBAR_BG, ["#F1F5F9", "#111218"])
        update_list(SURFACE, ["#FFFFFF", "#111218"])
        update_list(SURFACE_ALT, ["#F8FAFC", "#050506"])
        update_list(SURFACE_HOVER, ["#E2E8F0", "#1C1E26"])
        update_list(CONTROL_BG, ["#F1F5F9", "#111218"])
        update_list(CONTROL_HOVER, ["#E2E8F0", "#1C1E26"])
        update_list(SECONDARY_BUTTON, ["#6366F1", "#3B82F6"])
        update_list(SECONDARY_HOVER, ["#4F46E5", "#2563EB"])
        update_list(BORDER, ["#DCE3EC", "#1C1E26"])
        update_list(BORDER_DARK, ["#DCE3EC", "#1C1E26"])
        update_list(CARD_BORDER, ["#DCE3EC", "#1C1E26"])
        
        update_list(TEXT_PRIMARY, ["#111827", "#E5E7EB"])
        update_list(TEXT_SECONDARY, ["#6B7280", "#A1A1AA"])
        update_list(TEXT_MUTED, ["#6B7280", "#A1A1AA"])
        update_list(TEXT_DISABLED, ["#9CA3AF", "#4B5563"])
        update_list(SUCCESS_COLOR, ["#7C3AED", "#7C3AED"])
        update_list(HIGHLIGHT_COLOR, ["#A855F7", "#FFFFFF"])
    elif theme_name == "matrix":
        # Matrix theme colors (Jet Black background, Carbon Gray secondary background, Matrix Green primary accent, Neon Green glow, Lime Green secondary accent, White primary text, Gray secondary text, Silver metallic)
        ACCENT = "#7CFF00"
        ACCENT_HOVER = "#39FF14"
        ACCENT_TEXT = "#050505"
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, [ACCENT_TEXT, ACCENT_TEXT])
        
        update_list(APP_BG, ["#050505", "#050505"])
        update_list(SIDEBAR_BG, ["#121212", "#121212"])
        update_list(SURFACE, ["#121212", "#121212"])
        update_list(SURFACE_ALT, ["#050505", "#050505"])
        update_list(SURFACE_HOVER, ["#1D1D1D", "#1D1D1D"])
        update_list(CONTROL_BG, ["#121212", "#121212"])
        update_list(CONTROL_HOVER, ["#1D1D1D", "#1D1D1D"])
        update_list(SECONDARY_BUTTON, ["#A3FF12", "#A3FF12"])
        update_list(SECONDARY_HOVER, ["#7CFF00", "#7CFF00"])
        update_list(BORDER, ["#2D2D2D", "#2D2D2D"])
        update_list(BORDER_DARK, ["#2D2D2D", "#2D2D2D"])
        update_list(CARD_BORDER, ["#2D2D2D", "#2D2D2D"])
        
        update_list(TEXT_PRIMARY, ["#FFFFFF", "#FFFFFF"])
        update_list(TEXT_SECONDARY, ["#B0B3C0", "#B0B3C0"])
        update_list(TEXT_MUTED, ["#B0B3C0", "#B0B3C0"])
        update_list(TEXT_DISABLED, ["#4B5563", "#4B5563"])
        update_list(SUCCESS_COLOR, ["#7CFF00", "#7CFF00"])
        update_list(HIGHLIGHT_COLOR, ["#39FF14", "#39FF14"])
    elif theme_name == "shougun":
        # Shougun theme colors (Obsidian Black, Charcoal, Gunmetal Card, Crimson Red, Samurai Gold, Blood Red, White, Silver Gray)
        ACCENT = "#C1121F"
        ACCENT_HOVER = "#E63946"
        ACCENT_TEXT = "#F8F8F8"
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, [ACCENT_TEXT, ACCENT_TEXT])
        
        update_list(APP_BG, ["#090909", "#090909"])
        update_list(SIDEBAR_BG, ["#1A1A1D", "#1A1A1D"])
        update_list(SURFACE, ["#23252B", "#23252B"])
        update_list(SURFACE_ALT, ["#1A1A1D", "#1A1A1D"])
        update_list(SURFACE_HOVER, ["#2D3038", "#2D3038"])
        update_list(CONTROL_BG, ["#23252B", "#23252B"])
        update_list(CONTROL_HOVER, ["#2D3038", "#2D3038"])
        update_list(SECONDARY_BUTTON, ["#D4AF37", "#D4AF37"])
        update_list(SECONDARY_HOVER, ["#B8962D", "#B8962D"])
        update_list(BORDER, ["#2D2D2D", "#2D2D2D"])
        update_list(BORDER_DARK, ["#1A1A1D", "#1A1A1D"])
        update_list(CARD_BORDER, ["#D4AF37", "#D4AF37"])
        
        update_list(TEXT_PRIMARY, ["#F8F8F8", "#F8F8F8"])
        update_list(TEXT_SECONDARY, ["#B8BCC5", "#B8BCC5"])
        update_list(TEXT_MUTED, ["#B8BCC5", "#B8BCC5"])
        update_list(TEXT_DISABLED, ["#4B5563", "#4B5563"])
        update_list(SUCCESS_COLOR, ["#C1121F", "#C1121F"])
        update_list(HIGHLIGHT_COLOR, ["#E63946", "#E63946"])
    else:
        # Default green theme colors
        ACCENT = "#2ECC71"
        ACCENT_HOVER = "#27AE60"
        ACCENT_TEXT = "#121212"
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, [ACCENT_TEXT, ACCENT_TEXT])
        
        update_list(APP_BG, ["#F4F7F3", "#181818"])
        update_list(SIDEBAR_BG, ["#E9EFE7", "#121212"])
        update_list(SURFACE, ["#FFFFFF", "#1A1A1A"])
        update_list(SURFACE_ALT, ["#F7FAF6", "#141414"])
        update_list(SURFACE_HOVER, ["#E7EEE5", "#1E1E1E"])
        update_list(CONTROL_BG, ["#F8FBF7", "#101010"])
        update_list(CONTROL_HOVER, ["#E3EBE1", "#222222"])
        update_list(SECONDARY_BUTTON, ["#E0E8DD", "#2C2C2C"])
        update_list(SECONDARY_HOVER, ["#D2DDCF", "#3A3A3A"])
        update_list(BORDER, ["#D6E0D3", "#2A2A2A"])
        update_list(BORDER_DARK, ["#CAD6C7", "#222222"])
        update_list(CARD_BORDER, ["#CAD6C7", "#2C2C2C"])
        
        update_list(TEXT_PRIMARY, ["#000000", "#2ECC71"])
        update_list(TEXT_SECONDARY, ["#000000", "#2ECC71"])
        update_list(TEXT_MUTED, ["#000000", "#2ECC71"])
        update_list(TEXT_DISABLED, ["#333333", "#1F9F56"])
        update_list(SUCCESS_COLOR, ["#2ECC71", "#2ECC71"])
        update_list(HIGHLIGHT_COLOR, ["#A5D6A7", "#2ECC71"])

    # Update other modules in the ui package that imported ACCENT, ACCENT_HOVER, or ACCENT_TEXT directly
    import sys
    for mod_name, mod in list(sys.modules.items()):
        if mod and mod_name.startswith("ui."):
            if hasattr(mod, "ACCENT") and mod_name != "ui.theme":
                try:
                    mod.ACCENT = ACCENT
                except Exception:
                    pass
            if hasattr(mod, "ACCENT_HOVER") and mod_name != "ui.theme":
                try:
                    mod.ACCENT_HOVER = ACCENT_HOVER
                except Exception:
                    pass
            if hasattr(mod, "ACCENT_TEXT") and mod_name != "ui.theme":
                try:
                    mod.ACCENT_TEXT = ACCENT_TEXT
                except Exception:
                    pass

# Monkeypatch CTkFont to dynamically switch family to "Chewy" if current theme is unicorn
original_init = ctk.CTkFont.__init__
def new_init(self, *args, **kwargs):
    if CURRENT_THEME == "unicorn":
        kwargs["family"] = "Chewy"
    elif CURRENT_THEME == "onyx":
        kwargs["family"] = "Space Grotesk"
    elif CURRENT_THEME == "kitty":
        kwargs["family"] = "Fredoka"
    elif CURRENT_THEME == "eclipsex":
        kwargs["family"] = "Oxanium"
    elif CURRENT_THEME == "matrix":
        kwargs["family"] = "Exo 2"
        kwargs["weight"] = "bold"
    elif CURRENT_THEME == "shougun":
        kwargs["family"] = "Cinzel"
        kwargs["weight"] = "bold"
    original_init(self, *args, **kwargs)
ctk.CTkFont.__init__ = new_init

original_configure = ctk.CTkFont.configure
def new_configure(self, *args, **kwargs):
    if CURRENT_THEME == "unicorn" and "family" in kwargs:
        kwargs["family"] = "Chewy"
    elif CURRENT_THEME == "onyx" and "family" in kwargs:
        kwargs["family"] = "Space Grotesk"
    elif CURRENT_THEME == "kitty" and "family" in kwargs:
        kwargs["family"] = "Fredoka"
    elif CURRENT_THEME == "eclipsex" and "family" in kwargs:
        kwargs["family"] = "Oxanium"
    elif CURRENT_THEME == "matrix" and "family" in kwargs:
        kwargs["family"] = "Exo 2"
    elif CURRENT_THEME == "shougun" and "family" in kwargs:
        kwargs["family"] = "Cinzel"
    return original_configure(self, *args, **kwargs)
ctk.CTkFont.configure = new_configure

def normalize_structural_colors(widget):
    for option in STRUCTURAL_OPTIONS + TEXT_OPTIONS:
        try:
            value = widget.cget(option)
        except Exception:
            continue

        if isinstance(value, str):
            if option in TEXT_OPTIONS:
                mapped = TEXT_COLOR_MAP.get(value.upper())
            else:
                mapped = STRUCTURAL_COLOR_MAP.get(value.upper())
            if mapped:
                try:
                    widget.configure(**{option: mapped})
                except Exception:
                    pass

    # Apply dynamic highlights to Entry, Textbox, ComboBox, and Progressbar widgets
    class_name = widget.__class__.__name__.lower()
    if "entry" in class_name or "textbox" in class_name or "combobox" in class_name:
        try:
            widget.configure(select_color=HIGHLIGHT_COLOR, insert_color=SUCCESS_COLOR)
        except Exception:
            pass
    elif "progressbar" in class_name:
        try:
            widget.configure(progress_color=SUCCESS_COLOR)
        except Exception:
            pass

    try:
        children = widget.winfo_children()
    except Exception:
        return

    for child in children:
        normalize_structural_colors(child)

def get_asset_path(relative_path):
    import os
    import sys
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

