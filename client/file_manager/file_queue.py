# client/file_manager/file_queue.py
# Member 2 - File Queue (chuẩn theo MainWindow)

import queue
import time
import uuid
import uuid

class FileQueue:
    """Hàng đợi quản lý các file chờ upload"""

    def __init__(self):
        self._queue = queue.Queue()
        self._files = {}  # Lưu trữ file theo id -> thông tin

    def add_file(self, file_path: str):
        """Add a file to the queue.

        Returns a generated `file_id` string if added, or `False` if the path
        already exists in the queue.
        """
        # Kiểm tra trùng file theo đường dẫn
        existing_paths = [f.get('path') for f in self._files.values()]
        if file_path in existing_paths:
            return False  # Đã tồn tại

        file_id = f"fq_{int(time.time()*1000)}_{len(existing_paths)}"
        file_info = {
            'id': file_id,
            'path': file_path,
            'status': 'pending'
        }

        self._files[file_id] = file_info
        self._queue.put(file_info)
        return file_id

    def get_next(self):
        """Lấy file tiếp theo trong hàng đợi"""
        if not self._queue.empty():
            return self._queue.get()
        return None

    def mark_completed(self, fid: str):
        """Đánh dấu file đã hoàn thành"""
        if fid in self._files:
            self._files[fid]['status'] = 'completed'

    def list_all(self):
        """Trả về danh sách toàn bộ file"""
        return list(self._files.values())

    def clear(self):
        """Xóa toàn bộ hàng đợi"""
        while not self._queue.empty():
            self._queue.get()
        self._files.clear()
