import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


class ProfileManagerDialog(tk.Toplevel):
    def __init__(self, parent, *, on_create, on_rename, on_delete, on_export, on_import, on_set_install_dir, current_profile_name=""):
        super().__init__(parent)
        self.on_set_install_dir = on_set_install_dir  # <-- THIS LINE is required!
        self.title("Manage Profiles")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()

        self.current_profile_name = current_profile_name

        self._build_ui(on_create, on_rename, on_delete, on_export, on_import)

        self.wait_visibility()
        self.focus()

    def _build_ui(self, on_create, on_rename, on_delete, on_export, on_import):
        frame = tk.Frame(self, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        profile_label_text = f"Current Profile: {self.current_profile_name}" if self.current_profile_name else "No Profile Selected"
        self.profile_label = tk.Label(frame, text=profile_label_text, font=("Arial", 12, "bold"))
        self.profile_label.pack(pady=(0, 10))

        btn_frame = tk.Frame(frame)
        btn_frame.pack()

        for text, cmd in [("New", on_create),
                        ("Rename", on_rename),
                        ("Delete", on_delete),
                        ("Export", on_export),
                        ("Import", on_import)]:
            tk.Button(btn_frame, text=text, command=cmd, width=15).pack(side=tk.TOP, fill=tk.X, pady=3)

        tk.Button(frame, text="Set Install Directory", command=self.on_set_install_dir, width=15).pack(pady=(15, 0))



    def update_profile_name(self, new_name):
        self.current_profile_name = new_name
        self.profile_label.config(text=f"Current Profile: {new_name}" if new_name else "No Profile Selected")