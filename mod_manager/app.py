import tkinter as tk
import os
import json
import requests
import zipfile
import shutil
import tempfile
import subprocess
import sys
import logging
import re

from tkinter import filedialog, messagebox, simpledialog, ttk, Toplevel, Label
from profile_dialog import ProfileManagerDialog
from edit_mod_dialog import EditModDialog
from content_manager.dialogs import UpdateProgressDialog, show_error_dialog
from content_manager.logic import ContentManagerLogic

# Setup logging
logging.basicConfig(
    filename='mod_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
PROFILES_FILE = "cfg/mod_profiles.json"
CONFIG_FILE = "cfg/mod_manager_config.json"
VERSION_FILE = "version.json"  # Tool version (ships with releases)
# Use 'userdata' to match the --userdir parameter passed to the game launcher
DEFAULT_MODS_DIR = "userdata"

INSTALL_TYPE_DIRS = {
    "mod": "mods",
    "tileset": "gfx",
    "soundpack": "sound"
}

class ModManagerApp:
    def __init__(self, root):
        self.root = root
        
        self.root.title("Cataclysm Content Manager")
        self.root.geometry("950x650")
        self.root.minsize(950, 650)
    
        # initialize business logic layer
        self.logic = ContentManagerLogic(self.root)
        self.logic._ensure_config_files_exist()
        ContentManagerLogic.clear_log()

        # load configuration and profiles
        self.logic.load_config()
        self.logic.load_profiles()

        self._build_ui()

        # create default profile if none exist
        if not self.logic.profiles:
            self._create_profile("default")

        # ensure current profile is set
        if not self.logic.current_profile or self.logic.current_profile not in self.logic.profiles:
            self.logic.current_profile = list(self.logic.profiles.keys())[0]

        self.profile_var.set(self.logic.current_profile)
        self._refresh_profile_combo()
        self._refresh_mod_list()
        self._refresh_installed_mods()
    
    def _export_profile(self):
        if not self.logic.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return

        profile_data = self.logic.profiles.get(self.logic.current_profile)
        if not profile_data:
            messagebox.showerror("Error", "Current profile data not found.", parent=self.root)
            return

        export_path = filedialog.asksaveasfilename(
            title="Export Profile",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.logic.current_profile}.json",
            parent=self.root
        )
        if not export_path:
            return

        try:
            with open(export_path, "w") as f:
                json.dump({self.logic.current_profile: profile_data}, f, indent=2)
            messagebox.showinfo("Export Success", f"Profile exported to:\n{export_path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export profile:\n{e}", parent=self.root)

    def _import_profile(self):
        import_path = filedialog.askopenfilename(
            title="Import Profile",
            filetypes=[("JSON files", "*.json")],
            parent=self.root
        )
        if not import_path:
            return

        try:
            with open(import_path, "r") as f:
                data = json.load(f)

            # expecting data like: {"profile_name": {profile_data}}
            for name, pdata in data.items():
                if name in self.logic.profiles:
                    overwrite = messagebox.askyesno(
                        "Overwrite Profile?",
                        f"Profile '{name}' already exists. Overwrite?",
                        parent=self.root
                    )
                    if not overwrite:
                        continue
                self.logic.profiles[name] = pdata

            # auto-switch to last imported profile
            self.logic.current_profile = list(data.keys())[-1]
            self.profile_var.set(self.logic.current_profile)
            self.logic.save_profiles()
            self._refresh_profile_combo()
            self._refresh_mod_list()

            if hasattr(self, "profile_manager_dialog"):
                new_profile_name = self.profile_var.get()
                self.profile_manager_dialog.update_profile_name(new_profile_name)
            
            messagebox.showinfo("Import Success", "Profile(s) imported successfully.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import profile:\n{e}", parent=self.root)

    def _refresh_installed_mods(self):
        self.installed_listbox.delete(0, tk.END)
        folder_path = self._get_installed_folder_base()
        print(f"Listing installed mods in: {folder_path}")  # DEBUG
        if not os.path.isdir(folder_path):
            print(f"Directory does not exist: {folder_path}")  # DEBUG
            return
        try:
            entries = sorted([d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))])
            print(f"Entries found: {entries}")  # DEBUG
            for folder in entries:
                self.installed_listbox.insert(tk.END, folder)
        except Exception as e:
            logging.error(f"Error listing installed mods: {e}")

    def _delete_installed_mod(self):
        selected = self.installed_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Select an installed folder to delete.", parent=self.root)
            return

        index = selected[0]
        folder_name = self.installed_listbox.get(index)
        folder_path = self._get_installed_folder_path(folder_name)

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete folder:\n{folder_name}?", parent=self.root)
        if not confirm:
            return

        try:
            shutil.rmtree(folder_path)
            messagebox.showinfo("Deleted", f"Deleted folder: {folder_name}", parent=self.root)
            self._refresh_installed_mods()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete folder:\n{e}", parent=self.root)

    def _open_installed_mod_folder(self):
        selected = self.installed_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Select an installed folder to open.", parent=self.root)
            return

        index = selected[0]
        folder_name = self.installed_listbox.get(index)
        folder_path = self._get_installed_folder_path(folder_name)

        if not os.path.exists(folder_path):
            messagebox.showerror("Error", f"Folder does not exist:\n{folder_path}", parent=self.root)
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder:\n{e}", parent=self.root)

    
    # --- UI Construction ---
    def _build_ui(self):
        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.grid(row=0, column=0, sticky="nsew")

        # Profile management frame — SPANS BOTH columns (0 and 1)
        profile_frame = tk.Frame(self.frame)
        profile_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        profile_frame.columnconfigure(1, weight=1)  # Make combo box expand

        tk.Label(profile_frame, text="Profile:").grid(row=0, column=0, sticky="w", padx=(0, 5))

        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly", width=30)
        self.profile_combo.grid(row=0, column=1, sticky="ew")
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)

        tk.Button(profile_frame, text="Manage Profiles", command=self.open_profile_manager).grid(row=0, column=2, padx=10)

        explanation = (
            "Enter the GitHub ZIP URL for the mod archive.\n"
            "Leave Subdirectory blank to auto-detect folders with 'modinfo.json'.\n"
            "Use 'Keep original folder structure' option per mod as needed."
        )
        self.explanation_label = tk.Label(self.frame, text=explanation, justify="left", wraplength=800)
        self.explanation_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.folder_var = tk.StringVar(value="Mods")  # Use display name
        folder_options = [
            ("Mods", "mods"),
            ("Soundpacks", "sound"),
            ("Tilesets", "gfx"),
            ("Fonts", "font")
        ]
        self.folder_map = {name: folder for name, folder in folder_options}

        dropdown_row = tk.Frame(self.frame)
        dropdown_row.grid(row=1, column=1, sticky="e", padx=(0, 10), pady=(0, 0))
        tk.Label(dropdown_row, text="Installed Folder:").pack(side=tk.LEFT)
        folder_dropdown = ttk.Combobox(
            dropdown_row,
            textvariable=self.folder_var,
            values=[name for name, _ in folder_options],
            state="readonly",
            width=15
        )
        folder_dropdown.pack(side=tk.LEFT, padx=(5, 0))
        folder_dropdown.bind("<<ComboboxSelected>>", lambda e: self._refresh_installed_mods())

        # GitHub Mods List (left)
        listbox_frame = tk.Frame(self.frame)
        listbox_frame.grid(row=2, column=0, sticky="nsew")

        tk.Label(listbox_frame, text="GitHub Mods:").pack(anchor="w")

        # Container frame for Listbox + scrollbars
        listbox_container = tk.Frame(listbox_frame)
        listbox_container.pack(fill=tk.BOTH, expand=True)

        # Listbox itself
        self.listbox = tk.Listbox(listbox_container, width=50, height=20, activestyle='none', xscrollcommand=lambda *args: h_scrollbar.set(*args), yscrollcommand=lambda *args: v_scrollbar.set(*args))
        self.listbox.grid(row=0, column=0, sticky="nsew")
        
        # Bind hover events for scrolling
        self.listbox.bind("<Enter>", self._on_listbox_enter)
        self.listbox.bind("<Leave>", self._on_listbox_leave)
        self.listbox.bind("<Motion>", self._on_listbox_motion)
        self.hover_after_id = None
        self.scrolling_index = -1  # Track which item is currently scrolling
        self.original_text = ""  # Store the original text of scrolling item
        self.scroll_offset = 0

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.listbox.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")

        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(listbox_container, orient=tk.HORIZONTAL, command=self.listbox.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Configure grid weights for resizing
        listbox_container.grid_rowconfigure(0, weight=1)
        listbox_container.grid_columnconfigure(0, weight=1)
        

        # Buttons under GitHub Mods list
        mod_buttons_frame = tk.Frame(self.frame)
        mod_buttons_frame.grid(row=3, column=0, pady=(5, 0), sticky="ew")

        buttons = [
            ("Add Mod", self._add_mod),
            ("Edit Mod", self._edit_mod),
            ("Remove Mod", self._remove_mod),
            ("Update Mods", self._update_mods)
        ]
        for i, (text, cmd) in enumerate(buttons):
            btn = tk.Button(mod_buttons_frame, text=text, command=cmd)
            btn.grid(row=0, column=i, padx=5, sticky="ew")
            mod_buttons_frame.grid_columnconfigure(i, weight=1)

        # Installed Mods list (right)
        installed_mods_frame = tk.Frame(self.frame)
        installed_mods_frame.grid(row=2, column=1, rowspan=2, sticky="nsew", padx=(10, 0))

        # Label
        tk.Label(installed_mods_frame, text="Installed Mods:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 0))

        # List container (this should expand)
        installed_list_container = tk.Frame(installed_mods_frame)
        installed_list_container.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.installed_listbox = tk.Listbox(installed_list_container, width=40, height=20, activestyle='none')
        self.installed_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        installed_scrollbar = ttk.Scrollbar(installed_list_container, orient=tk.VERTICAL, command=self.installed_listbox.yview)
        installed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.installed_listbox.config(yscrollcommand=installed_scrollbar.set)

        # BUTTONS: Always visible, flush with left box
        button_frame = tk.Frame(installed_mods_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        self.installed_button = tk.Button(button_frame, text="Delete", command=self._delete_installed_mod)
        self.installed_button.grid(row=0, column=0, sticky="ew", padx=5)
        self.open_folder_button = tk.Button(button_frame, text="Open Folder", command=self._open_installed_mod_folder)
        self.open_folder_button.grid(row=0, column=1, sticky="ew", padx=5)
        self.refresh_installed_button = tk.Button(button_frame, text="Refresh", command=self._refresh_installed_mods)
        self.refresh_installed_button.grid(row=0, column=2, sticky="ew", padx=5)
        self.explore_button = tk.Button(button_frame, text="Explore", command=self._run_mod_viewer)
        self.explore_button.grid(row=0, column=3, sticky="ew", padx=5)
        for i in range(4):
            button_frame.grid_columnconfigure(i, weight=1)

        # Make sure installed_mods_frame expands
        installed_mods_frame.grid_rowconfigure(1, weight=1)  # Only the list container expands
        installed_mods_frame.grid_rowconfigure(2, weight=0)  # Buttons do not expand
        installed_mods_frame.grid_columnconfigure(0, weight=1)
        installed_mods_frame.grid_columnconfigure(1, weight=1)

        # Make sure the main frame expands both columns
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

        # Ensure root grid expands
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Bottom frame for Open Root Folder button
        bottom_frame = tk.Frame(self.frame)
        bottom_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        open_root_btn = tk.Button(
            bottom_frame,
            text="Open Root Folder",
            command=self._open_root_folder
        )
        open_root_btn.pack(fill="x", expand=True)

    # --- Profile Methods ---
    def _create_profile(self, default_name=None):
        if default_name:
            name = default_name
        else:
            name = simpledialog.askstring("New Profile", "Enter profile name:", parent=self.root)
            if not name:
                return
            if name in self.logic.profiles:
                messagebox.showerror("Error", f"Profile '{name}' already exists.", parent=self.root)
                return
        self.logic.profiles[name] = {"mods": [], "mod_install_dir": DEFAULT_MODS_DIR}
        self.logic.current_profile = name
        self.profile_var.set(name)
        self.logic.save_profiles()
        self._refresh_profile_combo()
        self._refresh_mod_list()

        if hasattr(self, "profile_manager_dialog"):
            new_profile_name = self.profile_var.get()  # or whatever is current
            self.profile_manager_dialog.update_profile_name(new_profile_name)

    def _rename_profile(self):
        if not self.logic.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return
        new_name = simpledialog.askstring("Rename Profile", "Enter new profile name:", initialvalue=self.logic.current_profile, parent=self.root)
        if not new_name or new_name == self.logic.current_profile:
            return
        if new_name in self.logic.profiles:
            messagebox.showerror("Error", f"Profile '{new_name}' already exists.", parent=self.root)
            return
        self.logic.profiles[new_name] = self.logic.profiles.pop(self.logic.current_profile)
        self.logic.current_profile = new_name
        self.profile_var.set(new_name)
        self.logic.save_profiles()
        self._refresh_profile_combo()
        self._refresh_mod_list()

        if hasattr(self, "profile_manager_dialog"):
            new_profile_name = self.profile_var.get()  # or whatever is current
            self.profile_manager_dialog.update_profile_name(new_profile_name)

    def _delete_profile(self):
        if not self.logic.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return
        if len(self.logic.profiles) == 1:
            messagebox.showerror("Error", "Cannot delete the only profile.", parent=self.root)
            return
        confirm = messagebox.askyesno("Delete Profile", f"Are you sure you want to delete profile '{self.logic.current_profile}'?", parent=self.root)
        if confirm:
            del self.logic.profiles[self.logic.current_profile]
            self.logic.current_profile = next(iter(self.logic.profiles.keys()), None)
            self.profile_var.set(self.logic.current_profile)
            self.logic.save_profiles()
            self._refresh_profile_combo()
            self._refresh_mod_list()
            
            if hasattr(self, "profile_manager_dialog"):
                new_profile_name = self.profile_var.get()  # or whatever is current
                self.profile_manager_dialog.update_profile_name(new_profile_name)

    def _refresh_profile_combo(self):
        profiles_list = list(self.logic.profiles.keys())
        self.profile_combo['values'] = profiles_list

    def _on_profile_change(self, event=None):
        selected = self.profile_var.get()
        if selected and selected != self.logic.current_profile:
            self.logic.current_profile = selected
            profile = self.logic.profiles.get(self.logic.current_profile, {})
            if isinstance(profile, dict):
                rel_path = profile.get("mod_install_dir", DEFAULT_MODS_DIR)
                self.logic.mod_install_dir = self.logic.resolve_install_dir(rel_path)
            else:
                self.logic.mod_install_dir = DEFAULT_MODS_DIR
            self.logic.save_profiles()
            self._refresh_mod_list()

    # --- Mod List Management ---
    def _get_mods(self):
        profile = self.logic.profiles.get(self.logic.current_profile, {})
        if isinstance(profile, dict):
            return profile.get("mods", [])
        return profile  # support old format

    def _get_install_dir(self, mod):
        install_type = mod.get("install_type", "mod")
        # Use profile's mod_install_dir for mods, else use default for tileset/soundpack
        if install_type == "mod":
            return self.logic.mod_install_dir
        else:
            return INSTALL_TYPE_DIRS.get(install_type, self.logic.mod_install_dir)

    def _set_mods(self, mods):
        profile = self.logic.profiles.get(self.logic.current_profile, {})
        if isinstance(profile, dict):
            profile["mods"] = mods
        else:
            self.logic.profiles[self.logic.current_profile] = mods
        self.logic.save_profiles()

    def _refresh_mod_list(self):
        self.listbox.delete(0, tk.END)
        for mod in self._get_mods():
            keep_text = "Auto-detect" if mod.get("keep_structure") else "Keep structure"
            mod_subdir = mod.get("mod_subdir", mod.get("subdir", ""))
            install_subdir = mod.get("install_subdir", "")

            url = mod['url']
            clean_url = url  # default fallback

            # Handle GitHub archive URLs
            github_zip = re.match(
                r"https?://github\.com/([^/]+)/([^/]+)/archive/(?:refs/(?:heads|tags)/)?([^/]+)\.zip", url
            )
            if github_zip:
                user, repo, ref = github_zip.groups()
                clean_url = f"{user}/{repo}"

            display = f"{clean_url}"
            if mod_subdir:
                display += f"  |  mod subdir: {mod_subdir}"
            if install_subdir:
                display += f"  |  install dir: {install_subdir}"
            display += f"  |  {keep_text}"
            self.listbox.insert(tk.END, display)

    def _on_listbox_enter(self, event):
        """Called when mouse enters listbox"""
        pass

    def _on_listbox_leave(self, event):
        """Called when mouse leaves listbox - restore original text"""
        self._stop_scrolling()

    def _on_listbox_motion(self, event):
        """Called when mouse moves over listbox - implements scrolling on hover"""
        # Get the item under the cursor
        index = self.listbox.nearest(event.y)
        if index == -1:
            self._stop_scrolling()
            return
        
        # Get the text of the item
        try:
            text = self.listbox.get(index)
        except:
            self._stop_scrolling()
            return
        
        # If we're already scrolling this item, don't restart
        if self.scrolling_index == index:
            return
        
        # Stop previous scroll if any
        self._stop_scrolling()
        
        # Check if text is longer than what fits in the listbox
        bbox = self.listbox.bbox(index)
        if not bbox:
            return
        
        # Estimate text width (approximate: ~8 pixels per character in monospace)
        text_width = len(text) * 8
        visible_width = bbox[2]
        
        # If text is longer than visible width, enable scrolling
        if text_width > visible_width:
            self._start_hover_scroll(index, text)

    def _stop_scrolling(self):
        """Stop the current scrolling and restore original text"""
        if self.hover_after_id:
            self.root.after_cancel(self.hover_after_id)
            self.hover_after_id = None
        
        # Restore original text if we were scrolling
        if self.scrolling_index >= 0 and self.original_text and self.scrolling_index < self.listbox.size():
            selection = self.listbox.curselection()
            self.listbox.delete(self.scrolling_index)
            self.listbox.insert(self.scrolling_index, self.original_text)
            # Restore selection if there was one
            if selection and len(selection) > 0:
                self.listbox.selection_set(selection[0])
        
        self.scrolling_index = -1
        self.original_text = ""
        self.scroll_offset = 0

    def _start_hover_scroll(self, index, text):
        """Start the marquee scrolling effect - text cycles like a radio display"""
        self.scrolling_index = index
        self.original_text = text
        self.scroll_offset = 0
        
        # Create extended text with spaces for smooth circular scrolling
        space_padding = " " * 15
        scrolling_text = text + space_padding + text
        
        def scroll():
            if self.hover_after_id is None:
                return
            
            # Create the display string by rotating the text
            # Take a substring starting at offset
            display_text = scrolling_text[self.scroll_offset : self.scroll_offset + len(text)]
            
            # If we're near the end, wrap around
            if len(display_text) < len(text):
                remaining = len(text) - len(display_text)
                display_text += scrolling_text[:remaining]
            
            # Update just this item by deleting and reinserting at the same position
            if self.scrolling_index < self.listbox.size():
                selection = self.listbox.curselection()
                self.listbox.delete(self.scrolling_index)
                self.listbox.insert(self.scrolling_index, display_text)
                # Restore selection if there was one
                if selection and len(selection) > 0:
                    self.listbox.selection_set(selection[0])
            
            # Increment offset for next frame (loop back to start)
            total_len = len(scrolling_text)
            self.scroll_offset = (self.scroll_offset + 1) % total_len
            
            # Schedule next scroll
            self.hover_after_id = self.root.after(80, scroll)
        
        # Start scrolling
        self.hover_after_id = self.root.after(80, scroll)

    def _fix_github_url(self, url):
        url = url.rstrip('/')
        if url.startswith("https://github.com/") and not url.endswith(".zip"):
            return f"{url}/archive/refs/heads/master.zip"
        return url


    def _add_mod(self):
        from edit_mod_dialog import EditModDialog
        dialog = EditModDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result:
            url, mod_subdir, install_subdir, keep_structure = dialog.result
            url = self._fix_github_url(url)
            mods = self._get_mods()
            mods.append({
                "url": url,
                "mod_subdir": mod_subdir,
                "install_subdir": install_subdir,
                "keep_structure": keep_structure
            })
            self._set_mods(mods)
            self._refresh_mod_list()

    def _edit_mod(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("No selection", "Select a mod to edit.", parent=self.root)
            return
        index = selected[0]
        mods = self._get_mods()
        mod = mods[index]

        from edit_mod_dialog import EditModDialog
        dialog = EditModDialog(
            self.root,
            mod.get("url", ""),
            mod.get("mod_subdir", mod.get("subdir", "")),
            mod.get("install_subdir", ""),
            mod.get("keep_structure", True)
        )
        self.root.wait_window(dialog)

        if dialog.result:
            url, mod_subdir, install_subdir, keep_structure = dialog.result
            url = self._fix_github_url(url)
            mods[index] = {
                "url": url,
                "mod_subdir": mod_subdir,
                "install_subdir": install_subdir,
                "keep_structure": keep_structure
            }
            self._set_mods(mods)
            self._refresh_mod_list()


    def _remove_mod(self):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showwarning("No selection", "Select a mod to remove.", parent=self.root)
            return
        index = selected[0]
        mods = self._get_mods()
        mod = mods[index]
        confirm = messagebox.askyesno("Remove Mod", f"Remove mod?\n{mod['url']}", parent=self.root)
        if confirm:
            mods.pop(index)
            self._set_mods(mods)
            self._refresh_mod_list()
    
    def _set_mod_install_dir(self):
        new_dir = filedialog.askdirectory(title="Select Mod Install Directory", initialdir=self.logic.mod_install_dir)
        if new_dir:
            self.logic.mod_install_dir = new_dir
            if self.logic.current_profile and self.logic.current_profile in self.logic.profiles:
                profile = self.logic.profiles[self.logic.current_profile]
                if isinstance(profile, dict):
                    profile["mod_install_dir"] = self.logic.make_path_relative(new_dir)
                else:
                    self.logic.profiles[self.logic.current_profile] = {"mods": profile, "mod_install_dir": self.logic.make_path_relative(new_dir)}
                self.logic.save_profiles()

            # If dialog open, update any UI if needed (example: update profile label)
            if hasattr(self, "profile_manager_dialog"):
                self.profile_manager_dialog.update_profile_name(self.logic.current_profile)

    def _open_mod_folder(self):
        if not os.path.isdir(self.logic.mod_install_dir):
            messagebox.showerror("Error", f"Mod install directory does not exist:\n{self.logic.mod_install_dir}", parent=self.root)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.logic.mod_install_dir)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", self.logic.mod_install_dir])
            else:
                subprocess.Popen(["xdg-open", self.logic.mod_install_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory:\n{e}", parent=self.root)

    def _update_mods(self):
        mods = self._get_mods()
        if not mods:
            messagebox.showinfo("Info", "No mods to update.", parent=self.root)
            return

        # show updating popup using new dialog class
        self.update_progress_dialog = UpdateProgressDialog(self.root)

        self.root.after(100, self._update_mods_worker)

    def _show_error_dialog(self, title, message, errors):
        """show a scrollable error dialog for long error messages
        now uses the refactored dialog class
        """
        show_error_dialog(self.root, title, message, errors)

    def _update_mods_worker(self, mod_index=0, errors=None, success_count=0):
        """Recursively update mods with delays between each one"""
        if errors is None:
            errors = []
        
        mods = self._get_mods()
        
        if mod_index >= len(mods):
            # close the popup
            self.update_progress_dialog.close()

            if errors:
                # create scrollable error dialog for long error messages
                self._show_error_dialog("Update Errors", "Some mods failed to update:", errors)
            else:
                messagebox.showinfo("Update Complete", f"Successfully updated {success_count} mods.", parent=self.root)
            return
        
        mod = mods[mod_index]
        
        # update status label
        mod_name = self._get_mod_display_name(mod)
        self.update_progress_dialog.update_status(
            f"Updating... ({mod_index+1}/{len(mods)})\n{mod_name}"
        )
        
        try:
            self._download_and_extract_mod(mod)
            success_count += 1
        except Exception as e:
            # append as tuple (name, error) for the dialog
            errors.append((mod_name, str(e)))
            logging.error(f"Error updating mod {mod['url']}: {e}")
        
        # Schedule the next mod update after 50ms delay
        self.root.after(50, lambda: self._update_mods_worker(mod_index + 1, errors, success_count))
    
    def _get_mod_display_name(self, mod):
        """Extract a clean display name from a mod entry"""
        url = mod['url']
        github_zip = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/archive/(?:refs/(?:heads|tags)/)?([^/]+)\.zip", url
        )
        if github_zip:
            user, repo, ref = github_zip.groups()
            return f"{user}/{repo}"
        return url
    
    def _download_and_extract_mod(self, mod):
        url = mod.get("url")
        mod_subdir = mod.get("mod_subdir", mod.get("subdir", ""))  # support old 'subdir'
        install_subdir = mod.get("install_subdir")
        keep_structure = mod.get("keep_structure", True)

        # If install_subdir is not defined, None, blank, or '.', always use <mod_install_dir>/mods
        if not install_subdir or install_subdir == ".":
            base_install_dir = os.path.join(os.path.abspath(self.logic.mod_install_dir), "mods")
        else:
            # If install_subdir is absolute, use as is; else, join with mod_install_dir
            if os.path.isabs(install_subdir):
                base_install_dir = install_subdir
            else:
                base_install_dir = os.path.join(os.path.abspath(self.logic.mod_install_dir), install_subdir)

        if not url:
            raise ValueError("No URL provided for mod")

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "mod.zip")

            logging.info(f"Downloading mod from {url}...")
            # Use streaming for better memory efficiency with large files
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Download in chunks
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"Download complete")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                namelist = zip_ref.namelist()
                logging.info("ZIP file contents:")
                for name in namelist:
                    logging.info(f" - {name}")

                # github zips often have a wrapper folder (e.g., "modname-master/").
                top_dirs = set()
                for name in namelist:
                    parts = name.split('/')
                    if len(parts) > 1 and parts[0]:
                        top_dirs.add(parts[0])
                
                # if all files are in one top-level dir, strip it.
                if len(top_dirs) == 1:
                    top_dir = list(top_dirs)[0]
                    logging.info(f"Detected single top-level directory in ZIP: {top_dir}")
                    root_prefix = top_dir + '/'
                else:
                    root_prefix = ''

                # navigate into subdirectory if specified by user.
                if mod_subdir:
                    root_prefix = root_prefix + mod_subdir.rstrip('/') + '/'

                members = [m for m in namelist if m.startswith(root_prefix)]

                if not members:
                    raise FileNotFoundError(f"No files found under '{mod_subdir}' in the archive")

                # extract files, stripping the prefix path.
                for member in members:
                    relative_path = member[len(root_prefix):].lstrip('/')
                    if not relative_path:
                        continue
                    target_file_path = os.path.join(base_install_dir, relative_path)

                    if member.endswith('/'):
                        os.makedirs(target_file_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                        with zip_ref.open(member) as source, open(target_file_path, "wb") as target:
                            shutil.copyfileobj(source, target)

                logging.info(f"Extracted '{mod_subdir or root_prefix}' to '{base_install_dir}'")

        self._refresh_installed_mods()

    def open_profile_manager(self):
        self.profile_manager_dialog = ProfileManagerDialog(
            self.root,
            on_create=self._create_profile,
            on_rename=self._rename_profile,
            on_delete=self._delete_profile,
            on_export=self._export_profile,
            on_import=self._import_profile,
            on_set_install_dir=self._set_mod_install_dir,
            current_profile_name=self.profile_var.get()
        )
    
    def _run_mod_viewer(self):
        selected = self.installed_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Select an installed folder to explore.", parent=self.root)
            return

        index = selected[0]
        folder_name = self.installed_listbox.get(index)
        folder_path = self._get_installed_folder_path(folder_name)

        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", f"Folder does not exist:\n{folder_path}", parent=self.root)
            return

        try:
            if sys.platform.startswith("win"):
                # Use os.path.normpath to normalize the path for Windows
                normalized_path = os.path.normpath(folder_path)
                batch_file = os.path.join("mod_manager", "run_mod_viewer.bat")
                cmd = ["cmd.exe", "/c", batch_file, normalized_path]
            else:
                batch_file = os.path.join("mod_manager", "run_mod_viewer.sh")
                cmd = ["bash", batch_file, folder_path]
            subprocess.Popen(cmd, cwd=os.getcwd())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch mod viewer:\n{e}", parent=self.root)

    def _get_installed_folder_path(self, folder_name):
        base = self._get_installed_folder_base()
        return os.path.join(base, folder_name)

    def _get_installed_folder_base(self):
        selected_display = self.folder_var.get()
        folder_type = self.folder_map.get(selected_display, "mods")
        return os.path.join(os.path.abspath(self.logic.mod_install_dir), folder_type)

    def _open_root_folder(self):
        """Open the game root directory (parent of mods dir) in the system file explorer."""
        mods_dir = os.path.abspath(self.logic.mod_install_dir)
        game_root = os.path.dirname(mods_dir)
        if not os.path.isdir(game_root):
            messagebox.showerror("Error", f"Game root directory does not exist:\n{game_root}", parent=self.root)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(game_root)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", game_root])
            else:
                subprocess.Popen(["xdg-open", game_root])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open game root directory:\n{e}", parent=self.root)