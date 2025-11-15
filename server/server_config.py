"""Server configuration

Edit these values to change server behavior without environment variables.
This file is imported by both the TCP server and the combined runner.
"""

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

# Upload handling
UPLOAD_DIR = 'server/uploads'
BUFFER_SIZE = 4096

# Logging
LOG_DIR = 'server/logs'
LOG_FILE = f"{LOG_DIR}/upload.log"

# Compatibility aliases expected by server.server
SERVER_HOST = HOST
SERVER_PORT = PORT
MAX_FILE_SIZE_MB = 100
ENABLE_LOGGING = False
CONNECTION_TIMEOUT = 60
