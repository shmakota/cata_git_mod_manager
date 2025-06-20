import os
import json
import tkinter as tk
import re
from tkinter import filedialog, ttk
import subprocess
import platform
import sys


def scan_mod_directory(directory):
    mod_data = []

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith('.json'):
                continue

            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, dict):
                        content = [content]
                    elif not isinstance(content, list):
                        continue

                    for entry in content:
                        if not isinstance(entry, dict):
                            continue

                        entry_type = entry.get('type')
                        entry_id = entry.get('id') or entry.get('om_terrain') or 'null'

                        # Handle 'recipe' specially because 'result' is used as ID
                        if entry_type == 'recipe':
                            result = entry.get('result', 'null')
                            category = entry.get('category', '')
                            subcategory = entry.get('subcategory', '')
                            description = f"{category} > {subcategory}" if subcategory else category
                            mod_data.append({
                                'type': 'recipe',
                                'id': result,
                                'name': None,
                                'name_plural': '',
                                'description': description,
                                'file': filepath,
                                'full': entry
                            })
                            continue
                        elif entry_type == 'speech':
                            speaker = entry.get('speaker', 'Unknown speaker')
                            sound = entry.get('sound', 'No speech line provided.')
                            mod_data.append({
                                'type': 'speech',
                                'id': entry.get('id', 'null'),
                                'name': speaker,
                                'name_plural': '',
                                'description': sound,
                                'file': filepath,
                                'full': entry
                            })
                            continue

                        # Generalized fallback for all other types
                        name = entry.get('name')
                        desc = entry.get('description') or entry.get('desc')

                        if isinstance(name, dict):
                            name_str = name.get('str') or name.get('str_sp', '')
                            name_plural = name.get('str_pl', '')
                        elif isinstance(name, list):
                            name_str = ' '.join(str(item) for item in name)
                            name_plural = ''
                        else:
                            name_str = str(name) if name else ''
                            name_plural = ''

                        if isinstance(desc, dict):
                            desc_str = desc.get('str') or ''
                        elif isinstance(desc, list):
                            desc_str = ' '.join(str(item) for item in desc)
                        else:
                            desc_str = str(desc) if desc else ''

                        # Fallback to 'text' field if no name/desc
                        if not name_str and not desc_str:
                            fallback_text = entry.get('text', '')
                            if isinstance(fallback_text, dict):
                                fallback_text = fallback_text.get('str', '')
                            if fallback_text:
                                name_str = fallback_text
                                desc_str = fallback_text
                            else:
                                desc_str = "This type has not yet been fully implemented. Bug the GitHub!"

                        name_str = re.sub(r'</?color[^>]*>', '', name_str)

                        mod_data.append({
                            'type': entry_type or 'unknown',
                            'id': entry_id,
                            'name': name_str or None,
                            'name_plural': name_plural,
                            'description': desc_str,
                            'file': filepath,
                            'full': entry
                        })


            except Exception as e:
                print(f"[!] Failed to read {filepath}: {e}")

    return mod_data


