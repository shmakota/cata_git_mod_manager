import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
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

# Setup logging
logging.basicConfig(
    filename='mod_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
PROFILES_FILE = "mod_profiles.json"
CONFIG_FILE = "mod_manager_config.json"
DEFAULT_MODS_DIR = "cdda/mods"


class ModManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cataclysm Mod Manager")
        self.root.geometry("950x650")
        self.root.minsize(950, 650)

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

            messagebox.showinfo("Import Success", "Profile(s) imported successfully.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import profile:\n{e}", parent=self.root)
    
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
    
    
    # --- UI Construction ---
    def _build_ui(self):
        self.frame = tk.Frame(self.root, padx=10, pady=10)
        self.frame.grid(row=0, column=0, sticky="nsew")

        # Profile management frame — SPANS BOTH columns (0 and 1)
        profile_frame = tk.Frame(self.frame)
        profile_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tk.Label(profile_frame, text="Profile:").pack(side=tk.LEFT, padx=(0, 5))
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly", width=30)
        self.profile_combo.pack(side=tk.LEFT)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_change)

        for text, cmd in [("New", self._create_profile),
                        ("Rename", self._rename_profile),
                        ("Delete", self._delete_profile),
                        ("Export", self._export_profile),
                        ("Import", self._import_profile)]:
            btn = tk.Button(profile_frame, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=5)

        tk.Button(profile_frame, text="Set Mod Install Directory", command=self._set_mod_install_dir).pack(side=tk.LEFT, padx=10)

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

        self.listbox = tk.Listbox(listbox_frame, width=50, height=20, activestyle='none')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)

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

        self.installed_button = tk.Button(installed_mods_frame, text="Delete (Unrecoverable)", command=self._delete_installed_mod)
        self.installed_button.pack(side=tk.LEFT, fill=tk.X, pady=(5, 0))

        # 🔄 Refresh Installed Mods button
        self.refresh_installed_button = tk.Button(installed_mods_frame, text="Refresh Installed Mods", command=self._refresh_installed_mods)
        self.refresh_installed_button.pack(side=tk.RIGHT, fill=tk.X, pady=(5, 0), padx=(10, 0))

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
            keep_text = "Keep structure" if mod.get("keep_structure") else "Auto-detect"
            subdir = mod.get("subdir", "")
            display = f"{mod['url']}  |  subdir: {subdir}  |  {keep_text}"
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
        keep_structure = messagebox.askyesno("Keep Structure", "Keep original folder structure? (No = auto-detect modinfo.json)", parent=self.root)
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

    # --- Other actions ---
    def _set_mod_install_dir(self):
        new_dir = filedialog.askdirectory(title="Select Mod Install Directory", initialdir=self.mod_install_dir)
        if new_dir:
            self.mod_install_dir = new_dir
            # Save to current profile mod_install_dir
            if self.current_profile and self.current_profile in self.profiles:
                profile = self.profiles[self.current_profile]
                if isinstance(profile, dict):
                    profile["mod_install_dir"] = new_dir
                else:
                    self.profiles[self.current_profile] = {"mods": profile, "mod_install_dir": new_dir}
                self._save_profiles()

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
        #self._disable_ui()
        self.root.after(100, self._update_mods_worker)

    def _disable_ui(self):
        for child in self.frame.winfo_children():
            child.configure(state="disabled")

    def _enable_ui(self):
        for child in self.frame.winfo_children():
            child.configure(state="normal")

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

        #self._enable_ui()
        if errors:
            msg = "Some mods failed to update:\n" + "\n".join(errors)
            messagebox.showerror("Update Errors", msg, parent=self.root)
        else:
            messagebox.showinfo("Update Complete", f"Successfully updated {success_count} mods.", parent=self.root)
    def _download_and_extract_mod(self, mod):
        url = mod.get("url")
        subdir = mod.get("subdir", "")
        keep_structure = mod.get("keep_structure", False)

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
                    # Extract all files exactly as they are in the zip
                    extract_path = os.path.join(self.mod_install_dir)
                    zip_ref.extractall(extract_path)
                    logging.info(f"Extracted entire archive with full structure to {extract_path}")

                elif subdir:
                    # Extract the specified subdirectory inside the zip, preserving its folder name
                    members = [m for m in zip_ref.namelist() if m.startswith(subdir + '/') or m == subdir]

                    if not members:
                        raise FileNotFoundError(f"Subdirectory '{subdir}' not found in the archive")

                    target_path = os.path.join(self.mod_install_dir, os.path.basename(subdir))
                    os.makedirs(target_path, exist_ok=True)

                    for member in members:
                        relative_path = member[len(subdir):].lstrip('/')
                        target_file_path = os.path.join(target_path, relative_path)

                        if member.endswith('/'):
                            os.makedirs(target_file_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                            with zip_ref.open(member) as source, open(target_file_path, "wb") as target:
                                shutil.copyfileobj(source, target)

                    logging.info(f"Extracted subdirectory '{subdir}' as '{os.path.basename(subdir)}' in {target_path}")

                else:
                    # Auto-detect mod folder by searching for modinfo.json inside the zip
                    mod_folders = set()

                    for file in zip_ref.namelist():
                        if file.endswith("modinfo.json"):
                            parts = file.split('/')
                            if len(parts) > 1:
                                # The mod folder is the parent directory of modinfo.json
                                mod_folder_path = '/'.join(parts[:-1])
                                mod_folders.add(mod_folder_path)
                            else:
                                mod_folders.add(parts[0])

                    if not mod_folders:
                        raise FileNotFoundError("No modinfo.json found in the archive")

                    for mod_folder in mod_folders:
                        # Folder name is the last part of the path (e.g. "Material Plants")
                        folder_name = mod_folder.split('/')[-1]

                        dest_folder = os.path.join(self.mod_install_dir, folder_name)
                        os.makedirs(dest_folder, exist_ok=True)

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



            logging.info(f"Mod {url} installed successfully.")
            self._refresh_installed_mods()


class EditModDialog(tk.Toplevel):
    def __init__(self, parent, url="", subdir="", keep_structure=False):
        super().__init__(parent)
        self.title("Edit Mod")
        self.geometry("500x180")
        self.result = None

        self.url_var = tk.StringVar(value=url)
        self.subdir_var = tk.StringVar(value=subdir)
        self.keep_structure_var = tk.BooleanVar(value=keep_structure)

        self._build_ui()

        self.transient(parent)
        self.grab_set()
        self.wait_visibility()
        self.focus()

    def _build_ui(self):
        frame = tk.Frame(self, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="GitHub ZIP URL:").grid(row=0, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.url_var, width=60).grid(row=0, column=1, sticky="ew", pady=5)

        tk.Label(frame, text="Subdirectory (optional):").grid(row=1, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.subdir_var, width=60).grid(row=1, column=1, sticky="ew", pady=5)

        tk.Checkbutton(frame, text="Keep original folder structure", variable=self.keep_structure_var).grid(row=2, column=1, sticky="w", pady=5)

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="OK", width=10, command=self._on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy).pack(side=tk.LEFT)

        frame.grid_columnconfigure(1, weight=1)

    def _on_ok(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "URL cannot be empty.", parent=self)
            return
        subdir = self.subdir_var.get().strip()
        keep_structure = self.keep_structure_var.get()
        self.result = (url, subdir, keep_structure)
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModManagerApp(root)
    root.mainloop()
