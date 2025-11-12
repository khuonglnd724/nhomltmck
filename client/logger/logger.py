# client/logger/logger.py
import datetime
import os

class Logger:
    """Logger cho client"""

    def __init__(self, log_file=None):
        """
        log_file: đường dẫn lưu log, nếu None thì chỉ in console
        """
        self.log_file = log_file
        if self.log_file:
            # tạo thư mục nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log(self, message, level="INFO"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"{now} - {level} - {message}"
        print(log_msg)
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n")
            except Exception as e:
                print(f" Không ghi được log vào file: {e}")

    def info(self, message):
        self.log(message, "INFO")

    def error(self, message):
        self.log(message, "ERROR")

    def success(self, file_name, size):
        self.log(f"UPLOAD SUCCESS - {file_name} ({size} bytes)", "INFO")

    def failure(self, file_name, error):
        self.log(f"UPLOAD FAILED - {file_name} - ERROR: {error}", "ERROR")


# Tạo logger mặc định cho client
client_logger = Logger(log_file="client/logger/logs/client_upload.log")