def get_mod_name(directory):
    modinfo_path = os.path.join(directory, "modinfo.json")
    if os.path.isfile(modinfo_path):
        try:
            with open(modinfo_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                name = None
                if isinstance(data, dict):
                    name = data.get('name')
                elif isinstance(data, list) and isinstance(data[0], dict):
                    name = data[0].get('name')

                if name:
                    return re.sub(r'</?color[^>]*>', '', name)
        except Exception as e:
            print(f"[!] Failed to read modinfo.json: {e}")

    return None


class ModViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cataclysm Mod Explorer")
        self.geometry("1000x650")

        self.mod_data = []
        self.filtered_data = []

        self.sort_column = None
        self.sort_reverse = False
        self.columns = ('name', 'description', 'id', 'type')

        self.create_widgets()

    def create_widgets(self):
        # Top Bar
        top_frame = tk.Frame(self)
        top_frame.pack(fill='x', padx=10, pady=10)

        tk.Button(top_frame, text="Browse Mod Folder", command=self.browse_folder).pack(side='left')

        self.open_folder_button = tk.Button(top_frame, text="Open Folder", command=self.open_folder)
        self.open_folder_button.pack(side='left', padx=5)
        self.open_folder_button.config(state='disabled')  # disabled until a folder is selected

        self.path_label = tk.Label(top_frame, text="No folder selected", anchor='w')
        self.path_label.pack(side='left', padx=10)

        # Search Bar
        search_frame = tk.Frame(self)
        search_frame.pack(fill='x', padx=10)

        tk.Label(search_frame, text="Search:").pack(side='left')
        self.search_field = tk.StringVar(value='All')
        search_options = ['All', 'Type', 'ID', 'Name', 'Description']
        search_dropdown = ttk.Combobox(search_frame, textvariable=self.search_field, values=search_options, state='readonly', width=12)
        search_dropdown.pack(side='left', padx=(5, 10))
        search_dropdown.bind("<<ComboboxSelected>>", self.update_filter)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.update_filter)
        tk.Entry(search_frame, textvariable=self.search_var).pack(side='left', fill='x', expand=True)

        self.use_new_order = tk.BooleanVar(value=True)
        tk.Checkbutton(search_frame, text="Swap Columns", variable=self.use_new_order, command=self.update_order_and_refresh).pack(side='right', padx=(10, 0))

        self.count_label = tk.Label(search_frame, text="Entries: 0", anchor='e', fg='gray', font=('Arial', 10, 'italic'))
        self.count_label.pack(side='right', padx=(10, 0))

        # Paned Window: Treeview and Detail Panel
        main_pane = tk.PanedWindow(self, orient=tk.VERTICAL)
        main_pane.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        # Treeview
        tree_frame = tk.Frame(main_pane)
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side='right', fill='y')

        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.tree.yview)

        for col in self.columns:
            self.tree.heading(col, text=col.capitalize(), command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=150 if col != 'description' else 400, anchor='w')

        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        main_pane.add(tree_frame, stretch='always')

        # Detail Text
        self.detail_text = tk.Text(main_pane, wrap='word')
        main_pane.add(self.detail_text, height=150)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            mod_name = get_mod_name(folder)
            self.title(f"Cataclysm Mod Explorer: {mod_name}")
            self.path_label.config(text=folder)
            self.mod_data = scan_mod_directory(folder)
            self.update_filter()

            # Enable the open folder button
            self.open_folder_button.config(state='normal')


    def open_folder(self):
        folder = self.path_label.cget("text")
        if os.path.isdir(folder):
            self.open_path(folder)

    def open_entry_source(self):
        selected = self.tree.selection()
        if not selected:
            return
        entry = self.filtered_data[int(selected[0])]
        filepath = entry.get('file')
        if filepath and os.path.isfile(filepath):
            self.open_path(filepath)

    def open_path(self, path):
        # Open folder or file in system's default file explorer or editor
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(["explorer", path])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux and others
                subprocess.run(["xdg-open", path])
        except Exception as e:
            print(f"[!] Failed to open path {path}: {e}")

    def on_select(self, event):
        selected = self.tree.selection()
        print(f"Selection changed: {selected}")

        entry = self.filtered_data[idx]
        self.detail_text.delete(1.0, tk.END)

        if self.use_new_order.get():
            lines = [
                f"Name: {entry.get('name', '')}",
                f"Description:\n{entry.get('description', '')}\n",
                f"ID: {entry['id']}",
                f"Type: {entry['type']}\n"
            ]
        else:
            lines = [
                f"Type: {entry['type']}",
                f"ID: {entry['id']}",
                f"Name: {entry.get('name', '')}",
                f"Description:\n{entry.get('description', '')}\n"
            ]

        lines.append(f"File: {entry['file']}\n")
        lines.append(json.dumps(entry['full'], indent=2))
        self.detail_text.insert(tk.END, "\n".join(lines))


    def update_filter(self, *_):
        query = self.search_var.get().lower()
        field = self.search_field.get()

        def match(entry):
            fields = {
                'ID': str(entry['id']),
                'Name': str(entry.get('name', '')),
                'Description': str(entry.get('description', '')),
                'Type': str(entry.get('type', ''))
            }
            if field == 'All':
                return any(query in v.lower() for v in fields.values())
            return query in fields.get(field, '').lower()

        self.filtered_data = [e for e in self.mod_data if match(e)]
        self.populate_tree()
        self.count_label.config(text=f"Entries: {len(self.filtered_data)}")

    def update_order_and_refresh(self):
        self.update_columns()
        self.populate_tree()
        self.detail_text.delete(1.0, tk.END)

    def update_columns(self):
        self.columns = ('name', 'description', 'id', 'type') if self.use_new_order.get() else ('type', 'id', 'name', 'description')
        self.tree.config(columns=self.columns)
        for col in self.columns:
            self.tree.heading(col, text=col.capitalize(), command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=150 if col != 'description' else 400, anchor='w')

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, entry in enumerate(self.filtered_data):
            values = []
            for col in self.columns:
                if col == 'id':
                    values.append(entry['id'] or 'null')
                elif col == 'name':
                    values.append(entry.get('name') or 'null')
                elif col == 'description':
                    values.append((entry.get('description') or 'null')[:100])
                elif col == 'type':
                    values.append(entry.get('type') or 'null')
                else:
                    values.append('null')
            self.tree.insert('', 'end', iid=idx, values=values)

    def sort_by(self, column):
        reverse = self.sort_column == column and not self.sort_reverse
        self.filtered_data.sort(key=lambda e: str(e.get(column, '')).lower(), reverse=reverse)
        self.sort_column = column
        self.sort_reverse = reverse
        self.populate_tree()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        entry = self.filtered_data[int(selected[0])]
        self.detail_text.delete(1.0, tk.END)

        if self.use_new_order.get():
            lines = [
                f"Name: {entry.get('name', '')}",
                f"Description:\n{entry.get('description', '')}\n",
                f"ID: {entry['id']}",
                f"Type: {entry['type']}\n"
            ]
        else:
            lines = [
                f"Type: {entry['type']}",
                f"ID: {entry['id']}",
                f"Name: {entry.get('name', '')}",
                f"Description:\n{entry.get('description', '')}\n"
            ]

        lines.append(f"File: {entry['file']}\n")
        lines.append(json.dumps(entry['full'], indent=2))
        self.detail_text.insert(tk.END, "\n".join(lines))


if __name__ == "__main__":
    app = ModViewerApp()

    # Check for command-line argument
    if len(sys.argv) > 1:
        folder = sys.argv[1]
        if os.path.isdir(folder):
            mod_name = get_mod_name(folder)
            app.title(f"Cataclysm Mod Explorer: {mod_name or 'Unnamed Mod'}")
            app.path_label.config(text=folder)
            app.mod_data = scan_mod_directory(folder)
            app.update_filter()
            app.open_folder_button.config(state='normal')

    app.mainloop()