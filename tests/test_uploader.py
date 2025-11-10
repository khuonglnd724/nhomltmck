import unittest
import os
import threading
import time
from client.uploader.upload_client import UploadClient
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

    def setUp(self):
        self.upload_client = UploadClient(port=9999)
        
        # Create a test file
        self.test_file = "test_upload.txt"
        with open(self.test_file, "w") as f:
            f.write("Test file content" * 1000)  # Create some content

    def tearDown(self):
        # Clean up test file
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        
        # Clean up uploaded file
        uploaded_file = os.path.join("uploads", self.test_file)
        if os.path.exists(uploaded_file):
            os.remove(uploaded_file)

    def test_successful_upload(self):
        def progress_callback(progress, speed):
            self.assertIsInstance(progress, int)
            self.assertIsInstance(speed, float)
            self.assertGreaterEqual(progress, 0)
            self.assertLessEqual(progress, 100)
            self.assertGreaterEqual(speed, 0)

        response = self.upload_client.upload_file(self.test_file, progress_callback)
        
        self.assertEqual(response["status"], "success")
        self.assertTrue(os.path.exists(os.path.join("uploads", self.test_file)))

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.upload_client.upload_file("nonexistent_file.txt")

if __name__ == '__main__':
    unittest.main()
