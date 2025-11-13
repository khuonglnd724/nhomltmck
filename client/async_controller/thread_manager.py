import threading
import os
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

    def add_file(self, path, meta=None, file_id=None):
        """Thêm file vào hàng đợi. Nếu `file_id` được cung cấp thì dùng id đó,
        để đồng bộ với `FileQueue` và GUI."""
        file_id = file_id or str(uuid.uuid4())
        # If file already known, return existing id
        if file_id in self._file_map:
            return file_id
        file_info = {
            'id': file_id,
            'path': path,
            'meta': meta or {},
            'status': 'queued',
            'uploaded': 0,
            'progress': 0,
            'speed': 0.0,
            'size': os.path.getsize(path) if os.path.exists(path) else 0
        }
        self._file_map[file_id] = file_info
        self.queue.put(file_info)
        if self.gui_update_cb:
            self.gui_update_cb('added', file_info.copy())
        return file_id

    def _progress_callback(self, file_id, progress, speed, status):
        """Callback nhận từ UploadClient"""
        fi = self._file_map.get(file_id)
        if not fi:
            return
        # progress: percentage (0-100) from UploadClient
        fi['progress'] = progress
        fi['speed'] = speed
        fi['status'] = status

        # Convert to GUI-friendly shape: uploaded bytes, total bytes, speed in bytes/s
        total = fi.get('size', 0) or 0
        uploaded = int((progress / 100.0) * total) if total else 0
        # UploadClient reports speed in MB/s; convert to bytes/s
        try:
            speed_bytes = float(speed) * 1024 * 1024
        except Exception:
            speed_bytes = 0.0

        fi['uploaded'] = uploaded

        if self.gui_update_cb:
            self.gui_update_cb('progress', {
                'id': file_id,
                'uploaded': uploaded,
                'total': total,
                'speed': speed_bytes,
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

    def _session_worker(self, work_queue: Queue):
        """Worker for a single upload session.

        Processes items from `work_queue` only. When the work_queue is empty,
        the worker exits. This ensures files added after session start are
        not uploaded until the next session begins.
        """
        while not self._stop_event.is_set():
            try:
                file_info = work_queue.get(timeout=1)
            except Empty:
                # If no more items, exit the session worker
                break

            fid = file_info['id']
            path = file_info['path']
            file_info['status'] = 'uploading'
            if self.gui_update_cb:
                self.gui_update_cb('status', {'id': fid, 'status': 'uploading'})

            try:
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
                work_queue.task_done()

    def start_workers(self):
        """Khởi tạo các luồng upload"""
        # Start a new upload session: move all currently queued items into a
        # session-specific work queue and spawn threads to process that queue.
        # Files added after this call remain in `self.queue` for the next session.
        work_q = Queue()

        # Drain current queue into work_q (non-blocking)
        while True:
            try:
                item = self.queue.get_nowait()
            except Empty:
                break
            work_q.put(item)

        if work_q.empty():
            return  # nothing to do

        # spawn session-specific workers
        for i in range(self.max_workers):
            t = threading.Thread(target=self._session_worker, args=(work_q,), daemon=True, name=f"uploader-session-worker-{i}")
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
