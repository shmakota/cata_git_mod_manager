import os
import json
import requests
import zipfile
import shutil
import tempfile
import sys
import logging
from pathlib import Path

VERSION_FILE = "version.json"  # Tool version (ships with releases, gets overwritten)
CONFIG_FILE = "cfg/mod_manager_config.json"  # User config (preserved)
BASE_PRESERVED_DIRS = ["cfg", "mods"]  # Always preserve these directories
PRESERVED_FILES = ["mod_debug.log"]  # Files to preserve during update


class Updater:
    def __init__(self):
        self.current_version = self._load_version()
        self.update_url = self._load_update_url()
        
    def _load_version(self):
        """Load current version from version.json (tool version file)"""
        if os.path.exists(VERSION_FILE):
            try:
                with open(VERSION_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("version", "1.0.5")
            except Exception as e:
                logging.error(f"Error loading version: {e}")
                return "1.0.5"
        return "1.0.5"
    
    def _load_update_url(self):
        """Load update URL from user config (preserved across updates)"""
        # First try user config (preserved)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    update_url = data.get("update_url", "")
                    if update_url:
                        return update_url
            except Exception as e:
                logging.error(f"Error loading update URL from config: {e}")
        
        # Fallback to version.json (for backwards compatibility)
        if os.path.exists(VERSION_FILE):
            try:
                with open(VERSION_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("update_url", "")
            except Exception as e:
                logging.error(f"Error loading update URL from version file: {e}")
        
        return ""
    
    def _save_version(self, version):
        """Save new version to version.json (this file ships with releases)"""
        try:
            data = {}
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r') as f:
                    data = json.load(f)
            
            data["version"] = version
            
            with open(VERSION_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info(f"Updated version to {version}")
        except Exception as e:
            logging.error(f"Error saving version: {e}")
    
    def save_update_url(self, url):
        """Save update URL to user config (preserved across updates)"""
        try:
            data = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
            
            data["update_url"] = url
            
            # Ensure cfg directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info(f"Saved update URL to config")
        except Exception as e:
            logging.error(f"Error saving update URL: {e}")
    
    def check_for_updates(self):
        """Check GitHub for latest release
        
        Returns:
            tuple: (has_update, latest_version, download_url, release_notes)
        """
        if not self.update_url:
            logging.warning("No update URL configured")
            return False, None, None, None
        
        try:
            # Check if URL points to a specific tag
            if "/tags/" in self.update_url:
                # Specific tag URL
                response = requests.get(self.update_url, timeout=10)
            else:
                # Try /latest first, if that fails try /releases
                response = requests.get(self.update_url, timeout=10)
                if response.status_code == 404:
                    # /latest doesn't exist, try getting all releases
                    base_url = self.update_url.replace("/releases/latest", "/releases")
                    response = requests.get(base_url, timeout=10)
                    if response.status_code == 200:
                        releases = response.json()
                        if releases and len(releases) > 0:
                            # Use the first (most recent) release
                            release_data = releases[0]
                        else:
                            return False, None, None, None
                    else:
                        response.raise_for_status()
                else:
                    release_data = response.json()
            
            if response.status_code == 200 and 'release_data' not in locals():
                release_data = response.json()
            
            response.raise_for_status()
            
            latest_version = release_data.get("tag_name", "").lstrip("v")
            release_notes = release_data.get("body", "")
            
            # Find the zipball URL from assets or use the zipball_url
            download_url = None
            assets = release_data.get("assets", [])
            
            # Look for a source code zip
            for asset in assets:
                if asset.get("name", "").endswith(".zip"):
                    download_url = asset.get("browser_download_url")
                    break
            
            # Fallback to zipball_url if no asset found
            if not download_url:
                download_url = release_data.get("zipball_url")
            
            # Compare versions
            has_update = self._compare_versions(self.current_version, latest_version)
            
            return has_update, latest_version, download_url, release_notes
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking for updates: {e}")
            return False, None, None, None
        except Exception as e:
            logging.error(f"Unexpected error checking for updates: {e}")
            return False, None, None, None
    
    def _compare_versions(self, current, latest):
        """Compare version strings
        
        Returns True if latest > current
        """
        try:
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            
            # Pad with zeros if needed
            max_len = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))
            
            return latest_parts > current_parts
        except:
            # If version comparison fails (non-semantic version like "update_test"),
            # check if versions are different - if so, treat as update available
            if current != latest:
                logging.info(f"Non-semantic version detected: {latest}. Treating as update available.")
                return True
            return False
    
    def _get_preserved_dirs(self):
        """Get list of directories to preserve, including dynamic paths from config"""
        preserved = list(BASE_PRESERVED_DIRS)  # Start with base dirs
        
        # Load config to find additional directories to preserve
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                
                # Check paths in config
                paths_to_check = [
                    config.get("game_install_dir", ""),
                    config.get("backup_dir", ""),
                    config.get("mod_install_dir", "")
                ]
                
                root_dir = os.getcwd()
                for path in paths_to_check:
                    if not path:
                        continue
                    
                    # Convert to absolute path
                    abs_path = os.path.abspath(path)
                    
                    # Check if this path is inside the root directory
                    try:
                        rel_path = os.path.relpath(abs_path, root_dir)
                        # If relative path doesn't start with .., it's inside root_dir
                        if not rel_path.startswith('..') and os.path.exists(abs_path):
                            # Get the top-level directory name
                            top_level = rel_path.split(os.sep)[0]
                            if top_level and top_level not in preserved:
                                preserved.append(top_level)
                                logging.info(f"Will preserve directory from config: {top_level}")
                    except ValueError:
                        # Different drives on Windows, skip
                        pass
            except Exception as e:
                logging.error(f"Error reading config for preserved dirs: {e}")
        
        return preserved
    
    def perform_update(self, download_url, new_version):
        """Download and apply update while preserving user data
        
        Args:
            download_url: URL to download the new version
            new_version: Version string of the new release
            
        Returns:
            bool: True if update successful, False otherwise
        """
        root_dir = os.getcwd()
        
        # Get list of directories to preserve (including dynamic paths)
        PRESERVED_DIRS = self._get_preserved_dirs()
        logging.info(f"Preserving directories: {PRESERVED_DIRS}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Step 1: Download the new version
                logging.info(f"Downloading update from {download_url}")
                zip_path = os.path.join(temp_dir, "update.zip")
                
                response = requests.get(download_url, timeout=30)
                response.raise_for_status()
                
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Step 2: Extract to temporary location
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find the root directory in the extracted files
                # GitHub releases typically have a single top-level directory
                extracted_items = os.listdir(extract_dir)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                    source_dir = os.path.join(extract_dir, extracted_items[0])
                else:
                    source_dir = extract_dir
                
                # Step 3: Backup user data to temp location
                backup_dir = os.path.join(temp_dir, "user_backup")
                os.makedirs(backup_dir, exist_ok=True)
                
                for item in PRESERVED_DIRS:
                    src = os.path.join(root_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(backup_dir, item)
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                
                for item in PRESERVED_FILES:
                    src = os.path.join(root_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(backup_dir, item)
                        shutil.copy2(src, dst)
                
                # Step 4: Remove ALL old files (we have backups of preserved data)
                for item in os.listdir(root_dir):
                    item_path = os.path.join(root_dir, item)
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                    except Exception as e:
                        logging.warning(f"Could not remove {item}: {e}")
                
                # Step 5: Copy new files (SKIP preserved directories completely)
                for item in os.listdir(source_dir):
                    src = os.path.join(source_dir, item)
                    dst = os.path.join(root_dir, item)
                    
                    # Skip if this is a preserved directory - don't copy from new release at all
                    if item in PRESERVED_DIRS:
                        continue
                    
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                # Step 6: Restore user data (ALWAYS restore from backup, NEVER from new release)
                for item in PRESERVED_DIRS:
                    src = os.path.join(backup_dir, item)
                    dst = os.path.join(root_dir, item)
                    
                    if os.path.exists(src):
                        # Always use the backed up version
                        # Remove any directory that might exist from the new release
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                shutil.rmtree(dst)
                            else:
                                os.remove(dst)
                        
                        # Restore the backed up directory/file
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                
                for item in PRESERVED_FILES:
                    src = os.path.join(backup_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(root_dir, item)
                        shutil.copy2(src, dst)
                
                # Step 7: Update version file
                self._save_version(new_version)
                
                logging.info(f"Successfully updated to version {new_version}")
                return True
                
        except Exception as e:
            logging.error(f"Error performing update: {e}")
            return False
    
    def get_current_version(self):
        """Return the current version string"""
        return self.current_version

