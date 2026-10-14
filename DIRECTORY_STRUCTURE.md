# Directory Structure

This document explains the directory structure used by the Cataclysm: Bright Nights Mod Manager.

## Overview

The mod manager and game launcher use separate directories for different purposes:

```
cata_git_mod_manager/          # Root directory
├── cataclysmbn-unstable/      # Game installation (--basepath)
│   ├── cataclysm-bn-tiles.exe # Game executable
│   ├── data/                  # Game data files
│   ├── gfx/                   # Graphics/tilesets
│   └── ...
│
├── userdata/                  # User data directory (--userdir)
│   ├── save/                  # Save games
│   ├── config/                # User configuration
│   ├── mods/                  # User-installed mods
│   ├── memorial/              # Character memorials
│   └── ...
│
├── cfg/                       # Mod manager configuration
│   ├── mod_manager_config.json
│   └── mod_profiles.json
│
└── ...                        # Other mod manager files
```

## Directory Purposes

### `cataclysmbn-unstable/` (Game Installation Directory)
- **Purpose**: Contains the game executable and core game data
- **Set via**: `game_install_dir` in `cfg/mod_manager_config.json`
- **Launcher parameter**: `--basepath`
- **Contains**:
  - Game executable (`cataclysm-bn-tiles.exe` on Windows, `cataclysm-bn-tiles` on Linux)
  - Core game data (`data/` folder)
  - Default graphics and soundpacks
  
### `userdata/` (User Data Directory)
- **Purpose**: Contains user-specific data (saves, configs, mods)
- **Set via**: `mod_install_dir` in `cfg/mod_manager_config.json`
- **Launcher parameter**: `--userdir`
- **Contains**:
  - `mods/` - User-installed mods (installed by mod manager)
  - `save/` - Save games
  - `config/` - User configuration files
  - `memorial/` - Character death memorials
  - `templates/` - Custom templates
  - Other user-generated content

## Game Launch

When you launch the game using the "Launch Game" button, it runs with:

```bash
cataclysm-bn-tiles.exe --basepath "cataclysmbn-unstable" --userdir "userdata"
```

This ensures:
- The game reads its core data from `cataclysmbn-unstable/`
- All user data (saves, configs, mods) is stored in `userdata/`
- User data is kept separate from game installation
- Updates to the game won't affect user data

## Mod Installation

When you install a mod through the mod manager:
1. The mod is downloaded
2. It's extracted to `userdata/mods/<mod_name>/`
3. The game will load it from there when launched with `--userdir userdata`

Tilesets and soundpacks are installed to their respective subdirectories:
- Tilesets: `userdata/gfx/`
- Soundpacks: `userdata/sound/`

## Configuration

The mod manager configuration is stored in `cfg/mod_manager_config.json`:
```json
{
  "mod_install_dir": "userdata",       // Where mods are installed
  "backup_dir": "",                    // Optional backup directory
  "game_install_dir": ""               // Game installation path (auto-detected)
}
```

## Benefits of This Structure

1. **Clean separation**: Game files and user data are kept separate
2. **Easy updates**: Game can be updated without affecting saves/mods
3. **Portable**: The entire `userdata/` folder can be backed up or moved
4. **Cross-platform**: Same structure works on Windows and Linux

