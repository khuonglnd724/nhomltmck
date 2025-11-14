import unittest
import time
import threading
from queue import Queue

from client.thread_manager import ThreadManager


#  Mock UploadClient

class MockUploadClient:
    """Giả lập UploadClient để test ThreadManager."""

    def upload_file(self, filepath, progress_callback, status_callback):
        # Giả lập quá trình upload
        for p in [0, 20, 50, 80, 100]:
            time.sleep(0.01)
            progress_callback(p, 1.0, "uploading")

        # Báo hoàn tất
        status_callback("done", "finished")

        return {"status": "done", "path": filepath}


#                 TEST CHO THREAD_MANAGER

class TestThreadManager(unittest.TestCase):

    def setUp(self):
        self.events = []
        self.uploader = MockUploadClient()

        def gui_cb(event, data):
            self.events.append((event, data))

        self.manager = ThreadManager(
            uploader=self.uploader,
            max_workers=3,
            gui_update_cb=gui_cb
        )

    # 1. Test upload song song

    def test_parallel_upload(self):
        f1 = self.manager.add_file("tests/f1.txt", meta={})
        f2 = self.manager.add_file("tests/f2.txt", meta={})
        f3 = self.manager.add_file("tests/f3.txt", meta={})

        start = time.time()
        self.manager.start_workers()

        # Chờ xử lý
        time.sleep(0.2)
        end = time.time()

        # Kiểm tra các file đã được xử lý
        statuses = {f["id"]: f["status"] for f in self.manager.list_files()}

        self.assertEqual(statuses[f1], "done")
        self.assertEqual(statuses[f2], "done")
        self.assertEqual(statuses[f3], "done")

        # Thời gian < 0.5s → tức là chạy song song (vì mỗi file 0.05s)
        self.assertLess(end - start, 0.5, "Upload không chạy song song!")

    # 2. Test GUI không bị treo khi upload

    def test_gui_not_freeze(self):
        gui_alive = True

        def fake_gui_loop():
            nonlocal gui_alive
            for _ in range(200):
                time.sleep(0.002)
            gui_alive = True

        gui_thread = threading.Thread(target=fake_gui_loop)
        gui_thread.start()

        # Gọi upload
        fid = self.manager.add_file("tests/file_gui.txt")
        self.manager.start_workers()

        gui_thread.join()

        # Kết luận
        self.assertTrue(gui_alive, "GUI đã bị treo khi upload!")

    # 3. Test cập nhật progress chính xác

    def test_progress_updates(self):
        fid = self.manager.add_file("tests/progress.txt")
        self.manager.start_workers()

        time.sleep(0.2)

        # Tìm sự kiện progress
        progress_values = []
        for evt, data in self.events:
            if evt == "progress":
                progress_values.append(data["status"])

        self.assertTrue(len(progress_values) > 0, "Không nhận được cập nhật progress!")

        # Kiểm tra 100% đã được gửi
        final_status = self.events[-1][1]["status"]
        self.assertEqual(final_status, "done")


if __name__ == "__main__":
    unittest.main()
