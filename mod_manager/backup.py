import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import time
import json
from datetime import datetime

CONFIG_FILE = os.path.join("cfg", "mod_manager_config.json")
DEFAULT_BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'backup')

def get_backup_dir():
    """Get or create backup directory from config
    
    Returns:
        str: Absolute path to backup directory
    """
    config = {}
    changed = False
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding='utf-8') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config: {e}")
            config = {}
    
    # ensure backup directory is configured.
    if "backup_dir" not in config or not config["backup_dir"]:
        config["backup_dir"] = DEFAULT_BACKUP_DIR
        changed = True
    
    # save config if we added the default.
    if changed:
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w", encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: Failed to save config: {e}")
    
    # create the backup directory if it doesn't exist.
    backup_dir = os.path.abspath(config["backup_dir"])
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create backup directory: {e}")
        # fallback to default if configured path fails.
        backup_dir = os.path.abspath(DEFAULT_BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
    
    return backup_dir

class BackupViewerCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("Backup Viewer")
        self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        # store backups and metadata
        self.files = []
        self.metadata = {}
        self.create_widgets()

    def create_widgets(self):
        # Top: folder actions
        top = ttk.Frame(self.root, padding=5)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Select Folder", command=self.select_folder).pack(side=tk.LEFT)
        self.folder_label = ttk.Label(top, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="Delete Backup", command=self.delete_backup).pack(side=tk.RIGHT)
        ttk.Button(top, text="Load Backup", command=self.load_backup).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top, text="Create Backup", command=self.create_backup).pack(side=tk.RIGHT, padx=5)

        # Middle: directory lists
        middle = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        middle.pack(fill=tk.BOTH, expand=True, pady=5)

        # left: folders with sort
        left_frame = ttk.Frame(middle)
        lsort_frame = ttk.Frame(left_frame)
        lsort_frame.pack(fill=tk.X, pady=(0,5))
        ttk.Label(lsort_frame, text="Sort folders:").pack(side=tk.LEFT)
        self.lsort_var = tk.StringVar()
        self.lsort_box = ttk.Combobox(lsort_frame, textvariable=self.lsort_var, state="readonly", values=[
            'Name A-Z','Name Z-A','Date New-Old','Date Old-New'])
        self.lsort_box.current(0)
        self.lsort_box.pack(side=tk.LEFT, padx=5)
        self.lsort_box.bind('<<ComboboxSelected>>', lambda e: self.populate_current())

        self.left_list = tk.Listbox(left_frame, selectmode=tk.MULTIPLE)
        left_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_list.yview)
        self.left_list.config(yscrollcommand=left_scroll.set)
        self.left_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_list.bind('<<ListboxSelect>>', self.on_select_left)
        middle.add(left_frame, weight=1)

        # right: backups with sort and multiselect
        right_frame = ttk.Frame(middle)
        rsort_frame = ttk.Frame(right_frame)
        rsort_frame.pack(fill=tk.X, pady=(0,5))
        ttk.Label(rsort_frame, text="Sort backups:").pack(side=tk.LEFT)
        self.rsort_var = tk.StringVar()
        self.rsort_box = ttk.Combobox(rsort_frame, textvariable=self.rsort_var, state="readonly", values=[
            'Date New-Old','Date Old-New','Name A-Z','Name Z-A','Description A-Z','Description Z-A'])
        self.rsort_box.current(0)
        self.rsort_box.pack(side=tk.RIGHT, padx=5)
        self.rsort_box.bind('<<ComboboxSelected>>', lambda e: self.populate_backup())

        self.right_list = tk.Listbox(right_frame, selectmode=tk.MULTIPLE)
        right_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_list.yview)
        self.right_list.config(yscrollcommand=right_scroll.set)
        self.right_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_list.bind('<<ListboxSelect>>', self.on_select_backup)
        middle.add(right_frame, weight=1)

        self.left_list.bind('<FocusIn>', self.on_select_left)
        self.right_list.bind('<FocusIn>', self.on_select_backup)

        # Bottom: info display
        info_frame = ttk.LabelFrame(self.root, text="Details", padding=5)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        self.info_text = tk.Text(info_frame, height=10, state='disabled', wrap='word')
        self.info_text.pack(fill=tk.X)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.folder = folder
        self.folder_label.config(text=folder)
        self.populate_current()
        self.populate_backup()

    def _extract_mod_list(self, world_path):
        """extract list of mods from world save folder
        
        args:
            world_path: path to the world save folder
            
        returns:
            list of mod names, or empty list if not found
        """
        mods = []
        
        # check for mods.json in the world folder (cataclysm saves mod list here)
        mods_json_path = os.path.join(world_path, 'mods.json')
        if os.path.isfile(mods_json_path):
            try:
                with open(mods_json_path, 'r', encoding='utf-8') as f:
                    mods_data = json.load(f)
                    # mods.json is typically a list of mod IDs
                    if isinstance(mods_data, list):
                        mods = mods_data
                    elif isinstance(mods_data, dict):
                        # some versions might store it differently
                        mods = mods_data.get('mods', [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to read mods.json: {e}")
        
        # if mods.json doesn't exist, try worldoptions.json or worldoptions.txt
        if not mods:
            worldoptions_path = os.path.join(world_path, 'worldoptions.json')
            if os.path.isfile(worldoptions_path):
                try:
                    with open(worldoptions_path, 'r', encoding='utf-8') as f:
                        options = json.load(f)
                        # worldoptions might have a mods list
                        if isinstance(options, list):
                            for opt in options:
                                if isinstance(opt, dict) and opt.get('name') == 'ACTIVE_WORLD_MODS':
                                    mods = opt.get('value', [])
                                    break
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to read worldoptions.json: {e}")
        
        return mods

    def create_backup(self):
        """Create backup archives for selected folders"""
        backup_dir = get_backup_dir()
        if not hasattr(self, 'folder') or not self.folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        
        sels = self.left_list.curselection()
        dirs = [self.left_list.get(i) for i in sels]
        if not dirs:
            messagebox.showinfo("No Selection", "Please select folders to backup.")
            return
        
        success_count = 0
        failed = []
        
        for d in dirs:
            src = os.path.join(self.folder, d)
            if not os.path.isdir(src):
                failed.append((d, "Not a directory"))
                continue
            
            try:
                desc = simpledialog.askstring("Backup Description", f"Enter description for '{d}':")
                if desc is None:  # user cancelled.
                    continue
                
                # generate timestamp-based filename.
                ts = time.strftime('%Y%m%d%H%M%S')
                base = f"{d}_{ts}"
                zip_path = os.path.join(backup_dir, base)
                
                # create backup archive.
                shutil.make_archive(zip_path, 'zip', src)
                
                # extract mod list from the world save.
                mod_list = self._extract_mod_list(src)
                
                # save metadata alongside the zip.
                meta = {
                    'name': d,
                    'timestamp': ts,
                    'description': desc or '',
                    'mods': mod_list,
                    'mod_count': len(mod_list)
                }
                with open(zip_path + '.json', 'w', encoding='utf-8') as sf:
                    json.dump(meta, sf, indent=2)
                
                success_count += 1
            except Exception as e:
                failed.append((d, str(e)))
        
        # Show results
        if success_count > 0:
            msg = f"Successfully backed up {success_count} folder(s)."
            if failed:
                msg += f"\n\nFailed: {len(failed)}"
                for name, error in failed:
                    msg += f"\n- {name}: {error}"
            messagebox.showinfo("Backup Complete", msg)
        elif failed:
            msg = "All backups failed:\n"
            for name, error in failed:
                msg += f"\n- {name}: {error}"
            messagebox.showerror("Backup Failed", msg)
        
        self.populate_backup()

    def populate_current(self):
        """populate left list with folders from selected directory."""
        self.left_list.delete(0, tk.END)
        folders = []
        for e in os.listdir(self.folder):
            p = os.path.join(self.folder, e)
            if os.path.isdir(p):
                ctime = datetime.fromtimestamp(os.path.getctime(p))
                folders.append((e, ctime))
        
        # sort based on user selection.
        opt = self.lsort_var.get()
        if opt.startswith('Name'):
            folders.sort(key=lambda f: f[0].lower(), reverse=(opt=='Name Z-A'))
        else:
            folders.sort(key=lambda f: f[1], reverse=(opt=='Date ↑'))
        
        self.left_folders = folders
        for name, _ in folders:
            self.left_list.insert(tk.END, name)

    def populate_backup(self):
        """populate right list with available backup archives."""
        backup_dir = get_backup_dir()
        self.right_list.delete(0, tk.END)
        entries = []
        
        # scan backup directory for zip files and their metadata.
        for fn in os.listdir(backup_dir):
            if not fn.endswith('.zip'): continue
            
            # try to load metadata from companion json file.
            sc = os.path.join(backup_dir, fn.replace('.zip','.json'))
            meta = {}
            if os.path.isfile(sc):
                try:
                    meta = json.load(open(sc))
                except:
                    meta = {}
            
            # extract info from metadata or fallback to filename.
            world = meta.get('name', fn)
            desc = meta.get('description', '')
            dt = None
            ts = meta.get('timestamp')
            if ts:
                try:
                    dt = datetime.strptime(ts, '%Y%m%d%H%M%S')
                except:
                    dt = None
            entries.append((fn, world, desc, dt))
        
        # sort based on user selection.
        opt = self.rsort_var.get()
        if opt.startswith('Date'):
            entries.sort(key=lambda e: e[3] or datetime.min, reverse=(opt=='Date ↓'))
        elif opt.startswith('Name'):
            entries.sort(key=lambda e: e[1].lower(), reverse=(opt=='Name Z-A'))
        else:
            entries.sort(key=lambda e: e[2].lower(), reverse=(opt=='Description Z-A'))
        
        # store for later use.
        self.files = [e[0] for e in entries]
        self.metadata = {e[0]:{'name':e[1],'description':e[2],'timestamp':e[3].strftime('%Y%m%d%H%M%S') if e[3] else ''} for e in entries}
        
        # display in list.
        for _, world, desc, dt in entries:
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''
            display = f"{desc} | {world} | {time_str}" if desc else f"{world} | {time_str}"
            self.right_list.insert(tk.END, display)

    def on_select_left(self, event):
        sel = self.left_list.curselection()
        info = []
        if not sel:
            self.clear_info()
            return
        for i in sel:
            name, ctime = self.left_folders[i]
            path = os.path.join(self.folder, name)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            
            # extract mod list from current world
            mod_list = self._extract_mod_list(path)
            
            parts = []
            parts.append(f"World: {name}")
            parts.append(f"Created: {ctime.strftime('%Y-%m-%d %H:%M:%S')}")
            parts.append(f"Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # show mod information if available
            if mod_list:
                parts.append(f"Mods: {len(mod_list)}")
                # show first few mods as preview
                if len(mod_list) <= 5:
                    mod_preview = ", ".join(mod_list)
                else:
                    mod_preview = ", ".join(mod_list[:5]) + f", ... (+{len(mod_list)-5} more)"
                parts.append(f"  → {mod_preview}")
            
            info.append("\n".join(parts))
        self.show_info("\n\n".join(info))


    def on_select_backup(self, event):
        sel = self.right_list.curselection()
        info = []
        if not sel:
            self.clear_info()
            return
        for i in sel:
            fn = self.files[i]
            m = self.metadata.get(fn, {})
            date_str = ''
            ts = m.get('timestamp')
            if ts:
                try:
                    date_str = datetime.strptime(ts, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
                except:
                    date_str = ts
            desc = m.get('description', '')
            world = m.get('name', '')
            mod_list = m.get('mods', [])
            mod_count = m.get('mod_count', len(mod_list))
            
            parts = []
            if desc:
                parts.append(f"Description: {desc}")
            parts.append(f"World: {world}")
            parts.append(f"Time: {date_str}")
            
            # add mod information if available
            if mod_list:
                parts.append(f"Mods: {mod_count}")
                # show first few mods as preview
                if len(mod_list) <= 5:
                    mod_preview = ", ".join(mod_list)
                else:
                    mod_preview = ", ".join(mod_list[:5]) + f", ... (+{len(mod_list)-5} more)"
                parts.append(f"  → {mod_preview}")
            
            info.append("\n".join(parts))
        self.show_info("\n\n".join(info))
        

    def load_backup(self):
        """Load selected backup archives"""
        if not hasattr(self, 'folder') or not self.folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        
        sel = self.right_list.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select backups to restore.")
            return
        
        backup_dir = get_backup_dir()
        success_count = 0
        failed = []
        
        for i in sel:
            fn = self.files[i]
            backup_path = os.path.join(backup_dir, fn)
            
            try:
                # get world name from metadata.
                meta = self.metadata.get(fn, {})
                world_name = meta.get('name', '')
                
                # fallback: extract world name from filename (format: worldname_timestamp.zip).
                if not world_name:
                    world_name = fn.rsplit('_', 1)[0] if '_' in fn else fn.replace('.zip', '')
                
                # sanitize to prevent path traversal attacks.
                world_name = os.path.basename(world_name)
                if not world_name or world_name in ('.', '..'):
                    failed.append((fn, "Invalid world name"))
                    continue
                
                # backups extract into a folder named after the world.
                target_dir = os.path.join(self.folder, world_name)
                
                # warn if target already exists.
                if os.path.exists(target_dir):
                    response = messagebox.askyesno(
                        "Overwrite?",
                        f"'{world_name}' already exists. Overwrite?",
                        parent=self.root
                    )
                    if not response:
                        continue
                    shutil.rmtree(target_dir, ignore_errors=True)
                
                # extract the backup.
                shutil.unpack_archive(backup_path, target_dir)
                success_count += 1
                
            except Exception as e:
                failed.append((fn, str(e)))
        
        # Show results
        if success_count > 0:
            msg = f"Successfully restored {success_count} backup(s)."
            if failed:
                msg += f"\n\nFailed: {len(failed)}"
                for name, error in failed:
                    msg += f"\n- {name}: {error}"
            messagebox.showinfo("Restore Complete", msg)
        elif failed:
            msg = "All restores failed:\n"
            for name, error in failed:
                msg += f"\n- {name}: {error}"
            messagebox.showerror("Restore Failed", msg)
        
        self.populate_current()
        self.populate_backup()
        self.clear_info()

    def delete_backup(self):
        """Delete selected backup archives"""
        sel = self.right_list.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Please select backups to delete.")
            return
        
        # Confirm deletion
        count = len(sel)
        if not messagebox.askyesno(
            "Delete Backups",
            f"Delete {count} backup(s)? This cannot be undone.",
            parent=self.root
        ):
            return
        
        backup_dir = get_backup_dir()
        success_count = 0
        failed = []
        
        for i in sel:
            fn = self.files[i]
            try:
                # Delete backup file
                backup_path = os.path.join(backup_dir, fn)
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                
                # Delete metadata file
                meta_path = os.path.join(backup_dir, fn.replace('.zip', '.json'))
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                
                success_count += 1
            except Exception as e:
                failed.append((fn, str(e)))
        
        # Show results
        if success_count > 0 and not failed:
            messagebox.showinfo("Delete Complete", f"Deleted {success_count} backup(s).")
        elif failed:
            msg = f"Deleted {success_count} backup(s).\n\nFailed: {len(failed)}"
            for name, error in failed:
                msg += f"\n- {name}: {error}"
            messagebox.showwarning("Delete Partial", msg)
        
        self.populate_backup()
        self.clear_info()

    def show_info(self, text):
        self.info_text.config(state='normal')
        self.info_text.delete('1.0', tk.END)
        self.info_text.insert(tk.END, text)
        self.info_text.config(state='disabled')

    def clear_info(self):
        self.show_info("")

if __name__ == '__main__':
    root = tk.Tk()
    BackupViewerCreator(root)
    root.mainloop()