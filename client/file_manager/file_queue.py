# file_queue.py - Member 2
import queue

class FileQueue:
    """Hàng đợi quản lý các file chờ upload"""
    def __init__(self):
        self._queue = queue.Queue()

    def add_file(self, file_path):
        if file_path not in [f['path'] for f in list(self._queue.queue)]:
            self._queue.put({'path': file_path, 'status': 'pending'})
            return True
        return False

    def get_next(self):
        if not self._queue.empty():
            return self._queue.get()
        return None

    def list_all(self):
        return list(self._queue.queue)

    def clear(self):
        while not self._queue.empty():
            self._queue.get()
