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
UPDATE_LOG_FILE = "update_history.log"  # Permanent update log (never deleted)
BASE_PRESERVED_DIRS = ["cfg", "mods"]  # Always preserve these directories
PRESERVED_FILES = ["mod_debug.log", "update_history.log"]  # Files to preserve during update


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
                    # Try program_version first, fall back to version for backwards compatibility
                    return data.get("program_version", data.get("version", "1.0.5"))
            except Exception as e:
                logging.error(f"Error loading version: {e}")
                return "1.0.5"
        return "1.0.5"
    
    def _load_update_url(self):
        """Load update URL from version.json"""
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
            
            # Save as program_version, keep game_version if it exists
            data["program_version"] = version
            # Keep existing game_version if present
            if "game_version" not in data:
                data["game_version"] = ""
            
            with open(VERSION_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info(f"Updated program version to {version}")
        except Exception as e:
            logging.error(f"Error saving version: {e}")
    
    def save_update_url(self, url):
        """Save update URL to version.json"""
        try:
            data = {}
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r') as f:
                    data = json.load(f)
            
            data["update_url"] = url
            
            with open(VERSION_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info(f"Saved update URL to version.json")
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
                        if not rel_path.startswith('..'):
                            # Get the top-level directory name
                            top_level = rel_path.split(os.sep)[0]
                            # Check if this directory actually exists in the root dir
                            local_path = os.path.join(root_dir, top_level)
                            if top_level and top_level not in preserved and os.path.exists(local_path):
                                preserved.append(top_level)
                                logging.info(f"Will preserve directory from config: {top_level} (exists at {local_path})")
                            elif not os.path.exists(local_path):
                                logging.info(f"Skipping {top_level} from config path {path} - doesn't exist locally")
                    except ValueError:
                        # Different drives on Windows, skip
                        pass
            except Exception as e:
                logging.error(f"Error reading config for preserved dirs: {e}")
        
        return preserved
    
    def _log_update(self, message):
        """Log to both regular log and permanent update history log"""
        logging.info(message)
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(UPDATE_LOG_FILE, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logging.error(f"Failed to write to update log: {e}")
    
    def perform_update(self, download_url, new_version):
        """Download and apply update while preserving user data
        
        Args:
            download_url: URL to download the new version
            new_version: Version string of the new release
            
        Returns:
            bool: True if update successful, False otherwise
        """
        root_dir = os.getcwd()
        
        self._log_update("="*60)
        self._log_update(f"UPDATE STARTED: {self.current_version} → {new_version}")
        self._log_update(f"Download URL: {download_url}")
        
        # Get list of directories to preserve (including dynamic paths)
        PRESERVED_DIRS = self._get_preserved_dirs()
        self._log_update(f"Preserving directories: {PRESERVED_DIRS}")
        self._log_update(f"Preserving files: {PRESERVED_FILES}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Step 1: Download the new version
                self._log_update(f"STEP 1: Downloading update from {download_url}")
                zip_path = os.path.join(temp_dir, "update.zip")
                
                response = requests.get(download_url, timeout=30)
                response.raise_for_status()
                
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                self._log_update(f"STEP 2: Extracting update to temporary location")
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
                self._log_update(f"STEP 3: Backing up user data to temp location")
                backup_dir = os.path.join(temp_dir, "user_backup")
                os.makedirs(backup_dir, exist_ok=True)
                
                for item in PRESERVED_DIRS:
                    src = os.path.join(root_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(backup_dir, item)
                        try:
                            if os.path.isdir(src):
                                # Use ignore_dangling_symlinks to skip broken links
                                shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)
                                self._log_update(f"  ✓ Backed up directory: {item}")
                            else:
                                shutil.copy2(src, dst)
                                self._log_update(f"  ✓ Backed up file: {item}")
                        except Exception as e:
                            self._log_update(f"  ✗ Failed to backup {item}: {e}")
                            raise
                    else:
                        self._log_update(f"  - Skipping {item} (doesn't exist)")
                
                for item in PRESERVED_FILES:
                    src = os.path.join(root_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(backup_dir, item)
                        shutil.copy2(src, dst)
                        self._log_update(f"  ✓ Backed up file: {item}")
                
                self._log_update(f"STEP 4: Removing old files")
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
                
                self._log_update(f"STEP 5: Installing new files (skipping preserved directories)")
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
                
                self._log_update(f"STEP 6: Restoring user data from backup")
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
                            self._log_update(f"  ✓ Restored directory: {item}")
                        else:
                            shutil.copy2(src, dst)
                            self._log_update(f"  ✓ Restored file: {item}")
                
                for item in PRESERVED_FILES:
                    src = os.path.join(backup_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(root_dir, item)
                        shutil.copy2(src, dst)
                        self._log_update(f"  ✓ Restored file: {item}")
                
                # Step 7: Update version file
                # Note: new_version comes from the GitHub tag name
                # The new release's version.json was already installed in Step 5
                # We only update it if it doesn't match
                self._log_update(f"STEP 7: Verifying version file")
                
                # Read what version the new release has
                if os.path.exists(VERSION_FILE):
                    try:
                        with open(VERSION_FILE, 'r') as f:
                            new_version_data = json.load(f)
                            # Check for program_version first, fall back to version
                            installed_version = new_version_data.get("program_version", new_version_data.get("version", new_version))
                            game_version = new_version_data.get("game_version", "")
                            
                            self._log_update(f"  New release program_version: {installed_version}")
                            if game_version:
                                self._log_update(f"  New release game_version: {game_version}")
                            
                            # If the tag is different from the version in the file, log it
                            if installed_version != new_version:
                                self._log_update(f"  Note: GitHub tag '{new_version}' differs from program_version '{installed_version}'")
                    except Exception as e:
                        self._log_update(f"  Warning: Could not read new version.json: {e}")
                        # Fall back to saving the tag name
                        self._save_version(new_version)
                
                self._log_update(f"✅ UPDATE COMPLETED SUCCESSFULLY: {self.current_version} → {new_version}")
                self._log_update("="*60 + "\n")
                return True
                
        except Exception as e:
            import traceback
            error_msg = f"❌ UPDATE FAILED: {e}"
            self._log_update(error_msg)
            self._log_update(f"Traceback:\n{traceback.format_exc()}")
            self._log_update("="*60 + "\n")
            logging.error(f"Error performing update: {e}")
            logging.error(f"Traceback:\n{traceback.format_exc()}")
            return False
    
    def get_current_version(self):
        """Return the current version string"""
        return self.current_version

