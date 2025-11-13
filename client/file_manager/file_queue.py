# client/file_manager/file_queue.py
# Member 2 - File Queue (chuẩn theo MainWindow)

import queue
import uuid

class FileQueue:
    """Hàng đợi quản lý các file chờ upload"""

    def __init__(self):
        self._queue = queue.Queue()
        self._files = {}  # Lưu trữ file theo id -> thông tin

    def add_file(self, file_path: str):
        """Thêm file mới vào hàng đợi, trả về id duy nhất nếu thành công"""
        # Kiểm tra trùng file theo đường dẫn
        for f in self._files.values():
            if f['path'] == file_path:
                return None  # Đã tồn tại

        fid = str(uuid.uuid4())
        file_info = {
            'id': fid,
            'path': file_path,
            'status': 'pending'
        }

        self._files[fid] = file_info
        self._queue.put(file_info)
        return fid

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
