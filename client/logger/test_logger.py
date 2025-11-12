from logger import client_logger

client_logger.info("Test thông tin")
client_logger.error("Test lỗi")
client_logger.success("file_demo.txt", 1024)
client_logger.failure("file_demo.txt", "Connection error")
