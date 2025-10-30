"""
Constants and configuration for Content Manager
"""

# file paths
PROFILES_FILE = "cfg/mod_profiles.json"
CONFIG_FILE = "cfg/mod_manager_config.json"
VERSION_FILE = "version.json"

# defaults
# Use 'userdata' to match the --userdir parameter passed to the game launcher
DEFAULT_MODS_DIR = "userdata"

# install type directories
INSTALL_TYPE_DIRS = {
    "mod": "mods",
    "tileset": "gfx",
    "soundpack": "sound"
}

