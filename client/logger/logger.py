# client/logger/logger.py
import datetime
import os
import traceback

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

    def _format_size(self, size_bytes):
        """Chuyển đổi byte → KB, MB, GB cho dễ đọc"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def log(self, message, level="INFO"):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"{now} - {level} - {message}"
        print(log_msg)
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n")
            except Exception as e:
                print(f"Không ghi được log vào file: {e}")

    def info(self, message):
        self.log(message, "INFO")

    def error(self, message, detail=None):
        """Ghi lỗi + lỗi chi tiết nếu có"""
        if detail:
            detail_msg = f"{message} | DETAIL: {detail}"
        else:
            detail_msg = message
        self.log(detail_msg, "ERROR")

    def success(self, file_name, size, upload_time=None):
        """
        Ghi log thành công + kích thước + tốc độ upload nếu có
        upload_time: thời gian upload (giây)
        """
        size_str = self._format_size(size)

        if upload_time and upload_time > 0:
            speed = size / upload_time / 1024 / 1024     # MB/s
            speed_str = f"{speed:.2f} MB/s"
            msg = f"UPLOAD SUCCESS - {file_name} | Size: {size_str} | Speed: {speed_str}"
        else:
            msg = f"UPLOAD SUCCESS - {file_name} | Size: {size_str}"

        self.log(msg, "INFO")

    def failure(self, file_name, error):
        """Ghi log thất bại + chi tiết traceback"""
        error_detail = traceback.format_exc()
        self.log(
            f"UPLOAD FAILED - {file_name} - ERROR: {error} | TRACEBACK: {error_detail}",
            "ERROR"
        )


# Tạo logger mặc định cho client
client_logger = Logger(log_file="client/logger/logs/client_upload.log")
