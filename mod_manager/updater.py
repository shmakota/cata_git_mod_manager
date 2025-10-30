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
            logging.info(f"Checking for updates from: {self.update_url}")
            
            # Check if URL points to a specific tag
            if "/tags/" in self.update_url:
                # Specific tag URL
                response = requests.get(self.update_url, timeout=15)
                response.raise_for_status()
                release_data = response.json()
            else:
                # Try /latest first, if that fails try /releases
                response = requests.get(self.update_url, timeout=15)
                
                if response.status_code == 404:
                    # /latest doesn't exist, try getting all releases
                    base_url = self.update_url.replace("/releases/latest", "/releases")
                    logging.info(f"Latest endpoint not found, trying: {base_url}")
                    response = requests.get(base_url, timeout=15)
                    response.raise_for_status()
                    releases = response.json()
                    
                    if not releases or len(releases) == 0:
                        logging.warning("No releases found")
                        return False, None, None, None
                    
                    # Use the first (most recent) release
                    release_data = releases[0]
                elif response.status_code == 200:
                    release_data = response.json()
                else:
                    response.raise_for_status()
                    return False, None, None, None
            
            # extract version from tag_name (e.g., "v1.0.6" -> "1.0.6").
            tag_name = release_data.get("tag_name", "")
            latest_version = tag_name.lstrip("v")
            
            # some repos use "latest" as tag; extract version from release name instead.
            if latest_version == "latest" or not latest_version:
                release_name = release_data.get("name", "")
                import re
                version_match = re.search(r'(\d+\.\d+\.\d+)', release_name)
                if version_match:
                    latest_version = version_match.group(1)
                    logging.info(f"Extracted version {latest_version} from release name: {release_name}")
                else:
                    logging.error(f"Could not extract version from tag '{tag_name}' or name '{release_name}'")
                    return False, None, None, None
            
            release_notes = release_data.get("body", "")
            
            # find download url from assets or use github's zipball.
            download_url = None
            assets = release_data.get("assets", [])
            
            # prefer explicit .zip assets over zipball.
            for asset in assets:
                if asset.get("name", "").endswith(".zip"):
                    download_url = asset.get("browser_download_url")
                    logging.info(f"Found asset download URL: {download_url}")
                    break
            
            # fallback to github's automatic zipball url.
            if not download_url:
                download_url = release_data.get("zipball_url")
                logging.info(f"Using zipball_url: {download_url}")
            
            if not download_url:
                logging.error("No download URL found in release data")
                return False, latest_version, None, release_notes
            
            # Compare versions
            has_update = self._compare_versions(self.current_version, latest_version)
            logging.info(f"Version comparison - Current: {self.current_version}, Latest: {latest_version}, Has update: {has_update}")
            
            return has_update, latest_version, download_url, release_notes
            
        except requests.exceptions.Timeout:
            logging.error("Update check timed out")
            return False, None, None, None
        except requests.exceptions.ConnectionError:
            logging.error("Connection error while checking for updates")
            return False, None, None, None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error checking for updates: {e}")
            return False, None, None, None
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Error parsing update response: {e}")
            return False, None, None, None
        except Exception as e:
            logging.error(f"Unexpected error checking for updates: {e}")
            return False, None, None, None
    
    def _compare_versions(self, current, latest):
        """Compare version strings
        
        Returns True if latest > current
        """
        try:
            # parse semantic versions (e.g., "1.0.5" -> [1, 0, 5]).
            current_parts = [int(x) for x in current.split('.')]
            latest_parts = [int(x) for x in latest.split('.')]
            
            # pad shorter version with zeros for comparison.
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
        preserved = list(BASE_PRESERVED_DIRS)
        
        # scan config for additional paths that exist inside the tool directory.
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                
                # check configured paths.
                paths_to_check = [
                    config.get("game_install_dir", ""),
                    config.get("backup_dir", ""),
                    config.get("mod_install_dir", "")
                ]
                
                root_dir = os.getcwd()
                for path in paths_to_check:
                    if not path:
                        continue
                    
                    abs_path = os.path.abspath(path)
                    
                    # only preserve if path is inside the tool directory.
                    try:
                        rel_path = os.path.relpath(abs_path, root_dir)
                        # paths starting with ".." are outside root_dir.
                        if not rel_path.startswith('..'):
                            # extract top-level directory name.
                            top_level = rel_path.split(os.sep)[0]
                            local_path = os.path.join(root_dir, top_level)
                            
                            # only add if it exists and isn't already in the list.
                            if top_level and top_level not in preserved and os.path.exists(local_path):
                                preserved.append(top_level)
                                logging.info(f"Will preserve directory from config: {top_level} (exists at {local_path})")
                            elif not os.path.exists(local_path):
                                logging.info(f"Skipping {top_level} from config path {path} - doesn't exist locally")
                    except ValueError:
                        # different drives on windows; skip.
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
                
                # Download with timeout and streaming for large files
                response = requests.get(download_url, timeout=60, stream=True)
                response.raise_for_status()
                
                # Write in chunks for better memory efficiency
                total_size = int(response.headers.get('content-length', 0))
                self._log_update(f"Download size: {total_size / 1024 / 1024:.2f} MB")
                
                with open(zip_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                
                self._log_update(f"Download complete: {downloaded / 1024 / 1024:.2f} MB")
                
                self._log_update(f"STEP 2: Extracting update to temporary location")
                # Step 2: Extract to temporary location
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # github zips typically have one top-level folder; unwrap it.
                extracted_items = os.listdir(extract_dir)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                    source_dir = os.path.join(extract_dir, extracted_items[0])
                else:
                    source_dir = extract_dir
                
                # Step 3: Backup user data to temp location
                self._log_update(f"STEP 3: Backing up user data to temp location")
                backup_dir = os.path.join(temp_dir, "user_backup")
                os.makedirs(backup_dir, exist_ok=True)
                
                # backup directories.
                for item in PRESERVED_DIRS:
                    src = os.path.join(root_dir, item)
                    if os.path.exists(src):
                        dst = os.path.join(backup_dir, item)
                        try:
                            if os.path.isdir(src):
                                # preserve symlinks, skip dangling ones.
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
                            shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)
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

