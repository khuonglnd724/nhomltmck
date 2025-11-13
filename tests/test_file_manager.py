import unittest
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.file_manager.file_queue import FileQueue

class TestFileQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n==============================")
        print(" MEMBER 2 - FILE QUEUE TESTS ")
        print("==============================")

    def setUp(self):
        self.queue = FileQueue()
        self.test_files = [f"file_{i}.txt" for i in range(3)]
        for f in self.test_files:
            with open(f, "w", encoding="utf-8") as fp:
                fp.write(f"Content of {f}\n")
        print("\n[SETUP] Created test files and initialized queue")

    def tearDown(self):
        for f in self.test_files:
            if os.path.exists(f):
                os.remove(f)
        self.queue.clear()
        print("[TEARDOWN] Cleaned up test files and cleared queue")

    # ---------------------------
    # 1️⃣ Test thêm file vào hàng đợi
    # ---------------------------
    def test_add_file(self):
        print("\n[TEST] Running test_add_file...")
        added = self.queue.add_file(self.test_files[0])
        self.assertTrue(added, "File should be added to queue")
        all_files = self.queue.list_all()
        self.assertEqual(len(all_files), 1)
        self.assertEqual(all_files[0]['path'], self.test_files[0])
        self.assertEqual(all_files[0]['status'], 'pending')
        print("[RESULT] ✓ File added successfully to queue")

    # ---------------------------
    # 2️⃣ Test không cho thêm trùng
    # ---------------------------
    def test_prevent_duplicate_addition(self):
        print("\n[TEST] Running test_prevent_duplicate_addition...")
        added_first = self.queue.add_file(self.test_files[0])
        added_second = self.queue.add_file(self.test_files[0])
        self.assertTrue(added_first)
        self.assertFalse(added_second, "Duplicate file should not be added")
        print("[RESULT] ✓ Duplicate prevention working correctly")

    # ---------------------------
    # 3️⃣ Test lấy file kế tiếp
    # ---------------------------
    def test_get_next_file(self):
        print("\n[TEST] Running test_get_next_file...")
        self.queue.add_file(self.test_files[0])
        self.queue.add_file(self.test_files[1])
        next_file = self.queue.get_next()
        self.assertIsNotNone(next_file)
        self.assertEqual(next_file['path'], self.test_files[0])
        print(f"[RESULT] ✓ Got next file: {next_file['path']}")

    # ---------------------------
    # 4️⃣ Test lấy file khi queue rỗng
    # ---------------------------
    def test_get_next_empty_queue(self):
        print("\n[TEST] Running test_get_next_empty_queue...")
        result = self.queue.get_next()
        self.assertIsNone(result, "Should return None when queue is empty")
        print("[RESULT] ✓ Empty queue handled correctly")

    # ---------------------------
    # 5️⃣ Test list_all
    # ---------------------------
    def test_list_all_files(self):
        print("\n[TEST] Running test_list_all_files...")
        for f in self.test_files:
            self.queue.add_file(f)
        all_files = self.queue.list_all()
        self.assertEqual(len(all_files), 3)
        paths = [item['path'] for item in all_files]
        self.assertListEqual(paths, self.test_files)
        print(f"[RESULT] ✓ Listed {len(all_files)} files correctly")

    # ---------------------------
    # 6️⃣ Test clear queue
    # ---------------------------
    def test_clear_queue(self):
        print("\n[TEST] Running test_clear_queue...")
        for f in self.test_files:
            self.queue.add_file(f)
        print(f"  Before clear: {len(self.queue.list_all())} files in queue")
        self.queue.clear()
        self.assertEqual(len(self.queue.list_all()), 0)
        print("[RESULT] ✓ Queue cleared successfully")

    # ---------------------------
    # 7️⃣ Test kết hợp thêm nhiều file + lấy tuần tự
    # ---------------------------
    def test_multiple_file_order(self):
        print("\n[TEST] Running test_multiple_file_order...")
        for f in self.test_files:
            self.queue.add_file(f)
        retrieved = []
        while True:
            item = self.queue.get_next()
            if not item:
                break
            retrieved.append(item['path'])
        self.assertListEqual(retrieved, self.test_files)
        print("[RESULT] ✓ Files dequeued in correct order")

    # ---------------------------
    # 8️⃣ Test thêm file không hợp lệ (chuỗi rỗng)
    # ---------------------------
    def test_invalid_file_path(self):
        print("\n[TEST] Running test_invalid_file_path...")
        added = self.queue.add_file("")
        self.assertTrue(added, "Empty string should still be added as path if logic allows")
        all_files = self.queue.list_all()
        self.assertEqual(len(all_files), 1)
        print("[RESULT] ✓ Handled empty string path (consistent behavior)")

if __name__ == '__main__':
    print("="*60)
    print("RUNNING UNIT TESTS FOR MEMBER 2 - FileQueue")
    print("="*60)
    unittest.main(verbosity=2)
