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

# Setup logging
logging.basicConfig(
    filename='mod_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
PROFILES_FILE = "mod_manager/cfg/mod_profiles.json"
CONFIG_FILE = "mod_manager/cfg/mod_manager_config.json"
# It is not necessary to store files in this folder at all, just a default location for organization
DEFAULT_MODS_DIR = "mods/cbn"



class ModManagerApp:
    # hopefully this is stable...
    version = "1.0.2"

    def __init__(self, root):
        self.root = root
        self.root.title("Cataclysm Mod Manager v" + self.version)
        self.root.geometry("950x650")
        self.root.minsize(950, 650)
    
        self._ensure_config_files_exist()
        self.clear_log()

        self.mod_install_dir = DEFAULT_MODS_DIR
        self.profiles = {}
        self.current_profile = None
        
        self._load_config()
        self._load_profiles()

        self._build_ui()

        if not self.profiles:
            self._create_profile("default")

        if not self.current_profile or self.current_profile not in self.profiles:
            self.current_profile = list(self.profiles.keys())[0]

        self.profile_var.set(self.current_profile)
        self._refresh_profile_combo()
        self._refresh_mod_list()
        self._refresh_installed_mods()
    
    def clear_log(self, log_file='mod_debug.log'):
        """Clears the contents of the specified log file."""
        with open(log_file, 'w'):
            pass  # Just open in write mode to truncate the file
        logging.info('Log file has been cleared.')
    
    def _ensure_config_files_exist(self):
        # Ensure default mod directory exists
        if not os.path.isdir(DEFAULT_MODS_DIR):
            try:
                os.makedirs(DEFAULT_MODS_DIR)
                logging.info(f"Created default mod directory at: {DEFAULT_MODS_DIR}")
            except Exception as e:
                logging.error(f"Failed to create default mod directory: {e}")

        # Ensure config file exists
        if not os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump({"mod_install_dir": DEFAULT_MODS_DIR}, f, indent=2)
                logging.info("Created config file with default mod path.")
            except Exception as e:
                logging.error(f"Failed to create config file: {e}")

        # Ensure profiles file exists
        profiles_dir = os.path.dirname(PROFILES_FILE)
        if not os.path.isdir(profiles_dir):
            try:
                os.makedirs(profiles_dir)
                logging.info(f"Created profiles directory at: {profiles_dir}")
            except Exception as e:
                logging.error(f"Failed to create profiles directory: {e}")

        if not os.path.isfile(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "w") as f:
                    json.dump({}, f, indent=2)  # Empty dict for initial profiles
                logging.info(f"Created empty profiles file at: {PROFILES_FILE}")
            except Exception as e:
                logging.error(f"Failed to create profiles file: {e}")
    
    # --- Config Management ---
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                self.mod_install_dir = config.get("mod_install_dir", DEFAULT_MODS_DIR)
                logging.info("Config loaded successfully.")
            except Exception as e:
                logging.error(f"Error loading config: {e}")
                self.mod_install_dir = DEFAULT_MODS_DIR

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"mod_install_dir": self.mod_install_dir}, f, indent=2)
            logging.info("Config saved successfully.")
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    # --- Profiles Management ---
    def _load_profiles(self):
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r") as f:
                    data = json.load(f)
                self.profiles = data.get("profiles", {})
                self.current_profile = data.get("current_profile")
                self._convert_old_profiles()
                if self.current_profile in self.profiles:
                    self.mod_install_dir = self.profiles[self.current_profile].get("mod_install_dir", DEFAULT_MODS_DIR)
                logging.info("Profiles loaded successfully.")
            except Exception as e:
                logging.error(f"Error loading profiles: {e}")
                self.profiles = {}
                self.current_profile = None
        else:
            self.profiles = {}
            self.current_profile = None

    def _save_profiles(self):
        # Save current profile's mod_install_dir before saving profiles
        if self.current_profile in self.profiles:
            profile = self.profiles[self.current_profile]
            if isinstance(profile, dict):
                profile["mod_install_dir"] = self.mod_install_dir
            else:
                self.profiles[self.current_profile] = {"mods": profile, "mod_install_dir": self.mod_install_dir}

        try:
            with open(PROFILES_FILE, "w") as f:
                json.dump({"profiles": self.profiles, "current_profile": self.current_profile}, f, indent=2)
            logging.info("Profiles saved successfully.")
        except Exception as e:
            logging.error(f"Error saving profiles: {e}")

    def _convert_old_profiles(self):
        # Convert any old-format profile (list) to new dict format
        for name, pdata in list(self.profiles.items()):
            if isinstance(pdata, list):
                self.profiles[name] = {"mods": pdata, "mod_install_dir": DEFAULT_MODS_DIR}
    
    def _export_profile(self):
        if not self.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return

        profile_data = self.profiles.get(self.current_profile)
        if not profile_data:
            messagebox.showerror("Error", "Current profile data not found.", parent=self.root)
            return

        export_path = filedialog.asksaveasfilename(
            title="Export Profile",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.current_profile}.json",
            parent=self.root
        )
        if not export_path:
            return

        try:
            with open(export_path, "w") as f:
                json.dump({self.current_profile: profile_data}, f, indent=2)
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

            # Expecting data like: {"profile_name": {profile_data}}
            for name, pdata in data.items():
                if name in self.profiles:
                    overwrite = messagebox.askyesno(
                        "Overwrite Profile?",
                        f"Profile '{name}' already exists. Overwrite?",
                        parent=self.root
                    )
                    if not overwrite:
                        continue
                self.profiles[name] = pdata

            # Auto-switch to last imported profile
            self.current_profile = list(data.keys())[-1]
            self.profile_var.set(self.current_profile)
            self._save_profiles()
            self._refresh_profile_combo()
            self._refresh_mod_list()

            if hasattr(self, "profile_manager_dialog"):
                new_profile_name = self.profile_var.get()  # or whatever is current
                self.profile_manager_dialog.update_profile_name(new_profile_name)
            
            messagebox.showinfo("Import Success", "Profile(s) imported successfully.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import profile:\n{e}", parent=self.root)
         # Then update label if dialog is open
    
    def _export_profile(self):
        if not self.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return

        profile_data = self.profiles.get(self.current_profile)
        if not profile_data:
            messagebox.showerror("Error", "Current profile data not found.", parent=self.root)
            return

        export_path = filedialog.asksaveasfilename(
            title="Export Profile",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.current_profile}.json",
            parent=self.root
        )
        if not export_path:
            return

        try:
            with open(export_path, "w") as f:
                json.dump({self.current_profile: profile_data}, f, indent=2)
            messagebox.showinfo("Export Success", f"Profile exported to:\n{export_path}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export profile:\n{e}", parent=self.root)

    def _refresh_installed_mods(self):
        self.installed_listbox.delete(0, tk.END)
        if not os.path.isdir(self.mod_install_dir):
            return
        try:
            entries = sorted([d for d in os.listdir(self.mod_install_dir) if os.path.isdir(os.path.join(self.mod_install_dir, d))])
            for folder in entries:
                self.installed_listbox.insert(tk.END, folder)
        except Exception as e:
            logging.error(f"Error listing installed mods: {e}")

    def _delete_installed_mod(self):
        selected = self.installed_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Select an installed mod folder to delete.", parent=self.root)
            return

        index = selected[0]
        folder_name = self.installed_listbox.get(index)
        folder_path = os.path.join(self.mod_install_dir, folder_name)

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete installed mod folder:\n{folder_name}?", parent=self.root)
        if not confirm:
            return

        try:
            # Use shutil.rmtree to delete the folder and all its contents
            import shutil
            shutil.rmtree(folder_path)
            messagebox.showinfo("Deleted", f"Deleted installed mod folder: {folder_name}", parent=self.root)
            self._refresh_installed_mods()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete folder:\n{e}", parent=self.root)
    

    def _open_installed_mod_folder(self):
        selected = self.installed_listbox.curselection()
        if not selected:
            messagebox.showwarning("No Selection", "Select an installed mod folder to open.", parent=self.root)
            return

        index = selected[0]
        folder_name = self.installed_listbox.get(index)
        folder_path = os.path.join(self.mod_install_dir, folder_name)

        if not os.path.exists(folder_path):
            messagebox.showerror("Error", f"Folder does not exist:\n{folder_path}", parent=self.root)
            return

        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:  # Linux and others
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
        installed_mods_frame.grid(row=2, column=1, rowspan=2, sticky="nsew", padx=(10, 0))  # rowspan=2 is key

        tk.Label(installed_mods_frame, text="Installed Mods:").pack(anchor="w")

        installed_list_container = tk.Frame(installed_mods_frame)
        installed_list_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.installed_listbox = tk.Listbox(installed_list_container, width=40, height=20, activestyle='none')
        self.installed_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        installed_scrollbar = ttk.Scrollbar(installed_list_container, orient=tk.VERTICAL, command=self.installed_listbox.yview)
        installed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.installed_listbox.config(yscrollcommand=installed_scrollbar.set)

        button_frame = tk.Frame(installed_mods_frame)
        button_frame.pack(pady=(5, 0), fill=tk.X)

        self.installed_button = tk.Button(button_frame, text="Delete", command=self._delete_installed_mod)
        self.installed_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.open_folder_button = tk.Button(button_frame, text="Open Folder", command=self._open_installed_mod_folder)
        self.open_folder_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.refresh_installed_button = tk.Button(button_frame, text="Refresh", command=self._refresh_installed_mods)
        self.refresh_installed_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.explore_button = tk.Button(button_frame, text="Explore", command=self._run_mod_viewer)
        self.explore_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # Bottom — Open Mod Folder (spans both columns)
        open_mod_btn_frame = tk.Frame(self.frame)
        open_mod_btn_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        open_mod_btn = tk.Button(open_mod_btn_frame, text="Open Mod Folder", command=self._open_mod_folder)
        open_mod_btn.pack(fill=tk.X)

        # Grid weight config for resizing
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=0)

    # --- Profile Methods ---
    def _create_profile(self, default_name=None):
        if default_name:
            name = default_name
        else:
            name = simpledialog.askstring("New Profile", "Enter profile name:", parent=self.root)
            if not name:
                return
            if name in self.profiles:
                messagebox.showerror("Error", f"Profile '{name}' already exists.", parent=self.root)
                return
        self.profiles[name] = {"mods": [], "mod_install_dir": DEFAULT_MODS_DIR}
        self.current_profile = name
        self.profile_var.set(name)
        self._save_profiles()
        self._refresh_profile_combo()
        self._refresh_mod_list()

        if hasattr(self, "profile_manager_dialog"):
            new_profile_name = self.profile_var.get()  # or whatever is current
            self.profile_manager_dialog.update_profile_name(new_profile_name)

    def _rename_profile(self):
        if not self.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return
        new_name = simpledialog.askstring("Rename Profile", "Enter new profile name:", initialvalue=self.current_profile, parent=self.root)
        if not new_name or new_name == self.current_profile:
            return
        if new_name in self.profiles:
            messagebox.showerror("Error", f"Profile '{new_name}' already exists.", parent=self.root)
            return
        self.profiles[new_name] = self.profiles.pop(self.current_profile)
        self.current_profile = new_name
        self.profile_var.set(new_name)
        self._save_profiles()
        self._refresh_profile_combo()
        self._refresh_mod_list()

        if hasattr(self, "profile_manager_dialog"):
            new_profile_name = self.profile_var.get()  # or whatever is current
            self.profile_manager_dialog.update_profile_name(new_profile_name)

    def _delete_profile(self):
        if not self.current_profile:
            messagebox.showerror("Error", "No profile selected.", parent=self.root)
            return
        if len(self.profiles) == 1:
            messagebox.showerror("Error", "Cannot delete the only profile.", parent=self.root)
            return
        confirm = messagebox.askyesno("Delete Profile", f"Are you sure you want to delete profile '{self.current_profile}'?", parent=self.root)
        if confirm:
            del self.profiles[self.current_profile]
            self.current_profile = next(iter(self.profiles.keys()), None)
            self.profile_var.set(self.current_profile)
            self._save_profiles()
            self._refresh_profile_combo()
            self._refresh_mod_list()
            
            if hasattr(self, "profile_manager_dialog"):
                new_profile_name = self.profile_var.get()  # or whatever is current
                self.profile_manager_dialog.update_profile_name(new_profile_name)

    def _refresh_profile_combo(self):
        profiles_list = list(self.profiles.keys())
        self.profile_combo['values'] = profiles_list

    def _on_profile_change(self, event=None):
        selected = self.profile_var.get()
        if selected and selected != self.current_profile:
            self.current_profile = selected
            profile = self.profiles.get(self.current_profile, {})
            if isinstance(profile, dict):
                self.mod_install_dir = profile.get("mod_install_dir", DEFAULT_MODS_DIR)
            else:
                self.mod_install_dir = DEFAULT_MODS_DIR
            self._save_profiles()
            self._refresh_mod_list()

    # --- Mod List Management ---
    def _get_mods(self):
        profile = self.profiles.get(self.current_profile, {})
        if isinstance(profile, dict):
            return profile.get("mods", [])
        return profile  # support old format

    def _set_mods(self, mods):
        profile = self.profiles.get(self.current_profile, {})
        if isinstance(profile, dict):
            profile["mods"] = mods
        else:
            self.profiles[self.current_profile] = mods
        self._save_profiles()

    def _refresh_mod_list(self):
        self.listbox.delete(0, tk.END)
        for mod in self._get_mods():
            keep_text = "Auto-detect" if mod.get("keep_structure") else "Keep structure"
            subdir = mod.get("subdir", "")

            url = mod['url']
            clean_url = url  # default fallback

            # Handle GitHub archive URLs
            github_zip = re.match(
                r"https?://github\.com/([^/]+)/([^/]+)/archive/(?:refs/(?:heads|tags)/)?([^/]+)\.zip", url
            )
            if github_zip:
                user, repo, ref = github_zip.groups()
                clean_url = f"{user}/{repo}"

            display = f"{clean_url}  |  subdir: {subdir}  |  {keep_text}"
            self.listbox.insert(tk.END, display)

    def _fix_github_url(self, url):
        url = url.rstrip('/')
        if url.startswith("https://github.com/") and not url.endswith(".zip"):
            return f"{url}/archive/refs/heads/master.zip"
        return url


    def _add_mod(self):
        url = simpledialog.askstring("GitHub URL", "Enter GitHub ZIP URL:", parent=self.root)
        if not url:
            return
        url = self._fix_github_url(url)
        subdir = simpledialog.askstring("Subdirectory", "Enter mod subdirectory (optional):", parent=self.root) or ""
        keep_structure = messagebox.askyesno("Auto Detect", "Automatically find folder structure? (Yes = auto-detect modinfo.json)", parent=self.root)
        mods = self._get_mods()
        mods.append({"url": url, "subdir": subdir, "keep_structure": keep_structure})
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

        dialog = EditModDialog(self.root, mod.get("url", ""), mod.get("subdir", ""), mod.get("keep_structure", False))
        self.root.wait_window(dialog)

        if dialog.result:
            url, subdir, keep_structure = dialog.result
            url = self._fix_github_url(url)
            mods[index] = {"url": url, "subdir": subdir, "keep_structure": keep_structure}
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
        new_dir = filedialog.askdirectory(title="Select Mod Install Directory", initialdir=self.mod_install_dir)
        if new_dir:
            self.mod_install_dir = new_dir
            if self.current_profile and self.current_profile in self.profiles:
                profile = self.profiles[self.current_profile]
                if isinstance(profile, dict):
                    profile["mod_install_dir"] = new_dir
                else:
                    self.profiles[self.current_profile] = {"mods": profile, "mod_install_dir": new_dir}
                self._save_profiles()

            # If dialog open, update any UI if needed (example: update profile label)
            if hasattr(self, "profile_manager_dialog"):
                self.profile_manager_dialog.update_profile_name(self.current_profile)

    def _open_mod_folder(self):
        if not os.path.isdir(self.mod_install_dir):
            messagebox.showerror("Error", f"Mod install directory does not exist:\n{self.mod_install_dir}", parent=self.root)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self.mod_install_dir)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", self.mod_install_dir])
            else:
                subprocess.Popen(["xdg-open", self.mod_install_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory:\n{e}", parent=self.root)

    def _update_mods(self):
        mods = self._get_mods()
        if not mods:
            messagebox.showinfo("Info", "No mods to update.", parent=self.root)
            return

        # Show updating popup
        self.update_popup = Toplevel(self.root)
        self.update_popup.title("Updating Mods")
        self.update_popup.geometry("300x100")
        self.update_popup.transient(self.root)
        self.update_popup.grab_set()
        Label(self.update_popup, text="Updating...").pack(expand=True, pady=20)

        self.root.after(100, self._update_mods_worker)

    def _update_mods_worker(self):
        mods = self._get_mods()
        errors = []
        success_count = 0

        for mod in mods:
            try:
                self._download_and_extract_mod(mod)
                success_count += 1
            except Exception as e:
                errors.append(f"{mod['url']}: {e}")
                logging.error(f"Error updating mod {mod['url']}: {e}")

        # Close the popup
        self.update_popup.destroy()

        if errors:
            msg = "Some mods failed to update:\n" + "\n".join(errors)
            messagebox.showerror("Update Errors", msg, parent=self.root)
        else:
            messagebox.showinfo("Update Complete", f"Successfully updated {success_count} mods.", parent=self.root)
    
    def _download_and_extract_mod(self, mod):
        url = mod.get("url")
        subdir = mod.get("subdir", "")
        keep_structure = mod.get("keep_structure", True)

        if not url:
            raise ValueError("No URL provided for mod")

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "mod.zip")

            logging.info(f"Downloading mod from {url}...")
            response = requests.get(url, timeout=20)
            response.raise_for_status()

            with open(zip_path, "wb") as f:
                f.write(response.content)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                logging.info("ZIP file contents:")
                for name in zip_ref.namelist():
                    logging.info(f" - {name}")

                if keep_structure:
                    # Define root inside zip to search for mods (all files under subdir if specified, else whole zip)
                    root_prefix = subdir.rstrip('/') + '/' if subdir else ""

                    # Find all modinfo.json files recursively under root_prefix
                    modinfo_paths = [f for f in zip_ref.namelist() if f.startswith(root_prefix) and f.endswith('modinfo.json')]

                    if not modinfo_paths:
                        raise FileNotFoundError(f"No modinfo.json found under '{subdir}' in the archive")

                    # For each modinfo.json, extract its parent folder as a separate mod
                    extracted_mods = set()
                    for modinfo_path in modinfo_paths:
                        parts = modinfo_path.split('/')
                        mod_folder = '/'.join(parts[:-1])  # folder containing modinfo.json

                        if mod_folder in extracted_mods:
                            continue  # avoid extracting the same folder twice
                        extracted_mods.add(mod_folder)

                        folder_name = mod_folder.split('/')[-1] if mod_folder else ''
                        dest_folder = os.path.join(self.mod_install_dir, folder_name)
                        os.makedirs(dest_folder, exist_ok=True)

                        # Extract all members belonging to this mod folder
                        members = [m for m in zip_ref.namelist() if m == mod_folder or m.startswith(mod_folder + '/')]
                        for member in members:
                            relative_path = member[len(mod_folder):].lstrip('/')
                            target_file_path = os.path.join(dest_folder, relative_path)

                            if member.endswith('/'):
                                os.makedirs(target_file_path, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                                with zip_ref.open(member) as source, open(target_file_path, "wb") as target:
                                    shutil.copyfileobj(source, target)

                        logging.info(f"Extracted mod folder '{mod_folder}' as '{folder_name}' in {dest_folder}")

                else:
                    # Extract all files exactly as they are in the zip
                    extract_path = os.path.join(self.mod_install_dir)
                    zip_ref.extractall(extract_path)
                    logging.info(f"Extracted entire archive with full structure to {extract_path}")

            logging.info(f"Mod {url} installed successfully.")
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
            messagebox.showwarning("No Selection", "Select an installed mod folder to explore.", parent=self.root)
            return

        index = selected[0]
        folder_name = self.installed_listbox.get(index)
        folder_path = os.path.join(self.mod_install_dir, folder_name)

        if not os.path.isdir(folder_path):
            messagebox.showerror("Error", f"Mod folder does not exist:\n{folder_path}", parent=self.root)
            return

        try:
            if sys.platform.startswith("win"):
                cmd = ["cmd.exe", "/c", "run_mod_viewer.bat", folder_path]
            else:
                cmd = ["bash", "run_mod_viewer.sh", folder_path]

            subprocess.Popen(cmd, cwd=os.getcwd())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch mod viewer:\n{e}", parent=self.root)