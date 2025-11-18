import socket
import json
import time
import sys
import os

# Import shared config
try:
    from config import CONNECTION_TIMEOUT, CHUNK_SIZE
except ImportError:
    # Fallback nếu không tìm thấy config chung
    CONNECTION_TIMEOUT = 60
    CHUNK_SIZE = 8192

class ServerConnection:
    def __init__(self, host='localhost', port=9999, timeout=CONNECTION_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.max_buffer = CHUNK_SIZE

    def connect(self):
        """Establish connection to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            self.socket = None
            raise ConnectionError(f"Failed to connect to server: {str(e)}")

    def send_data(self, data):
        """Send data with length prefix"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif isinstance(data, dict):
            data = json.dumps(data).encode('utf-8')

        # Send length prefix
        length = len(data)
        self.socket.send(length.to_bytes(8, byteorder='big'))
        
        # Send actual data
        total_sent = 0
        while total_sent < length:
            sent = self.socket.send(data[total_sent:])
            if sent == 0:
                raise ConnectionError("Connection broken")
            total_sent += sent

    def receive_response(self):
        """Receive server response"""
        try:
            data = self.socket.recv(self.max_buffer)
            return data
        except socket.timeout:
            raise TimeoutError("Server response timeout")

    def close(self):
        """Close the connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            finally:
                self.socket = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
