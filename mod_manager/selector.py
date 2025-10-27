# this script is used to select which tool to launch: backup.py, restore.py, mod_manager.py, etc. it is launched from the parent directory .sh or .bat file. it uses tkinter gui

import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

TOOLS = [
    ("Game Launcher", "launcher.py"),
    ("Backup Manager", "backup.py"),
    ("Content Manager", "main.py"),
    ("Mod Explorer", "mod_viewer.py"),
]

def launch_tool(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        messagebox.showerror("Error", f"Script not found: {script_path}")
        return
    # Use sys.executable to launch with the same Python interpreter
    try:
        subprocess.Popen([sys.executable, script_path])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to launch {script_name}:\n{e}")

def main():
    root = tk.Tk()
    root.title("Cataclysm Multitool")
    root.geometry("400x250")

    label = tk.Label(root, text="Select a tool to launch:", font=("Arial", 12))
    label.pack(pady=10)

    for tool_name, script in TOOLS:
        btn = tk.Button(root, text=tool_name, width=25, command=lambda s=script: launch_tool(s))
        btn.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()