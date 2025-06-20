import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

class EditModDialog(tk.Toplevel):

    def __init__(self, parent, url="", subdir="", keep_structure=False):
        super().__init__(parent)
        self.title("Edit Mod")
        self.geometry("500x180")
        self.result = None

        self.url_var = tk.StringVar(value=url)
        self.subdir_var = tk.StringVar(value=subdir)
        self.keep_structure_var = tk.BooleanVar(value=keep_structure)

        self._build_ui()

        self.transient(parent)
        self.grab_set()
        self.wait_visibility()
        self.focus()

    def _build_ui(self):
        frame = tk.Frame(self, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="GitHub ZIP URL:").grid(row=0, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.url_var, width=60).grid(row=0, column=1, sticky="ew", pady=5)

        tk.Label(frame, text="Subdirectory (optional):").grid(row=1, column=0, sticky="w")
        tk.Entry(frame, textvariable=self.subdir_var, width=60).grid(row=1, column=1, sticky="ew", pady=5)

        tk.Checkbutton(frame, text="Keep original folder structure", variable=self.keep_structure_var).grid(row=2, column=1, sticky="w", pady=5)

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="OK", width=10, command=self._on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.destroy).pack(side=tk.LEFT)

        frame.grid_columnconfigure(1, weight=1)

    def _on_ok(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "URL cannot be empty.", parent=self)
            return
        subdir = self.subdir_var.get().strip()
        keep_structure = self.keep_structure_var.get()
        self.result = (url, subdir, keep_structure)
        self.destroy()