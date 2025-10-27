# Cataclysm Multitool
A utility program primarily created for **Cataclysm: Bright Nights (CBN)**

<img width="428" height="316" alt="image" src="https://github.com/user-attachments/assets/11ab2858-1296-4971-b353-c8ecd5e35343" />

---

## Features
  
### - C:BN Launcher - Allows the user to install the latest C:BN nightly or experimental release.
  <img width="545" height="253" alt="image" src="https://github.com/user-attachments/assets/85e7b9cc-11dd-48c7-93e3-f398377adde4" />
  
### - Content Manager – Add multiple GitHub repositories and update them all with a single click.
  <img width="978" height="716" alt="image" src="https://github.com/user-attachments/assets/1dcd7a9b-3dd7-4d2b-8290-fd01dbb9e555" />
  
  - Multi-profile support – Easily switch between different mod setups.
  - Supports modpacks and individual mods – Automatically scans nested folders for `modinfo.json`, ensuring compatibility with complex mod structures. The user can also define a custom subdirectory for the mod or custom install folder name.
  - Quick explorer access - Allows quick access to the Mod Explorer, or your system's file explorer.
### - Mod Explorer – Directly view and quickly sort through every JSON entry (and soon LUA scripts) a mod adds to the game.
  ![image](https://github.com/user-attachments/assets/a85facb4-c834-415b-964c-ece3f928d6e7)
  
### - Backup Manager - Name, create and load backups at any time.
  <img width="918" height="533" alt="image" src="https://github.com/user-attachments/assets/30c07e7d-d14e-4fab-8a88-762310665865" />

---

### Requirements
Requires Python3, everything else should automatically be setup by the install script.

### Compatibility
Currently only has a launcher/installer for Cataclysm: Bright Nights. Most tools should be able to be used on a DDA installation however.

### Installation

Clone the repo and run the install/launch script. Follow the Usage guide below to setup your profile and install directory.

### Usage

1. Use the launcher to download the latest version.
2. Create a mod profile, or download an existing one from the discord.
3. Add any additional mod repos – Input GitHub URLs pointing to mod or modpack repositories.
4. Set the content manager's profile install directory to the Cataclysm BN installation's root folder.
5. One-click update – The tool pulls the latest versions of all mods from the defined GitHub sources.
6. Automatic scanning – The tool locates all valid mods via their `modinfo.json`, even in nested subfolders. If necessary, you can define specific subdirectories.
