# this script is used to select which tool to launch: backup.py, restore.py, mod_manager.py, etc. it is launched from the parent directory .sh or .bat file. it uses tkinter gui

import tkinter as tk
from tkinter import messagebox, ttk, Toplevel, Label
import subprocess
import os
import sys
import logging

# Setup logging
logging.basicConfig(
    filename='mod_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Import updater
try:
    from updater import Updater
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    logging.warning("Updater module not available")

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

class MultitoolApp:
    def __init__(self, root):
        self.root = root
        
        # Initialize updater
        if UPDATER_AVAILABLE:
            self.updater = Updater()
            self.version = self.updater.get_current_version()
        else:
            self.updater = None
            self.version = "Unknown"
        
        # Set title with version
        self.root.title(f"Cataclysm Multitool v{self.version}")
        self.root.geometry("400x300")
        
        # Main label
        label = tk.Label(root, text="Select a tool to launch:", font=("Arial", 12))
        label.pack(pady=10)
        
        # Tool buttons
        for tool_name, script in TOOLS:
            btn = tk.Button(root, text=tool_name, width=25, command=lambda s=script: launch_tool(s))
            btn.pack(pady=5)
        
        # Community & Updates button at bottom
        community_frame = tk.Frame(root)
        community_frame.pack(pady=(10, 5))
        
        self.community_button = tk.Button(
            community_frame,
            text="Community & Updates",
            command=self._open_community_window,
            width=25,
            anchor="center"
        )
        self.community_button.pack()
    
    def _open_community_window(self):
        """Open the Community & Updates window with links and update checker"""
        import webbrowser
        
        window = Toplevel(self.root)
        window.title("Community & Updates")
        window.geometry("500x600")
        window.transient(self.root)
        window.grab_set()
        
        # Title
        title_label = Label(
            window,
            text="Cataclysm: Bright Nights Community",
            font=("TkDefaultFont", 14, "bold")
        )
        title_label.pack(pady=15)
        
        # Update section (moved to top)
        if UPDATER_AVAILABLE:
            update_section = tk.Frame(window)
            update_section.pack(pady=10)
            
            tk.Label(
                update_section,
                text="Multitool Updates:",
                font=("TkDefaultFont", 11, "bold")
            ).pack()
            
            version_label = Label(
                update_section,
                text=f"Current Version: v{self.version}",
                fg="gray"
            )
            version_label.pack(pady=5)
            
            self.community_update_button = tk.Button(
                update_section,
                text="Check for Updates",
                command=lambda: self._check_for_updates_in_community(window),
                width=30
            )
            self.community_update_button.pack(pady=5)
            
            # github link for multitool
            github_btn = tk.Button(
                update_section,
                text="📦 Multitool GitHub",
                command=lambda: webbrowser.open("https://github.com/shmakota/cata_git_mod_manager"),
                width=30
            )
            github_btn.pack(pady=(5, 0))
            
            # Store original button configuration
            self.community_original_button_config = {
                'width': 30,
                'fg': self.community_update_button.cget('fg'),
                'font': self.community_update_button.cget('font')
            }
        else:
            tk.Label(
                window,
                text="Updater not available",
                fg="gray"
            ).pack(pady=10)
        
        # Separator
        separator = ttk.Separator(window, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=15)
        
        # Community links section
        links_frame = tk.Frame(window)
        links_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        tk.Label(
            links_frame,
            text="Community Links:",
            font=("TkDefaultFont", 11, "bold")
        ).pack(pady=(0, 10))
        
        # Define community links
        links = [
            ("📖 Official Documentation", "https://docs.cataclysmbn.org/"),
            ("🎮 Discord Server", "https://discord.gg/XW7XhXuZ89"),
            ("💬 Subreddit (r/cataclysmbn)", "https://www.reddit.com/r/cataclysmbn/"),
            ("📚 Hitchhiker's Guide", "https://next.cbn-guide.pages.dev/?t=UNDEAD_PEOPLE"),
            ("🔧 BN GitHub", "https://github.com/cataclysmbnteam/Cataclysm-BN")
        ]
        
        # Create buttons for each link
        for label, url in links:
            btn = tk.Button(
                links_frame,
                text=label,
                command=lambda u=url: webbrowser.open(u),
                width=40,
                anchor="w"
            )
            btn.pack(pady=3)
        
        # Close button
        tk.Button(
            window,
            text="Close",
            command=window.destroy,
            width=15
        ).pack(pady=(10, 15))
    
    def _check_for_updates_in_community(self, parent_window):
        """Check for updates from within the community window"""
        if not UPDATER_AVAILABLE:
            messagebox.showerror("Error", "Updater module not available", parent=parent_window)
            return
        
        # Update button to show checking
        original_text = self.community_update_button.cget("text")
        self.community_update_button.config(
            text="Checking...",
            state="disabled",
            width=self.community_original_button_config['width']
        )
        parent_window.update()
        
        try:
            has_update, latest_version, download_url, release_notes = self.updater.check_for_updates()
            
            if has_update and latest_version:
                # Update button appearance
                self.community_update_button.config(
                    text=f"Update Available (v{latest_version})",
                    fg="green",
                    font=self.community_original_button_config['font'],
                    state="normal",
                    width=self.community_original_button_config['width']
                )
                # Close community window and show update dialog
                parent_window.destroy()
                self._show_update_dialog(latest_version, download_url, release_notes)
            else:
                # Reset button
                self.community_update_button.config(
                    text=original_text,
                    state="normal",
                    fg=self.community_original_button_config['fg'],
                    font=self.community_original_button_config['font'],
                    width=self.community_original_button_config['width']
                )
                messagebox.showinfo(
                    "No Updates",
                    f"You are running the latest version (v{self.version}).",
                    parent=parent_window
                )
        except Exception as e:
            # Reset button on error
            self.community_update_button.config(
                text=original_text,
                state="normal",
                fg=self.community_original_button_config['fg'],
                font=self.community_original_button_config['font'],
                width=self.community_original_button_config['width']
            )
            messagebox.showerror(
                "Update Check Failed",
                f"Failed to check for updates:\n{e}",
                parent=parent_window
            )
    
    def _check_for_updates(self):
        """Manual update check triggered by button"""
        if not UPDATER_AVAILABLE:
            messagebox.showerror("Error", "Updater module not available")
            return
        
        # Update button to show checking
        original_text = self.update_button.cget("text")
        self.update_button.config(
            text="Checking...",
            state="disabled",
            width=self.original_button_config['width']
        )
        self.root.update()
        
        try:
            has_update, latest_version, download_url, release_notes = self.updater.check_for_updates()
            
            if has_update and latest_version:
                # Update button appearance to show update available (keep consistent size)
                self.update_button.config(
                    text=f"Update Available (v{latest_version})",
                    fg="green",
                    font=self.original_button_config['font'],
                    state="normal",
                    width=self.original_button_config['width']
                )
                self._show_update_dialog(latest_version, download_url, release_notes)
            else:
                # Reset button to normal
                self.update_button.config(
                    text=original_text,
                    state="normal",
                    fg=self.original_button_config['fg'],
                    font=self.original_button_config['font'],
                    width=self.original_button_config['width']
                )
                messagebox.showinfo(
                    "No Updates",
                    f"You are running the latest version (v{self.version}).",
                    parent=self.root
                )
        except Exception as e:
            # Reset button to normal on error
            self.update_button.config(
                text=original_text,
                state="normal",
                fg=self.original_button_config['fg'],
                font=self.original_button_config['font'],
                width=self.original_button_config['width']
            )
            messagebox.showerror(
                "Update Check Failed",
                f"Failed to check for updates:\n{e}",
                parent=self.root
            )
    
    def _show_update_dialog(self, latest_version, download_url, release_notes):
        """Show dialog with update details and option to install"""
        dialog = Toplevel(self.root)
        dialog.title("Update Available")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Title
        title_label = Label(
            dialog,
            text=f"Version {latest_version} is available!",
            font=("TkDefaultFont", 12, "bold")
        )
        title_label.pack(pady=10)
        
        # Current version
        current_label = Label(dialog, text=f"Current version: {self.version}")
        current_label.pack()
        
        # Release notes with scrollbar
        notes_frame = tk.Frame(dialog)
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(notes_frame, text="Release Notes:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        
        # Text widget with scrollbar
        notes_container = tk.Frame(notes_frame)
        notes_container.pack(fill=tk.BOTH, expand=True)
        
        notes_scrollbar = ttk.Scrollbar(notes_container)
        notes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        notes_text = tk.Text(notes_container, wrap=tk.WORD, height=10, yscrollcommand=notes_scrollbar.set)
        notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        notes_scrollbar.config(command=notes_text.yview)
        
        if release_notes:
            notes_text.insert(1.0, release_notes)
        else:
            notes_text.insert(1.0, "No release notes available.")
        notes_text.config(state=tk.DISABLED)
        
        # Warning label (no expansion)
        warning_label = Label(
            dialog,
            text="⚠️  The application will restart after updating.\nYour settings and mods will be preserved.",
            fg="orange",
            justify=tk.CENTER
        )
        warning_label.pack(pady=(10, 5), padx=10)
        
        # Buttons (fixed size, no expansion)
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=(5, 15))
        
        def do_update():
            dialog.destroy()
            self._perform_update(download_url, latest_version)
        
        tk.Button(button_frame, text="Update Now", command=do_update, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Later", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)
    
    def _perform_update(self, download_url, new_version):
        """Perform the update with progress indication"""
        # Show progress dialog
        progress_dialog = Toplevel(self.root)
        progress_dialog.title("Updating...")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        status_label = Label(progress_dialog, text="Downloading update...", wraplength=350)
        status_label.pack(expand=True, pady=20)
        
        progress_dialog.update()
        
        def update_worker():
            try:
                success = self.updater.perform_update(download_url, new_version)
                progress_dialog.destroy()
                
                if success:
                    # Show success message and restart
                    messagebox.showinfo(
                        "Update Complete",
                        "Update installed successfully!\n\nThe application will now restart.",
                        parent=self.root
                    )
                    
                    # Restart the application
                    self._restart_application()
                else:
                    messagebox.showerror(
                        "Update Failed",
                        "Failed to install update. Check mod_debug.log and update_history.log for details.",
                        parent=self.root
                    )
            except Exception as e:
                progress_dialog.destroy()
                messagebox.showerror(
                    "Update Error",
                    f"An error occurred during update:\n{e}",
                    parent=self.root
                )
        
        # Run update in background
        self.root.after(100, update_worker)
    
    def _restart_application(self):
        """Restart the application"""
        try:
            python = sys.executable
            logging.info(f"Restarting application with: {python} {sys.argv}")
            os.execl(python, python, *sys.argv)
        except Exception as e:
            logging.error(f"Failed to restart application: {e}")
            messagebox.showwarning(
                "Restart Manually",
                f"Update completed successfully!\n\nPlease restart the application manually to use the new version.\n\nTechnical details: {e}",
                parent=self.root
            )
            self.root.quit()

def main():
    root = tk.Tk()
    app = MultitoolApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()