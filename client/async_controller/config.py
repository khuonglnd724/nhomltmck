"""
Shared Configuration - Dùng chung cho cả Client và Server
Đảm bảo đồng bộ giữa client và server về timeout và max file size
"""

# ===========================
# CONNECTION SETTINGS
# ===========================
# Connection timeout - áp dụng cho cả client và server
# Client sẽ timeout sau thời gian này khi kết nối/upload
# Server sẽ timeout khi đợi dữ liệu từ client
CONNECTION_TIMEOUT = 60  # seconds

# ===========================
# FILE UPLOAD LIMITS
# ===========================
# Max file size - áp dụng cho cả client và server
# Client sẽ từ chối file lớn hơn giới hạn này
# Server sẽ từ chối file lớn hơn giới hạn này
MAX_FILE_SIZE_MB = 100  # MB

# ===========================
# NETWORK SETTINGS
# ===========================
# Chunk/Buffer size cho upload streaming
CHUNK_SIZE = 8192  # bytes (8KB per chunk)
BUFFER_SIZE = 4096  # bytes (cho server socket recv)
