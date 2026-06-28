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

def set_theme(theme_name):
    global ACCENT, ACCENT_HOVER, ACCENT_TEXT
    theme_name = theme_name.lower()
    
    if theme_name == "unicorn":
        # Unicorn theme colors (pastels, pinks, purples)
        ACCENT = "#FF66CC"
        ACCENT_HOVER = "#FF3399"
        ACCENT_TEXT = "#000000" # Black in light mode
        
        update_list(ACCENT_COLOR, [ACCENT, ACCENT])
        update_list(ACCENT_HOVER_COLOR, [ACCENT_HOVER, ACCENT_HOVER])
        update_list(ACCENT_TEXT_COLOR, ["#000000", "#1B0B22"]) # Black in light, dark purple/black in dark
        
        update_list(APP_BG, ["#FFF0F8", "#24142C"])
        update_list(SIDEBAR_BG, ["#FFE4F2", "#1B0B22"])
        update_list(SURFACE, ["#FFFFFF", "#2F1A3B"])
        update_list(SURFACE_ALT, ["#FFF5FA", "#271432"])
        update_list(SURFACE_HOVER, ["#FFE4F2", "#3D224C"])
        update_list(CONTROL_BG, ["#FFF8FC", "#1F0E28"])
        update_list(CONTROL_HOVER, ["#FFD6EB", "#351A44"])
        update_list(SECONDARY_BUTTON, ["#FFD6EB", "#3F224E"])
        update_list(SECONDARY_HOVER, ["#FFAEDC", "#532E66"])
        update_list(BORDER, ["#FFC2E3", "#4D235D"])
        update_list(BORDER_DARK, ["#FFA6D8", "#3F1B4E"])
        update_list(CARD_BORDER, ["#FFC2E3", "#4D235D"])
        
        update_list(TEXT_PRIMARY, ["#000000", "#FF66CC"]) # Black in light mode, pink in dark mode
        update_list(TEXT_SECONDARY, ["#000000", "#FF8AD8"]) # Black in light mode, pink in dark mode
        update_list(TEXT_MUTED, ["#000000", "#FFA6D5"]) # Black in light mode, pink in dark mode
        update_list(TEXT_DISABLED, ["#333333", "#A84C8F"])
        update_list(SUCCESS_COLOR, ["#000000", "#FF66CC"]) # Black in light mode, pink in dark mode
        update_list(HIGHLIGHT_COLOR, ["#FFC2E3", "#FF66CC"]) # Light pink in light mode, bright pink in dark mode
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
