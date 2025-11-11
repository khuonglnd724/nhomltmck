import threading
from queue import Queue, Empty
import time
import uuid

class ThreadManager:
    """
    ThreadManager quản lý việc upload song song qua UploadClient.
    - uploader: đối tượng UploadClient
    - max_workers: số luồng upload đồng thời
    - gui_update_cb: callback cập nhật GUI ('progress', 'status', 'added', 'removed')
    """

    def __init__(self, uploader, max_workers=3, gui_update_cb=None):
        self.uploader = uploader
        self.max_workers = max_workers
        self.gui_update_cb = gui_update_cb
        self.queue = Queue()
        self.threads = []
        self._stop_event = threading.Event()
        self._workers_started = False
        self._file_map = {}  # file_id -> file_info

    def add_file(self, path, meta=None):
        """Thêm file vào hàng đợi"""
        file_id = str(uuid.uuid4())
        file_info = {
            'id': file_id,
            'path': path,
            'meta': meta or {},
            'status': 'queued',
            'uploaded': 0,
            'progress': 0,
            'speed': 0.0
        }
        self._file_map[file_id] = file_info
        self.queue.put(file_info)
        if self.gui_update_cb:
            self.gui_update_cb('added', file_info.copy())
        if not self._workers_started:
            self.start_workers()
        return file_id

    def _progress_callback(self, file_id, progress, speed, status):
        """Callback nhận từ UploadClient"""
        fi = self._file_map.get(file_id)
        if not fi:
            return
        fi['progress'] = progress
        fi['speed'] = speed
        fi['status'] = status
        if self.gui_update_cb:
            self.gui_update_cb('progress', {
                'id': file_id,
                'progress': progress,
                'speed': speed,
                'status': status
            })

    def worker(self):
        """Worker chạy trong luồng upload"""
        while not self._stop_event.is_set():
            try:
                file_info = self.queue.get(timeout=1)
            except Empty:
                continue

            fid = file_info['id']
            path = file_info['path']
            file_info['status'] = 'uploading'
            if self.gui_update_cb:
                self.gui_update_cb('status', {'id': fid, 'status': 'uploading'})

            try:
                # Gọi UploadClient.upload_file
                result = self.uploader.upload_file(
                    filepath=path,
                    progress_callback=lambda p, s, st: self._progress_callback(fid, p, s, st),
                    status_callback=lambda st, msg: self.gui_update_cb('status', {'id': fid, 'status': st, 'message': msg})
                )

                file_info['status'] = result.get('status', 'done')
                if self.gui_update_cb:
                    self.gui_update_cb('status', {'id': fid, 'status': file_info['status'], 'result': result})

            except Exception as e:
                file_info['status'] = 'error'
                file_info['error_msg'] = str(e)
                if self.gui_update_cb:
                    self.gui_update_cb('status', {'id': fid, 'status': 'error', 'error_msg': str(e)})

            finally:
                self.queue.task_done()

    def start_workers(self):
        """Khởi tạo các luồng upload"""
        if self._workers_started:
            return
        self._workers_started = True
        for i in range(self.max_workers):
            t = threading.Thread(target=self.worker, daemon=True, name=f"uploader-worker-{i}")
            t.start()
            self.threads.append(t)

    def stop(self, wait=True):
        """Dừng toàn bộ luồng"""
        self._stop_event.set()
        if wait:
            for t in self.threads:
                t.join(timeout=2)

    def cancel_file(self, file_id):
        """Đánh dấu file bị hủy"""
        fi = self._file_map.get(file_id)
        if not fi:
            return False
        fi['status'] = 'canceled'
        if self.gui_update_cb:
            self.gui_update_cb('status', {'id': file_id, 'status': 'canceled'})
        return True

    def list_files(self):
        """Trả về danh sách file đang quản lý"""
        return [v.copy() for v in self._file_map.values()]
