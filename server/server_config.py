"""Server configuration

Edit these values to change server behavior without environment variables.
This file is imported by both the TCP server and the combined runner.
"""

# Import shared config cho timeout và max file size
try:
    from config import CONNECTION_TIMEOUT, MAX_FILE_SIZE_MB, BUFFER_SIZE
except ImportError:
    # Fallback nếu không tìm thấy config chung
    CONNECTION_TIMEOUT = 60
    MAX_FILE_SIZE_MB = 100
    BUFFER_SIZE = 4096

# Core TCP server settings
HOST = '127.0.0.1'
PORT = 9999
MAX_CONNECTIONS = 5

# HTTP API (FastAPI / uvicorn)
HTTP_HOST = '127.0.0.1'
HTTP_PORT = 8000

# UDP discovery/heartbeat
ENABLE_UDP = True
UDP_PORT = 9998

# Multicast monitoring (Week 7: Multicast & Broadcast)
ENABLE_MULTICAST = True
MULTICAST_GROUP = '239.0.0.1'  # Multicast IP range: 239.0.0.0 - 239.255.255.255
MULTICAST_PORT = 5555
MULTICAST_INTERVAL = 3.0  # Seconds between stat broadcasts
MULTICAST_TTL = 2  # Time-to-live: 1=same subnet, 2=same site, >2=wider network

# Upload handling
UPLOAD_DIR = 'uploads'
# BUFFER_SIZE được import từ config.py

# Logging
LOG_DIR = 'server/logs'
LOG_FILE = f"{LOG_DIR}/upload.log"

# Compatibility aliases expected by server.server
SERVER_HOST = HOST
SERVER_PORT = PORT
# MAX_FILE_SIZE_MB và CONNECTION_TIMEOUT được import từ config.py
ENABLE_LOGGING = False
