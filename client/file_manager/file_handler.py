# client/file_manager/file_handler.py
# Member 2 - File Handler (chuẩn theo MainWindow)

import os
from tkinter import messagebox

class FileHandlerGUI:
    """Xử lý và kiểm tra file trước khi thêm vào danh sách upload"""

    def __init__(self, master=None):
        # Không tạo GUI riêng — chỉ phục vụ validate logic
        self.master = master
        self.max_size_mb = 100  # Giới hạn kích thước 100MB mỗi file

    def validate_file(self, file_path: str) -> bool:
        """Kiểm tra tính hợp lệ của file trước khi thêm"""
        if not os.path.exists(file_path):
            messagebox.showerror("Lỗi", f"File không tồn tại:\n{file_path}")
            return False

        if not os.path.isfile(file_path):
            messagebox.showwarning("Cảnh báo", f"'{os.path.basename(file_path)}' không phải là file hợp lệ!")
            return False

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > self.max_size_mb:
            messagebox.showwarning("Cảnh báo", f"File '{os.path.basename(file_path)}' vượt quá {self.max_size_mb} MB!")
            return False

        # Kiểm tra định dạng hợp lệ (tuỳ chọn)
        allowed_ext = {'.jpg', '.png', '.pdf', '.txt', '.zip', '.rar', '.docx', '.mp4'}
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in allowed_ext:
            messagebox.showwarning("Cảnh báo", f"Định dạng file '{ext}' không được hỗ trợ!")
            return False

        return True
