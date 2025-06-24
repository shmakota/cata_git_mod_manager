# Cataclysm Mod Manager

A mod management tool for **Cataclysm: Dark Days Ahead (CDDA)** and **Cataclysm: Bright Nights (CBN)**

<details>
  <summary>📸 Click to view screenshots</summary>
  
  ![image](https://github.com/user-attachments/assets/fedd87ca-e452-442c-9e8f-6113992b2106)
  ![image](https://github.com/user-attachments/assets/a85facb4-c834-415b-964c-ece3f928d6e7)

</details>

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

## Requirements

Requires Python3, everything else should automatically be setup by the install script.

## Installation

Clone the repo and run the install/launch script. Setup your profile and install directory.

As of 1.0.2, mod explorer functionality is included by default in this repo and the mod explorer repo has been discontinued.

## Compatibility
Should work fine with any fork of Cataclysm: Dark Days Ahead.
