import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import time
import json
from datetime import datetime

CONFIG_FILE = os.path.join("mod_manager", "cfg", "mod_manager_config.json")
DEFAULT_BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'backup')

def get_backup_dir():
    config = {}
    changed = False
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except Exception:
            config = {}
    if "backup_dir" not in config or not config["backup_dir"]:
        config["backup_dir"] = DEFAULT_BACKUP_DIR
        changed = True
    if changed:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    backup_dir = os.path.abspath(config["backup_dir"])
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
        self.info_text = tk.Text(info_frame, height=8, state='disabled', wrap='word')
        self.info_text.pack(fill=tk.X)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.folder = folder
        self.folder_label.config(text=folder)
        self.populate_current()
        self.populate_backup()

    def create_backup(self):
        backup_dir = get_backup_dir()
        if not hasattr(self, 'folder'):
            return
        sels = self.left_list.curselection()
        dirs = [self.left_list.get(i) for i in sels]
        if not dirs:
            messagebox.showinfo("No Selection", "Please select folders to backup.")
            return
        for d in dirs:
            src = os.path.join(self.folder, d)
            if os.path.isdir(src):
                desc = simpledialog.askstring("Backup Description", f"Enter description for '{d}':")
                ts = time.strftime('%Y%m%d%H%M%S')
                base = f"{d}_{ts}"
                zip_path = os.path.join(backup_dir, base)
                shutil.make_archive(zip_path, 'zip', src)
                meta = {'name': d, 'timestamp': ts, 'description': desc or ''}
                with open(zip_path + '.json', 'w') as sf:
                    json.dump(meta, sf, indent=2)
        self.populate_backup()

    def populate_current(self):
        self.left_list.delete(0, tk.END)
        folders = []
        for e in os.listdir(self.folder):
            p = os.path.join(self.folder, e)
            if os.path.isdir(p):
                ctime = datetime.fromtimestamp(os.path.getctime(p))
                folders.append((e, ctime))
        opt = self.lsort_var.get()
        if opt.startswith('Name'):
            folders.sort(key=lambda f: f[0].lower(), reverse=(opt=='Name Z-A'))
        else:
            folders.sort(key=lambda f: f[1], reverse=(opt=='Date ↑'))
        self.left_folders = folders
        for name, _ in folders:
            self.left_list.insert(tk.END, name)

    def populate_backup(self):
        backup_dir = get_backup_dir()
        self.right_list.delete(0, tk.END)
        entries = []
        for fn in os.listdir(backup_dir):
            if not fn.endswith('.zip'): continue
            sc = os.path.join(backup_dir, fn.replace('.zip','.json'))
            meta = {}
            if os.path.isfile(sc):
                try:
                    meta = json.load(open(sc))
                except:
                    meta = {}
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
        opt = self.rsort_var.get()
        if opt.startswith('Date'):
            entries.sort(key=lambda e: e[3] or datetime.min, reverse=(opt=='Date ↓'))
        elif opt.startswith('Name'):
            entries.sort(key=lambda e: e[1].lower(), reverse=(opt=='Name Z-A'))
        else:
            entries.sort(key=lambda e: e[2].lower(), reverse=(opt=='Description Z-A'))
        self.files = [e[0] for e in entries]
        self.metadata = {e[0]:{'name':e[1],'description':e[2],'timestamp':e[3].strftime('%Y%m%d%H%M%S') if e[3] else ''} for e in entries}
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
            info.append(f"World: {name} | Created: {ctime.strftime('%Y-%m-%d %H:%M:%S')} | Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        self.show_info("\n".join(info))


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
            parts = []
            if desc:
                parts.append(f"Description: {desc}")
            parts.append(f"World: {world}")
            parts.append(f"Time: {date_str}")
            info.append(" | ".join(parts))
        self.show_info("\n".join(info))
        

    def load_backup(self):
        backup_dir = get_backup_dir()
        sel = self.right_list.curselection()
        if not sel or not hasattr(self, 'folder'):
            return
        for i in sel:
            fn = self.files[i]
            shutil.unpack_archive(os.path.join(backup_dir, fn), self.folder)
        self.populate_current()
        self.populate_backup()
        self.clear_info()

    def delete_backup(self):
        backup_dir = get_backup_dir()
        sel = self.right_list.curselection()
        if not sel:
            return
        for i in sel:
            fn = self.files[i]
            if messagebox.askyesno("Delete Backup", f"Delete '{fn}'? This cannot be undone."):
                os.remove(os.path.join(backup_dir, fn))
                sc = os.path.join(backup_dir, fn.replace('.zip', '.json'))
                if os.path.isfile(sc):
                    os.remove(sc)
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