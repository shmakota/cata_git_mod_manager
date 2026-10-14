# Cataclysm Multitool

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-Supported-0078D6?logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-Supported-FCC624?logo=linux&logoColor=black)

A comprehensive utility program primarily created for **Cataclysm: Bright Nights (CBN)**, providing essential tools for game management, mod installation, and backup handling.

<img width="428" height="316" alt="image" src="https://github.com/user-attachments/assets/11ab2858-1296-4971-b353-c8ecd5e35343" />

---

## 🚀 Features

### 📦 Game Launcher
Choose Stable, Nightly, or Experimental in the release channel selector, then select a version and click Download & Install. Stable and Nightly list up to ten releases. Use Launch Game to play the installed version. All channels install into the configured game folder; switching channels replaces the installed game there.
  
<img width="545" height="253" alt="image" src="https://github.com/user-attachments/assets/85e7b9cc-11dd-48c7-93e3-f398377adde4" />
  
### 🔧 Content Manager
Add multiple GitHub repositories and update them all with a single click.
  
<img width="978" height="716" alt="image" src="https://github.com/user-attachments/assets/1dcd7a9b-3dd7-4d2b-8290-fd01dbb9e555" />
  
**Key Features:**
- ✅ **Multi-profile support** – Easily switch between different mod setups
- ✅ **Modpack & Individual Mod Support** – Automatically scans nested folders for `modinfo.json`, ensuring compatibility with complex mod structures. The user can also define a custom subdirectory for the mod or custom install folder name
- ✅ **Quick Explorer Access** – Allows quick access to the Mod Explorer, or your system's file explorer
- ✅ **Auto-Update** – Automatically checks for and installs tool updates from GitHub while preserving your settings and mods
  
### 🔍 Mod Explorer
Directly view and quickly sort through every JSON entry and Lua scripts a mod adds to the game.
  
![image](https://github.com/user-attachments/assets/a85facb4-c834-415b-964c-ece3f928d6e7)
  
**Features:**
- Advanced search with inclusion/exclusion filters
- Filter by ID, Name, Description, or Type
- Export filtered results to JSON
- Display balance options, languages, and special entry types
  
### 💾 Backup Manager
Name, create and load backups at any time.
  
<img width="918" height="533" alt="image" src="https://github.com/user-attachments/assets/30c07e7d-d14e-4fab-8a88-f762310665865" />
  
**Features:**
- Create timestamped backups with custom names
- View backup metadata including mod lists
- Restore from backups or manage current world saves
- Browse backup archives with detailed information

---

## 📋 Requirements

- **Python 3.x** – Python 3.6 or higher recommended
- All other dependencies are automatically set up by the install script

---

## 🖥️ Compatibility

Currently optimized for **Cataclysm: Bright Nights** with a dedicated launcher/installer. Most tools should work with DDA installations as well.

**Supported Platforms:**
- ✅ Windows
- ✅ Linux

---

## 🔧 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shmakota/cata_git_mod_manager.git
   cd cata_git_mod_manager
   ```

2. Run the install/launch script:
   - **Linux/Mac**: `./run.sh`
   - **Windows**: `run.bat`

3. Follow the Usage guide below to set up your profile and install directory.

---

## 📖 Usage

1. **Launch the Game** – Use the Game Launcher to download the latest version of Cataclysm: Bright Nights
2. **Create a Mod Profile** – Set up your mod profile, or download an existing one from the Discord
3. **Add Mod Repositories** – Input GitHub URLs pointing to mod or modpack repositories in the Content Manager
4. **Set Install Directory** – Configure the Content Manager's profile install directory to point to your game's userdata folder
5. **One-Click Update** – The tool pulls the latest versions of all mods from the defined GitHub sources with a single click
6. **Automatic Scanning** – The tool automatically locates all valid mods via their `modinfo.json`, even in nested subfolders. You can also define specific subdirectories if needed

---

## 🔗 Community & Links

- 📖 [Official Documentation](https://docs.cataclysmbn.org/)
- 🎮 [Discord Server](https://discord.gg/XW7XhXuZ89)
- 💬 [Subreddit (r/cataclysmbn)](https://www.reddit.com/r/cataclysmbn/)
- 📚 [Hitchhiker's Guide](https://next.cbn-guide.pages.dev/?t=UNDEAD_PEOPLE)
- 🔧 [Bright Nights GitHub](https://github.com/cataclysmbnteam/Cataclysm-BN)
- 📦 [Multitool GitHub](https://github.com/shmakota/cata_git_mod_manager)

---

## 📝 License

This project is open source. Please refer to the repository for license information.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

*Made with ❤️ for the Cataclysm: Bright Nights community*
