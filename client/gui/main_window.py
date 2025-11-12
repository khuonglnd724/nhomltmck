"""
Main Window GUI - Multi File Uploader
Member 1 - GUI Component
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import threading

# Setup path để import module client
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(current_dir))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import các module thật
from client.gui.progress_bar import ProgressBarManager
from client.file_manager.file_handler import FileHandlerGUI
from client.file_manager.file_queue import FileQueue
from client.uploader.upload_client import UploadClient
from client.async_controller.thread_manager import ThreadManager
from client.logger.logger import Logger

# TkinterDnD2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


class MainWindow:
    """Cửa sổ chính ứng dụng upload"""
    
    # Colors
    C = {
        'bg': '#1e1e2e', 'bg2': '#2d2d44', 'accent': '#7c3aed',
        'success': '#10b981', 'danger': '#ef4444', 'warning': '#f59e0b',
        'text': '#e0e0e0', 'muted': '#9ca3af'
    }
    
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Multi File Uploader Pro")
        self.root.geometry("900x600")
        self.root.configure(bg=self.C['bg'])
        
        self.file_map = {}
        self.is_uploading = False
        
        # Init components
        self.logger = Logger()
        self.file_handler = FileHandlerGUI(self.root)
        self.file_queue = FileQueue()
        
        self.logger.log("App started")
        
        # Build UI
        self.build_ui()
        self.setup_uploader()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        """Xây dựng giao diện"""
        # Header
        self.make_frame(self.root, self.C['bg2'], 'x', 80, False).pack(fill='x')
        self.make_label(self.root.winfo_children()[-1], "🚀 Multi File Uploader Pro", 
                       20, True, pady=10)
        self.make_label(self.root.winfo_children()[-1], 
                       "Kéo & thả file hoặc click • Upload đồng thời", 9)
        
        # Drop Zone
        drop_f = self.make_frame(self.root, self.C['bg'])
        drop_f.pack(fill='x', padx=20, pady=15)
        
        self.drop_zone = tk.Frame(drop_f, bg=self.C['bg2'], relief='solid', bd=2,
                                 highlightthickness=2, highlightbackground=self.C['accent'])
        self.drop_zone.pack(fill='x', ipady=30)
        
        self.make_label(self.drop_zone, "📁 Kéo & thả file vào đây", 14, True, pady=5)
        self.make_label(self.drop_zone, "hoặc click để chọn file", 10)
        
        self.drop_zone.bind("<Button-1>", lambda e: self.add_files())
        
        if HAS_DND and hasattr(self.drop_zone, 'drop_target_register'):
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind('<<Drop>>', self.on_drop)
        
        # Progress Section
        prog_f = self.make_frame(self.root, self.C['bg'])
        prog_f.pack(fill='both', expand=True, padx=20, pady=10)
        self.make_label(prog_f, "📋 Danh sách file", 12, True, anchor='w').pack(fill='x', pady=(0,10))
        
        self.progress_manager = ProgressBarManager(prog_f)
        
        # Controls
        ctrl = self.make_frame(self.root, self.C['bg'])
        ctrl.pack(fill='x', padx=20, pady=15)
        
        left = self.make_frame(ctrl, self.C['bg'])
        left.pack(side='left')
        self.btn_add = self.make_btn(left, "➕ Thêm", self.add_files, self.C['accent'])
        self.btn_start = self.make_btn(left, "🚀 Upload", self.start_upload, self.C['success'])
        
        right = self.make_frame(ctrl, self.C['bg'])
        right.pack(side='right')
        self.btn_cancel = self.make_btn(right, "⏸️ Dừng", self.cancel_upload, 
                                       self.C['warning'], 'disabled')
        self.btn_clear = self.make_btn(right, "🗑️ Xóa", self.clear_list, self.C['danger'])
        
        # Status Bar
        status = self.make_frame(self.root, self.C['bg2'], 'x', 35, False)
        status.pack(fill='x', side='bottom')
        self.status_label = self.make_label(status, "📋 Sẵn sàng | 0 file", 9, 
                                           anchor='w', side='left', padx=15, expand=True)

    # --- Helper methods ---
    def make_frame(self, parent, bg, fill='both', h=None, prop=True):
        f = tk.Frame(parent, bg=bg)
        if h:
            f.configure(height=h)
            if not prop:
                f.pack_propagate(False)
        return f

    def make_label(self, parent, text, size=10, bold=False, **pack_kw):
        l = tk.Label(parent, text=text, font=("Segoe UI", size, "bold" if bold else ""),
                    bg=parent['bg'], fg=self.C['text'] if size > 10 else self.C['muted'])
        l.pack(**pack_kw)
        return l

    def make_btn(self, parent, text, cmd, color, state='normal'):
        b = tk.Button(parent, text=text, command=cmd, bg=color, fg='white',
                     font=("Segoe UI", 10, "bold"), relief='flat', padx=20, 
                     pady=10, cursor='hand2', state=state)
        b.pack(side='left', padx=5)
        return b

    # --- File handling ---
    def on_drop(self, event):
        for path in self.root.tk.splitlist(event.data):
            if os.path.isfile(path):
                self.add_single_file(path)

    def add_files(self):
        for path in filedialog.askopenfilenames(title="Chọn file"):
            self.add_single_file(path)

    def add_single_file(self, path):
        if not os.path.exists(path):
            return
        
        if not self.file_handler.validate_file(path):
            messagebox.showwarning("Lỗi", f"File không hợp lệ!")
            return
        
        fid = self.file_queue.add_file(path)
        self.thread_manager.add_file(path)
        self.file_map[fid] = path
        self.progress_manager.add_progress_bar(fid, os.path.basename(path), os.path.getsize(path))
        self.update_status()
        self.logger.log(f"Added: {os.path.basename(path)}")

    # --- Upload ---
    def setup_uploader(self):
        self.uploader = UploadClient(host="127.0.0.1", port=9999)
        self.thread_manager = ThreadManager(self.uploader, max_workers=3,
                                           gui_update_cb=self.gui_update)
        self.logger.log("Uploader ready")

    def start_upload(self):
        if not self.file_map:
            return messagebox.showwarning("Lỗi", "Chưa có file!")
        self.is_uploading = True
        self.toggle_buttons(False)
        self.status_label.config(text="🚀 Đang tải lên...")
        self.logger.log("Upload started")
        threading.Thread(target=self.thread_manager.start, daemon=True).start()

    def cancel_upload(self):
        if self.thread_manager and messagebox.askyesno("Xác nhận", "Dừng upload?"):
            self.thread_manager.stop(wait=False)
            self.toggle_buttons(True)
            self.status_label.config(text="⏸️ Đã dừng")
            self.logger.log("Cancelled")

    def clear_list(self):
        if self.is_uploading:
            return messagebox.showwarning("Lỗi", "Đang upload!")
        if self.file_map and messagebox.askyesno("Xác nhận", "Xóa danh sách?"):
            self.progress_manager.clear_all()
            self.file_map.clear()
            self.file_queue.clear()
            self.update_status()
            self.logger.log("List cleared")

    # --- GUI update callback ---
    def gui_update(self, event_type, payload):
        fid = payload.get("id")
        if event_type == "progress":
            self.progress_manager.update_progress(fid, payload["uploaded"],
                                                 payload["total"], payload.get("speed", 0))
        elif event_type == "status":
            status_map = {"waiting": "waiting", "uploading": "uploading",
                         "completed": "completed", "error": "error"}
            self.progress_manager.set_status(fid, status_map.get(
                payload.get("status", "").lower(), "uploading"))
        elif event_type == "completed":
            self.toggle_buttons(True)
            self.status_label.config(text="✅ Hoàn thành!")
            messagebox.showinfo("Thành công", "Upload xong!")
            self.logger.log("Completed")

    def toggle_buttons(self, enable):
        self.is_uploading = not enable
        self.btn_start.config(state='normal' if enable else 'disabled')
        self.btn_cancel.config(state='disabled' if enable else 'normal')
        self.btn_add.config(state='normal' if enable else 'disabled')
        self.btn_clear.config(state='normal' if enable else 'disabled')

    def update_status(self):
        self.status_label.config(text=f"📋 Sẵn sàng | {len(self.file_map)} file")

    def on_close(self):
        if self.is_uploading and not messagebox.askyesno("Cảnh báo", "Đang upload. Thoát?"):
            return
        if messagebox.askyesno("Thoát", "Thoát chương trình?"):
            self.thread_manager.stop(wait=False)
            self.logger.log("App closed")
            self.root.destroy()


def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
