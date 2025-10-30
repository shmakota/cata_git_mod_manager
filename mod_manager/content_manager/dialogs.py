"""
Dialog classes for Content Manager
Extracted from app.py for better organization and reusability
"""

import tkinter as tk
from tkinter import ttk, Toplevel, Label


class UpdateProgressDialog:
    """
    Shows progress while updating mods
    Displays current mod being updated and count (X/Y)
    """
    
    def __init__(self, parent):
        """
        Create update progress dialog
        
        Args:
            parent: Parent tkinter window
        """
        self.dialog = Toplevel(parent)
        self.dialog.title("Updating Mods")
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.status_label = Label(
            self.dialog,
            text="Updating...",
            wraplength=350
        )
        self.status_label.pack(expand=True, pady=20)
    
    def update_status(self, text):
        """
        Update the status text
        
        Args:
            text: Status message to display
        """
        self.status_label.config(text=text)
        self.dialog.update()
    
    def close(self):
        """Close the dialog"""
        self.dialog.destroy()


class ScrollableErrorDialog:
    """
    Scrollable error dialog for displaying multiple errors
    Much better than messagebox for long error lists
    """
    
    def __init__(self, parent, title, message, errors):
        """
        Create scrollable error dialog
        
        Args:
            parent: Parent tkinter window
            title: Dialog window title
            message: Header message
            errors: List of (name, error_message) tuples
        """
        self.dialog = Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # header label
        header_label = Label(
            self.dialog,
            text=message,
            font=("TkDefaultFont", 11, "bold")
        )
        header_label.pack(padx=20, pady=(20, 10), anchor="w")
        
        # scrollable text frame
        text_frame = tk.Frame(self.dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        error_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            font=("TkDefaultFont", 10)
        )
        error_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=error_text.yview)
        
        # populate error text
        for name, error in errors:
            error_text.insert(tk.END, f"• {name}\n", "bold")
            error_text.insert(tk.END, f"  {error}\n\n")
        
        # make bold tag
        error_text.tag_config("bold", font=("TkDefaultFont", 10, "bold"))
        error_text.config(state=tk.DISABLED)
        
        # close button
        tk.Button(
            self.dialog,
            text="Close",
            command=self.dialog.destroy,
            width=15
        ).pack(pady=(0, 20))
    
    def wait_window(self):
        """Wait for dialog to close"""
        self.dialog.wait_window()


# Convenience function for backward compatibility
def show_error_dialog(parent, title, message, errors):
    """
    Show a scrollable error dialog
    
    Args:
        parent: Parent tkinter window
        title: Dialog window title  
        message: Header message
        errors: List of (name, error_message) tuples
    """
    dialog = ScrollableErrorDialog(parent, title, message, errors)
    # Don't wait - let it be non-blocking

