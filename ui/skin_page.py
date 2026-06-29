import io
import json
import os
import re
import threading

import customtkinter as ctk
import requests
from PIL import Image
import ui.custom_dialog as messagebox

from ui.theme import (
    ACCENT, ACCENT_HOVER, ACCENT_TEXT, BORDER, CARD_BORDER, CONTROL_BG,
    CONTROL_HOVER, SECONDARY_BUTTON, SECONDARY_HOVER, SURFACE, SURFACE_ALT,
    TEXT_PRIMARY, normalize_structural_colors
)


class SkinPage(ctk.CTkFrame):
    def __init__(self, parent, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.config_manager = config_manager
        self.toplevel = self.winfo_toplevel()
        self.current_sort = "best"
        self.current_page = 1
        self.loading = False
        self.equipped_skin_id = self.get_equipped_skin_id()
        self.skin_images = []
        self.skin_cache_dir = os.path.join(self.config_manager.get_minecraft_folder(), "skin_cache")
        os.makedirs(self.skin_cache_dir, exist_ok=True)
        self.setup_ui()
        self.load_profile_skin()
        self.load_catalog(reset=True)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        title_label = ctk.CTkLabel(
            self,
            text="Skin",
            font=ctk.CTkFont(family="Orbitron", size=22, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.profile_card = ctk.CTkFrame(self, fg_color=SURFACE, border_width=1, border_color=BORDER)
        self.profile_card.grid(row=1, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.profile_card.grid_columnconfigure(1, weight=1)

        self.profile_preview = ctk.CTkLabel(self.profile_card, text="Loading...", width=96, height=160)
        self.profile_preview.grid(row=0, column=0, padx=15, pady=15, sticky="w")

        username = self.config_manager.get("username", "AlienPlayer")
        account_type = self.config_manager.get("account_type", "Offline")
        profile_info = ctk.CTkFrame(self.profile_card, fg_color="transparent")
        profile_info.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="ew")

        ctk.CTkLabel(
            profile_info,
            text=f"Your skin: {username} ({account_type})",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        self.profile_status = ctk.CTkLabel(
            profile_info,
            text="Loading your current skin...",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_PRIMARY
        )
        self.profile_status.pack(anchor="w", pady=(5, 0))

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        controls.grid_columnconfigure(0, weight=1)

        self.sort_selector = ctk.CTkSegmentedButton(
            controls,
            values=["Best", "New"],
            command=self.on_sort_changed,
            fg_color=CONTROL_BG,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=CONTROL_BG,
            text_color=TEXT_PRIMARY
        )
        self.sort_selector.set("Best")
        self.sort_selector.grid(row=0, column=0, sticky="w")

        self.refresh_btn = ctk.CTkButton(
            controls,
            text="Refresh",
            width=110,
            fg_color=SECONDARY_BUTTON,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT_PRIMARY,
            command=lambda: self.load_catalog(reset=True)
        )
        self.refresh_btn.grid(row=0, column=1, padx=(10, 0), sticky="e")

        self.gallery = ctk.CTkScrollableFrame(self, fg_color=SURFACE_ALT, border_width=1, border_color=CARD_BORDER)
        self.gallery.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="nsew")
        for col in range(4):
            self.gallery.grid_columnconfigure(col, weight=1, uniform="skins")

        self.load_more_btn = ctk.CTkButton(
            self,
            text="Load More Skins",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=ACCENT_TEXT,
            command=lambda: self.load_catalog(reset=False)
        )
        self.load_more_btn.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")

        normalize_structural_colors(self)

    def on_sort_changed(self, value):
        self.current_sort = "time" if value == "New" else "best"
        self.load_catalog(reset=True)

    def load_profile_skin(self):
        username = self.config_manager.get("username", "AlienPlayer")
        equipped = self.config_manager.get("equipped_skin", {})
        equipped_url = equipped.get("skin_url") if isinstance(equipped, dict) else None

        def _thread():
            urls = []
            if equipped_url:
                urls.append(equipped_url)
            
            # If account is Ely.by, try to fetch their Ely.by skin as a fallback
            account_type = self.config_manager.get("account_type", "Offline")
            if account_type == "Ely.by":
                urls.append(f"https://ely.by/services/skins/{username}.png")

            urls.extend([
                f"https://minotar.net/skin/{username}",
                f"https://minecraft.tools/download-skin/{username}"
            ])
            for url in urls:
                try:
                    res = requests.get(url, headers={"User-Agent": "Alien Launcher"}, timeout=12)
                    if res.status_code == 200 and res.content:
                        img = Image.open(io.BytesIO(res.content)).convert("RGBA")
                        if img.width >= 64 and img.height >= 32:
                            preview = self.render_skin_front(img, scale=5)
                            status_text = "Showing your equipped skin." if (equipped_url and url == equipped_url) else "Showing your current username skin."
                            self.run_in_gui(self.set_profile_preview, preview, status_text)
                            return
                except Exception:
                    pass

            self.run_in_gui(self.profile_status.configure, text="Could not load your current skin preview.")

        threading.Thread(target=_thread, daemon=True).start()

    def set_profile_preview(self, pil_img, status):
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        self.skin_images.append(ctk_img)
        self.profile_preview.configure(image=ctk_img, text="")
        self.profile_status.configure(text=status)

    def load_catalog(self, reset=False):
        if self.loading:
            return
        self.loading = True
        if reset:
            self.current_page = 1
            for widget in self.gallery.winfo_children():
                widget.destroy()
            self.skin_images.clear()

        self.load_more_btn.configure(state="disabled", text="Loading Ely.by skins...")

        def _thread():
            try:
                skins, last_page = self.fetch_ely_skins(self.current_page, self.current_sort)
                self.run_in_gui(self.display_skins, skins, last_page)
            except Exception as e:
                self.run_in_gui(self.show_error, str(e))

        threading.Thread(target=_thread, daemon=True).start()

    def fetch_ely_skins(self, page, sort):
        params = {}
        if sort == "time":
            params["sort"] = "time"
        if page > 1:
            params["skinsPage"] = str(page)

        res = requests.get(
            "https://ely.by/skins",
            params=params,
            headers={"User-Agent": "Alien Launcher"},
            timeout=20
        )
        res.raise_for_status()
        html = res.text
        match = re.search(r"alight\.service\.skins\s*=\s*(\{.*?\})\s*</script>", html, re.S)
        if not match:
            raise ValueError("Could not find Ely.by skins data.")

        data = json.loads(match.group(1))
        return data.get("items", []), int(data.get("last", page))

    def display_skins(self, skins, last_page):
        try:
            if not self.winfo_exists() or not self.gallery.winfo_exists():
                return
        except Exception:
            return

        start_index = len(self.gallery.winfo_children())
        if not skins and start_index == 0:
            ctk.CTkLabel(
                self.gallery,
                text="No Ely.by skins found.",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT_PRIMARY
            ).grid(row=0, column=0, padx=15, pady=30)

        for idx, skin in enumerate(skins, start=start_index):
            self.add_skin_card(skin, idx)

        self.current_page += 1
        self.loading = False
        if self.current_page <= last_page:
            self.load_more_btn.configure(state="normal", text="Load More Skins")
        else:
            self.load_more_btn.configure(state="disabled", text="No More Skins")

    def show_error(self, message):
        self.loading = False
        try:
            if not self.winfo_exists() or not self.gallery.winfo_exists():
                return
            self.load_more_btn.configure(state="normal", text="Retry")
            
            friendly_message = message
            if "Max retries exceeded" in message or "ConnectionPool" in message or "getaddrinfo failed" in message:
                friendly_message = "Connection to Ely.by failed. Please check your internet connection and try again."
                
            ctk.CTkLabel(
                self.gallery,
                text=f"Error loading skins: {friendly_message}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=TEXT_PRIMARY,
                wraplength=600,
                justify="left"
            ).grid(row=0, column=0, padx=15, pady=30, sticky="nw")
        except Exception:
            pass

    def add_skin_card(self, skin, index):
        row = index // 4
        col = index % 4
        card = ctk.CTkFrame(self.gallery, fg_color=SURFACE, border_width=1, border_color=CARD_BORDER, corner_radius=6)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        preview = ctk.CTkLabel(card, text="Loading...", width=120, height=180)
        preview.grid(row=0, column=0, padx=10, pady=(10, 5))

        tags = skin.get("tags") or []
        title = ", ".join(tags[:2]) if tags else f"Skin #{skin.get('id', '?')}"
        if len(title) > 24:
            title = title[:21] + "..."
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=1, column=0, padx=10, pady=(0, 3), sticky="w")

        stats = f"Views {self.short_number(skin.get('count_views_total', 0))} | Worn {self.short_number(skin.get('count_wearers', 0))}"
        ctk.CTkLabel(
            card,
            text=stats,
            font=ctk.CTkFont(size=10),
            text_color=TEXT_PRIMARY
        ).grid(row=2, column=0, padx=10, pady=(0, 8), sticky="w")

        is_equipped = self.equipped_skin_id == skin.get("id")
        equip_btn = ctk.CTkButton(
            card,
            text="Equipped" if is_equipped else "Equip Skin",
            height=28,
            fg_color=ACCENT if is_equipped else SECONDARY_BUTTON,
            hover_color=ACCENT_HOVER if is_equipped else SECONDARY_HOVER,
            text_color=ACCENT_TEXT if is_equipped else TEXT_PRIMARY,
            command=lambda s=skin: self.equip_skin(s)
        )
        equip_btn.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.load_skin_preview_async(skin.get("skin_url"), preview)

    def get_equipped_skin_id(self):
        equipped = self.config_manager.get("equipped_skin", {})
        if isinstance(equipped, dict):
            return equipped.get("id")
        return None

    def equip_skin(self, skin):
        account_type = self.config_manager.get("account_type", "Offline")
        ely_data = self.config_manager.get("elyby_data", {})
        token = ely_data.get("access_token") if isinstance(ely_data, dict) else None

        if account_type != "Ely.by" or not token:
            messagebox.showerror("Ely.by Required", "Log in with Ely.by first before equipping Ely.by skins.")
            return

        skin_id = skin.get("id")
        if not skin_id:
            messagebox.showerror("Skin Error", "This skin does not have a valid Ely.by skin ID.")
            return

        if not messagebox.askyesno(
            "Equip Skin",
            "To equip this skin, the launcher will open the Ely.by skin page in your web browser.\n\n"
            "Once the page loads, make sure you are logged in on the website, then click the checkmark icon to apply it.\n\n"
            "Would you like to proceed?"
        ):
            return

        import webbrowser
        webbrowser.open(f"https://ely.by/skins/s{skin_id}")
        self.finish_equip_skin(True, "", skin)

    def post_equip_skin(self, skin_id, token):
        res = requests.post(
            "https://ely.by/skins/wear",
            data={"skinId": skin_id},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Alien Launcher"
            },
            timeout=20
        )

        content_type = res.headers.get("content-type", "")
        if "text/html" in content_type:
            return False, "Ely.by rejected the launcher request. Open Ely.by in a browser and log in if this keeps happening."

        if res.status_code not in (200, 204):
            return False, f"Ely.by returned HTTP {res.status_code}."

        if res.text.strip():
            try:
                payload = res.json()
                error = str(payload.get("error", ""))
                text = str(payload.get("text", ""))
                if error and "success" not in error.lower():
                    msg = text or error
                    # Strip HTML tags
                    msg = re.sub(r'<[^>]+>', '', msg)
                    import html
                    msg = html.unescape(msg)
                    return False, msg.strip()
            except Exception:
                pass

        return True, "Skin equipped."

    def finish_equip_skin(self, success, message, skin):
        self.load_more_btn.configure(state="normal", text="Load More Skins")
        if not success:
            messagebox.showerror("Equip Failed", message)
            return

        self.equipped_skin_id = skin.get("id")
        self.config_manager.set("equipped_skin", {
            "id": skin.get("id"),
            "skin_url": skin.get("skin_url"),
            "is_slim": skin.get("is_slim", False)
        })

        try:
            if skin.get("skin_url"):
                threading.Thread(
                    target=lambda: self.load_equipped_profile_preview(skin.get("skin_url")),
                    daemon=True
                ).start()
        except Exception:
            pass

        messagebox.showinfo("Skin Equipped", "Skin equipped. Restart Minecraft if it is already running.")
        self.load_catalog(reset=True)

    def load_equipped_profile_preview(self, skin_url):
        res = requests.get(skin_url, headers={"User-Agent": "Alien Launcher"}, timeout=15)
        res.raise_for_status()
        texture = Image.open(io.BytesIO(res.content)).convert("RGBA")
        preview = self.render_skin_front(texture, scale=5)
        self.run_in_gui(self.set_profile_preview, preview, "Showing the skin you equipped from Ely.by.")

    def load_skin_preview_async(self, skin_url, label):
        if not skin_url:
            try:
                if label.winfo_exists():
                    label.configure(text="No preview")
            except Exception:
                pass
            return

        def _thread():
            try:
                res = requests.get(skin_url, headers={"User-Agent": "Alien Launcher"}, timeout=15)
                res.raise_for_status()
                texture = Image.open(io.BytesIO(res.content)).convert("RGBA")
                preview = self.render_skin_front(texture, scale=5)
                self.run_in_gui(self.set_skin_label_image, label, preview)
            except Exception:
                self.run_in_gui(self.set_skin_label_text, label, "Preview failed")

        threading.Thread(target=_thread, daemon=True).start()

    def set_skin_label_text(self, label, text):
        try:
            if label.winfo_exists():
                label.configure(text=text)
        except Exception:
            pass

    def set_skin_label_image(self, label, pil_img):
        try:
            if label.winfo_exists():
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                self.skin_images.append(ctk_img)
                label.configure(image=ctk_img, text="")
        except Exception:
            pass

    def render_skin_front(self, skin, scale=5):
        if skin.size[0] < 64:
            skin = skin.resize((64, max(32, skin.size[1])), Image.Resampling.NEAREST)

        canvas = Image.new("RGBA", (16, 32), (0, 0, 0, 0))

        def paste(src_box, dest):
            part = skin.crop(src_box)
            canvas.alpha_composite(part, dest)

        slim = False
        if skin.height >= 64:
            arm_alpha = skin.crop((54, 20, 56, 32)).getchannel("A").getbbox()
            slim = arm_alpha is None

        arm_w = 3 if slim else 4
        left_x = 12 if not slim else 13

        paste((8, 8, 16, 16), (4, 0))
        paste((20, 20, 28, 32), (4, 8))
        paste((44, 20, 44 + arm_w, 32), (0, 8))
        paste((4, 20, 8, 32), (4, 20))

        if skin.height >= 64:
            paste((40, 8, 48, 16), (4, 0))
            paste((20, 36, 28, 48), (4, 8))
            paste((36, 52, 36 + arm_w, 64), (left_x, 8))
            paste((20, 52, 24, 64), (8, 20))
        else:
            left_arm = skin.crop((44, 20, 44 + arm_w, 32)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            canvas.alpha_composite(left_arm, (left_x, 8))
            left_leg = skin.crop((4, 20, 8, 32)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            canvas.alpha_composite(left_leg, (8, 20))

        return canvas.resize((16 * scale, 32 * scale), Image.Resampling.NEAREST)

    def short_number(self, value):
        try:
            value = int(value)
        except Exception:
            return "0"
        if value >= 1000000:
            return f"{value / 1000000:.1f}m"
        if value >= 1000:
            return f"{value / 1000:.1f}k"
        return str(value)

    def run_in_gui(self, func, *args, **kwargs):
        toplevel = getattr(self, "toplevel", None)
        if toplevel and hasattr(toplevel, "run_in_gui_thread"):
            toplevel.run_in_gui_thread(func, *args, **kwargs)
        else:
            self.after(0, lambda: func(*args, **kwargs))

    def refresh(self):
        self.load_profile_skin()
        self.load_catalog(reset=True)
