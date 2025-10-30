import os
import platform
import subprocess
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from zipfile import ZipFile
import tarfile
from io import BytesIO
import webbrowser
import re
import json

CONFIG_FILE = os.path.join("cfg", "mod_manager_config.json")
DEFAULT_INSTALL_DIR = os.path.join(os.getcwd(), "cataclysmbn-unstable")

def load_and_update_config():
    """Load configuration and ensure game_install_dir is set
    
    Returns:
        dict: Configuration dictionary
    """
    config = {}
    changed = False
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config, using defaults: {e}")
            config = {}
    
    # Ensure game_install_dir is present (launcher uses this for game installation)
    if "game_install_dir" not in config or not config["game_install_dir"]:
        # Use DEFAULT_INSTALL_DIR as the game installation directory
        config["game_install_dir"] = DEFAULT_INSTALL_DIR
        changed = True
    
    if changed:
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: Failed to save config: {e}")
    
    return config

config = load_and_update_config()
# Use game_install_dir for installing the game itself
INSTALL_DIR = os.path.abspath(config.get("game_install_dir", DEFAULT_INSTALL_DIR))

GITHUB_API = "https://api.github.com/repos/cataclysmbnteam/Cataclysm-BN/releases"
EXPERIMENTAL_API = "https://api.github.com/repos/cataclysmbnteam/Cataclysm-BN/releases/tags/experimental"


class CataInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cataclysm-BN Updater")
        self.root.resizable(False, False)

        self.releases = []
        self.selected_release = None
        self.use_experimental = tk.BooleanVar(value=False)

        # Experimental toggle
        exp_frame = tk.Frame(root)
        exp_frame.pack(padx=10, pady=(10, 5))
        tk.Checkbutton(exp_frame, text="Show Experimental Build", variable=self.use_experimental, command=self.toggle_experimental).pack(side=tk.LEFT)

        # Dropdown
        self.dropdown = ttk.Combobox(root, state="readonly", width=60)
        self.dropdown.pack(padx=10, pady=(5, 10))
        self.dropdown.set("Loading releases...")

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()

        self.download_btn = tk.Button(btn_frame, text="Download & Install", command=self.download_selected)
        self.download_btn.grid(row=0, column=0, padx=5)

        self.changelog_btn = tk.Button(btn_frame, text="View Changelog", command=self.show_changelog)
        self.changelog_btn.grid(row=0, column=1, padx=5)
        
        self.installed_version_var = tk.StringVar()
        self.installed_version_var.set("Installed version: (not installed)")

        self.installed_version_label = tk.Label(root, textvariable=self.installed_version_var)
        self.installed_version_label.pack()

        self.launch_btn = tk.Button(root, text="Launch Game", command=self.launch_game, bg="green", fg="white")
        self.launch_btn.pack(pady=10)

        # load installed version immediately (fast)
        self.load_installed_version()
        
        # fetch releases after window is shown (slower, async)
        self.root.after(100, self.fetch_releases)

    def save_installed_version(self, version):
        """Save the installed game version
        
        Args:
            version: Game version string to save
        """
        version_file = "version.json"
        data = {}
        
        # Load existing version.json
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load version file: {e}")
        
        # Update only the game_version field
        data["game_version"] = version
        
        # Ensure program_version and update_url exist
        if "program_version" not in data:
            data["program_version"] = "1.0.5"
        if "update_url" not in data:
            data["update_url"] = "https://api.github.com/repos/shmakota/cata_git_mod_manager/releases/latest"
        
        try:
            with open(version_file, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except (IOError, OSError) as e:
            messagebox.showerror("Error", f"Failed to save version information: {e}")

    def load_installed_version(self):
        """Load the installed game version"""
        version_file = "version.json"
        version = "(not installed)"
        
        if os.path.exists(version_file):
            try:
                with open(version_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    # Load game_version, not program_version
                    version = data.get("game_version", "")
                    if not version:
                        version = "(unknown)"
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load version: {e}")
                version = "(unknown)"
        
        self.installed_version_var.set(f"Installed version: {version}")

    def fetch_releases(self):
        try:
            # show loading state
            self.dropdown.set("Loading releases from GitHub...")
            self.root.update()
            
            if self.use_experimental.get():
                response = requests.get(EXPERIMENTAL_API)
                response.raise_for_status()
                release_data = response.json()
                all_releases = [release_data]  # Wrap single release in list
            else:
                response = requests.get(GITHUB_API)
                response.raise_for_status()
                all_releases = response.json()

            system = platform.system().lower()
            ext = ".zip" if "windows" in system else ".tar.gz"
            keyword = "windows" if "windows" in system else "linux"

            filtered = []
            for release in all_releases:
                for asset in release.get("assets", []):
                    name = asset["name"].lower()
                    # Check for tiles build and skip experimental unless checkbox is on
                    is_experimental = "experimental" in name
                    if name.endswith(ext) and keyword in name and "tiles" in name:
                        if not self.use_experimental.get() and is_experimental:
                            continue
                        if self.use_experimental.get() and not is_experimental:
                            continue
                        filtered.append({
                            "name": release["name"],
                            "description": release.get("body", "No changelog available."),
                            "asset": asset
                        })
                        break

            self.releases = filtered[:10]
            self.dropdown["values"] = [r["name"] for r in self.releases]
            if self.releases:
                self.dropdown.current(0)
                self.selected_release = self.releases[0]
                self.dropdown.bind("<<ComboboxSelected>>", self.on_select)
            else:
                self.dropdown.set("No releases found")
        except Exception as e:
            self.dropdown.set("Failed to load releases")
            messagebox.showerror("Error", f"Failed to fetch releases:\n{e}")
    
    def toggle_experimental(self):
        self.fetch_releases()

    def on_select(self, event):
        idx = self.dropdown.current()
        self.selected_release = self.releases[idx]

    def show_changelog(self):
        if not self.selected_release:
            return

        raw_text = self.selected_release["description"] or "No changelog available."
        release_title = self.selected_release["name"]

        build_pattern = r"These are the outputs for the build of commit [a-f0-9]{40}"
        cleaned_text = re.sub(build_pattern, "", raw_text).strip()

        pr_pattern = r"https://github\.com/cataclysmbnteam/Cataclysm-BN/pull/(\d+)"
        pr_links = re.findall(pr_pattern, cleaned_text)

        display_text = re.sub(pr_pattern, r"Pull Request #\1", cleaned_text)

        changelog_win = tk.Toplevel(self.root)
        changelog_win.title(f"Changelog: {release_title}")
        changelog_win.geometry("800x600")
        changelog_win.minsize(400, 300)
        changelog_win.resizable(True, True)

        container = tk.Frame(changelog_win, padx=10, pady=10)
        container.pack(fill="both", expand=True)

        title_label = tk.Label(container, text=release_title, font=("Helvetica", 16, "bold"), anchor="w")
        title_label.pack(anchor="w", pady=(0, 10))

        text_frame = tk.Frame(container)
        text_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        text_widget = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Courier New", 11),
            padx=5,
            pady=5,
            bg="#f9f9f9"
        )
        text_widget.pack(fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)

        text_widget.insert("1.0", display_text)
        text_widget.configure(state="disabled")

        text_widget.configure(state="normal")

        for match in re.finditer(r"Pull Request #(\d+)", display_text):
            pr_number = match.group(1)
            start_idx = f"1.0 + {match.start()} chars"
            end_idx = f"1.0 + {match.end()} chars"
            url = f"https://github.com/cataclysmbnteam/Cataclysm-BN/pull/{pr_number}"
            text_widget.tag_add(f"pr_{pr_number}", start_idx, end_idx)
            text_widget.tag_config(f"pr_{pr_number}", foreground="blue", underline=True)
            text_widget.tag_bind(f"pr_{pr_number}", "<Enter>", lambda e: text_widget.config(cursor="hand2"))
            text_widget.tag_bind(f"pr_{pr_number}", "<Leave>", lambda e: text_widget.config(cursor=""))
            text_widget.tag_bind(f"pr_{pr_number}", "<Button-1>", lambda e, url=url: webbrowser.open_new_tab(url))

        text_widget.configure(state="disabled")

    def download_selected(self):
        if not self.selected_release:
            return

        asset = self.selected_release["asset"]
        url = asset["browser_download_url"]
        name = asset["name"]

        try:
            # create non-blocking status window
            status_window = tk.Toplevel(self.root)
            status_window.title("Downloading...")
            status_window.geometry("400x100")
            status_window.transient(self.root)
            status_window.resizable(False, False)
            
            status_label = tk.Label(status_window, text=f"Downloading {name}...\nPlease wait...", pady=20)
            status_label.pack()
            
            self.root.update()
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            data = BytesIO(response.content)
            
            # close status window
            status_window.destroy()

            os.makedirs(INSTALL_DIR, exist_ok=True)

            if name.endswith(".zip"):
                with ZipFile(data) as zipf:
                    members = zipf.namelist()
                    # Strip both the archive wrapper (like "cataclysmbn-unstable-master")
                    # and any nested "cataclysmbn-unstable" folder
                    for member in members:
                        parts = member.split('/')
                        # Remove empty parts and filter out the first directory (usually the archive name)
                        filtered_parts = [p for p in parts if p]  # Remove empty strings
                        
                        if len(filtered_parts) <= 1:
                            continue
                        
                        # Skip the first part (archive name like "cataclysmbn-unstable-master")
                        # and also skip 'cataclysmbn-unstable' if it's nested
                        target_parts = filtered_parts[1:]
                        if len(target_parts) > 0 and target_parts[0] == 'cataclysmbn-unstable':
                            target_parts = target_parts[1:]
                        
                        target_path = '/'.join(target_parts)
                        if not target_path:
                            continue
                        dest = os.path.join(INSTALL_DIR, target_path)
                        if member.endswith('/'):
                            os.makedirs(dest, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            with zipf.open(member) as source, open(dest, "wb") as target:
                                target.write(source.read())
            elif name.endswith(".tar.gz"):
                with tarfile.open(fileobj=data, mode="r:gz") as tarf:
                    for member in tarf.getmembers():
                        parts = member.name.split('/')
                        # Remove empty parts
                        filtered_parts = [p for p in parts if p]
                        
                        if len(filtered_parts) <= 1:
                            continue
                        
                        # Skip the first part (archive name) and also skip 'cataclysmbn-unstable' if nested
                        target_parts = filtered_parts[1:]
                        if len(target_parts) > 0 and target_parts[0] == 'cataclysmbn-unstable':
                            target_parts = target_parts[1:]
                        
                        if target_parts:
                            member.name = '/'.join(target_parts)
                            tarf.extract(member, INSTALL_DIR)
            else:
                raise ValueError("Unsupported archive format.")

            self.save_installed_version(self.selected_release["name"])
            self.load_installed_version()
            messagebox.showinfo("Success", f"Installed {name} to {INSTALL_DIR}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to download or extract:\n{e}")

    def launch_game(self):
        exe_path = ""
        system = platform.system()

        if system == "Windows":
            exe_name = "cataclysm-bn-tiles.exe"
        else:
            exe_name = "cataclysm-bn-tiles"

        exe_path = os.path.join(INSTALL_DIR, exe_name)

        if not os.path.isfile(exe_path):
            for root, dirs, files in os.walk(INSTALL_DIR):
                if exe_name in files:
                    exe_path = os.path.join(root, exe_name)
                    break
            else:
                messagebox.showwarning("Not Found", f"'{exe_name}' not found in /cataclysmbn-unstable.")
                return

        try:
            if system != "Windows":
                os.chmod(exe_path, 0o755)
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch game:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CataInstallerApp(root)
    root.mainloop()
