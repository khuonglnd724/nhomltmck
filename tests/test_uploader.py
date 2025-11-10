import unittest
import os
import sys
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from client.uploader.upload_client import UploadClient
from client.file_manager.file_queue import FileQueue
from server.server import FileUploadServer

class TestUploader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server in a separate thread
        cls.server = FileUploadServer(port=9999)
        cls.server_thread = threading.Thread(target=cls.server.start)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1)  # Give server time to start
        print("\n[TEST] Server started for testing")

    def setUp(self):
        self.upload_client = UploadClient(host='127.0.0.1', port=9999)
        self.file_queue = FileQueue()
        
        # Create a test file
        self.test_file = "test_upload.txt"
        with open(self.test_file, "w", encoding='utf-8') as f:
            f.write("Test file content for Member 3\n" * 100)  # Create some content
        
        print(f"\n[TEST] Created test file: {self.test_file}")

    def tearDown(self):
        # Clean up test file
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        
        # Clean up uploaded file
        uploaded_file = os.path.join("uploads", self.test_file)
        if os.path.exists(uploaded_file):
            os.remove(uploaded_file)
        
        print(f"[TEST] Cleaned up test files")

    def test_successful_upload(self):
        """Test uploading a file successfully"""
        print("\n[TEST] Running test_successful_upload...")
        
        progress_calls = []
        status_calls = []
        
        def progress_callback(progress, speed, status):
            progress_calls.append((progress, speed, status))
            self.assertIsInstance(progress, int)
            self.assertIsInstance(speed, float)
            self.assertIsInstance(status, str)
            self.assertGreaterEqual(progress, 0)
            self.assertLessEqual(progress, 100)
            self.assertGreaterEqual(speed, 0)
        
        def status_callback(status, message):
            status_calls.append((status, message))
            self.assertIsInstance(status, str)
            self.assertIsInstance(message, str)

        response = self.upload_client.upload_file(
            self.test_file, 
            progress_callback=progress_callback,
            status_callback=status_callback
        )
        
        self.assertEqual(response["status"], "success")
        self.assertTrue(os.path.exists(os.path.join("uploads", self.test_file)))
        self.assertGreater(len(progress_calls), 0, "Progress callback should be called")
        print(f"[TEST] ✓ Upload successful with {len(progress_calls)} progress updates")

    def test_file_not_found(self):
        """Test error handling when file doesn't exist"""
        print("\n[TEST] Running test_file_not_found...")
        
        status_calls = []
        def status_callback(status, message):
            status_calls.append((status, message))
        
        response = self.upload_client.upload_file(
            "nonexistent_file.txt",
            status_callback=status_callback
        )
        
        self.assertEqual(response["status"], "error")
        self.assertIn("not found", response["message"].lower())
        print(f"[TEST] ✓ File not found error handled correctly")
    
    def test_file_queue_integration(self):
        """Test integration with FileQueue from Member 2"""
        print("\n[TEST] Running test_file_queue_integration...")
        
        # Add file to queue
        added = self.file_queue.add_file(self.test_file)
        self.assertTrue(added, "File should be added to queue")
        
        # Get file from queue
        file_item = self.file_queue.get_next()
        self.assertIsNotNone(file_item)
        self.assertEqual(file_item['path'], self.test_file)
        self.assertEqual(file_item['status'], 'pending')
        
        # Upload the file from queue
        response = self.upload_client.upload_file(file_item['path'])
        self.assertEqual(response["status"], "success")
        
        print(f"[TEST] ✓ FileQueue integration working correctly")
    
    def test_multiple_files_from_queue(self):
        """Test uploading multiple files from FileQueue"""
        print("\n[TEST] Running test_multiple_files_from_queue...")
        
        # Create multiple test files
        test_files = []
        for i in range(3):
            filename = f"test_file_{i}.txt"
            with open(filename, "w", encoding='utf-8') as f:
                f.write(f"Test content for file {i}\n" * 50)
            test_files.append(filename)
            self.file_queue.add_file(filename)
        
        # Upload all files from queue
        uploaded_count = 0
        while True:
            file_item = self.file_queue.get_next()
            if not file_item:
                break
            
            response = self.upload_client.upload_file(file_item['path'])
            if response["status"] == "success":
                uploaded_count += 1
        
        self.assertEqual(uploaded_count, 3, "All 3 files should be uploaded successfully")
        
        # Cleanup
        for filename in test_files:
            if os.path.exists(filename):
                os.remove(filename)
            uploaded_path = os.path.join("uploads", filename)
            if os.path.exists(uploaded_path):
                os.remove(uploaded_path)
        
        print(f"[TEST] ✓ Uploaded {uploaded_count} files from queue successfully")
    
    def test_upload_multiple_files_with_progress(self):
        """Test upload nhiều file cùng lúc với progress tracking"""
        print("\n[TEST] Running test_upload_multiple_files_with_progress...")
        
        # Tạo nhiều file test với kích thước khác nhau
        test_files = []
        for i in range(5):
            filename = f"multi_test_{i}.txt"
            with open(filename, "w", encoding='utf-8') as f:
                # Tạo file với kích thước khác nhau
                f.write(f"Content for file {i}\n" * (100 * (i + 1)))
            test_files.append(filename)
            self.file_queue.add_file(filename)
        
        print(f"  Created {len(test_files)} test files")
        
        # Tracking progress cho từng file
        upload_results = []
        progress_tracking = {}
        
        def track_progress(file_path, progress, speed, status):
            filename = os.path.basename(file_path)
            if filename not in progress_tracking:
                progress_tracking[filename] = []
            progress_tracking[filename].append({
                'progress': progress,
                'speed': speed,
                'status': status
            })
            print(f"    [{filename}] {progress}% - {speed:.2f} MB/s - {status}")
        
        def track_status(file_path, status, message):
            filename = os.path.basename(file_path)
            print(f"    [{filename}] {status}: {message}")
        
        def on_complete(file_path, result):
            filename = os.path.basename(file_path)
            upload_results.append({
                'filename': filename,
                'result': result
            })
            if result['status'] == 'success':
                print(f"    ✓ [{filename}] Upload hoàn thành!")
            else:
                print(f"    ✗ [{filename}] Lỗi: {result['message']}")
        
        # Upload tất cả file từ queue với progress tracking
        print(f"\n  Bắt đầu upload {len(test_files)} files...\n")
        
        results = self.upload_client.upload_from_queue(
            self.file_queue,
            progress_callback=track_progress,
            status_callback=track_status,
            complete_callback=on_complete
        )
        
        # Kiểm tra kết quả
        self.assertEqual(len(results), len(test_files), 
                        f"Should upload all {len(test_files)} files")
        
        success_count = sum(1 for r in results if r['result']['status'] == 'success')
        self.assertEqual(success_count, len(test_files), 
                        "All files should upload successfully")
        
        # Kiểm tra progress tracking
        for filename in test_files:
            base_name = os.path.basename(filename)
            self.assertIn(base_name, progress_tracking, 
                         f"Progress should be tracked for {base_name}")
            self.assertGreater(len(progress_tracking[base_name]), 0,
                             f"Should have progress updates for {base_name}")
        
        # Tổng kết
        print(f"\n  KẾT QUẢ:")
        print(f"    - Tổng số file: {len(results)}")
        print(f"    - Thành công: {success_count}")
        print(f"    - Thất bại: {len(results) - success_count}")
        
        for filename in test_files:
            base_name = os.path.basename(filename)
            if base_name in progress_tracking:
                updates = len(progress_tracking[base_name])
                print(f"    - {base_name}: {updates} progress updates")
        
        # Cleanup
        for filename in test_files:
            if os.path.exists(filename):
                os.remove(filename)
            uploaded_path = os.path.join("uploads", filename)
            if os.path.exists(uploaded_path):
                os.remove(uploaded_path)
        
        print(f"[TEST] ✓ Successfully uploaded {len(test_files)} files with progress tracking")

if __name__ == '__main__':
    print("="*60)
    print("MEMBER 3 - UPLOAD CLIENT & SERVER TESTS")
    print("Testing integration with Member 2 (FileQueue)")
    print("="*60)
    unittest.main(verbosity=2)
