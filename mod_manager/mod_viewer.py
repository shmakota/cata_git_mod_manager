import os
import json
import tkinter as tk
import re
from tkinter import filedialog, ttk, messagebox
import subprocess
import platform
import sys


def scan_mod_directory(directory):
    mod_data = []

    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)

            # --- JSON files ---
            if file.endswith('.json'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        if isinstance(content, dict):
                            content = [content]
                        elif not isinstance(content, list):
                            continue

                        # check if this is a config/options.json file
                        is_balance_option = 'config' in filepath and 'options.json' in filepath
                        
                        # check if this is data/raw/languages.json
                        is_language = 'data' in filepath and 'raw' in filepath and 'languages.json' in filepath

                        for entry in content:
                            if not isinstance(entry, dict):
                                continue

                            entry_type = entry.get('type')
                            entry_id = entry.get('id') or entry.get('om_terrain') or 'null'

                            # Special handling for certain types
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

                            # Special handling for name entries (city/world names)
                            elif 'usage' in entry and 'name' in entry:
                                usage = entry.get('usage', 'unknown')
                                name_val = entry.get('name', '')
                                mod_data.append({
                                    'type': f'name_{usage}',
                                    'id': name_val,
                                    'name': name_val,
                                    'name_plural': '',
                                    'description': f'{usage.capitalize()} name',
                                    'file': filepath,
                                    'full': entry
                                })
                                continue

                            # Special handling for config/options.json entries
                            elif is_balance_option and 'name' in entry:
                                option_name = entry.get('name', 'unknown')
                                option_info = entry.get('info', '')
                                option_default = entry.get('default', '')
                                option_value = entry.get('value', '')
                                
                                # combine info, default, and value for description
                                desc_parts = []
                                if option_info:
                                    desc_parts.append(option_info)
                                if option_default:
                                    desc_parts.append(option_default)
                                if option_value:
                                    desc_parts.append(f"Current: {option_value}")
                                
                                mod_data.append({
                                    'type': 'balance_option',
                                    'id': option_name,
                                    'name': option_name,
                                    'name_plural': '',
                                    'description': ' | '.join(desc_parts) if desc_parts else 'Balance option',
                                    'file': filepath,
                                    'full': entry
                                })
                                continue

                            # Special handling for data/raw/languages.json entries
                            elif is_language:
                                lang_id = entry.get('id', entry.get('type', 'unknown'))
                                lang_name = entry.get('name', lang_id)
                                
                                mod_data.append({
                                    'type': 'language',
                                    'id': lang_id,
                                    'name': lang_name,
                                    'name_plural': '',
                                    'description': f'Language: {lang_name}',
                                    'file': filepath,
                                    'full': entry
                                })
                                continue

                            # General fallback for all other JSON types
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

                            if not name_str and not desc_str:
                                fallback_text = entry.get('text', '')
                                if isinstance(fallback_text, dict):
                                    fallback_text = fallback_text.get('str', '')
                                if fallback_text:
                                    name_str = fallback_text
                                    desc_str = fallback_text
                                else:
                                    desc_str = "null"

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
                    continue

            # --- LUA files ---
            elif file.endswith('.lua'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        snippet = ''.join(lines[:5]).strip()  # Preview first few lines
                        mod_data.append({
                            'type': 'lua',
                            'id': os.path.basename(filepath),
                            'name': os.path.splitext(file)[0],
                            'name_plural': '',
                            'description': snippet or 'Lua script',
                            'file': filepath,
                            'full': ''.join(lines)
                        })
                except Exception as e:
                    print(f"[!] Failed to read Lua file {filepath}: {e}")

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
        self.open_file_button = tk.Button(top_frame, text="Open with Default Program", command=self.open_selected_entry)
        self.open_file_button.pack(side='left', padx=5)
        self.open_file_button.config(state='disabled')  # disabled until an entry is selected

        self.save_results_button = tk.Button(top_frame, text="Save Results", command=self.save_results)
        self.save_results_button.pack(side='left', padx=5)
        self.save_results_button.config(state='disabled')  # disabled until entries are loaded

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
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side='left', fill='x', expand=True)
        
        # help tooltip button
        help_btn = tk.Button(search_frame, text="?", width=2, command=self.show_search_help)
        help_btn.pack(side='left', padx=(5, 0))

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

    def open_selected_entry(self):
        selected = self.tree.selection()
        if not selected:
            return
        entry = self.filtered_data[int(selected[0])]
        filepath = entry.get('file')
        if filepath and os.path.isfile(filepath):
            self.open_path(filepath)


    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            mod_name = get_mod_name(folder)
            self.title(f"Cataclysm Mod Explorer: {mod_name}")
            self.path_label.config(text=folder)
            self.mod_data = scan_mod_directory(folder)
            self.update_filter()

            # Enable the buttons
            self.open_folder_button.config(state='normal')
            self.open_file_button.config(state='normal')
            self.save_results_button.config(state='normal')


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
                subprocess.Popen(["explorer", path])
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", path])
            else:  # Linux and others
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            print(f"[!] Failed to open path {path}: {e}")

    def show_search_help(self):
        """Show help dialog for search features"""
        help_text = """Search Features:

Basic Search:
  • Type any text to search entries
  • Select field from dropdown to search specific fields

Exclusion Filter:
  • Use -"text" to EXCLUDE results containing that text
  • Example: gun -"zombie" 
    (shows guns but excludes anything with "zombie")
  
  • Multiple exclusions: gun -"zombie" -"broken"
    (excludes both zombie and broken items)

Advanced:
  • Combine inclusions and exclusions
  • Case-insensitive search
  • Works across all selected fields"""
        
        # create custom dialog with text widget
        help_window = tk.Toplevel(self)
        help_window.title("Search Help")
        help_window.geometry("500x350")
        help_window.transient(self)
        help_window.grab_set()
        
        # text widget with scrollbar
        text_frame = tk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("TkDefaultFont", 10))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
        # close button
        tk.Button(help_window, text="Close", command=help_window.destroy, width=15).pack(pady=(0, 10))
    
    def save_results(self):
        """Save all currently filtered entries to a file"""
        if not self.filtered_data:
            messagebox.showinfo("No Data", "No entries to save. Load a mod folder first.")
            return
        
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            title="Save Results"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"Cataclysm Mod Explorer - Results Export\n")
                f.write(f"Total Entries: {len(self.filtered_data)}\n")
                f.write(f"Source Folder: {self.path_label.cget('text')}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write each entry
                for idx, entry in enumerate(self.filtered_data, 1):
                    f.write(f"Entry #{idx}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Name: {entry.get('name', 'null')}\n")
                    f.write(f"ID: {entry.get('id', 'null')}\n")
                    f.write(f"Type: {entry.get('type', 'unknown')}\n")
                    f.write(f"Description: {entry.get('description', 'null')}\n")
                    f.write(f"File: {entry.get('file', 'unknown')}\n")
                    f.write("\nFull Entry:\n")
                    
                    # Write full JSON or Lua content
                    if entry.get('type') == 'lua':
                        f.write(entry.get('full', ''))
                    else:
                        f.write(json.dumps(entry.get('full', {}), indent=2))
                    
                    f.write("\n\n" + "=" * 80 + "\n\n")
            
            messagebox.showinfo("Success", f"Saved {len(self.filtered_data)} entries to:\n{file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results:\n{e}")



    def update_filter(self, *_):
        query = self.search_var.get().lower()
        field = self.search_field.get()

        # parse exclusions using -"text" pattern
        exclusion_pattern = r'-"([^"]+)"'
        exclusions = re.findall(exclusion_pattern, query)
        
        # remove exclusions from main query
        clean_query = re.sub(exclusion_pattern, '', query).strip()

        def match(entry):
            fields = {
                'ID': str(entry['id']),
                'Name': str(entry.get('name', '')),
                'Description': str(entry.get('description', '')),
                'Type': str(entry.get('type', ''))
            }
            
            # check if entry matches the inclusion query
            if clean_query:
                if field == 'All':
                    if not any(clean_query in v.lower() for v in fields.values()):
                        return False
                else:
                    if clean_query not in fields.get(field, '').lower():
                        return False
            
            # check if entry contains any exclusions
            for exclusion in exclusions:
                exclusion = exclusion.lower()
                if field == 'All':
                    if any(exclusion in v.lower() for v in fields.values()):
                        return False
                else:
                    if exclusion in fields.get(field, '').lower():
                        return False
            
            return True

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
        if entry['type'] == 'lua':
            lines.append(entry['full'])
        else:
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
            app.open_file_button.config(state='normal')
            app.save_results_button.config(state='normal')

    app.mainloop()