import os
import threading
import io
import urllib.request
import requests
import customtkinter as ctk
from PIL import Image
import ui.custom_dialog as messagebox

class ModsPage(ctk.CTkFrame):
    MODRINTH_CONTENT_TYPES = {
        "Mods": "mod",
        "Resource Packs": "resourcepack",
        "Data Packs": "datapack",
        "Shaders": "shader",
        "Modpacks": "modpack"
    }

    CURSEFORGE_CONTENT_TYPES = {
        "Mods": "mod",
        "Bukkit Plugins": "bukkit_plugin",
        "Worlds": "world",
        "Resource Packs": "resourcepack",
        "Customization": "customization",
        "Data Packs": "datapack",
        "Addons": "addon",
        "Modpacks": "modpack",
        "Shaders": "shader"
    }

    CURSEFORGE_CLASS_IDS = {
        "mod": 6,
        "bukkit_plugin": 5,
        "world": 17,
        "resourcepack": 12,
        "customization": 4546,
        "datapack": 6945,
        "addon": 4559,
        "modpack": 4471,
        "shader": 6552
    }

    CONTENT_LABELS = {
        "mod": "Mods",
        "bukkit_plugin": "Bukkit Plugins",
        "world": "Worlds",
        "resourcepack": "Resource Packs",
        "customization": "Customization",
        "datapack": "Data Packs",
        "addon": "Addons",
        "modpack": "Modpacks",
        "shader": "Shaders"
    }

    def __init__(self, parent, mods_manager, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.mods_manager = mods_manager
        self.config_manager = config_manager
        self.toplevel = self.winfo_toplevel()
        
        self.current_offset = 0
        self.limit = 10
        self.selected_files = {} # Track checkboxes: mapping filename -> (BooleanVar, project_type, project_id)
        
        self.setup_ui()
        # Load popular mods on open
        self.perform_search("")

    def run_in_gui(self, func, *args, **kwargs):
        toplevel = getattr(self, "toplevel", None)
        if toplevel and hasattr(toplevel, "run_in_gui_thread"):
            toplevel.run_in_gui_thread(func, *args, **kwargs)
        else:
            self.after(0, lambda: func(*args, **kwargs))

    def setup_ui(self):
        # Grid layout
        self.grid_columnconfigure(0, weight=3) # Search side gets more weight
        self.grid_columnconfigure(1, weight=2) # Downloaded side
        self.grid_rowconfigure(3, weight=1) # Scrollable frames on row 3
        self.grid_rowconfigure(4, weight=0) # Pagination on row 4

        # Header
        title_label = ctk.CTkLabel(
            self,
            text="Modrinth Downloader",
            font=ctk.CTkFont(family="Orbitron", size=22, weight="bold"),
            text_color="#2ECC71"
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="w")

        desc_label = ctk.CTkLabel(
            self,
            text="Browse and install mods, resource packs, data packs, shaders, and modpacks from Modrinth.",
            font=ctk.CTkFont(family="Orbitron", size=11),
            text_color="#888888"
        )
        desc_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")

        # Search Bar Frame (Left Column)
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=2, column=0, padx=(20, 10), pady=(0, 10), sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        # Source Switcher (Segmented Button)
        self.source_var = ctk.StringVar(value="Modrinth")
        self.source_selector = ctk.CTkSegmentedButton(
            search_frame,
            values=["Modrinth", "CurseForge"],
            variable=self.source_var,
            command=self.on_source_changed,
            fg_color="#101010",
            selected_color="#2ECC71",
            selected_hover_color="#27AE60"
        )
        self.source_selector.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.content_type_var = ctk.StringVar(value="Mods")
        self.content_type_selector = ctk.CTkSegmentedButton(
            search_frame,
            values=list(self.MODRINTH_CONTENT_TYPES.keys()),
            variable=self.content_type_var,
            command=self.on_content_type_changed,
            fg_color="#101010",
            selected_color="#2ECC71",
            selected_hover_color="#27AE60"
        )
        self.content_type_selector.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Search text field
        self.search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Search mods (e.g. Fabric API, Sodium, JEI)...",
            fg_color="#101010", 
            border_color="#2C2C2C",
            height=36
        )
        self.search_entry.grid(row=2, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda event: self.start_search_thread(reset_offset=True))

        btn_search = ctk.CTkButton(
            search_frame, 
            text="Search", 
            width=80, 
            height=36,
            fg_color="#2ECC71", 
            hover_color="#27AE60", 
            text_color="#121212",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.start_search_thread(reset_offset=True)
        )
        btn_search.grid(row=2, column=1)

        # Results Scrollable Frame
        self.results_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="#141414", 
            border_width=1, 
            border_color="#222222"
        )
        self.results_frame.grid(row=3, column=0, padx=(20, 10), pady=(0, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)

        # Pagination Control Panel
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.grid(row=4, column=0, padx=(20, 10), pady=(0, 15), sticky="ew")
        
        self.btn_prev = ctk.CTkButton(
            self.pagination_frame,
            text="< Previous",
            width=100,
            height=30,
            fg_color="#1A1A1A",
            hover_color="#2A2A2A",
            text_color="#CCCCCC",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.prev_page,
            state="disabled"
        )
        self.btn_prev.pack(side="left")
        
        self.lbl_page = ctk.CTkLabel(
            self.pagination_frame,
            text="Page 1",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#888888"
        )
        self.lbl_page.pack(side="left", fill="x", expand=True)
        
        self.btn_next = ctk.CTkButton(
            self.pagination_frame,
            text="Next >",
            width=100,
            height=30,
            fg_color="#1A1A1A",
            hover_color="#2A2A2A",
            text_color="#CCCCCC",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.next_page,
            state="disabled"
        )
        self.btn_next.pack(side="right")

        # Right Column: Downloaded Mods Header Frame
        downloaded_header_frame = ctk.CTkFrame(self, fg_color="transparent")
        downloaded_header_frame.grid(row=2, column=1, padx=(10, 20), pady=(0, 10), sticky="ew")
        
        self.lbl_downloaded_title = ctk.CTkLabel(
            downloaded_header_frame,
            text="Downloaded Mods",
            font=ctk.CTkFont(family="Orbitron", size=14, weight="bold"),
            text_color="#2ECC71"
        )
        self.lbl_downloaded_title.pack(side="left", anchor="w")
        
        btn_refresh_downloads = ctk.CTkButton(
            downloaded_header_frame,
            text="🔄",
            width=30,
            height=24,
            fg_color="#1A1A1A",
            hover_color="#2A2A2A",
            text_color="#CCCCCC",
            font=ctk.CTkFont(size=11),
            command=self.refresh_installed_mods
        )
        btn_refresh_downloads.pack(side="right", padx=(10, 0))

        btn_delete_selected = ctk.CTkButton(
            downloaded_header_frame,
            text="🗑️ Delete Selected",
            width=120,
            height=24,
            fg_color="#E74C3C",
            hover_color="#C0392B",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.delete_selected_files
        )
        btn_delete_selected.pack(side="right", padx=(10, 0))

        self.btn_update_mods = ctk.CTkButton(
            downloaded_header_frame,
            text="🚀 Update Mods",
            width=110,
            height=24,
            fg_color="#2ECC71",
            hover_color="#27AE60",
            text_color="#121212",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.trigger_one_click_updater
        )
        self.btn_update_mods.pack(side="right", padx=(10, 0))

        # Downloaded Mods Scrollable Frame
        self.downloaded_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="#141414", 
            border_width=1, 
            border_color="#222222"
        )
        self.downloaded_frame.grid(row=3, column=1, rowspan=2, padx=(10, 20), pady=(0, 15), sticky="nsew")
        self.downloaded_frame.grid_columnconfigure(0, weight=1)

        # Initial refresh
        self.refresh_installed_mods()

    def on_source_changed(self, value):
        if value == "CurseForge":
            self.search_entry.configure(placeholder_text="Search CurseForge mods...")
            self.content_type_selector.configure(values=list(self.CURSEFORGE_CONTENT_TYPES.keys()))
            self.content_type_var.set("Mods")
        else:
            self.content_type_selector.configure(values=list(self.MODRINTH_CONTENT_TYPES.keys()))
            self.content_type_var.set("Mods")
        self.update_content_placeholder()
        self.refresh_installed_mods()
        self.start_search_thread(reset_offset=True)

    def on_content_type_changed(self, value):
        self.update_content_placeholder()
        self.refresh_installed_mods()
        self.start_search_thread(reset_offset=True)

    def get_selected_project_type(self):
        source = self.source_var.get()
        category = self.content_type_var.get()
        if source == "CurseForge":
            return self.CURSEFORGE_CONTENT_TYPES.get(category, "mod")
        return self.MODRINTH_CONTENT_TYPES.get(category, "mod")

    def get_content_label(self, project_type=None):
        project_type = project_type or self.get_selected_project_type()
        return self.CONTENT_LABELS.get(project_type, "Mods")

    def update_content_placeholder(self):
        project_type = self.get_selected_project_type()
        examples = {
            "mod": "Search mods (e.g. Fabric API, Sodium, JEI)...",
            "bukkit_plugin": "Search Bukkit plugins...",
            "world": "Search worlds/saves...",
            "resourcepack": "Search resource packs (e.g. Faithful, Fresh Animations)...",
            "customization": "Search customizations...",
            "datapack": "Search data packs (e.g. Terralith, Incendium)...",
            "addon": "Search addons...",
            "modpack": "Search modpacks (e.g. Fabulously Optimized)...",
            "shader": "Search shaders (e.g. Complementary, BSL)..."
        }
        self.search_entry.configure(placeholder_text=examples.get(project_type, examples["mod"]))

    def prev_page(self):
        self.current_offset = max(0, self.current_offset - self.limit)
        self.start_search_thread(reset_offset=False)

    def next_page(self):
        self.current_offset += self.limit
        self.start_search_thread(reset_offset=False)

    def start_search_thread(self, reset_offset=True):
        if reset_offset:
            self.current_offset = 0
            
        query = self.search_entry.get()
        # Show loading text
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        lbl_loading = ctk.CTkLabel(
            self.results_frame, 
            text=f"Searching {self.get_content_label().lower()} database...",
            font=ctk.CTkFont(size=14, slant="italic"), 
            text_color="#888888"
        )
        lbl_loading.pack(pady=40)

        # Disable pagination buttons while loading
        self.btn_prev.configure(state="disabled")
        self.btn_next.configure(state="disabled")

        threading.Thread(target=lambda: self.perform_search(query), daemon=True).start()

    def perform_search(self, query):
        source = self.source_var.get()
        project_type = self.get_selected_project_type()
        if source == "CurseForge":
            class_id = self.CURSEFORGE_CLASS_IDS.get(project_type, 6)
            success, raw_hits = self.mods_manager.search_curseforge(query, class_id=class_id, offset=self.current_offset, limit=self.limit)
            if success:
                # Map CurseForge to common Modrinth schema
                hits = []
                for cf_hit in raw_hits:
                    logo = cf_hit.get("logo") or {}
                    authors = cf_hit.get("authors", [])
                    author_name = authors[0].get("name", "Unknown") if authors else "Unknown"
                    cats = [cat.get("name", "") for cat in cf_hit.get("categories", []) if cat.get("name")]
                    
                    hits.append({
                        "project_id": f"cf_{cf_hit.get('id')}",
                        "slug": f"cf_{cf_hit.get('id')}",
                        "title": cf_hit.get("name", "Unknown Mod"),
                        "author": author_name,
                        "description": cf_hit.get("summary", "No description available."),
                        "downloads": cf_hit.get("downloadCount", 0),
                        "categories": cats,
                        "icon_url": logo.get("url", ""),
                        "project_type": project_type,
                        "is_curseforge": True,
                        "cf_raw_hit": cf_hit
                    })
                self.run_in_gui(self.display_results, True, hits)
            else:
                self.run_in_gui(self.display_results, False, raw_hits)
        else:
            success, hits = self.mods_manager.search_mods(
                query,
                offset=self.current_offset,
                limit=self.limit,
                project_type=project_type
            )
            self.run_in_gui(self.display_results, success, hits)

    def display_results(self, success, hits_or_error):
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        if not success:
            lbl_error = ctk.CTkLabel(
                self.results_frame, 
                text=f"Error: {hits_or_error}", 
                font=ctk.CTkFont(size=14, weight="bold"), 
                text_color="#E74C3C"
            )
            lbl_error.pack(pady=40)
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            self.lbl_page.configure(text="Page 1")
            return

        hits = hits_or_error
        if not hits:
            lbl_no_results = ctk.CTkLabel(
                self.results_frame, 
                text=f"No {self.get_content_label().lower()} found matching your query.",
                font=ctk.CTkFont(size=14, weight="bold"), 
                text_color="#888888"
            )
            lbl_no_results.pack(pady=40)
            
            # Reset/configure pagination controls on empty page
            if self.current_offset == 0:
                self.btn_prev.configure(state="disabled")
                self.btn_next.configure(state="disabled")
                self.lbl_page.configure(text="Page 1")
            else:
                self.btn_prev.configure(state="normal")
                self.btn_next.configure(state="disabled")
                self.lbl_page.configure(text=f"Page {(self.current_offset // self.limit) + 1}")
            return

        # Load installed mapping
        installed_map = self.config_manager.get("installed_mods", {})
        active_project_type = self.get_selected_project_type()
        cleaned_map = {}
        for pid, val in installed_map.items():
            fname = val.get("filename") if isinstance(val, dict) else val
            project_type = val.get("project_type", "mod") if isinstance(val, dict) else "mod"
            content_dir = self.mods_manager.get_content_directory(project_type)
            if fname and os.path.exists(os.path.join(content_dir, fname)):
                cleaned_map[pid] = val
        if len(cleaned_map) != len(installed_map):
            self.config_manager.set("installed_mods", cleaned_map)
            installed_map = cleaned_map

        for hit in hits:
            # Create a mod card
            card = ctk.CTkFrame(self.results_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C", corner_radius=8)
            card.pack(fill="x", pady=6, padx=5)
            card.grid_columnconfigure(1, weight=1)
            
            # Left: Icon
            icon_label = ctk.CTkLabel(card, text="📦", font=ctk.CTkFont(size=24), width=50, height=50)
            icon_label.grid(row=0, column=0, padx=15, pady=15, sticky="n")
            
            # Asynchronously load mod icon if available
            icon_url = hit.get("icon_url")
            if icon_url:
                self.load_icon_async(icon_url, icon_label)

            # Center: Info Frame
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.grid(row=0, column=1, padx=(0, 15), pady=12, sticky="nsew")
            info_frame.grid_columnconfigure(0, weight=1)

            # Title
            title_text = hit.get("title", "Unknown Mod")
            author_text = hit.get("author", "Unknown")
            title_lbl = ctk.CTkLabel(
                info_frame, 
                text=f"{title_text} by {author_text}", 
                font=ctk.CTkFont(size=15, weight="bold"), 
                text_color="#FFFFFF"
            )
            title_lbl.grid(row=0, column=0, sticky="w")

            # Description
            desc_text = hit.get("description", "No description available.")
            if len(desc_text) > 100:
                desc_text = desc_text[:97] + "..."
            desc_lbl = ctk.CTkLabel(
                info_frame, 
                text=desc_text, 
                font=ctk.CTkFont(size=12), 
                text_color="#AAAAAA",
                justify="left",
                wraplength=550
            )
            desc_lbl.grid(row=1, column=0, sticky="w", pady=(4, 4))

            # Metadata (Downloads, categories)
            downloads = hit.get("downloads", 0)
            cats = hit.get("categories", [])
            cat_str = ", ".join(cats).upper()
            meta_lbl = ctk.CTkLabel(
                info_frame, 
                text=f"Downloads: {downloads}  |  Categories: {cat_str}", 
                font=ctk.CTkFont(size=10, weight="bold"), 
                text_color="#666666"
            )
            meta_lbl.grid(row=2, column=0, sticky="w")

            # Right: Install/Uninstall Button & Progress Frame
            actions_frame = ctk.CTkFrame(card, fg_color="transparent")
            actions_frame.grid(row=0, column=2, padx=15, pady=15, sticky="e")

            btn_install = ctk.CTkButton(
                actions_frame, 
                text="Install", 
                width=100, 
                font=ctk.CTkFont(weight="bold")
            )
            btn_install.pack()

            # Progress details
            progress_bar = ctk.CTkProgressBar(actions_frame, width=100, height=4, progress_color="#2ECC71")
            progress_bar.set(0)
            
            status_lbl = ctk.CTkLabel(actions_frame, text="", font=ctk.CTkFont(size=10), text_color="#888888")

            # Bind action depending on installation status
            project_id = hit.get("project_id")
            slug = hit.get("slug")
            is_curseforge = hit.get("is_curseforge", False)
            cf_raw_hit = hit.get("cf_raw_hit")
            project_type = active_project_type if active_project_type == "datapack" else hit.get("project_type", active_project_type)
            
            saved_install = installed_map.get(project_id)
            saved_project_type = saved_install.get("project_type", "mod") if isinstance(saved_install, dict) else "mod"
            is_installed = project_id in installed_map and saved_project_type == project_type
            
            if is_installed:
                btn_install.configure(
                    text="Uninstall", 
                    fg_color="#E74C3C", 
                    hover_color="#C0392B",
                    text_color="#FFFFFF",
                    command=lambda p=project_id, b=btn_install, pb=progress_bar, sl=status_lbl, title=title_text, s=slug: self.uninstall_mod(p, b, pb, sl, title, s)
                )
            else:
                btn_install.configure(
                    text="Install", 
                    fg_color="#2C2C2C", 
                    hover_color="#3A3A3A",
                    text_color="#CCCCCC",
                    command=lambda p=project_id, s=slug, b=btn_install, pb=progress_bar, sl=status_lbl, title=title_text, isc=is_curseforge, cf=cf_raw_hit, pt=project_type, icon=icon_url: self.click_install_mod(p, s, b, pb, sl, title, isc, cf, pt, icon)
                )

        # Update pagination buttons state
        current_page_num = (self.current_offset // self.limit) + 1
        self.lbl_page.configure(text=f"Page {current_page_num}")
        
        if self.current_offset > 0:
            self.btn_prev.configure(state="normal")
        else:
            self.btn_prev.configure(state="disabled")
            
        if len(hits) == self.limit:
            self.btn_next.configure(state="normal")
        else:
            self.btn_next.configure(state="disabled")

    def load_icon_async(self, icon_url, label_widget, size=(40, 40)):
        def _thread():
            try:
                req = urllib.request.Request(
                    icon_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Alien Launcher Mod Manager)'}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    img_data = response.read()
                pil_img = Image.open(io.BytesIO(img_data))
                # Resize
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                
                def _update():
                    if label_widget.winfo_exists():
                        label_widget.configure(image=ctk_img, text="")
                self.run_in_gui(_update)
            except Exception as e:
                # Silently fail, fallback icon is already set
                pass
        threading.Thread(target=_thread, daemon=True).start()

    def click_install_mod(self, project_id, slug, button, progress_bar, status_label, mod_title, is_curseforge=False, cf_raw_hit=None, project_type="mod", icon_url=None):
        button.configure(state="disabled", text="Loading...")
        status_label.configure(text="Loading versions...")
        status_label.pack(pady=(2, 0))
        
        def _fetch_thread():
            mc_ver = self.config_manager.get("selected_version", "1.20.1")
            loader_type = self.config_manager.get("loader_type", "Vanilla")
            
            files_list = []
            
            if is_curseforge:
                # CurseForge
                latest_files = cf_raw_hit.get("latestFiles", []) if cf_raw_hit else []
                for f in latest_files:
                    raw_gvs = f.get("gameVersions", [])
                    
                    loaders = []
                    game_versions = []
                    for gv in raw_gvs:
                        if gv.lower() in ["fabric", "forge", "neoforge", "quilt", "liteloader", "optifine"]:
                            loaders.append(gv.capitalize())
                        else:
                            game_versions.append(gv)
                            
                    files_list.append({
                        "id": f.get("id"),
                        "name": f.get("displayName") or f.get("fileName"),
                        "game_versions": game_versions,
                        "loaders": loaders,
                        "download_url": f.get("downloadUrl"),
                        "filename": f.get("fileName"),
                        "mod_id": cf_raw_hit.get("id") if cf_raw_hit else None,
                        "project_type": "mod"
                    })
            else:
                # Modrinth
                versions = self.mods_manager.get_project_versions(project_id) or []
                for v in versions:
                    files = v.get("files", [])
                    if not files:
                        continue
                    primary_file = None
                    for f in files:
                        if f.get("primary", False):
                            primary_file = f
                            break
                    if not primary_file:
                        primary_file = files[0]
                        
                    files_list.append({
                        "id": v.get("id"),
                        "name": v.get("name") or v.get("version_number"),
                        "game_versions": v.get("game_versions", []),
                        "loaders": [l.capitalize() for l in v.get("loaders", [])],
                        "download_url": primary_file.get("url"),
                        "filename": primary_file.get("filename"),
                        "project_type": project_type
                    })
            
            if not files_list:
                self.run_in_gui(button.configure, text="Install", state="normal")
                self.run_in_gui(status_label.configure, text="No files found.")
                return
                
            self.run_in_gui(button.configure, text="Install", state="normal")
            self.run_in_gui(status_label.pack_forget)
            self.run_in_gui(self.show_mod_versions_dialog, project_id, slug, button, progress_bar, status_label, mod_title, files_list, is_curseforge, project_type, icon_url)

        threading.Thread(target=_fetch_thread, daemon=True).start()

    def show_mod_versions_dialog(self, project_id, slug, button, progress_bar, status_label, mod_title, files_list, is_curseforge, project_type="mod", icon_url=None):
        dialog_attr = f"mod_dialog_{project_id}"
        if hasattr(self, dialog_attr):
            old_dialog = getattr(self, dialog_attr)
            if old_dialog.winfo_exists():
                old_dialog.focus()
                return

        dialog = ctk.CTkToplevel(self)
        setattr(self, dialog_attr, dialog)
        
        dialog.title(f"Install {mod_title}")
        dialog.geometry("520x450")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        x = self.winfo_x() + (self.winfo_width() // 2) - 260
        y = self.winfo_y() + (self.winfo_height() // 2) - 225
        dialog.geometry(f"+{x}+{y}")

        header_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        lbl_title = ctk.CTkLabel(
            header_frame, 
            text=mod_title, 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color="#2ECC71"
        )
        lbl_title.pack(anchor="w")
        
        mc_ver = self.config_manager.get("selected_version", "1.20.1")
        loader_type = self.config_manager.get("loader_type", "Vanilla")
        
        lbl_config = ctk.CTkLabel(
            header_frame,
            text=f"Your profile: Minecraft {mc_ver} ({loader_type})",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#888888"
        )
        lbl_config.pack(anchor="w", pady=(2, 0))

        lbl_help = ctk.CTkLabel(
            header_frame,
            text="Verify compatibility and choose a version to install:",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#666666"
        )
        lbl_help.pack(anchor="w", pady=(5, 0))

        scroll_frame = ctk.CTkScrollableFrame(dialog, fg_color="#141414", border_width=1, border_color="#222222")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        scroll_frame.grid_columnconfigure(0, weight=1)

        def get_compatibility_score(f):
            score = 0
            gvs = f.get("game_versions", [])
            loaders = [l.lower() for l in f.get("loaders", [])]
            mc_match = mc_ver in gvs
            loader_match = (
                project_type in ["resourcepack", "datapack"]
                or not loaders
                or loader_type.lower() in loaders
                or loader_type == "Vanilla"
            )
            if mc_match:
                score += 1
                if loader_match:
                    score += 1
            return score

        # Sort files_list by compatibility score desc, and limit to top 20 to prevent Tkinter widget creation from freezing the GUI
        sorted_files = sorted(files_list, key=get_compatibility_score, reverse=True)[:20]

        for f in sorted_files:
            gvs = f.get("game_versions", [])
            loaders = f.get("loaders", [])
            
            mc_match = mc_ver in gvs
            loader_match = (
                project_type in ["resourcepack", "datapack"]
                or not loaders
                or loader_type.lower() in [l.lower() for l in loaders]
                or loader_type == "Vanilla"
            )
            
            if mc_match and loader_match:
                status_text = "Compatible"
                status_color = "#2ECC71"
            elif mc_match:
                status_text = "Loader Mismatch"
                status_color = "#F39C12"
            else:
                status_text = "Incompatible"
                status_color = "#7F8C8D"
                
            row = ctk.CTkFrame(scroll_frame, fg_color="#1C1C1C", border_width=1, border_color="#2A2A2A", corner_radius=6)
            row.pack(fill="x", pady=4, padx=2)
            row.grid_columnconfigure(0, weight=1)
            
            info_side = ctk.CTkFrame(row, fg_color="transparent")
            info_side.grid(row=0, column=0, padx=12, pady=10, sticky="w")
            
            v_title = f.get("name")
            if len(v_title) > 36:
                v_title = v_title[:33] + "..."
            lbl_vtitle = ctk.CTkLabel(info_side, text=v_title, font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
            lbl_vtitle.pack(anchor="w")
            
            badge_text = []
            if loaders:
                badge_text.append(f"Loaders: {', '.join(loaders)}")
            if gvs:
                show_gvs = gvs[:3]
                badge_text.append(f"MC: {', '.join(show_gvs)}" + ("..." if len(gvs) > 3 else ""))
                
            lbl_badges = ctk.CTkLabel(info_side, text="  |  ".join(badge_text), font=ctk.CTkFont(size=10), text_color="#888888")
            lbl_badges.pack(anchor="w", pady=(2, 0))
            
            lbl_compat = ctk.CTkLabel(info_side, text=f"● {status_text}", font=ctk.CTkFont(size=10, weight="bold"), text_color=status_color)
            lbl_compat.pack(anchor="w", pady=(2, 0))
            
            btn_install_row = ctk.CTkButton(
                row,
                text="Install",
                width=80,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#2A2A2A" if status_text != "Compatible" else "#2ECC71",
                hover_color="#3A3A3A" if status_text != "Compatible" else "#27AE60",
                text_color="#CCCCCC" if status_text != "Compatible" else "#121212",
                command=lambda f_obj=f: self.trigger_mod_download_from_dialog(dialog, project_id, slug, button, progress_bar, status_label, mod_title, f_obj, is_curseforge, project_type, icon_url)
            )
            btn_install_row.grid(row=0, column=1, padx=12, pady=10, sticky="e")

    def trigger_mod_download_from_dialog(self, dialog, project_id, slug, button, progress_bar, status_label, mod_title, file_obj, is_curseforge, project_type="mod", icon_url=None):
        dialog.destroy()
        button.configure(state="disabled", text="Connecting...")
        
        def _download_thread():
            def _set_status(txt):
                self.run_in_gui(status_label.configure, text=txt)
                
            self.run_in_gui(progress_bar.pack, pady=(5, 0))
            self.run_in_gui(status_label.pack, pady=(2, 0))
            self.run_in_gui(button.configure, text="Downloading")

            filename = file_obj.get("filename")
            download_url = file_obj.get("download_url")

            if is_curseforge and not download_url:
                mod_id = file_obj.get("mod_id")
                file_id = file_obj.get("id")
                _set_status("Fetching download URL...")
                cf_base_url = "https://api.curseforge.com/v1"
                api_key = self.mods_manager.get_cf_api_key()
                try:
                    res = requests.get(
                        f"{cf_base_url}/mods/{mod_id}/files/{file_id}/download-url",
                        headers={"x-api-key": api_key, "Accept": "application/json"},
                        timeout=10
                    )
                    if res.status_code == 200:
                        download_url = res.json().get("data")
                except Exception as e:
                    print(f"Error fetching CF download url: {e}")
                    
            if not download_url:
                self.run_in_gui(button.configure, text="Failed", state="normal")
                _set_status("Direct download disabled")
                return

            primary_file = {
                "url": download_url,
                "filename": filename
            }

            def progress_cb(downloaded, total):
                pct = downloaded / total
                self.run_in_gui(progress_bar.set, pct)
                pct_int = int(pct * 100)
                _set_status(f"{pct_int}% downloaded")

            success, result = self.mods_manager.download_content(primary_file, project_type, progress_cb)

            if success:
                # If this is a CurseForge modpack, extract and download its dependencies
                if project_type == "modpack" and is_curseforge:
                    _set_status("Extracting modpack...")
                    zip_path = os.path.join(self.mods_manager.get_content_directory("modpack"), result)
                    
                    def cb(step, total, msg):
                        if total > 0:
                            pct = step / total
                            self.run_in_gui(progress_bar.set, pct)
                        _set_status(msg)
                        
                    pack_success, pack_msg = self.mods_manager.install_curseforge_modpack(zip_path, cb)
                    if not pack_success:
                        self.run_in_gui(button.configure, text="Retry", state="normal")
                        _set_status(f"Installation failed: {pack_msg}")
                        return

                installed_map = self.config_manager.get("installed_mods", {})
                installed_map[project_id] = {
                    "filename": result,
                    "title": mod_title,
                    "project_type": project_type,
                    "icon_url": icon_url,
                    "is_curseforge": is_curseforge
                }
                self.config_manager.set("installed_mods", installed_map)
                
                self.run_in_gui(button.configure, text="Uninstall", fg_color="#E74C3C", hover_color="#C0392B", text_color="#FFFFFF", state="normal")
                self.run_in_gui(button.configure, command=lambda: self.uninstall_mod(project_id, button, progress_bar, status_label, mod_title, slug))
                _set_status("Ready!")
                
                # Refresh installed mods list!
                self.refresh_installed_mods()
                
                def _hide():
                    if progress_bar.winfo_exists():
                        progress_bar.pack_forget()
                self.after(2000, _hide)
            else:
                self.run_in_gui(button.configure, text="Retry", state="normal")
                _set_status(f"Error: {result}")


        threading.Thread(target=_download_thread, daemon=True).start()

    def uninstall_mod(self, project_id, button, progress_bar, status_label, mod_title, slug):
        button.configure(state="disabled", text="Uninstalling...")
        status_label.configure(text="Deleting file...")
        status_label.pack(pady=(2, 0))
        
        installed_map = self.config_manager.get("installed_mods", {})
        val = installed_map.get(project_id)
        filename = val.get("filename") if isinstance(val, dict) else val
        project_type = val.get("project_type", "mod") if isinstance(val, dict) else "mod"
        icon_url = val.get("icon_url") if isinstance(val, dict) else None
        
        if filename:
            success, msg = self.mods_manager.delete_content(filename, project_type)
            if success:
                # Remove from config
                installed_map.pop(project_id, None)
                self.config_manager.set("installed_mods", installed_map)
                
                button.configure(
                    text="Install", 
                    fg_color="#2C2C2C", 
                    hover_color="#3A3A3A",
                    text_color="#CCCCCC",
                    state="normal",
                    command=lambda: self.click_install_mod(project_id, slug, button, progress_bar, status_label, mod_title, is_curseforge=slug.startswith("cf_"), cf_raw_hit=None, project_type=project_type, icon_url=icon_url)
                )
                status_label.configure(text="Uninstalled.")
                
                # Refresh installed mods list!
                self.refresh_installed_mods()
                
                # Hide progress after 2 seconds
                def _hide():
                    if status_label.winfo_exists():
                        status_label.pack_forget()
                self.after(2000, _hide)
            else:
                button.configure(text="Failed", state="normal")
                status_label.configure(text=f"Error: {msg}")
        else:
            button.configure(
                text="Install", 
                fg_color="#2C2C2C", 
                hover_color="#3A3A3A",
                text_color="#CCCCCC",
                state="normal",
                command=lambda: self.click_install_mod(project_id, slug, button, progress_bar, status_label, mod_title, is_curseforge=slug.startswith("cf_"), cf_raw_hit=None, project_type=project_type, icon_url=icon_url)
            )
            status_label.configure(text="File not found.")

    def refresh_installed_mods(self):
        # Run on GUI thread
        def _update():
            for widget in self.downloaded_frame.winfo_children():
                widget.destroy()

            self.selected_files.clear() # Clear tracked selections on refresh
            project_type = self.get_selected_project_type()
            content_label = self.get_content_label(project_type)
            content_dir = self.mods_manager.get_content_directory(project_type)
            self.lbl_downloaded_title.configure(text=f"Downloaded {content_label}")

            if not os.path.exists(content_dir):
                lbl_empty = ctk.CTkLabel(
                    self.downloaded_frame,
                    text=f"No {content_label.lower()} directory found.",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="#888888"
                )
                lbl_empty.pack(pady=40)
                return

            installed_files = [
                f for f in os.listdir(content_dir)
                if os.path.isfile(os.path.join(content_dir, f))
            ]
            if not installed_files:
                lbl_empty = ctk.CTkLabel(
                    self.downloaded_frame,
                    text=f"No downloaded {content_label.lower()} yet.\nSearch and install to add content!",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    text_color="#888888"
                )
                lbl_empty.pack(pady=40)
                return

            installed_map = self.config_manager.get("installed_mods", {})
            # Map filename -> (project_id, title, icon_url)
            file_to_info = {}
            for pid, val in installed_map.items():
                if isinstance(val, dict):
                    fname = val.get("filename")
                    title = val.get("title")
                    val_project_type = val.get("project_type", "mod")
                    icon_url = val.get("icon_url")
                else:
                    fname = val
                    title = None
                    val_project_type = "mod"
                    icon_url = None
                if fname and val_project_type == project_type:
                    file_to_info[fname] = (pid, title, icon_url)

            for jar in installed_files:
                # Mod card inside Downloaded Mods list
                card = ctk.CTkFrame(self.downloaded_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C", corner_radius=6)
                card.pack(fill="x", pady=4, padx=5)
                
                # Column weights: Checkbox (w=0), Icon (w=0), Info (w=1), Delete button (w=0)
                card.grid_columnconfigure(0, weight=0)
                card.grid_columnconfigure(1, weight=0)
                card.grid_columnconfigure(2, weight=1)
                card.grid_columnconfigure(3, weight=0)
                
                pid, title, icon_url = file_to_info.get(jar, (None, None, None))
                
                # Checkbox
                var = ctk.BooleanVar(value=False)
                self.selected_files[jar] = (var, project_type, pid)
                
                chk = ctk.CTkCheckBox(
                    card,
                    text="",
                    variable=var,
                    width=20,
                    height=20,
                    checkbox_width=16,
                    checkbox_height=16,
                    fg_color="#2ECC71",
                    hover_color="#27AE60"
                )
                chk.grid(row=0, column=0, padx=(10, 0), pady=8, sticky="w")
                
                # Icon
                icon_lbl = ctk.CTkLabel(card, text="📦", font=ctk.CTkFont(size=18), width=32, height=32)
                icon_lbl.grid(row=0, column=1, padx=(10, 0), pady=8, sticky="w")
                if icon_url:
                    self.load_icon_async(icon_url, icon_lbl, size=(32, 32))
                
                # Info frame
                info_f = ctk.CTkFrame(card, fg_color="transparent")
                info_f.grid(row=0, column=2, padx=(10, 10), pady=8, sticky="w")
                
                disp_title = title if title else jar
                if len(disp_title) > 28:
                    disp_title = disp_title[:25] + "..."
                    
                lbl_title = ctk.CTkLabel(
                    info_f, 
                    text=disp_title,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#FFFFFF"
                )
                lbl_title.pack(anchor="w")
                
                # Subtext (filename or version info)
                sub_text = jar
                if title: # If we have a pretty title, show filename as subtext
                    if len(sub_text) > 30:
                        sub_text = "..." + sub_text[-27:]
                else:
                    sub_text = f"Installed {content_label[:-1] if content_label.endswith('s') else content_label} File"
                    
                lbl_sub = ctk.CTkLabel(
                    info_f,
                    text=sub_text,
                    font=ctk.CTkFont(size=10),
                    text_color="#888888"
                )
                lbl_sub.pack(anchor="w")
                
                # Delete Button
                btn_del = ctk.CTkButton(
                    card,
                    text="🗑️",
                    width=30,
                    height=30,
                    fg_color="transparent",
                    hover_color="#E74C3C",
                    text_color="#CCCCCC",
                    font=ctk.CTkFont(size=12),
                    command=lambda f=jar, p=pid, pt=project_type: self.delete_jar_file(f, p, pt)
                )
                btn_del.grid(row=0, column=3, padx=10, pady=8, sticky="e")
                
        self.run_in_gui(_update)

    def delete_jar_file(self, filename, project_id, project_type="mod"):
        # Confirms deletion with a messagebox
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {filename}?"):
            return
            
        success, msg = self.mods_manager.delete_content(filename, project_type)
        if success:
            if project_id:
                installed_map = self.config_manager.get("installed_mods", {})
                installed_map.pop(project_id, None)
                self.config_manager.set("installed_mods", installed_map)
            
            # Refresh installed mods list
            self.refresh_installed_mods()
            # Also refresh search results to update "Install" buttons state
            self.start_search_thread(reset_offset=False)
        else:
            messagebox.showerror("Delete Error", f"Failed to delete mod file:\n{msg}")

    def delete_selected_files(self):
        selected = [filename for filename, (var, pt, pid) in self.selected_files.items() if var.get()]
        if not selected:
            messagebox.showinfo("Delete Selected", "No items selected to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the {len(selected)} selected files?"):
            return

        success_count = 0
        installed_map = self.config_manager.get("installed_mods", {})
        
        for filename in selected:
            var, pt, pid = self.selected_files[filename]
            success, msg = self.mods_manager.delete_content(filename, pt)
            if success:
                success_count += 1
                if pid:
                    installed_map.pop(pid, None)

        self.config_manager.set("installed_mods", installed_map)
        messagebox.showinfo("Delete Selected", f"Successfully deleted {success_count} files.")
        
        # Refresh lists
        self.refresh_installed_mods()
        self.start_search_thread(reset_offset=False)

    def trigger_one_click_updater(self):
        # Prevent double click/run
        self.btn_update_mods.configure(state="disabled", text="Checking...")
        
        def run_update():
            # Create progress dialog
            dialog = ctk.CTkToplevel(self)
            dialog.title("One-Click Mod Updater")
            dialog.geometry("400x180")
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.grab_set()
            
            x = self.winfo_x() + (self.winfo_width() // 2) - 200
            y = self.winfo_y() + (self.winfo_height() // 2) - 90
            dialog.geometry(f"+{x}+{y}")
            
            lbl_title = ctk.CTkLabel(dialog, text="Updating Mods...", font=ctk.CTkFont(size=14, weight="bold"), text_color="#2ECC71")
            lbl_title.pack(pady=(20, 10))
            
            progress_bar = ctk.CTkProgressBar(dialog, width=320, height=8, progress_color="#2ECC71")
            progress_bar.set(0)
            progress_bar.pack(pady=5)
            
            lbl_status = ctk.CTkLabel(dialog, text="Initializing...", font=ctk.CTkFont(size=11), text_color="#888888")
            lbl_status.pack(pady=5)
            
            def progress_cb(current, total, msg):
                pct = current / total if total > 0 else 0
                self.run_in_gui(progress_bar.set, pct)
                self.run_in_gui(lbl_status.configure, text=msg)
                
            success, updated, errors = self.mods_manager.update_all_installed_mods(progress_cb)
            
            def finish_gui():
                dialog.destroy()
                self.btn_update_mods.configure(state="normal", text="🚀 Update Mods")
                self.refresh_installed_mods()
                self.start_search_thread(reset_offset=False)
                
                # Show results summary
                if updated:
                    summary = "\n".join([f"• {title}: {old} -> {new}" for title, old, new in updated])
                    messagebox.showinfo("Update Complete", f"Successfully updated {len(updated)} mods:\n\n{summary}")
                else:
                    clean_errors = [e for e in errors if e]
                    if clean_errors:
                        err_summary = "\n".join(clean_errors[:5])
                        messagebox.showwarning("Update Finished", f"No updates were installed.\nErrors encountered:\n{err_summary}")
                    else:
                        messagebox.showinfo("Up to Date", "All mods are already up to date!")
            
            self.run_in_gui(finish_gui)

        threading.Thread(target=run_update, daemon=True).start()

