# Cataclysm Mod Manager

A mod management tool for **Cataclysm: Dark Days Ahead (CDDA)** and **Cataclysm: Bright Nights (CBN)**.

![image](https://github.com/user-attachments/assets/a49e923c-195a-4ef0-aa69-ebcc62e2aa43)

## Features

- Multi-profile support – Easily switch between different mod setups.
- Custom mod install directory – Set your own path to where mods are installed.
- GitHub repo management – Add multiple GitHub repositories and update them all with a single click.
- Supports modpacks and individual mods – Automatically scans nested folders for `modinfo.json`, ensuring compatibility with complex mod structures.
- Integrated with the Cataclysm Mod Explorer – Directly view every JSON entry a mod adds to the game through seamless integration.

## How It Works

1. Set your mod install folder – Define where you want mods to be installed.
2. Create one or more profiles – Each profile can have a different mod loadout.
3. Add mod repos – Input GitHub URLs pointing to mod or modpack repositories.
4. One-click update – The tool pulls the latest versions of all mods from the defined GitHub sources.
5. Automatic scanning – The tool locates all valid mods via their `modinfo.json`, even in nested subfolders.

## Ideal For

- Players who use multiple mod combinations.
- Those who want to stay up to date with community mods.
- Modpack creators looking to manage modular updates.
- Developers or tinkerers who want to explore mod content in-depth.

## Installation

Download repo and run the install/launch script. Setup your profile and install directory.

If you'd like mod explorer functionality, be sure to download, extract, and run the explorer in the same directory as run.py:
https://github.com/shmakota/cataclysm_mod_explorer

## Compatibility
Should work fine with any fork of Cataclysm: Dark Days Ahead.
