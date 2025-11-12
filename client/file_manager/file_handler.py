# file_handler.py - Member 2
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .file_queue import FileQueue

class FileHandlerGUI:
    """Giao diện xử lý kéo thả & chọn file"""
    def __init__(self, master):
        self.master = master
        self.master.title("Multi File Upload - File Manager (Member 2)")
        self.master.geometry("600x400")

        self.file_queue = FileQueue()

        # Label hướng dẫn kéo thả
        self.label = tk.Label(master, text="Kéo thả file vào đây hoặc nhấn 'Chọn file'",
                              width=60, height=4, bg="#ececec", relief="ridge")
        self.label.pack(pady=10)

        # Nút chọn file
        self.select_button = ttk.Button(master, text="Chọn file", command=self.select_files)
        self.select_button.pack(pady=5)

        # Treeview hiển thị danh sách file
        self.tree = ttk.Treeview(master, columns=("size", "status"), show="headings")
        self.tree.heading("size", text="Kích thước (KB)")
        self.tree.heading("status", text="Trạng thái")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.column("size", width=120)
        self.tree.column("status", width=150)

        # Cấu hình drop (dành cho Windows/Linux)
        self.master.drop_target_register(tk.DND_FILES)
        self.master.dnd_bind('<<Drop>>', self.drop_files)

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
        if size_kb > 50000:  # Giới hạn ví dụ: 50MB
            messagebox.showwarning("Cảnh báo", f"File quá lớn: {os.path.basename(file_path)}")
            return

        added = self.file_queue.add_file(file_path)
        if added:
            self.tree.insert("", "end", values=(size_kb, "Chờ upload"))
        else:
            messagebox.showinfo("Thông báo", f"File '{os.path.basename(file_path)}' đã có trong danh sách.")

if __name__ == "__main__":
    from tkinterdnd2 import TkinterDnD
    root = TkinterDnD.Tk()
    app = FileHandlerGUI(root)
    root.mainloop()
