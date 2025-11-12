# logger.py
import datetime

class Logger:
    """Logger tạm thời - ghi log ra console"""

    def __init__(self, log_file=None):
        """
        log_file: nếu muốn lưu log vào file, cung cấp đường dẫn
        """
        self.log_file = log_file

    def log(self, message, level="INFO"):
        """
        message: chuỗi log
        level: INFO / WARNING / ERROR
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"{now} - {level} - {message}"
        print(log_msg)
        
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_msg + "\n")
            except Exception as e:
                print(f"⚠️ Không ghi được log vào file: {e}")
