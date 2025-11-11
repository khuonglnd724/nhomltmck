import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import time

from async_controller.thread_manager import ThreadManager
from uploader.upload_client import UploadClient  # chắc chắn file này là upload_client.py


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi File Uploader - Member 4 GUI")
        self.root.geometry("700x400")
        self.root.configure(bg="#f2f2f2")

        # --- Top buttons ---
        top_frame = tk.Frame(root, bg="#f2f2f2")
        top_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(top_frame, text="➕ Thêm file", command=self.add_files).pack(side="left", padx=5)
        tk.Button(top_frame, text="🚀 Bắt đầu Upload", command=self.start_upload).pack(side="left", padx=5)
        tk.Button(top_frame, text="❌ Thoát", command=self.on_close).pack(side="right", padx=5)

        # --- Table ---
        self.tree = ttk.Treeview(root, columns=("name", "status", "progress", "speed"), show="headings")
        self.tree.heading("name", text="Tên file")
        self.tree.heading("status", text="Trạng thái")
        self.tree.heading("progress", text="Tiến độ (%)")
        self.tree.heading("speed", text="Tốc độ (KB/s)")

        self.tree.column("name", width=250)
        self.tree.column("status", width=100)
        self.tree.column("progress", width=100, anchor="center")
        self.tree.column("speed", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Drag and drop hint ---
        label = tk.Label(root, text="Kéo & thả file vào đây để thêm", bg="#f2f2f2", fg="gray")
        label.pack(pady=5)

        # --- Setup uploader and thread manager ---
        # Sửa host/port cho đúng với UploadClient
        self.uploader = UploadClient(host="127.0.0.1", port=9999)
        self.thread_manager = ThreadManager(self.uploader, max_workers=3, gui_update_cb=self.gui_update)

        self.file_map = {}  # file_id -> path

        # --- Close handler ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -------------------------------
    def add_files(self):
        files = filedialog.askopenfilenames(title="Chọn file để upload")
        for path in files:
            file_id = self.thread_manager.add_file(path)
            self.file_map[file_id] = path
            self.tree.insert("", "end", iid=file_id, values=(os.path.basename(path), "Chờ xử lý", "0%", "0.0"))

    def start_upload(self):
        if not self.file_map:
            messagebox.showwarning("Chưa có file", "Vui lòng thêm ít nhất 1 file để upload.")
            return
        messagebox.showinfo("Bắt đầu", "Đang tải lên... Xem tiến trình bên dưới.")
        # Bắt đầu upload bằng ThreadManager
        threading.Thread(target=self.thread_manager.start, daemon=True).start()

    # -------------------------------
    def gui_update(self, event_type, payload):
        """Callback từ ThreadManager"""
        if event_type == "progress":
            fid = payload["id"]
            uploaded = payload["uploaded"]
            total = payload["total"] or 1
            percent = int((uploaded / total) * 100)
            speed = round(payload.get("speed", 0.0) / 1024, 1)
            self.tree.set(fid, "progress", f"{percent}%")
            self.tree.set(fid, "speed", f"{speed}")
            self.tree.set(fid, "status", payload.get("status", "Uploading"))

        elif event_type == "status":
            fid = payload["id"]
            status = payload.get("status", "")
            self.tree.set(fid, "status", status)

        elif event_type == "added":
            fid = payload["id"]
            path = payload["path"]
            self.tree.insert("", "end", iid=fid, values=(os.path.basename(path), "Chờ xử lý", "0%", "0.0"))

    # -------------------------------
    def on_close(self):
        if messagebox.askyesno("Thoát", "Bạn có chắc muốn thoát chương trình không?"):
            self.thread_manager.stop(wait=False)
            self.root.destroy()


# -------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
