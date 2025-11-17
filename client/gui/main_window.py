"""
Main Window GUI - Multi File Uploader
Member 1 - GUI Component
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys
import threading
import json

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
from client.logger.logger import Logger, client_logger

# TkinterDnD2
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# File lưu file upload theo user
UPLOADS_DB = os.path.join(project_dir, "uploads_per_user.json")


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
        self.user_id = 1  # Guest user_id
        self.username = "Guest"

        # Init components
        self.logger = client_logger
        self.file_handler = FileHandlerGUI(self.root)
        self.file_queue = FileQueue()

        self.logger.log("App started")

        # Build UI
        self.build_ui()
        self.setup_uploader()
        # Cập nhật hiển thị nút auth ban đầu (Guest)
        self.update_auth_buttons()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----------------------------
    # UI build
    # ----------------------------
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
        self.lbl_user.pack(side='left', padx=(0, 6))
        self.btn_logout = tk.Button(right_box, text="🚪 Đăng xuất", command=self.logout_user,
                                    bg=self.C['danger'], fg='white', font=("Segoe UI", 9, 'bold'), relief='flat')
        self.btn_logout.pack(side='right')
        self.btn_register = tk.Button(right_box, text="🆕 Đăng ký", command=self.register_dialog,
                                      bg=self.C['warning'], fg='white', font=("Segoe UI", 9, 'bold'), relief='flat')
        self.btn_register.pack(side='right', padx=(6, 0))
        self.btn_login = tk.Button(right_box, text="🔐 Đăng nhập", command=self.login_dialog,
                                   bg=self.C['accent'], fg='white', font=("Segoe UI", 9, 'bold'), relief='flat')
        self.btn_login.pack(side='right', padx=(0, 6))

        # --- Mới: Nút xem file đã upload ---
        self.btn_view_uploaded = tk.Button(
            right_box,
            text="📂 File đã upload",
            command=self.show_uploaded_files,
            bg='#3b82f6', fg='white',
            font=("Segoe UI", 9, 'bold'),
            relief='flat'
        )
        self.btn_view_uploaded.pack(side='right', padx=(6, 0))

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

        # === Controls Section ===
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

        # === Status Bar ===
        status = tk.Frame(self.root, bg=self.C['bg2'], height=30)
        status.pack(fill='x', side='bottom')
        status.pack_propagate(False)
        self.status_label = tk.Label(status, text="📋 Sẵn sàng | 0 file", font=("Segoe UI", 9),
                                     bg=self.C['bg2'], fg=self.C['muted'], anchor='w', padx=15)
        self.status_label.pack(fill='both', expand=True)

    # ----------------------------
    # Helper methods
    # ----------------------------
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

    # ----------------------------
    # File handling
    # ----------------------------
    def on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        for path in paths:
            if os.path.isfile(path):
                self.add_single_file(path)

    def add_files(self):
        for path in filedialog.askopenfilenames(title="Chọn file"):
            self.add_single_file(path)

    def add_single_file(self, path):
        """Thêm 1 file vào danh sách upload và progress bar"""
        if not os.path.exists(path):
            self.logger.log(f"❌ File không tồn tại: {path}")
            return

        # Thêm vào queue
        fqid = self.file_queue.add_file(path)
        if not fqid:
            fqid = path  # fallback

        # Thêm vào thread_manager
        try:
            fid = self.thread_manager.add_file(path, file_id=fqid)
        except Exception:
            fid = fqid

        # Thêm vào file_map và progress
        self.file_map[fid] = path
        self.progress_manager.add_progress_bar(fid, os.path.basename(path), os.path.getsize(path))
        self.update_status()
        self.logger.log(f"✅ Added: {os.path.basename(path)}")

    # ----------------------------
    # Upload
    # ----------------------------
    def setup_uploader(self):
        self.uploader = UploadClient(host="127.0.0.1", port=9999, user_id=self.user_id)
        self.thread_manager = ThreadManager(self.uploader, max_workers=3,
                                           gui_update_cb=self.gui_update)

    def start_upload(self):
        if not self.file_map:
            messagebox.showwarning("Lỗi", "Chưa có file nào để upload!")
            return

        if self.is_uploading:
            return

        self.is_uploading = True
        self.toggle_buttons(False)
        self.status_label.config(text="🚀 Đang tải lên...")
        self.logger.log("Upload started")

        try:
            self.thread_manager.start_workers()
        except Exception as e:
            self.logger.log(f"⚠️ ThreadManager start lỗi: {e}")
            self.is_uploading = False
            self.toggle_buttons(True)
            messagebox.showerror("Lỗi", f"Upload không thể bắt đầu: {e}")

    def cancel_upload(self):
        if not self.is_uploading:
            return
        self.is_uploading = False
        self.toggle_buttons(True)
        self.status_label.config(text="⏸️ Đã dừng upload.")
        try:
            self.thread_manager.stop_workers()
        except Exception:
            pass

    def clear_list(self):
        if self.is_uploading:
            return messagebox.showwarning("Lỗi", "Đang upload!")
        if self.file_map and messagebox.askyesno("Xác nhận", "Xóa danh sách?"):
            self.progress_manager.clear_all()
            self.file_map.clear()
            self.file_queue.clear()
            self.update_status()
            self.logger.log("List cleared")

    # ----------------------------
    # GUI update callback
    # ----------------------------
    def gui_update(self, event_type, payload):
        try:
            self.root.after(0, lambda: self._process_gui_update(event_type, payload))
        except Exception:
            self._process_gui_update(event_type, payload)

    def _process_gui_update(self, event_type, payload):
        fid = payload.get("id")
        if event_type == "progress":
            uploaded = payload.get("uploaded", 0)
            total = payload.get("total", 1)
            speed = payload.get("speed", 0)
            self.progress_manager.update_progress(fid, uploaded, total, speed)
        elif event_type == "status":
            raw = payload.get("status", "").lower()
            msg = payload.get("message", "")
            if raw in ("waiting", "queued"):
                mapped = "waiting"
            elif raw in ("uploading", "in_progress"):
                mapped = "uploading"
            elif raw in ("completed", "success", "done"):
                mapped = "completed"
            else:
                mapped = "error"
            self.progress_manager.set_status(fid, mapped)
            if mapped == "completed":
                self.toggle_buttons(True)
                self.status_label.config(text="✅ Hoàn thành!")
                self.update_status()  # Cập nhật trạng thái nút Upload
                # File đã được lưu vào DB bởi server, không cần lưu JSON
            elif mapped == "error":
                self.toggle_buttons(True)
                self.status_label.config(text=f"❌ Lỗi upload: {msg}")
                self.update_status()  # Cập nhật trạng thái nút Upload
            elif mapped == "uploading":
                self.status_label.config(text="🚀 Đang tải lên...")

    # ----------------------------
    # Auth
    # ----------------------------
    def login_dialog(self):
        import tkinter.simpledialog as sd
        from services.user_service import authenticate_user
        username = sd.askstring("Đăng nhập", "Tên đăng nhập:")
        if not username:
            return
        password = sd.askstring("Đăng nhập", "Mật khẩu:", show='*')
        if password is None:
            return
        uid = authenticate_user(username, password)
        if uid:
            # Luôn xóa queue hiện tại khi chuyển user (kể cả từ user sang user khác)
            self.progress_manager.clear_all()
            self.file_map.clear()
            self.file_queue.clear()
            
            self.user_id = int(uid)
            self.username = username
            self.lbl_user.config(text=f"👤 {self.username}")
            try:
                self.uploader.user_id = self.user_id
            except Exception:
                pass
            
            # Cập nhật hiển thị nút auth
            self.update_auth_buttons()
            
            # Không load file từ JSON nữa - user xem file đã upload qua nút "File đã upload"
            self.update_status()
            messagebox.showinfo("Đăng nhập", "Đăng nhập thành công!")
        else:
            messagebox.showwarning("Đăng nhập", "Sai thông tin đăng nhập!")

    def register_dialog(self):
        import tkinter.simpledialog as sd
        from services.user_service import register_user, authenticate_user
        username = sd.askstring("Đăng ký", "Chọn tên đăng nhập:")
        if not username:
            return
        password = sd.askstring("Đăng ký", "Mật khẩu:", show='*')
        if password is None or password == "":
            return
        confirm = sd.askstring("Đăng ký", "Nhập lại mật khẩu:", show='*')
        if confirm != password:
            messagebox.showwarning("Đăng ký", "Mật khẩu không khớp!")
            return
        uid = register_user(username, password)
        if uid:
            auth_uid = authenticate_user(username, password)
            if auth_uid:
                # Luôn xóa queue hiện tại khi chuyển user (kể cả từ user sang user khác)
                self.progress_manager.clear_all()
                self.file_map.clear()
                self.file_queue.clear()
                
                self.user_id = int(auth_uid)
                self.username = username
                self.lbl_user.config(text=f"👤 {self.username}")
                try:
                    self.uploader.user_id = self.user_id
                except Exception:
                    pass
                
                # Cập nhật hiển thị nút auth
                self.update_auth_buttons()
                self.update_status()
                messagebox.showinfo("Đăng ký", "Tạo tài khoản và đăng nhập thành công!")
        else:
            messagebox.showwarning("Đăng ký", "Không thể tạo tài khoản. Tên có thể đã tồn tại.")

    def logout_user(self):
        if messagebox.askokcancel("Xác nhận đăng xuất", "Bạn có chắc muốn đăng xuất và xóa danh sách file?"):
            # Không cần save vào JSON nữa, DB là nguồn chân lý duy nhất
            self.progress_manager.clear_all()
            self.file_map.clear()
            self.update_status()
            self.user_id = 1
            self.username = "Guest"
            self.lbl_user.config(text=f"👤 {self.username}")
            try:
                self.uploader.user_id = 1
            except Exception:
                pass
            
            # Cập nhật hiển thị nút auth về trạng thái Guest
            self.update_auth_buttons()
            messagebox.showinfo("Đăng xuất", "Bạn đã đăng xuất.")

    # ----------------------------
    # Mới: Hiển thị file đã upload
    # ----------------------------
    def show_uploaded_files(self):
        """Hiển thị danh sách file đã upload từ database"""
        try:
            from services.user_service import list_user_files
            from database.config import CONFIG
            
            # Kiểm tra DB có được bật không
            if not CONFIG.enabled:
                messagebox.showwarning("Lỗi", "Database chưa được bật. Không thể lấy danh sách file!")
                return
            
            # Lấy danh sách file từ database theo user_id
            files = list_user_files(self.user_id)
            
            if not files:
                messagebox.showinfo("File đã upload", "Chưa có file nào được upload!")
                return
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lấy danh sách file: {e}")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title(f"📂 File của {self.username}")
        popup.geometry("500x350")
        popup.configure(bg=self.C['bg2'])
        tk.Label(popup, text=f"📂 Danh sách file đã upload ({len(files)} file)",
                 font=("Segoe UI", 11, 'bold'), bg=self.C['bg2'], fg=self.C['text']).pack(pady=10)
        listbox = tk.Listbox(popup, bg=self.C['bg'], fg=self.C['text'], selectbackground=self.C['accent'])
        listbox.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Lưu map từ index -> file info để có thể mở file
        file_map = {}
        
        # Lấy đường dẫn thư mục uploads (cùng cấp với thư mục client)
        uploads_dir = os.path.join(project_dir, "uploads")
        
        for idx, file_info in enumerate(files):
            # file_info chứa: file_id, original_filename, file_size_bytes, upload_date, status
            filename = file_info.get('original_filename', 'Unknown')
            file_size = file_info.get('file_size_bytes', 0)
            status = file_info.get('status', 'unknown')
            
            # Hiển thị: tên file + kích thước + trạng thái
            size_mb = file_size / (1024 * 1024)
            display_text = f"{filename} ({size_mb:.2f} MB) - {status}"
            listbox.insert('end', display_text)
            
            # Lưu thông tin file để mở sau
            file_path = os.path.join(uploads_dir, filename)
            file_map[idx] = {
                'filename': filename,
                'path': file_path,
                'status': status
            }

        # Mở file khi double-click
        def open_file(event):
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                file_info = file_map.get(idx)
                if file_info:
                    file_path = file_info['path']
                    filename = file_info['filename']
                    
                    if os.path.exists(file_path):
                        try:
                            os.startfile(file_path)
                        except Exception as e:
                            messagebox.showerror("Lỗi", f"Không thể mở file: {e}")
                    else:
                        messagebox.showwarning("Lỗi", f"File không tồn tại trong thư mục uploads: {filename}")

        listbox.bind("<Double-1>", open_file)

        tk.Button(popup, text="Đóng", command=popup.destroy, bg=self.C['accent'],
                  fg='white', font=("Segoe UI", 10, 'bold')).pack(pady=5)

    # ----------------------------
    # Auth button visibility
    # ----------------------------
    def update_auth_buttons(self):
        """Cập nhật hiển thị các nút đăng nhập/đăng ký/đăng xuất dựa trên trạng thái user"""
        is_guest = (self.user_id == 1 and self.username == "Guest")
        
        if is_guest:
            # Guest: hiện đăng nhập và đăng ký, ẩn đăng xuất
            self.btn_login.pack(side='right', padx=(0, 6))
            self.btn_register.pack(side='right', padx=(6, 0))
            self.btn_logout.pack_forget()
        else:
            # Đã đăng nhập: chỉ hiện đăng xuất, ẩn đăng nhập và đăng ký
            self.btn_login.pack_forget()
            self.btn_register.pack_forget()
            self.btn_logout.pack(side='right')

    # ----------------------------
    # Button control
    # ----------------------------
    def toggle_buttons(self, enable):
        self.is_uploading = not enable
        self.btn_start.config(state='normal' if enable else 'disabled')
        self.btn_cancel.config(state='disabled' if enable else 'normal')
        self.btn_add.config(state='normal' if enable else 'disabled')
        self.btn_clear.config(state='normal' if enable else 'disabled')

    # ----------------------------
    # Misc
    # ----------------------------
    def update_status(self):
        file_count = len(self.file_map)
        self.status_label.config(text=f"📋 Sẵn sàng | {file_count} file")
        
        # Kiểm tra xem có file chưa upload không
        has_uploadable_files = False
        if file_count > 0:
            # Kiểm tra xem có file nào chưa hoàn thành không
            for fid in self.file_map:
                status = self.progress_manager.get_status(fid)
                # Nếu file đang waiting hoặc chưa bắt đầu thì có thể upload
                if status in (None, 'waiting'):
                    has_uploadable_files = True
                    break
        
        # Enable/disable nút Upload dựa trên trạng thái
        if not self.is_uploading:
            if has_uploadable_files:
                self.btn_start.config(state='normal')
            else:
                self.btn_start.config(state='disabled')

    def on_close(self):
        if self.is_uploading and not messagebox.askyesno("Xác nhận", "Đang upload, thoát sẽ hủy!"):
            return
        # Không cần lưu JSON nữa - DB là nguồn chân lý
        self.root.destroy()


# ----------------------------
# Main
# ----------------------------
def main():
    from tkinterdnd2 import TkinterDnD  # đảm bảo có dòng này
    root = TkinterDnD.Tk()              # KHÔNG dùng tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

