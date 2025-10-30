"""
Business logic for Content Manager
Handles configuration, profiles, and mod operations
"""

import os
import json
import logging
import shutil
import tempfile
import zipfile
import requests
import re
from tkinter import messagebox

from .constants import (
    PROFILES_FILE,
    CONFIG_FILE,
    VERSION_FILE,
    DEFAULT_MODS_DIR,
    INSTALL_TYPE_DIRS
)


class ContentManagerLogic:
    """
    Business logic layer for Content Manager
    Handles all non-UI operations
    """
    
    def __init__(self, root=None):
        """
        Initialize logic layer
        
        Args:
            root: Parent tkinter window (for messageboxes)
        """
        self.root = root
        self.mod_install_dir = DEFAULT_MODS_DIR
        self.profiles = {}
        self.current_profile = None
    
    # ========== Utility Methods ==========
    
    @staticmethod
    def clear_log(log_file='mod_debug.log'):
        """clear the contents of the specified log file"""
        with open(log_file, 'w'):
            pass
        logging.info('Log file has been cleared.')
    
    def _ensure_config_files_exist(self):
        """ensure default directories and config files exist"""
        # ensure default mod directory exists
        if not os.path.isdir(DEFAULT_MODS_DIR):
            try:
                os.makedirs(DEFAULT_MODS_DIR)
                logging.info(f"Created default mod directory at: {DEFAULT_MODS_DIR}")
            except Exception as e:
                logging.error(f"Failed to create default mod directory: {e}")

        # ensure config file exists
        if not os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump({"mod_install_dir": DEFAULT_MODS_DIR}, f, indent=2)
                logging.info("Created config file with default mod path.")
            except Exception as e:
                logging.error(f"Failed to create config file: {e}")

        # ensure profiles file exists
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
                    json.dump({}, f, indent=2)
                logging.info(f"Created empty profiles file at: {PROFILES_FILE}")
            except Exception as e:
                logging.error(f"Failed to create profiles file: {e}")
    
    # ========== Configuration Management ==========
    
    def load_config(self):
        """load configuration from file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                    config = json.load(f)
                self.mod_install_dir = config.get("mod_install_dir", DEFAULT_MODS_DIR)
                logging.info(f"Config loaded successfully: {self.mod_install_dir}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading config: {e}")
                self.mod_install_dir = DEFAULT_MODS_DIR
                if self.root:
                    messagebox.showwarning(
                        "Config Error",
                        f"Failed to load configuration. Using defaults.\nError: {e}",
                        parent=self.root
                    )
        else:
            self.mod_install_dir = DEFAULT_MODS_DIR

    def save_config(self):
        """save configuration to file"""
        try:
            # load existing config to preserve other fields
            config = {}
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                        config = json.load(f)
                except:
                    pass
            
            # update mod_install_dir
            config["mod_install_dir"] = self.mod_install_dir
            
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logging.info("Config saved successfully.")
        except (IOError, OSError) as e:
            logging.error(f"Error saving config: {e}")
            if self.root:
                messagebox.showerror(
                    "Save Error",
                    f"Failed to save configuration.\nError: {e}",
                    parent=self.root
                )
    
    # ========== Profile Management ==========
    
    def load_profiles(self):
        """load profiles from file"""
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r", encoding='utf-8') as f:
                    data = json.load(f)
                self.profiles = data.get("profiles", {})
                self.current_profile = data.get("current_profile")
                
                # perform migrations
                self._convert_old_profiles()
                self._migrate_absolute_paths_to_relative()
                
                # load current profile's install dir
                if self.current_profile and self.current_profile in self.profiles:
                    rel_path = self.profiles[self.current_profile].get("mod_install_dir", DEFAULT_MODS_DIR)
                    self.mod_install_dir = self._resolve_install_dir(rel_path)
                    
                logging.info(f"Profiles loaded successfully. Current profile: {self.current_profile}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Error loading profiles: {e}")
                self.profiles = {}
                self.current_profile = None
        else:
            self.profiles = {}
            self.current_profile = None

    def save_profiles(self):
        """save profiles to file"""
        # save current profile's mod_install_dir before saving profiles
        if self.current_profile and self.current_profile in self.profiles:
            profile = self.profiles[self.current_profile]
            if isinstance(profile, dict):
                # save as relative path
                profile["mod_install_dir"] = self._make_path_relative(self.mod_install_dir)
            else:
                # old format: list of mod dicts. convert to new format.
                self.profiles[self.current_profile] = {
                    "mods": profile,
                    "mod_install_dir": self._make_path_relative(self.mod_install_dir)
                }

        try:
            with open(PROFILES_FILE, "w", encoding='utf-8') as f:
                json.dump({
                    "profiles": self.profiles,
                    "current_profile": self.current_profile
                }, f, indent=2)
            logging.info("Profiles saved successfully.")
        except (IOError, OSError) as e:
            logging.error(f"Error saving profiles: {e}")
            if self.root:
                messagebox.showerror(
                    "Save Error",
                    f"Failed to save profiles.\nError: {e}",
                    parent=self.root
                )

    def _convert_old_profiles(self):
        """convert any old-format profile (list) to new dict format"""
        for name, pdata in list(self.profiles.items()):
            if isinstance(pdata, list):
                self.profiles[name] = {"mods": pdata, "mod_install_dir": DEFAULT_MODS_DIR}
    
    def _migrate_absolute_paths_to_relative(self):
        """convert absolute paths to relative paths for portability"""
        cwd = os.getcwd()
        for name, profile in self.profiles.items():
            if isinstance(profile, dict):
                old_path = profile.get("mod_install_dir", "")
                if old_path and os.path.isabs(old_path):
                    # convert absolute path to relative
                    try:
                        rel_path = os.path.relpath(old_path, cwd)
                        # if the relative path would go outside the project, keep it as is
                        if not rel_path.startswith('..'):
                            profile["mod_install_dir"] = rel_path
                            logging.info(f"Migrated absolute path '{old_path}' to relative '{rel_path}' for profile '{name}'")
                    except ValueError:
                        # paths on different drives on Windows, keep absolute
                        logging.warning(f"Could not convert path '{old_path}' to relative, keeping absolute")
    
    def _make_path_relative(self, path):
        """convert a path to relative if it's within the project directory"""
        if not path or not os.path.isabs(path):
            return path
        cwd = os.getcwd()
        try:
            rel_path = os.path.relpath(path, cwd)
            # if the relative path would go outside the project, keep absolute
            if rel_path.startswith('..'):
                return path
            return rel_path
        except ValueError:
            # different drives on Windows, keep absolute
            return path
    
    def _resolve_install_dir(self, path):
        """resolve a path (relative or absolute) to absolute for use"""
        if not path:
            return DEFAULT_MODS_DIR
        if os.path.isabs(path):
            return path
        # make relative paths absolute relative to current working directory
        return os.path.abspath(path)
    
    def create_profile(self, name):
        """
        create a new profile
        
        args:
            name: profile name
            
        returns:
            bool: True if created, False if already exists
        """
        if name in self.profiles:
            return False
        
        self.profiles[name] = {"mods": [], "mod_install_dir": DEFAULT_MODS_DIR}
        self.current_profile = name
        self.save_profiles()
        return True
    
    def rename_profile(self, old_name, new_name):
        """
        rename a profile
        
        args:
            old_name: current profile name
            new_name: new profile name
            
        returns:
            bool: True if renamed, False if new name already exists
        """
        if new_name in self.profiles or old_name not in self.profiles:
            return False
        
        self.profiles[new_name] = self.profiles.pop(old_name)
        if self.current_profile == old_name:
            self.current_profile = new_name
        self.save_profiles()
        return True
    
    def delete_profile(self, name):
        """
        delete a profile
        
        args:
            name: profile name to delete
            
        returns:
            bool: True if deleted, False if it's the only profile
        """
        if len(self.profiles) <= 1:
            return False
        
        if name in self.profiles:
            del self.profiles[name]
            if self.current_profile == name:
                self.current_profile = next(iter(self.profiles.keys()), None)
            self.save_profiles()
            return True
        return False
    
    def export_profile(self, name, file_path):
        """
        export a profile to JSON file
        
        args:
            name: profile name to export
            file_path: destination file path
            
        returns:
            tuple: (success: bool, error_message: str or None)
        """
        if name not in self.profiles:
            return False, f"Profile '{name}' not found"
        
        try:
            with open(file_path, "w") as f:
                json.dump({name: self.profiles[name]}, f, indent=2)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def import_profile(self, file_path, overwrite=False):
        """
        import profile(s) from JSON file
        
        args:
            file_path: source file path
            overwrite: whether to overwrite existing profiles
            
        returns:
            tuple: (imported_names: list, skipped_names: list, error_message: str or None)
        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            imported = []
            skipped = []
            
            for name, pdata in data.items():
                if name in self.profiles and not overwrite:
                    skipped.append(name)
                    continue
                self.profiles[name] = pdata
                imported.append(name)
            
            if imported:
                self.current_profile = imported[-1]
                self.save_profiles()
            
            return imported, skipped, None
        except Exception as e:
            return [], [], str(e)
    
    def switch_profile(self, name):
        """
        switch to a different profile
        
        args:
            name: profile name to switch to
            
        returns:
            bool: True if switched successfully
        """
        if name not in self.profiles:
            return False
        
        self.current_profile = name
        profile = self.profiles.get(self.current_profile, {})
        if isinstance(profile, dict):
            rel_path = profile.get("mod_install_dir", DEFAULT_MODS_DIR)
            self.mod_install_dir = self._resolve_install_dir(rel_path)
        else:
            self.mod_install_dir = DEFAULT_MODS_DIR
        self.save_profiles()
        return True
    
    # ========== Mod Operations ==========
    
    def get_mods(self):
        """get list of mods for current profile"""
        profile = self.profiles.get(self.current_profile, {})
        if isinstance(profile, dict):
            return profile.get("mods", [])
        return profile  # support old format
    
    def set_mods(self, mods):
        """set list of mods for current profile"""
        profile = self.profiles.get(self.current_profile, {})
        if isinstance(profile, dict):
            profile["mods"] = mods
        else:
            self.profiles[self.current_profile] = mods
        self.save_profiles()
    
    def add_mod(self, url, mod_subdir="", install_subdir="", keep_structure=False):
        """
        add a mod to current profile
        
        args:
            url: mod download URL
            mod_subdir: subdirectory within ZIP
            install_subdir: installation subdirectory
            keep_structure: whether to keep original folder structure
        """
        mods = self.get_mods()
        mods.append({
            "url": url,
            "mod_subdir": mod_subdir,
            "install_subdir": install_subdir,
            "keep_structure": keep_structure
        })
        self.set_mods(mods)
    
    def edit_mod(self, index, url, mod_subdir="", install_subdir="", keep_structure=False):
        """edit a mod at specific index"""
        mods = self.get_mods()
        if 0 <= index < len(mods):
            mods[index] = {
                "url": url,
                "mod_subdir": mod_subdir,
                "install_subdir": install_subdir,
                "keep_structure": keep_structure
            }
            self.set_mods(mods)
            return True
        return False
    
    def remove_mod(self, index):
        """remove a mod at specific index"""
        mods = self.get_mods()
        if 0 <= index < len(mods):
            mods.pop(index)
            self.set_mods(mods)
            return True
        return False
    
    def get_install_dir(self, mod):
        """get installation directory for a mod"""
        install_type = mod.get("install_type", "mod")
        # use profile's mod_install_dir for mods, else use default for tileset/soundpack
        if install_type == "mod":
            return self.mod_install_dir
        else:
            return INSTALL_TYPE_DIRS.get(install_type, self.mod_install_dir)
    
    @staticmethod
    def fix_github_url(url):
        """convert GitHub repo URL to archive URL"""
        url = url.rstrip('/')
        if url.startswith("https://github.com/") and not url.endswith(".zip"):
            return f"{url}/archive/refs/heads/master.zip"
        return url
    
    @staticmethod
    def get_mod_display_name(mod):
        """extract a clean display name from a mod entry"""
        url = mod['url']
        github_zip = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/archive/(?:refs/(?:heads|tags)/)?([^/]+)\.zip", url
        )
        if github_zip:
            user, repo, ref = github_zip.groups()
            return f"{user}/{repo}"
        return url
    
    def download_and_extract_mod(self, mod):
        """
        download and extract a mod
        
        args:
            mod: mod dictionary with url, mod_subdir, install_subdir, keep_structure
            
        raises:
            ValueError: if no URL provided
            FileNotFoundError: if subdirectory not found in archive
            Exception: for download/extraction errors
        """
        url = mod.get("url")
        mod_subdir = mod.get("mod_subdir", mod.get("subdir", ""))  # support old 'subdir'
        install_subdir = mod.get("install_subdir")
        keep_structure = mod.get("keep_structure", True)

        # if install_subdir is not defined, None, blank, or '.', always use <mod_install_dir>/mods
        if not install_subdir or install_subdir == ".":
            base_install_dir = os.path.join(os.path.abspath(self.mod_install_dir), "mods")
        else:
            # if install_subdir is absolute, use as is; else, join with mod_install_dir
            if os.path.isabs(install_subdir):
                base_install_dir = install_subdir
            else:
                base_install_dir = os.path.join(os.path.abspath(self.mod_install_dir), install_subdir)

        if not url:
            raise ValueError("No URL provided for mod")

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "mod.zip")

            logging.info(f"Downloading mod from {url}...")
            # use streaming for better memory efficiency with large files
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # download in chunks
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

