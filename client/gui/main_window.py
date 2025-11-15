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
        self.upload_thread = None
        self.user_id = 0
        self.username = "Guest"
        
        # Init components
        from client.logger.logger import client_logger
        self.logger = client_logger

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
        header = self.make_frame(self.root, self.C['bg2'], 'x', 80, False)
        header.pack(fill='x')
        top_row = tk.Frame(header, bg=self.C['bg2'])
        top_row.pack(fill='x')
        self.make_label(top_row, "🚀 Multi File Uploader Pro", 20, True, pady=10)
        # Login area
        right_box = tk.Frame(top_row, bg=self.C['bg2'])
        right_box.pack(side='right', padx=10)
        self.lbl_user = tk.Label(right_box, text=f"👤 {self.username}", font=("Segoe UI", 9),
                      bg=self.C['bg2'], fg=self.C['muted'])
        self.lbl_user.pack(side='left', padx=(0,6))
        self.btn_logout = tk.Button(right_box, text="🚪 Đăng xuất", command=self.logout_user,
                        bg=self.C['danger'], fg='white', font=("Segoe UI", 9, 'bold'), relief='flat')
        self.btn_logout.pack(side='right')
        self.btn_register = tk.Button(right_box, text="🆕 Đăng ký", command=self.register_dialog,
                          bg=self.C['warning'], fg='white', font=("Segoe UI", 9, 'bold'), relief='flat')
        self.btn_register.pack(side='right', padx=(6,0))
        self.btn_login = tk.Button(right_box, text="🔐 Đăng nhập", command=self.login_dialog,
                        bg=self.C['accent'], fg='white', font=("Segoe UI", 9, 'bold'), relief='flat')
        self.btn_login.pack(side='right', padx=(0,6))

        self.make_label(header, "Kéo & thả file hoặc click • Upload đồng thời", 9)

        # Drop Zone
        drop_f = self.make_frame(self.root, self.C['bg'])
        drop_f.pack(fill='x', padx=20, pady=15)
        self.drop_zone = tk.Frame(drop_f, bg=self.C['bg2'], relief='solid', bd=2,
                                  highlightthickness=2, highlightbackground=self.C['accent'])
        self.drop_zone.pack(fill='x', ipady=30)
        self.make_label(self.drop_zone, "📁 Kéo & thả file vào đây", 14, True, pady=5)
        self.make_label(self.drop_zone, "hoặc click để chọn file", 10)
        self.drop_zone.bind("<Button-1>", lambda e: self.add_files())

        if HAS_DND:
            try:
                self.drop_zone.drop_target_register(DND_FILES)
                self.drop_zone.dnd_bind('<<Drop>>', self.on_drop)
                self.logger.log("✅ Drag & Drop enabled")
            except Exception as e:
                self.logger.log(f"⚠️ Drag & Drop init failed: {e}")
        else:
            self.logger.log("⚠️ tkinterdnd2 not available — drag & drop disabled.")


        # === Progress Section ===
        prog_f = self.make_frame(self.root, self.C['bg'])
        prog_f.pack(fill='both', expand=True, padx=20, pady=(5, 5))
        self.make_label(prog_f, "📋 Danh sách file", 12, True, anchor='w').pack(fill='x', pady=(0, 10))
        self.progress_manager = ProgressBarManager(prog_f)

        # === Controls Section (đặt ở cuối cửa sổ) ===
        ctrl_wrapper = tk.Frame(self.root, bg=self.C['bg2'], height=80)
        ctrl_wrapper.pack(fill='x', side='bottom', padx=20, pady=(0, 5))
        ctrl_wrapper.pack_propagate(False)

        left = tk.Frame(ctrl_wrapper, bg=self.C['bg2'])
        left.pack(side='left', padx=10, pady=10)
        self.btn_add = self.make_btn(left, "➕ Thêm", self.add_files, self.C['accent'])
        self.btn_start = self.make_btn(left, "🚀 Upload", self.start_upload, self.C['success'])

        right = tk.Frame(ctrl_wrapper, bg=self.C['bg2'])
        right.pack(side='right', padx=10, pady=10)
        self.btn_cancel = self.make_btn(right, "⏸️ Dừng", self.cancel_upload, self.C['warning'], 'disabled')
        self.btn_clear = self.make_btn(right, "🗑️ Xóa", self.clear_list, self.C['danger'])

        # === Status Bar (luôn ở cuối cùng) ===
        status = tk.Frame(self.root, bg=self.C['bg2'], height=30)
        status.pack(fill='x', side='bottom')
        status.pack_propagate(False)
        self.status_label = tk.Label(status, text="📋 Sẵn sàng | 0 file", font=("Segoe UI", 9),
                                     bg=self.C['bg2'], fg=self.C['muted'], anchor='w', padx=15)
        self.status_label.pack(fill='both', expand=True)


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
        self.logger.log(f"📂 Drop event: {event.data}")
        paths = self.root.tk.splitlist(event.data)
        for path in paths:
            if os.path.isfile(path):
                self.logger.log(f"✅ Added from drop: {path}")
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
        
        # Add to FileQueue first; it returns a stable file id we can reuse
        fqid = self.file_queue.add_file(path)
        if not fqid:
            # already queued
            return

        # Register same id with ThreadManager so progress callbacks use the same id
        fid = self.thread_manager.add_file(path, file_id=fqid)
        self.file_map[fid] = path
        self.progress_manager.add_progress_bar(fid, os.path.basename(path), os.path.getsize(path))
        self.update_status()
        self.logger.log(f"Added: {os.path.basename(path)}")

    # --- Upload ---
    def setup_uploader(self):
        self.uploader = UploadClient(host="127.0.0.1", port=9999, user_id=self.user_id)
        self.thread_manager = ThreadManager(self.uploader, max_workers=3,
                                           gui_update_cb=self.gui_update)
        self.logger.log("Uploader ready")

    def start_upload(self):
        if not self.file_map:
            return messagebox.showwarning("Lỗi", "Chưa có file!")

        # Nếu đang upload thì không làm gì cả (tránh bấm nhiều lần)
        if self.is_uploading:
            return

        self.is_uploading = True
        self.toggle_buttons(False)  # Tắt nút Upload, bật nút Dừng
        self.status_label.config(text="🚀 Đang tải lên...")
        self.logger.log("Upload started")

        try:
            # Bắt đầu upload (gọi thread manager của bạn)
            self.thread_manager.start_workers()
        except AttributeError:
            # Trường hợp cũ hơn dùng start()
            self.thread_manager.start()

    def cancel_upload(self):
        """Hàm dừng upload"""   
        if not self.is_uploading:
            return

        self.is_uploading = False
        self.toggle_buttons(True)  # Bật lại nút Upload
        self.status_label.config(text="⏸️ Đã dừng upload.")
        self.logger.log("Upload cancelled")

        try:
            # Nếu thread_manager hỗ trợ dừng
            self.thread_manager.stop_workers()
        except AttributeError:
            pass
    
    def finish_upload(self):
        """Khi upload hoàn tất hoặc bị dừng"""
        self.is_uploading = False
        self.btn_cancel.config(state='disabled')
        self.btn_start.config(state='normal')
        print("✅ Upload hoàn tất hoặc bị dừng.")

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
        # Marshal all GUI updates to the Tk main thread to avoid thread-safety issues
        try:
            self.root.after(0, lambda: self._process_gui_update(event_type, payload))
        except Exception:
            # If root is gone or scheduling fails, fallback to direct call
            self._process_gui_update(event_type, payload)

    def _process_gui_update(self, event_type, payload):
        fid = payload.get("id")
        if event_type == "progress":
            # payload: {'id', 'uploaded', 'total', 'speed', 'status'}
            uploaded = payload.get("uploaded", 0)
            total = payload.get("total", 0) or 1
            speed = payload.get("speed", 0)
            self.progress_manager.update_progress(fid, uploaded, total, speed)
        elif event_type == "status":
            # Normalize a variety of status strings that may come from UploadClient
            raw = payload.get("status", "").lower()
            if raw in ("waiting", "queued"):
                mapped = "waiting"
            elif raw in ("uploading", "in_progress"):
                mapped = "uploading"
            elif raw in ("completed", "success", "done"):
                mapped = "completed"
            elif raw in ("cancelled", "canceled"):
                mapped = "error"
            else:
                mapped = "uploading"

            # Update progress bar status
            self.progress_manager.set_status(fid, mapped)

            # If upload completed, finalize UI state for this file
            if mapped == "completed":
                # Ensure progress shows 100%
                pb = self.progress_manager.get_progress_bar(fid)
                if pb:
                    try:
                        pb.update_progress(pb.file_size, pb.file_size, pb.speed)
                    except Exception:
                        pass

                # If no other uploads running, toggle buttons and show message
                self.toggle_buttons(True)
                self.status_label.config(text="✅ Hoàn thành!")
                # Don't spam modal dialogs for every file; log instead
                self.logger.log(f"Completed: {fid}")
        elif event_type == "completed":
            self.toggle_buttons(True)
            self.status_label.config(text="✅ Hoàn thành!")
            # Keep this non-blocking; log completion
            self.logger.log("Completed")

    # --- Auth ---
    def login_dialog(self):
        """Đăng nhập qua MySQL (tùy chọn). Yêu cầu ENABLE_DB=true và cấu hình DB hợp lệ."""
        try:
            import tkinter.simpledialog as sd
            from services.user_service import authenticate_user
        except Exception as e:
            messagebox.showerror("DB", f"Không thể tải module DB/Services: {e}")
            return

        username = sd.askstring("Đăng nhập", "Tên đăng nhập:")
        if not username:
            return
        password = sd.askstring("Đăng nhập", "Mật khẩu:", show='*')
        if password is None:
            return

        try:
            uid = authenticate_user(username, password)
        except Exception as e:
            messagebox.showerror("DB", f"Lỗi kết nối DB: {e}")
            return

        if uid:
            self.user_id = int(uid)
            self.username = username
            self.lbl_user.config(text=f"👤 {self.username}")
            # propagate into uploader
            try:
                self.uploader.user_id = self.user_id
            except Exception:
                pass
            messagebox.showinfo("Đăng nhập", "Đăng nhập thành công!")
        else:
            messagebox.showwarning("Đăng nhập", "Sai thông tin đăng nhập!")

    def register_dialog(self):
        """Đăng ký tài khoản mới trong MySQL (tùy chọn)."""
        try:
            import tkinter.simpledialog as sd
            from services.user_service import register_user, authenticate_user
        except Exception as e:
            messagebox.showerror("DB", f"Không thể tải module DB/Services: {e}")
            return

        username = sd.askstring("Đăng ký", "Chọn tên đăng nhập:")
        if not username:
            return
        password = sd.askstring("Đăng ký", "Mật khẩu:", show='*')
        if password is None or password == "":
            return
        confirm = sd.askstring("Đăng ký", "Nhập lại mật khẩu:", show='*')
        if confirm is None or confirm != password:
            messagebox.showwarning("Đăng ký", "Mật khẩu không khớp!")
            return

        try:
            uid = register_user(username, password)
            if uid:
                messagebox.showinfo("Đăng ký", "Tạo tài khoản thành công! Sẽ đăng nhập ngay.")
                # Auto-login
                auth_uid = authenticate_user(username, password)
                if auth_uid:
                    self.user_id = int(auth_uid)
                    self.username = username
                    self.lbl_user.config(text=f"👤 {self.username}")
                    try:
                        self.uploader.user_id = self.user_id
                    except Exception:
                        pass
            else:
                messagebox.showwarning("Đăng ký", "Không thể tạo tài khoản. Tên có thể đã tồn tại.")
        except Exception as e:
            messagebox.showerror("Đăng ký", f"Lỗi DB: {e}")

    def logout_user(self):
        """Đăng xuất người dùng hiện tại, quay về chế độ Guest."""
        self.user_id = 0
        self.username = "Guest"
        self.lbl_user.config(text=f"👤 {self.username}")
        try:
            self.uploader.user_id = 0
        except Exception:
            pass
        messagebox.showinfo("Đăng xuất", "Bạn đã đăng xuất.")

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
    from tkinterdnd2 import TkinterDnD  # đảm bảo có dòng này
    root = TkinterDnD.Tk()              # KHÔNG dùng tk.Tk()
    MainWindow(root)
    root.mainloop()



if __name__ == "__main__":
    main()
