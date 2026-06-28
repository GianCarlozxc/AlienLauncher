import os
import threading
import requests
import io
import customtkinter as ctk
from PIL import Image
import ui.custom_dialog as messagebox

class FriendsPage(ctk.CTkFrame):
    def __init__(self, parent, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.config_manager = config_manager
        
        # Ensure default config for friends exists
        if self.config_manager.get("friends") is None:
            self.config_manager.set("friends", [])
            
        # Path for caching avatars
        self.avatar_cache_dir = os.path.join(self.config_manager.get_minecraft_folder(), "avatars")
        os.makedirs(self.avatar_cache_dir, exist_ok=True)
        
        self.avatar_cache = {} # Cache loaded CTkImage objects
        self.friend_rows = []
        self.status_labels = {} # Map username -> status Label widget
        
        self.setup_ui()

    def setup_ui(self):
        # Grid layout: 2 columns (Form: Left, List: Right)
        self.grid_columnconfigure(0, weight=4) # Form
        self.grid_columnconfigure(1, weight=6) # Scrollable List
        self.grid_rowconfigure(0, weight=1)

        # Left Column: Add Friend Form container
        form_container = ctk.CTkFrame(self, fg_color="transparent")
        form_container.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        form_container.grid_columnconfigure(0, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            form_container,
            text="Friend Manager",
            font=ctk.CTkFont(family="Orbitron", size=22, weight="bold"),
            text_color="#2ECC71"
        )
        title_label.grid(row=0, column=0, pady=(0, 2), sticky="w")

        desc_label = ctk.CTkLabel(
            form_container,
            text="Keep track of your friends' Minecraft accounts and Tailscale IP addresses to join servers easily.",
            font=ctk.CTkFont(family="Orbitron", size=11),
            text_color="#888888",
            wraplength=350,
            justify="left"
        )
        desc_label.grid(row=1, column=0, pady=(0, 15), sticky="w")

        # Form Card
        form_card = ctk.CTkFrame(form_container, fg_color="#1A1A1A", border_width=1, border_color="#2A2A2A")
        form_card.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        form_card.grid_columnconfigure(0, weight=1)

        form_title = ctk.CTkLabel(form_card, text="ADD NEW FRIEND", font=ctk.CTkFont(size=11, weight="bold"), text_color="#777777")
        form_title.grid(row=0, column=0, padx=15, pady=(12, 10), sticky="w")

        # Username Input
        lbl_username = ctk.CTkLabel(form_card, text="Minecraft Username", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        lbl_username.grid(row=1, column=0, padx=15, pady=(0, 2), sticky="w")
        self.entry_username = ctk.CTkEntry(form_card, fg_color="#101010", border_color="#2C2C2C", placeholder_text="e.g. Steve")
        self.entry_username.grid(row=2, column=0, padx=15, pady=(0, 4), sticky="ew")
        self.entry_username.bind("<KeyRelease>", lambda e: self.update_friend_gamer_id_label(self.entry_username.get().strip()))

        # Gamer ID Display (deterministic based on typed username)
        self.lbl_friend_gamer_id = ctk.CTkLabel(
            form_card, 
            text="Gamer ID: #----", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#2ECC71"
        )
        self.lbl_friend_gamer_id.grid(row=3, column=0, padx=15, pady=(0, 10), sticky="w")

        # Account Type
        lbl_acc_type = ctk.CTkLabel(form_card, text="Account Type", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        lbl_acc_type.grid(row=4, column=0, padx=15, pady=(0, 2), sticky="w")
        
        self.acc_type_var = ctk.StringVar(value="Offline")
        self.acc_type_selector = ctk.CTkSegmentedButton(
            form_card,
            values=["Offline", "Microsoft", "Ely.by"],
            variable=self.acc_type_var,
            selected_color="#2ECC71",
            unselected_color="#101010",
            text_color="#CCCCCC"
        )
        self.acc_type_selector.grid(row=5, column=0, padx=15, pady=(0, 12), sticky="ew")

        # Tailscale IP
        lbl_ip = ctk.CTkLabel(form_card, text="Tailscale IP (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        lbl_ip.grid(row=6, column=0, padx=15, pady=(0, 2), sticky="w")
        self.entry_ip = ctk.CTkEntry(form_card, fg_color="#101010", border_color="#2C2C2C", placeholder_text="e.g. 100.127.109.98")
        self.entry_ip.grid(row=7, column=0, padx=15, pady=(0, 12), sticky="ew")

        # Notes
        lbl_notes = ctk.CTkLabel(form_card, text="Notes / Nickname (Optional)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        lbl_notes.grid(row=8, column=0, padx=15, pady=(0, 2), sticky="w")
        self.entry_notes = ctk.CTkEntry(form_card, fg_color="#101010", border_color="#2C2C2C", placeholder_text="e.g. Server Host")
        self.entry_notes.grid(row=9, column=0, padx=15, pady=(0, 15), sticky="ew")

        # Add Button
        self.btn_add = ctk.CTkButton(
            form_container,
            text="Add Friend",
            fg_color="#2ECC71",
            hover_color="#27AE60",
            text_color="#121212",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            command=self.add_friend
        )
        self.btn_add.grid(row=3, column=0, sticky="ew")

        # Right Column: Friends List container
        list_container = ctk.CTkFrame(self, fg_color="transparent")
        list_container.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(1, weight=1)

        # Header
        list_header_row = ctk.CTkFrame(list_container, fg_color="transparent")
        list_header_row.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        list_header_row.grid_columnconfigure(0, weight=1)

        list_title = ctk.CTkLabel(
            list_header_row,
            text="Your Friends List",
            font=ctk.CTkFont(family="Orbitron", size=16, weight="bold"),
            text_color="#CCCCCC"
        )
        list_title.grid(row=0, column=0, sticky="w")

        self.btn_refresh = ctk.CTkButton(
            list_header_row,
            text="🔄 Refresh Status",
            width=110,
            height=26,
            fg_color="#1C1C1C",
            hover_color="#2A2A2A",
            text_color="#AAAAAA",
            font=ctk.CTkFont(size=11),
            command=self.refresh_friends_list
        )
        self.btn_refresh.grid(row=0, column=1, sticky="e")

        # Scrollable Frame for List
        self.scroll_frame = ctk.CTkScrollableFrame(list_container, fg_color="#141414", border_width=1, border_color="#222222")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.refresh_friends_list()

    def refresh_friends_list(self):
        # Clear existing rows
        for row in self.friend_rows:
            row.pack_forget()
            row.destroy()
        self.friend_rows.clear()
        self.status_labels.clear()

        friends = self.config_manager.get("friends", [])
        
        if not friends:
            no_friends_lbl = ctk.CTkLabel(
                self.scroll_frame,
                text="No friends added yet.\nUse the form on the left to add your first friend!",
                font=ctk.CTkFont(size=13, slant="italic"),
                text_color="#666666"
            )
            no_friends_lbl.pack(pady=40)
            self.friend_rows.append(no_friends_lbl)
            return

        for index, friend in enumerate(friends):
            username = friend.get("username", "Unknown")
            acc_type = friend.get("account_type", "Offline")
            ip = friend.get("ip_address", "")
            notes = friend.get("notes", "")

            # Friend row card
            row_card = ctk.CTkFrame(self.scroll_frame, fg_color="#1E1E1E", border_width=1, border_color="#2C2C2C", height=75)
            row_card.pack(fill="x", pady=4, padx=5)
            row_card.pack_propagate(False)
            self.friend_rows.append(row_card)

            # 1. Avatar display
            avatar_lbl = ctk.CTkLabel(row_card, text="", width=32, height=32)
            avatar_lbl.pack(side="left", padx=10)
            self.load_avatar_async(username, acc_type, avatar_lbl)

            # 2. Text Details
            details_frame = ctk.CTkFrame(row_card, fg_color="transparent")
            details_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
            
            # Row for Name + Badge + Status
            name_row = ctk.CTkFrame(details_frame, fg_color="transparent")
            name_row.pack(anchor="w", fill="x")
            
            name_lbl = ctk.CTkLabel(name_row, text=username, font=ctk.CTkFont(weight="bold", size=13), text_color="#CCCCCC")
            name_lbl.pack(side="left", anchor="w")
            
            # Badge
            badge_color = "#3498DB" if acc_type == "Microsoft" else ("#2ECC71" if acc_type == "Ely.by" else "#95A5A6")
            badge = ctk.CTkLabel(
                name_row, text=acc_type.upper(), 
                font=ctk.CTkFont(size=8, weight="bold"), 
                text_color="#FFFFFF", fg_color=badge_color, 
                corner_radius=4, height=14, width=50
            )
            badge.pack(side="left", padx=8)

            # Status label
            status_lbl = ctk.CTkLabel(
                name_row, text="🔍 Checking...", 
                font=ctk.CTkFont(size=10, weight="bold"), 
                text_color="#777777"
            )
            status_lbl.pack(side="left", padx=5)
            self.status_labels[username.lower()] = status_lbl

            # Deterministic 4-digit ID
            import hashlib
            h = hashlib.md5(username.lower().encode('utf-8')).hexdigest()
            four_digit = f"#{int(h, 16) % 9000 + 1000}"
            
            id_lbl = ctk.CTkLabel(details_frame, text=four_digit, font=ctk.CTkFont(size=11, weight="bold"), text_color="#555555")
            id_lbl.pack(anchor="w", pady=(0, 1))

            # Sub-text (IP / Notes)
            sub_text = ""
            if ip:
                sub_text += f"IP: {ip}"
            if notes:
                if sub_text:
                    sub_text += f"  |  {notes}"
                else:
                    sub_text += notes
            if not sub_text:
                sub_text = "No address / notes"

            sub_lbl = ctk.CTkLabel(details_frame, text=sub_text, font=ctk.CTkFont(size=11), text_color="#777777")
            sub_lbl.pack(anchor="w", pady=(0, 0))

            # 3. Actions Frame
            actions_frame = ctk.CTkFrame(row_card, fg_color="transparent")
            actions_frame.pack(side="right", padx=10, fill="y")

            # Copy IP Button
            if ip:
                btn_copy = ctk.CTkButton(
                    actions_frame, text="📋", width=26, height=26,
                    fg_color="#2C2C2C", hover_color="#3A3A3A",
                    command=lambda address=ip: self.copy_ip(address)
                )
                btn_copy.pack(side="left", padx=2, expand=True)

            # Delete Button
            btn_delete = ctk.CTkButton(
                actions_frame, text="🗑️", width=26, height=26,
                fg_color="#2C2C2C", hover_color="#C0392B",
                command=lambda u=username: self.delete_friend(u)
            )
            btn_delete.pack(side="left", padx=2, expand=True)

        # Trigger background status scanning
        self.start_status_scan()

    def start_status_scan(self):
        friends = self.config_manager.get("friends", [])
        
        def _scan_thread():
            import socket
            
            for friend in friends:
                username = friend.get("username", "Unknown")
                ip = friend.get("ip_address", "").strip()
                
                if not ip:
                    self.update_status_gui(username, "No IP", "#555555")
                    continue
                
                self.update_status_gui(username, "🔍 Checking...", "#777777")
                
                # Check server port 25565 (Java Minecraft)
                status_text = "🔴 Inactive"
                status_color = "#E74C3C"
                
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.4)
                    result = s.connect_ex((ip, 25565))
                    if result == 0:
                        status_text = "🟢 Active Server"
                        status_color = "#2ECC71"
                        s.close()
                        self.update_status_gui(username, status_text, status_color)
                        continue
                    s.close()
                except Exception:
                    pass

                # Check server port 19132 (Geyser Bedrock)
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.4)
                    result = s.connect_ex((ip, 19132))
                    if result == 0:
                        status_text = "🟢 Active Server"
                        status_color = "#2ECC71"
                        s.close()
                        self.update_status_gui(username, status_text, status_color)
                        continue
                    s.close()
                except Exception:
                    pass
                
                self.update_status_gui(username, status_text, status_color)

        threading.Thread(target=_scan_thread, daemon=True).start()

    def update_status_gui(self, username, text, color):
        def _update():
            lbl = self.status_labels.get(username.lower())
            if lbl and lbl.winfo_exists():
                lbl.configure(text=text, text_color=color)
        self.after(0, _update)

    def verify_mojang_username(self, username):
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "id" in data:
                    return True, data.get("name", username)
            return False, None
        except Exception:
            # Network issue, return True to not lock the user out if offline
            return True, username

    def add_friend(self):
        username = self.entry_username.get().strip()
        acc_type = self.acc_type_var.get()
        ip = self.entry_ip.get().strip()
        notes = self.entry_notes.get().strip()

        if not username:
            messagebox.showerror("Input Error", "Please enter a Minecraft username.")
            return

        # Username format regex check (3-16 chars, alphanumeric/underscore)
        import re
        if not re.match(r"^[a-zA-Z0-9_]{3,16}$", username):
            messagebox.showerror(
                "Invalid Username",
                "Minecraft usernames must be between 3 and 16 characters and contain only letters, numbers, and underscores."
            )
            return

        # Check self-addition
        my_username = self.config_manager.get("username", "")
        if username.lower() == my_username.lower():
            messagebox.showerror("Error", "You cannot add yourself as a friend!")
            return

        # Check self-IP
        my_ip = self.winfo_toplevel().tailscale_manager.get_ipv4()
        if ip and my_ip and ip == my_ip:
            messagebox.showerror("Error", "You cannot add your own Tailscale IP address as a friend's IP!")
            return

        friends = self.config_manager.get("friends", [])

        # Check for duplicate
        for f in friends:
            if f.get("username").lower() == username.lower():
                messagebox.showerror("Error", f"Friend '{username}' is already in your friends list.")
                return

        # Disable button to show work in progress
        toplevel = self.winfo_toplevel()
        self.btn_add.configure(state="disabled", text="Verifying Username...")

        def _verify_thread():
            exists, corrected_name = self.verify_mojang_username(username)
            
            def _finish():
                self.btn_add.configure(state="normal", text="Add Friend")
                
                if acc_type in ["Microsoft", "Ely.by"]:
                    if not exists:
                        messagebox.showerror(
                            "Account Not Found",
                            f"The {acc_type} Minecraft account '{username}' does not exist."
                        )
                        return
                    final_name = corrected_name
                else:
                    # Offline account type
                    if not exists:
                        confirm = messagebox.askyesno(
                            "Account Not Found",
                            f"The username '{username}' does not exist in Mojang's official database.\n\n"
                            "Since this is an Offline account, do you want to add it anyway?"
                        )
                        if not confirm:
                            return
                    final_name = corrected_name if exists else username

                # If Tailscale IP is provided, send live P2P request
                if ip:
                    self.btn_add.configure(state="disabled", text="Sending Request...")
                    
                    def _p2p_thread():
                        my_username = self.config_manager.get("username", "AlienPlayer")
                        my_acc_type = self.config_manager.get("account_type", "Offline")
                        my_ip = toplevel.tailscale_manager.get_ipv4()
                        if my_ip == "Not Connected / Unknown":
                            my_ip = ""
                            
                        status = toplevel.p2p_manager.send_friend_request(
                            ip, my_username, my_acc_type, my_ip
                        )
                        
                        def _p2p_finish():
                            self.btn_add.configure(state="normal", text="Add Friend")
                            
                            if status == "accepted":
                                messagebox.showinfo(
                                    "Request Accepted",
                                    f"'{username}' has accepted your friend request! Added to list."
                                )
                                self.save_friend_to_config(final_name, acc_type, ip, notes)
                            elif status == "declined":
                                messagebox.showerror(
                                    "Request Declined",
                                    f"'{username}' declined your friend request."
                                )
                            elif status == "already_friends":
                                messagebox.showinfo(
                                    "Already Friends",
                                    f"You are already in '{username}'s friends list!"
                                )
                                self.save_friend_to_config(final_name, acc_type, ip, notes)
                            elif status == "timeout":
                                messagebox.showwarning(
                                    "No Response",
                                    f"No response from '{username}'. Added locally."
                                )
                                self.save_friend_to_config(final_name, acc_type, ip, notes)
                            else:
                                messagebox.showwarning(
                                    "Offline",
                                    f"Could not connect to '{username}' on Tailscale. Added locally."
                                )
                                self.save_friend_to_config(final_name, acc_type, ip, notes)
                                
                        self.after(0, _p2p_finish)
                        
                    threading.Thread(target=_p2p_thread, daemon=True).start()
                else:
                    self.save_friend_to_config(final_name, acc_type, ip, notes)

            self.after(0, _finish)

        threading.Thread(target=_verify_thread, daemon=True).start()

    def save_friend_to_config(self, username, acc_type, ip, notes):
        friends = self.config_manager.get("friends", [])
        
        # Check duplicate
        for f in friends:
            if f.get("username").lower() == username.lower():
                return
                
        new_friend = {
            "username": username,
            "account_type": acc_type,
            "ip_address": ip,
            "notes": notes
        }

        friends.append(new_friend)
        self.config_manager.set("friends", friends)

        # Clear fields
        self.entry_username.delete(0, "end")
        self.entry_ip.delete(0, "end")
        self.entry_notes.delete(0, "end")
        self.lbl_friend_gamer_id.configure(text="Gamer ID: #----")

        self.refresh_friends_list()

    def update_friend_gamer_id_label(self, username):
        if not username:
            self.lbl_friend_gamer_id.configure(text="Gamer ID: #----")
            return
        import hashlib
        h = hashlib.md5(username.lower().encode('utf-8')).hexdigest()
        four_digit = f"#{int(h, 16) % 9000 + 1000}"
        self.lbl_friend_gamer_id.configure(text=f"Gamer ID: {four_digit}")

    def delete_friend(self, username):
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to remove '{username}' from your friends list?"):
            return

        friends = self.config_manager.get("friends", [])
        updated = [f for f in friends if f.get("username").lower() != username.lower()]
        
        self.config_manager.set("friends", updated)
        self.refresh_friends_list()

    def copy_ip(self, ip):
        self.clipboard_clear()
        self.clipboard_append(ip)
        messagebox.showinfo("Success", f"IP address '{ip}' copied to clipboard.")

    def load_avatar_async(self, username, acc_type, label_widget):
        # Local cache path
        cache_file = os.path.join(self.avatar_cache_dir, f"{username.lower()}_32.png")
        
        if os.path.exists(cache_file):
            try:
                # Load from cache
                pil_img = Image.open(cache_file)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                label_widget.configure(image=ctk_img)
                label_widget.image = ctk_img
                return
            except Exception:
                pass

        # If not cached, load asynchronously from minotar/mc-heads
        def _fetch_thread():
            # For Offline account, use standard steve if the username is common or empty,
            # or try to fetch from MC-Heads (which falls back to Steve anyway).
            url = f"https://minotar.net/avatar/{username}/32"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    pil_img = Image.open(io.BytesIO(res.content))
                    # Save to cache
                    pil_img.save(cache_file)
                    
                    def _update_gui():
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                        label_widget.configure(image=ctk_img)
                        label_widget.image = ctk_img
                        
                    self.after(0, _update_gui)
            except Exception:
                # Fallback to steve
                steve_url = "https://minotar.net/avatar/steve/32"
                try:
                    res = requests.get(steve_url, timeout=5)
                    if res.status_code == 200:
                        pil_img = Image.open(io.BytesIO(res.content))
                        pil_img.save(cache_file)
                        
                        def _update_gui():
                            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                            label_widget.configure(image=ctk_img)
                            label_widget.image = ctk_img
                            
                        self.after(0, _update_gui)
                except Exception:
                    pass

        threading.Thread(target=_fetch_thread, daemon=True).start()

    def on_view_active(self):
        self.refresh_friends_list()
