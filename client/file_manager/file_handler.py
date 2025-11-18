"""File handler (Member 2) – test-only UI, headless by default.

This module provides a simple file queue helper. When imported by
client.gui.main_window, it does NOT build any UI and does not change
the root window. A minimal test UI is available when running this file
directly (python -m client.file_manager.file_handler).
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .file_queue import FileQueue

# Optional drag & drop support
try:
    from tkinterdnd2 import DND_FILES  # type: ignore
    HAS_DND = True
except Exception:
    HAS_DND = False


class FileHandlerGUI:
    """
    Headless by default. Set build_ui=True to open the test-only UI.
    """

    def __init__(self, master=None, build_ui: bool = False):
        self.master = master
        self.file_queue = FileQueue()

        if build_ui and self.master is not None:
            # Basic test window
            try:
                self.master.title("Multi File Upload - File Manager (Member 2)")
                self.master.geometry("600x400")
            except Exception:
                pass

            self.label = tk.Label(self.master, text="Kéo thả file vào đây hoặc nhấn 'Chọn file'",
                                  width=60, height=4, bg="#ececec", relief="ridge")
            self.label.pack(pady=10)

            self.select_button = ttk.Button(self.master, text="Chọn file", command=self.select_files)
            self.select_button.pack(pady=5)

            self.tree = ttk.Treeview(self.master, columns=("size", "status"), show="headings")
            self.tree.heading("size", text="Kích thước (KB)")
            self.tree.heading("status", text="Trạng thái")
            self.tree.pack(fill="both", expand=True, padx=10, pady=10)
            self.tree.column("size", width=120)
            self.tree.column("status", width=150)

            # Drag & drop if available
            if HAS_DND and hasattr(self.master, 'drop_target_register'):
                try:
                    self.master.drop_target_register(DND_FILES)
                    self.master.dnd_bind('<<Drop>>', self.drop_files)
                except Exception:
                    pass

    # ---------- Handlers (used by test UI) ----------
    def select_files(self):
        files = filedialog.askopenfilenames(title="Chọn nhiều file để upload")
        for file in files:
            self.add_file(file)

    def drop_files(self, event):
        files = self.master.tk.splitlist(event.data)
        for file in files:
            self.add_file(file)

    def add_file(self, file_path):
        if not os.path.isfile(file_path):
            return
        size_kb = os.path.getsize(file_path) // 1024
        if hasattr(self, 'tree') and size_kb > 50000:  # 50MB test-only limit
            messagebox.showwarning("Cảnh báo", f"File quá lớn: {os.path.basename(file_path)}")
            return

        added = self.file_queue.add_file(file_path)
        if hasattr(self, 'tree'):
            if added:
                self.tree.insert("", "end", values=(size_kb, "Chờ upload"))
            else:
                messagebox.showinfo("Thông báo", f"File '{os.path.basename(file_path)}' đã có trong danh sách.")


if __name__ == "__main__":
    try:
        from tkinterdnd2 import TkinterDnD  # type: ignore
        root = TkinterDnD.Tk()
    except Exception:
        # Fallback: allow running without tkinterdnd2
        root = tk.Tk()
    app = FileHandlerGUI(root, build_ui=True)
    root.mainloop()
